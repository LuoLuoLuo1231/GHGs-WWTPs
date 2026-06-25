"""
元分析模块 v3 - 修正版

根据用户提供的分析逻辑和元分析理论重新设计：

1. 元分析的正确理解：
   - 传统元分析：需要对照组、均值、标准差、样本量
   - 单组元分析：单个指标值
   - 元回归：分析影响因素
   - 对于只有排放量数据：描述统计、非参数检验、Bootstrap、元回归

2. 分析逻辑（参考方法学差异分析.docx）：
   - 分布特征分析（箱线图、中位数比较）
   - 异常值检测和剔除
   - 正态性检验
   - 根据数据特征选择合适的统计方法
   - 效应量分析
   - 结论解释

3. 不是所有数据都要做全部分析：
   - 样本量太少的组不做对比
   - 不满足正态性假设的用非参数检验
   - 缺少对照组的不做传统元分析
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

warnings.filterwarnings('ignore')

# 统计分析
from scipy import stats
from scipy.stats import mannwhitneyu, kruskal, shapiro, kstest, levene, bartlett
from scipy.stats import spearmanr, pearsonr

# 可视化
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ============================================================
# 数据类型定义
# ============================================================

class AnalysisType(Enum):
    """分析类型"""
    DESCRIPTIVE = "描述统计"
    NORMALITY = "正态性检验"
    GROUP_COMPARISON = "组间比较"
    EFFECT_SIZE = "效应量分析"
    HETEROGENEITY = "异质性分析"
    META_REGRESSION = "元回归"
    BOOTSTRAP = "Bootstrap分析"


class DataCharacteristics(Enum):
    """数据特征"""
    NORMAL = "正态分布"
    NON_NORMAL = "非正态分布"
    SUFFICIENT_SAMPLE = "样本量充足"
    INSUFFICIENT_SAMPLE = "样本量不足"
    HAS_CONTROL = "有对照组"
    NO_CONTROL = "无对照组"


@dataclass
class OutlierInfo:
    """异常值信息"""
    index: int
    value: float
    method: str
    reason: str


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_type: AnalysisType
    test_name: str
    statistic: float
    p_value: float
    effect_size: Optional[float] = None
    effect_size_type: Optional[str] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    interpretation: str = ""
    is_significant: bool = False
    sample_sizes: Optional[Dict[str, int]] = None


@dataclass
class GroupAnalysisResult:
    """分组分析结果"""
    group_name: str
    n_samples: int
    median: float
    mean: float
    std: float
    q25: float
    q75: float
    cv: float
    is_normal: bool
    outlier_count: int
    data_characteristics: List[DataCharacteristics] = field(default_factory=list)


# ============================================================
# 异常值检测器
# ============================================================

class OutlierDetector:
    """异常值检测器"""

    @staticmethod
    def detect_iqr(data: np.ndarray, multiplier: float = 1.5) -> List[OutlierInfo]:
        """
        IQR方法检测异常值

        Parameters:
        -----------
        data : array-like
            数据
        multiplier : float
            IQR倍数，默认1.5

        Returns:
        --------
        List[OutlierInfo]
            异常值列表
        """
        outliers = []
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        for i, val in enumerate(data):
            if val < lower_bound or val > upper_bound:
                outliers.append(OutlierInfo(
                    index=i,
                    value=val,
                    method="IQR",
                    reason=f"值 {val:.2f} 超出范围 [{lower_bound:.2f}, {upper_bound:.2f}]"
                ))

        return outliers

    @staticmethod
    def detect_zscore(data: np.ndarray, threshold: float = 3.0) -> List[OutlierInfo]:
        """
        Z-score方法检测异常值

        Parameters:
        -----------
        data : array-like
            数据
        threshold : float
            Z-score阈值，默认3.0

        Returns:
        --------
        List[OutlierInfo]
            异常值列表
        """
        outliers = []
        mean = np.mean(data)
        std = np.std(data)

        if std == 0:
            return outliers

        for i, val in enumerate(data):
            zscore = abs((val - mean) / std)
            if zscore > threshold:
                outliers.append(OutlierInfo(
                    index=i,
                    value=val,
                    method="Z-score",
                    reason=f"Z-score = {zscore:.2f} > {threshold}"
                ))

        return outliers

    @staticmethod
    def detect_modified_zscore(data: np.ndarray, threshold: float = 3.5) -> List[OutlierInfo]:
        """
        修正Z-score方法（基于中位数和MAD）

        Parameters:
        -----------
        data : array-like
            数据
        threshold : float
            阈值，默认3.5

        Returns:
        --------
        List[OutlierInfo]
            异常值列表
        """
        outliers = []
        median = np.median(data)
        mad = np.median(np.abs(data - median))

        if mad == 0:
            return outliers

        for i, val in enumerate(data):
            modified_zscore = 0.6745 * (val - median) / mad
            if abs(modified_zscore) > threshold:
                outliers.append(OutlierInfo(
                    index=i,
                    value=val,
                    method="Modified Z-score",
                    reason=f"Modified Z-score = {modified_zscore:.2f} > {threshold}"
                ))

        return outliers

    @staticmethod
    def detect_all(data: np.ndarray) -> Tuple[List[OutlierInfo], List[OutlierInfo]]:
        """
        使用多种方法检测异常值

        Returns:
        --------
        Tuple[List[OutlierInfo], List[OutlierInfo]]
            (确认的异常值, 可能的异常值)
        """
        iqr_outliers = OutlierDetector.detect_iqr(data, multiplier=1.5)
        zscore_outliers = OutlierDetector.detect_zscore(data, threshold=3.0)
        modified_zscore_outliers = OutlierDetector.detect_modified_zscore(data, threshold=3.5)

        # 统计每个点被多少种方法判定为异常
        outlier_counts = {}
        for outlier in iqr_outliers + zscore_outliers + modified_zscore_outliers:
            idx = outlier.index
            if idx not in outlier_counts:
                outlier_counts[idx] = {'count': 0, 'methods': [], 'value': outlier.value}
            outlier_counts[idx]['count'] += 1
            outlier_counts[idx]['methods'].append(outlier.method)

        # 被2种以上方法确认的为确认异常值
        confirmed = []
        possible = []
        for idx, info in outlier_counts.items():
            outlier_info = OutlierInfo(
                index=idx,
                value=info['value'],
                method=', '.join(info['methods']),
                reason=f"被 {info['count']} 种方法判定为异常"
            )
            if info['count'] >= 2:
                confirmed.append(outlier_info)
            else:
                possible.append(outlier_info)

        return confirmed, possible


# ============================================================
# 数据特征分析器
# ============================================================

class DataProfiler:
    """数据特征分析器"""

    @staticmethod
    def analyze_group(data: np.ndarray, group_name: str) -> GroupAnalysisResult:
        """
        分析单个组的数据特征

        Parameters:
        -----------
        data : array-like
            数据
        group_name : str
            组名

        Returns:
        --------
        GroupAnalysisResult
            分析结果
        """
        # 基本统计
        n = len(data)
        mean = np.mean(data)
        std = np.std(data, ddof=1) if n > 1 else 0
        median = np.median(data)
        q25 = np.percentile(data, 25)
        q75 = np.percentile(data, 75)
        cv = (std / mean * 100) if mean != 0 else 0

        # 正态性检验
        is_normal = False
        if n >= 3:
            if n <= 5000:
                _, p_shapiro = shapiro(data)
                is_normal = p_shapiro > 0.05
            else:
                _, p_ks = kstest(data, 'norm', args=(mean, std))
                is_normal = p_ks > 0.05

        # 异常值检测
        confirmed_outliers, possible_outliers = OutlierDetector.detect_all(data)

        # 数据特征
        characteristics = []
        if is_normal:
            characteristics.append(DataCharacteristics.NORMAL)
        else:
            characteristics.append(DataCharacteristics.NON_NORMAL)

        if n >= 30:
            characteristics.append(DataCharacteristics.SUFFICIENT_SAMPLE)
        else:
            characteristics.append(DataCharacteristics.INSUFFICIENT_SAMPLE)

        return GroupAnalysisResult(
            group_name=group_name,
            n_samples=n,
            median=median,
            mean=mean,
            std=std,
            q25=q25,
            q75=q75,
            cv=cv,
            is_normal=is_normal,
            outlier_count=len(confirmed_outliers),
            data_characteristics=characteristics
        )


# ============================================================
# 统计检验器
# ============================================================

class StatisticalTester:
    """统计检验器"""

    @staticmethod
    def compare_groups(data_dict: Dict[str, np.ndarray],
                       alpha: float = 0.05) -> List[AnalysisResult]:
        """
        比较多组数据

        Parameters:
        -----------
        data_dict : Dict[str, np.ndarray]
            {组名: 数据}
        alpha : float
            显著性水平

        Returns:
        --------
        List[AnalysisResult]
            分析结果列表
        """
        results = []

        # 过滤样本量太小的组
        valid_groups = {k: v for k, v in data_dict.items() if len(v) >= 3}

        if len(valid_groups) < 2:
            results.append(AnalysisResult(
                analysis_type=AnalysisType.GROUP_COMPARISON,
                test_name="组间比较",
                statistic=0,
                p_value=1.0,
                interpretation="有效组数不足，无法进行组间比较"
            ))
            return results

        # 检查是否所有组都正态分布
        all_normal = all(
            DataProfiler.analyze_group(v, k).is_normal
            for k, v in valid_groups.items()
        )

        # 根据数据特征选择检验方法
        if all_normal and len(valid_groups) == 2:
            # 正态分布 + 两组 -> 独立t检验
            groups = list(valid_groups.keys())
            t_stat, p_value = stats.ttest_ind(valid_groups[groups[0]], valid_groups[groups[1]])

            # Cohen's d
            n1, n2 = len(valid_groups[groups[0]]), len(valid_groups[groups[1]])
            pooled_std = np.sqrt(((n1-1)*np.var(valid_groups[groups[0]], ddof=1) +
                                  (n2-1)*np.var(valid_groups[groups[1]], ddof=1)) / (n1+n2-2))
            cohens_d = abs(np.mean(valid_groups[groups[0]]) - np.mean(valid_groups[groups[1]])) / pooled_std if pooled_std > 0 else 0

            results.append(AnalysisResult(
                analysis_type=AnalysisType.GROUP_COMPARISON,
                test_name="独立t检验",
                statistic=t_stat,
                p_value=p_value,
                effect_size=cohens_d,
                effect_size_type="Cohen's d",
                is_significant=p_value < alpha,
                interpretation=f"t = {t_stat:.3f}, p = {p_value:.3f}, Cohen's d = {cohens_d:.3f}"
            ))

        elif all_normal and len(valid_groups) > 2:
            # 正态分布 + 多组 -> 单因素ANOVA
            groups = list(valid_groups.keys())
            f_stat, p_value = stats.f_oneway(*[valid_groups[g] for g in groups])

            # eta-squared
            all_data = np.concatenate([valid_groups[g] for g in groups])
            grand_mean = np.mean(all_data)
            ss_between = sum(len(valid_groups[g]) * (np.mean(valid_groups[g]) - grand_mean)**2 for g in groups)
            ss_total = np.sum((all_data - grand_mean)**2)
            eta_squared = ss_between / ss_total if ss_total > 0 else 0

            results.append(AnalysisResult(
                analysis_type=AnalysisType.GROUP_COMPARISON,
                test_name="单因素ANOVA",
                statistic=f_stat,
                p_value=p_value,
                effect_size=eta_squared,
                effect_size_type="η²",
                is_significant=p_value < alpha,
                interpretation=f"F = {f_stat:.3f}, p = {p_value:.3f}, η² = {eta_squared:.3f}"
            ))

        else:
            # 非正态分布 -> Kruskal-Wallis
            groups = list(valid_groups.keys())
            h_stat, p_value = kruskal(*[valid_groups[g] for g in groups])

            # epsilon-squared (Kruskal-Wallis的效应量)
            n_total = sum(len(valid_groups[g]) for g in groups)
            k = len(groups)
            epsilon_squared = (h_stat - k + 1) / (n_total - k) if (n_total - k) > 0 else 0

            results.append(AnalysisResult(
                analysis_type=AnalysisType.GROUP_COMPARISON,
                test_name="Kruskal-Wallis H检验",
                statistic=h_stat,
                p_value=p_value,
                effect_size=epsilon_squared,
                effect_size_type="ε²",
                is_significant=p_value < alpha,
                interpretation=f"H = {h_stat:.3f}, p = {p_value:.3f}, ε² = {epsilon_squared:.3f}"
            ))

            # 如果显著，进行事后比较
            if p_value < alpha and len(valid_groups) > 2:
                results.extend(StatisticalTester._post_hoc_tests(valid_groups, alpha))

        return results

    @staticmethod
    def _post_hoc_tests(data_dict: Dict[str, np.ndarray],
                        alpha: float) -> List[AnalysisResult]:
        """
        事后比较（Dunn检验或Mann-Whitney U + Bonferroni校正）
        """
        results = []
        groups = list(data_dict.keys())
        n_comparisons = len(groups) * (len(groups) - 1) / 2
        bonferroni_alpha = alpha / n_comparisons

        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                g1, g2 = groups[i], groups[j]
                u_stat, p_value = mannwhitneyu(data_dict[g1], data_dict[g2],
                                               alternative='two-sided')

                # 效应量 r = Z / sqrt(N)
                n1, n2 = len(data_dict[g1]), len(data_dict[g2])
                z = stats.norm.ppf(1 - p_value/2) if p_value > 0 else 0
                r = z / np.sqrt(n1 + n2) if (n1 + n2) > 0 else 0

                results.append(AnalysisResult(
                    analysis_type=AnalysisType.GROUP_COMPARISON,
                    test_name=f"Mann-Whitney U ({g1} vs {g2})",
                    statistic=u_stat,
                    p_value=p_value,
                    effect_size=r,
                    effect_size_type="r",
                    is_significant=p_value < bonferroni_alpha,
                    interpretation=f"U = {u_stat:.3f}, p = {p_value:.3f}, r = {r:.3f}" +
                                   (" *" if p_value < bonferroni_alpha else "")
                ))

        return results


# ============================================================
# 效应量计算器
# ============================================================

class EffectSizeCalculator:
    """效应量计算器"""

    @staticmethod
    def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
        """Cohen's d"""
        n1, n2 = len(group1), len(group2)
        pooled_std = np.sqrt(((n1-1)*np.var(group1, ddof=1) + (n2-1)*np.var(group2, ddof=1)) / (n1+n2-2))
        return abs(np.mean(group1) - np.mean(group2)) / pooled_std if pooled_std > 0 else 0

    @staticmethod
    def hedges_g(group1: np.ndarray, group2: np.ndarray) -> float:
        """Hedges' g（修正的Cohen's d）"""
        d = EffectSizeCalculator.cohens_d(group1, group2)
        n1, n2 = len(group1), len(group2)
        correction = 1 - 3 / (4 * (n1 + n2) - 9)
        return d * correction

    @staticmethod
    def eta_squared(groups: List[np.ndarray]) -> float:
        """η²（ANOVA效应量）"""
        all_data = np.concatenate(groups)
        grand_mean = np.mean(all_data)
        ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in groups)
        ss_total = np.sum((all_data - grand_mean)**2)
        return ss_between / ss_total if ss_total > 0 else 0

    @staticmethod
    def epsilon_squared(h_stat: float, n_total: int, k: int) -> float:
        """ε²（Kruskal-Wallis效应量）"""
        return (h_stat - k + 1) / (n_total - k) if (n_total - k) > 0 else 0

    @staticmethod
    def rank_biserial_correlation(u_stat: float, n1: int, n2: int) -> float:
        """秩二列相关系数（Mann-Whitney U的效应量）"""
        return 1 - (2 * u_stat) / (n1 * n2)


# ============================================================
# Bootstrap分析器
# ============================================================

class BootstrapAnalyzer:
    """Bootstrap置信区间分析"""

    @staticmethod
    def bootstrap_ci(data: np.ndarray, statistic_func=np.mean,
                     n_bootstrap: int = 10000, ci_level: float = 0.95,
                     random_state: int = 42) -> Tuple[float, float, float]:
        """
        计算Bootstrap置信区间

        Parameters:
        -----------
        data : array-like
            数据
        statistic_func : callable
            统计量函数
        n_bootstrap : int
            Bootstrap次数
        ci_level : float
            置信水平
        random_state : int
            随机种子

        Returns:
        --------
        Tuple[float, float, float]
            (统计量, CI下限, CI上限)
        """
        np.random.seed(random_state)

        stat = statistic_func(data)
        bootstrap_stats = []

        for _ in range(n_bootstrap):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_stats.append(statistic_func(sample))

        alpha = 1 - ci_level
        ci_lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
        ci_upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))

        return stat, ci_lower, ci_upper

    @staticmethod
    def bootstrap_difference_ci(group1: np.ndarray, group2: np.ndarray,
                                n_bootstrap: int = 10000, ci_level: float = 0.95,
                                random_state: int = 42) -> Tuple[float, float, float]:
        """
        计算两组差异的Bootstrap置信区间
        """
        np.random.seed(random_state)

        diff = np.mean(group1) - np.mean(group2)
        bootstrap_diffs = []

        for _ in range(n_bootstrap):
            sample1 = np.random.choice(group1, size=len(group1), replace=True)
            sample2 = np.random.choice(group2, size=len(group2), replace=True)
            bootstrap_diffs.append(np.mean(sample1) - np.mean(sample2))

        alpha = 1 - ci_level
        ci_lower = np.percentile(bootstrap_diffs, 100 * alpha / 2)
        ci_upper = np.percentile(bootstrap_diffs, 100 * (1 - alpha / 2))

        return diff, ci_lower, ci_upper


# ============================================================
# 元分析主类
# ============================================================

class MetaAnalyzer:
    """
    元分析器 - 修正版

    根据数据特征自动选择合适的分析方法：
    - 传统元分析：需要对照组、均值、标准差、样本量
    - 单组元分析：单个指标值
    - 元回归：分析影响因素
    - 描述统计 + 非参数检验：只有排放量数据
    """

    def __init__(self, data_path: str = None, df: pd.DataFrame = None):
        """
        初始化

        Parameters:
        -----------
        data_path : str
            数据文件路径（Excel或CSV）
        df : DataFrame
            直接传入DataFrame
        """
        if df is not None:
            self.df = df
        elif data_path:
            if data_path.endswith('.xlsx') or data_path.endswith('.xls'):
                self.df = pd.read_excel(data_path)
            elif data_path.endswith('.csv'):
                self.df = pd.read_csv(data_path)
            else:
                raise ValueError(f"不支持的文件格式: {data_path}")
        else:
            raise ValueError("必须提供 data_path 或 df")

        # 存储结果
        self.results = {}
        self.figures = []

    def run(self, group_col: str, value_col: str,
            exclude_groups: List[str] = None,
            exclude_outliers: bool = True,
            outlier_methods: str = 'auto') -> Dict:
        """
        运行元分析

        Parameters:
        -----------
        group_col : str
            分组列名（如"Method"、"核算方法"）
        value_col : str
            数值列名（如"CH4"、"排放强度"）
        exclude_groups : List[str]
            要排除的组（如样本量太少的组）
        exclude_outliers : bool
            是否剔除异常值
        outlier_methods : str
            异常值检测方法（'auto', 'iqr', 'zscore'）

        Returns:
        --------
        Dict
            分析结果
        """
        print("=" * 60)
        print("  元分析开始")
        print("=" * 60)

        # 准备数据
        df_clean = self._prepare_data(group_col, value_col, exclude_groups)

        # 分组分析
        group_results = self._analyze_groups(df_clean, group_col, value_col)

        # 异常值处理
        if exclude_outliers:
            df_clean = self._handle_outliers(df_clean, group_col, value_col, group_results)

        # 组间比较
        comparison_results = self._compare_groups(df_clean, group_col, value_col)

        # Bootstrap分析
        bootstrap_results = self._bootstrap_analysis(df_clean, group_col, value_col)

        # 汇总结果
        self.results = {
            'group_analysis': group_results,
            'comparison_results': comparison_results,
            'bootstrap_results': bootstrap_results,
            'data_summary': {
                'total_samples': len(df_clean),
                'n_groups': df_clean[group_col].nunique(),
                'groups': df_clean[group_col].unique().tolist()
            }
        }

        print("\n" + "=" * 60)
        print("  元分析完成")
        print("=" * 60)

        return self.results

    def _prepare_data(self, group_col: str, value_col: str,
                      exclude_groups: List[str] = None) -> pd.DataFrame:
        """准备数据"""
        df = self.df[[group_col, value_col]].copy()
        df = df.dropna()

        # 排除指定组
        if exclude_groups:
            df = df[~df[group_col].isin(exclude_groups)]
            print(f"  排除组: {exclude_groups}")

        # 转换为数值
        df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
        df = df.dropna()

        print(f"  有效数据: {len(df)} 条")
        print(f"  分组: {df[group_col].unique().tolist()}")

        return df

    def _analyze_groups(self, df: pd.DataFrame, group_col: str,
                        value_col: str) -> Dict[str, GroupAnalysisResult]:
        """分组分析"""
        print("\n  [1/4] 分组分析...")

        group_results = {}
        for group_name, group_data in df.groupby(group_col):
            data = group_data[value_col].values
            result = DataProfiler.analyze_group(data, group_name)
            group_results[group_name] = result

            print(f"    {group_name}: n={result.n_samples}, "
                  f"中位数={result.median:.2f}, "
                  f"CV={result.cv:.1f}%, "
                  f"正态={'是' if result.is_normal else '否'}, "
                  f"异常值={result.outlier_count}")

        return group_results

    def _handle_outliers(self, df: pd.DataFrame, group_col: str,
                         value_col: str, group_results: Dict) -> pd.DataFrame:
        """处理异常值"""
        print("\n  [2/4] 异常值处理...")

        df_clean = df.copy()
        total_removed = 0

        for group_name, group_data in df.groupby(group_col):
            data = group_data[value_col].values
            confirmed_outliers, possible_outliers = OutlierDetector.detect_all(data)

            if confirmed_outliers:
                print(f"    {group_name}: 发现 {len(confirmed_outliers)} 个确认异常值")
                for outlier in confirmed_outliers:
                    print(f"      - 索引 {outlier.index}, 值 {outlier.value:.2f}, 方法: {outlier.method}")

                    # 从DataFrame中移除
                    mask = (df_clean[group_col] == group_name) & (df_clean[value_col] == outlier.value)
                    df_clean = df_clean[~mask]
                    total_removed += 1

        print(f"  共剔除 {total_removed} 个异常值")

        return df_clean

    def _compare_groups(self, df: pd.DataFrame, group_col: str,
                        value_col: str) -> List[AnalysisResult]:
        """组间比较"""
        print("\n  [3/4] 组间比较...")

        # 准备数据字典
        data_dict = {}
        for group_name, group_data in df.groupby(group_col):
            data_dict[group_name] = group_data[value_col].values

        # 运行统计检验
        results = StatisticalTester.compare_groups(data_dict)

        # 打印结果
        for result in results:
            sig = "*" if result.is_significant else ""
            print(f"    {result.test_name}: {result.interpretation} {sig}")

        return results

    def _bootstrap_analysis(self, df: pd.DataFrame, group_col: str,
                            value_col: str) -> Dict:
        """Bootstrap分析"""
        print("\n  [4/4] Bootstrap分析...")

        bootstrap_results = {}

        # 每组的Bootstrap置信区间
        for group_name, group_data in df.groupby(group_col):
            data = group_data[value_col].values
            if len(data) >= 5:
                mean, ci_lower, ci_upper = BootstrapAnalyzer.bootstrap_ci(data)
                bootstrap_results[group_name] = {
                    'mean': mean,
                    'ci_lower': ci_lower,
                    'ci_upper': ci_upper,
                    'n': len(data)
                }
                print(f"    {group_name}: 均值={mean:.2f}, 95%CI=[{ci_lower:.2f}, {ci_upper:.2f}]")

        return bootstrap_results

    def generate_report(self, output_path: str = None) -> str:
        """生成分析报告"""
        if not self.results:
            raise ValueError("请先运行 run() 方法")

        report_lines = []
        report_lines.append("# 元分析报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 数据概览
        summary = self.results['data_summary']
        report_lines.append(f"\n## 数据概览")
        report_lines.append(f"- 总样本量: {summary['total_samples']}")
        report_lines.append(f"- 分组数: {summary['n_groups']}")
        report_lines.append(f"- 分组: {', '.join(summary['groups'])}")

        # 分组分析
        report_lines.append(f"\n## 分组分析")
        report_lines.append("| 组名 | 样本量 | 中位数 | 均值 | 标准差 | CV | 正态性 | 异常值 |")
        report_lines.append("|------|--------|--------|------|--------|-----|--------|--------|")

        for group_name, result in self.results['group_analysis'].items():
            report_lines.append(
                f"| {group_name} | {result.n_samples} | {result.median:.2f} | "
                f"{result.mean:.2f} | {result.std:.2f} | {result.cv:.1f}% | "
                f"{'是' if result.is_normal else '否'} | {result.outlier_count} |"
            )

        # 组间比较
        report_lines.append(f"\n## 组间比较")
        for result in self.results['comparison_results']:
            sig = "显著" if result.is_significant else "不显著"
            report_lines.append(f"\n### {result.test_name}")
            report_lines.append(f"- 统计量: {result.statistic:.3f}")
            report_lines.append(f"- p值: {result.p_value:.3f}")
            if result.effect_size is not None:
                report_lines.append(f"- 效应量 ({result.effect_size_type}): {result.effect_size:.3f}")
            report_lines.append(f"- 结论: {sig}")

        # Bootstrap分析
        if self.results['bootstrap_results']:
            report_lines.append(f"\n## Bootstrap置信区间")
            report_lines.append("| 组名 | 均值 | 95% CI下限 | 95% CI上限 |")
            report_lines.append("|------|------|------------|------------|")

            for group_name, result in self.results['bootstrap_results'].items():
                report_lines.append(
                    f"| {group_name} | {result['mean']:.2f} | "
                    f"{result['ci_lower']:.2f} | {result['ci_upper']:.2f} |"
                )

        report_text = "\n".join(report_lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n  报告已保存: {output_path}")

        return report_text


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    # 示例用法
    print("元分析模块 v3 - 使用示例")
    print()
    print("from meta_analysis_module_v3 import MetaAnalyzer")
    print()
    print("# 加载数据")
    print("analyzer = MetaAnalyzer('data.xlsx')")
    print()
    print("# 运行分析")
    print("results = analyzer.run(")
    print("    group_col='Method',      # 分组列")
    print("    value_col='CH4',         # 数值列")
    print("    exclude_groups=['混合法'],  # 排除样本量太少的组")
    print("    exclude_outliers=True     # 剔除异常值")
    print(")")
    print()
    print("# 生成报告")
    print("analyzer.generate_report('output/meta_report.md')")
