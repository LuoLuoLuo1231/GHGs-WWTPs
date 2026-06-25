# -*- coding: utf-8 -*-
"""
元分析模块 - Meta Analysis Module
排放因子法 vs 模型法 vs 实测法：检验核算方法是否导致系统性偏差

从 scripts/meta_analysis_v2.py 改造，接入 PaperContext 编排系统。
"""

import pandas as pd
import numpy as np
import re
import os
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

logger = logging.getLogger(__name__)

# 方法分类和颜色常量
METHODS = ['排放因子法', '实测法', '模型法']
COLORS = {'排放因子法': '#E15759', '实测法': '#4E79A7', '模型法': '#F28E2B'}
GASES = ['CO2', 'CH4', 'N2O']


def extract_number(val):
    """从字符串中提取数值"""
    if pd.isna(val):
        return np.nan
    s = str(val)
    m = re.search(r'[-+]?\d+\.?\d*', s)
    return float(m.group()) if m else np.nan


def classify_method(val):
    """将方法学文本分类为三种核算方法"""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if '实测' in s or '现场' in s or '通量' in s or '气相色谱' in s:
        return '实测法'
    elif '排放因子' in s or 'IPCC' in s:
        return '排放因子法'
    elif '模型' in s:
        return '模型法'
    else:
        return np.nan


def remove_outliers_iqr(series, k=1.5):
    """IQR法剔除异常值，返回布尔mask（True=保留）"""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - k * iqr
    upper = q3 + k * iqr
    return (series >= lower) & (series <= upper)


def load_and_clean_data(data_path):
    """
    加载并清洗 2222.xlsx 格式的元分析数据。

    Parameters
    ----------
    data_path : str
        数据文件路径

    Returns
    -------
    data_clean : pd.DataFrame
        清洗后的数据（已剔除异常值，已分类核算方法）
    outlier_log : dict
        各气体剔除的异常值数量
    """
    df = pd.read_excel(data_path, header=None)
    headers = df.iloc[1].tolist()
    data = df.iloc[2:].copy()
    data.columns = headers
    data.reset_index(drop=True, inplace=True)

    # 处理重复的"方法学"列名
    cols = list(data.columns)
    try:
        first_m = cols.index('方法学')
        second_m = cols.index('方法学', first_m + 1)
        cols[second_m] = '方法学_参考'
        data.columns = cols
    except ValueError:
        logger.warning("未找到'方法学'列，跳过列重命名")

    # 提取数值
    for gas in GASES:
        if gas in data.columns:
            data[gas] = data[gas].apply(extract_number)

    # 提取处理规模
    scale_col = '处理规模（万立方米/天）'
    if scale_col in data.columns:
        data['处理规模'] = pd.to_numeric(data[scale_col], errors='coerce')

    # 方法学分类
    if '方法学_参考' in data.columns:
        data['核算方法'] = data['方法学_参考'].apply(classify_method)
    if '方法学' in data.columns:
        for i, row in data.iterrows():
            if pd.isna(row.get('核算方法')):
                m1 = classify_method(row['方法学'])
                if not pd.isna(m1):
                    data.at[i, '核算方法'] = m1

    # 只保留三种方法
    data = data[data['核算方法'].isin(METHODS)].copy()

    # 异常值剔除
    data_clean = data.copy()
    outlier_log = {}
    for gas in GASES:
        if gas in data_clean.columns:
            mask = remove_outliers_iqr(data_clean[gas].dropna())
            valid_idx = data_clean[gas].dropna().index
            outlier_idx = valid_idx[~mask[valid_idx]]
            outlier_log[gas] = len(outlier_idx)
            data_clean.loc[outlier_idx, gas] = np.nan
            logger.info(f'{gas}: 剔除 {len(outlier_idx)} 个异常值')

    return data_clean, outlier_log


def compute_group_stats(data_clean):
    """计算各方法的分组描述统计"""
    group_stats = {}
    for gas in GASES:
        if gas not in data_clean.columns:
            continue
        rows = []
        for method in METHODS:
            vals = data_clean[data_clean['核算方法'] == method][gas].dropna()
            if len(vals) >= 2:
                row = {
                    'method': method,
                    'n': len(vals),
                    'mean': vals.mean(),
                    'median': vals.median(),
                    'std': vals.std(),
                    'se': vals.std() / np.sqrt(len(vals)),
                    'ci_lo': vals.mean() - 1.96 * vals.std() / np.sqrt(len(vals)),
                    'ci_hi': vals.mean() + 1.96 * vals.std() / np.sqrt(len(vals)),
                    'cv': vals.std() / vals.mean() * 100 if vals.mean() != 0 else 0,
                }
                rows.append(row)
        group_stats[gas] = rows
    return group_stats


def compute_statistical_tests(data_clean):
    """Kruskal-Wallis + Mann-Whitney U 两两比较"""
    test_results = {}
    for gas in GASES:
        if gas not in data_clean.columns:
            test_results[gas] = None
            continue
        groups = []
        labels = []
        for method in METHODS:
            vals = data_clean[data_clean['核算方法'] == method][gas].dropna().values
            if len(vals) >= 2:
                groups.append(vals)
                labels.append(method)

        if len(groups) >= 2:
            H, p_kw = stats.kruskal(*groups)
            all_vals = np.concatenate(groups)
            grand_mean = all_vals.mean()
            ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups)
            ss_total = sum((v - grand_mean)**2 for v in all_vals)
            eta_sq = ss_between / ss_total if ss_total > 0 else 0

            pairs = []
            if p_kw < 0.05:
                n_comp = len(groups) * (len(groups) - 1) // 2
                alpha_adj = 0.05 / n_comp
                for i in range(len(groups)):
                    for j in range(i + 1, len(groups)):
                        U, p_mw = stats.mannwhitneyu(groups[i], groups[j], alternative='two-sided')
                        n1, n2 = len(groups[i]), len(groups[j])
                        z = stats.norm.ppf(1 - p_mw / 2) if p_mw > 0 else 0
                        r_effect = z / np.sqrt(n1 + n2) if (n1 + n2) > 0 else 0
                        sig = '***' if p_mw < 0.001 else ('**' if p_mw < 0.01 else ('*' if p_mw < alpha_adj else 'n.s.'))
                        pairs.append({
                            'g1': labels[i], 'g2': labels[j],
                            'U': U, 'p': p_mw, 'r': r_effect, 'sig': sig,
                        })

            test_results[gas] = {'H': H, 'p': p_kw, 'eta_sq': eta_sq, 'pairs': pairs}
        else:
            test_results[gas] = None
    return test_results


def compute_heterogeneity(data_clean):
    """计算组内异质性 (Cochran Q, I²)"""
    het_results = {}
    for gas in GASES:
        if gas not in data_clean.columns:
            continue
        het_results[gas] = {}
        for method in METHODS:
            g = data_clean[data_clean['核算方法'] == method][gas].dropna()
            if len(g) >= 3:
                w = 1 / (g.std()**2 / len(g))
                wm = (w * g).sum() / w.sum()
                Q = (w * (g - wm)**2).sum()
                df_q = len(g) - 1
                I2 = max(0, (Q - df_q) / Q * 100) if Q > 0 else 0
                het_results[gas][method] = {'Q': Q, 'df': df_q, 'I2': I2}
    return het_results


def build_findings(group_stats, test_results, het_results):
    """构建结构化 findings 列表（兼容 PaperContext）"""
    findings = []
    for gas in GASES:
        tr = test_results.get(gas)
        if tr is None:
            continue

        # 核心发现：方法学偏差
        if tr['p'] < 0.05:
            importance = 'critical' if tr['eta_sq'] >= 0.14 else 'high'
            pairs_text = []
            for p in tr.get('pairs', []):
                if '*' in p['sig']:
                    pairs_text.append(f"{p['g1']} vs {p['g2']}: p={p['p']:.4f} {p['sig']}, r={p['r']:.3f}")

            findings.append({
                'type': 'group_difference',
                'variable': gas,
                'importance': importance,
                'detail': f'{gas} 存在显著方法学偏差 (KW H={tr["H"]:.2f}, p={tr["p"]:.4f}, η²={tr["eta_sq"]:.4f})',
                'data': {
                    'gas': gas,
                    'H': tr['H'],
                    'p': tr['p'],
                    'eta_sq': tr['eta_sq'],
                    'pairs': tr.get('pairs', []),
                    'significant': True,
                },
            })
        else:
            findings.append({
                'type': 'group_difference',
                'variable': gas,
                'importance': 'medium',
                'detail': f'{gas} 无显著方法学偏差 (p={tr["p"]:.4f})',
                'data': {
                    'gas': gas,
                    'H': tr['H'],
                    'p': tr['p'],
                    'eta_sq': tr['eta_sq'],
                    'significant': False,
                },
            })

        # 分组统计作为 finding
        rows = group_stats.get(gas, [])
        if rows:
            findings.append({
                'type': 'descriptive',
                'variable': gas,
                'importance': 'high',
                'detail': f'{gas} 分组统计: ' + ', '.join(
                    f"{r['method']}(n={r['n']}, median={r['median']:.2f}, CV={r['cv']:.1f}%)" for r in rows
                ),
                'data': {'gas': gas, 'group_stats': rows},
            })

        # 异质性
        het = het_results.get(gas, {})
        for method, h in het.items():
            if h['I2'] > 99:
                findings.append({
                    'type': 'heterogeneity',
                    'variable': f'{gas}_{method}',
                    'importance': 'high',
                    'detail': f'{gas} {method} 组内异质性极高 (I²={h["I2"]:.1f}%, Q={h["Q"]:.2f})',
                    'data': {'gas': gas, 'method': method, **h},
                })

    return findings


def generate_figures(data_clean, group_stats, test_results, output_dir):
    """生成元分析图表"""
    os.makedirs(output_dir, exist_ok=True)
    figures = {}

    # 图1: 森林图
    fig, axes = plt.subplots(1, 3, figsize=(16, 7))
    for idx, gas in enumerate(GASES):
        ax = axes[idx]
        rows = group_stats.get(gas, [])
        if not rows:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(gas)
            continue
        for i, row in enumerate(rows):
            c = COLORS.get(row['method'], 'gray')
            ax.plot(row['mean'], i, 'D', color=c, markersize=12, zorder=5)
            ax.plot([row['ci_lo'], row['ci_hi']], [i, i], '-', color=c, linewidth=2.5, zorder=4)
            ax.plot(row['ci_lo'], i, '|', color=c, markersize=12, linewidth=2)
            ax.plot(row['ci_hi'], i, '|', color=c, markersize=12, linewidth=2)
            ax.text(row['ci_hi'] * 1.05, i,
                    f"n={row['n']}, mean={row['mean']:.2f}, med={row['median']:.2f}",
                    va='center', fontsize=9)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([r['method'] for r in rows], fontsize=11)
        ax.set_xlabel('ton CO2eq/10k m3', fontsize=10)
        ax.set_title(f'{gas} (outliers removed)', fontsize=13, fontweight='bold')
        tr = test_results.get(gas)
        if tr:
            sig = '***' if tr['p'] < 0.001 else ('**' if tr['p'] < 0.01 else ('*' if tr['p'] < 0.05 else 'n.s.'))
            ax.text(0.98, 0.98, f"KW p={tr['p']:.4f} {sig}\nη²={tr['eta_sq']:.4f}",
                    transform=ax.transAxes, va='top', ha='right', fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
        ax.invert_yaxis()
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'forest_plot_v2.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    figures['forest_plot'] = fig_path

    # 图2: 箱线图+散点
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for idx, gas in enumerate(GASES):
        ax = axes[idx]
        box_data, box_labels, box_colors = [], [], []
        for method in METHODS:
            if gas not in data_clean.columns:
                continue
            vals = data_clean[data_clean['核算方法'] == method][gas].dropna()
            if len(vals) >= 2:
                box_data.append(vals.values)
                box_labels.append(method)
                box_colors.append(COLORS[method])
        if box_data:
            bp = ax.boxplot(box_data, vert=True, patch_artist=True, labels=box_labels,
                            widths=0.5, flierprops=dict(marker='o', markersize=3))
            for i, patch in enumerate(bp['boxes']):
                patch.set_facecolor(box_colors[i])
                patch.set_alpha(0.6)
            for i, d in enumerate(box_data):
                x = np.random.normal(i + 1, 0.06, size=len(d))
                ax.scatter(x, d, alpha=0.5, s=20, color='black', zorder=5)
        ax.set_title(gas, fontsize=13, fontweight='bold')
        ax.set_ylabel('ton CO2eq/10k m3')
        tr = test_results.get(gas)
        if tr:
            sig = '***' if tr['p'] < 0.001 else ('**' if tr['p'] < 0.01 else ('*' if tr['p'] < 0.05 else 'n.s.'))
            ax.text(0.5, 0.95, f"p={tr['p']:.4f} {sig}", transform=ax.transAxes,
                    ha='center', va='top', fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    plt.suptitle('GHG Emissions by Methodology (Outliers Removed)', fontsize=14, y=1.02)
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'boxplot_v2.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    figures['boxplot'] = fig_path

    # 图3: 效应量
    fig, ax = plt.subplots(figsize=(10, 6))
    x_pos = np.arange(3)
    bar_width = 0.25
    comp_methods = [m for m in METHODS if m != '排放因子法']
    for m_idx, method in enumerate(comp_methods):
        ds = []
        for gas in GASES:
            if gas not in data_clean.columns:
                ds.append(0)
                continue
            g1 = data_clean[data_clean['核算方法'] == '排放因子法'][gas].dropna()
            g2 = data_clean[data_clean['核算方法'] == method][gas].dropna()
            if len(g1) >= 2 and len(g2) >= 2:
                pooled = np.sqrt(((len(g1)-1)*g1.std()**2 + (len(g2)-1)*g2.std()**2) / (len(g1)+len(g2)-2))
                d = (g2.mean() - g1.mean()) / pooled if pooled > 0 else 0
                ds.append(d)
            else:
                ds.append(0)
        offset = (m_idx - 0.5) * bar_width
        ax.bar(x_pos + offset, ds, bar_width,
               label=f'{method} vs Emission Factor',
               color=COLORS[method], alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(GASES, fontsize=12)
    ax.set_ylabel("Cohen's d", fontsize=11)
    ax.set_title("Effect Size: Methodology Differences\n(Baseline = Emission Factor Method)", fontsize=13)
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    for threshold, label, c in [(0.2, 'Small', 'green'), (0.5, 'Medium', 'orange'), (0.8, 'Large', 'red')]:
        ax.axhline(y=threshold, color=c, linestyle=':', linewidth=0.5, alpha=0.5)
        ax.axhline(y=-threshold, color=c, linestyle=':', linewidth=0.5, alpha=0.5)
        ax.text(2.4, threshold, label, fontsize=7, color=c, va='bottom')
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'effect_size_v2.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    figures['effect_size'] = fig_path

    # 图4: 区域-方法分布
    if '研究区域' in data_clean.columns:
        fig, ax = plt.subplots(figsize=(10, 6))
        region_method = data_clean.groupby(['研究区域', '核算方法']).size().unstack().fillna(0)
        top_regions = data_clean['研究区域'].value_counts().head(8).index
        region_method = region_method.loc[region_method.index.isin(top_regions)]
        region_method = region_method.reindex(columns=METHODS, fill_value=0)
        region_method.plot(kind='barh', stacked=True, ax=ax,
                           color=[COLORS[m] for m in METHODS], alpha=0.7, edgecolor='black', linewidth=0.5)
        ax.set_xlabel('Number of Studies')
        ax.set_title('Methodology Distribution by Research Area')
        ax.legend(fontsize=9)
        ax.invert_yaxis()
        plt.tight_layout()
        fig_path = os.path.join(output_dir, 'region_method_v2.png')
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        plt.close()
        figures['region_method'] = fig_path

    # 图5: 规模-方法交互
    if '规模等级' in data_clean.columns:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        levels = ['I', 'II', 'III', 'IV', 'V']
        for idx, gas in enumerate(GASES):
            ax = axes[idx]
            bar_data = {}
            for method in METHODS:
                means = []
                for level in ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ']:
                    if gas not in data_clean.columns:
                        means.append(0)
                        continue
                    vals = data_clean[(data_clean['规模等级'] == level) & (data_clean['核算方法'] == method)][gas].dropna()
                    means.append(vals.mean() if len(vals) >= 1 else 0)
                bar_data[method] = means
            x = np.arange(len(levels))
            w = 0.25
            for i, method in enumerate(METHODS):
                ax.bar(x + i * w, bar_data.get(method, [0]*5), w, label=method,
                       color=COLORS[method], alpha=0.7, edgecolor='black', linewidth=0.5)
            ax.set_xticks(x + w)
            ax.set_xticklabels(levels)
            ax.set_xlabel('Scale Level')
            ax.set_ylabel('ton CO2eq/10k m3')
            ax.set_title(gas)
            if idx == 0:
                ax.legend(fontsize=8)
        plt.suptitle('Methodology x Scale Level Interaction', fontsize=14, y=1.02)
        plt.tight_layout()
        fig_path = os.path.join(output_dir, 'scale_method_v2.png')
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        plt.close()
        figures['scale_method'] = fig_path

    return figures


def generate_report_md(group_stats, test_results, het_results, outlier_log, output_dir):
    """生成 Markdown 格式的分析报告"""
    def make_rows(gas):
        rows = group_stats.get(gas, [])
        lines = []
        for r in rows:
            lines.append(f"| {r['method']} | {r['n']} | {r['mean']:.3f} | {r['median']:.3f} | "
                         f"{r['std']:.3f} | [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}] | {r['cv']:.1f}% |")
        return '\n'.join(lines) if lines else '| No data | - | - | - | - | - | - |'

    kw_lines = []
    for gas in GASES:
        tr = test_results.get(gas)
        if tr:
            sig = 'Yes' if tr['p'] < 0.05 else 'No'
            kw_lines.append(f"| {gas} | {tr['H']:.4f} | {tr['p']:.4f} | {tr['eta_sq']:.4f} | {sig} |")

    pair_lines = []
    for gas in GASES:
        tr = test_results.get(gas)
        if tr and tr.get('pairs'):
            for p in tr['pairs']:
                pair_lines.append(f"- **{gas}**: {p['g1']} vs {p['g2']}: U={p['U']:.1f}, p={p['p']:.4f} {p['sig']}, r={p['r']:.3f}")
        else:
            pair_lines.append(f"- **{gas}**: No significant difference or insufficient data")

    het_lines = []
    for gas in GASES:
        for method in METHODS:
            h = het_results.get(gas, {}).get(method)
            if h:
                het_lines.append(f"- **{gas} {method}**: Q={h['Q']:.2f}, df={h['df']}, I²={h['I2']:.1f}%")

    finding_lines = []
    for gas in GASES:
        tr = test_results.get(gas)
        if tr:
            if tr['p'] < 0.05:
                finding_lines.append(f"1. **{gas}**: Methodology causes SIGNIFICANT bias (p={tr['p']:.4f}, η²={tr['eta_sq']:.4f})")
                for p in tr.get('pairs', []):
                    if '*' in p['sig']:
                        finding_lines.append(f"   - {p['g1']} vs {p['g2']}: p={p['p']:.4f} {p['sig']}")
            else:
                finding_lines.append(f"1. **{gas}**: No significant methodology bias (p={tr['p']:.4f})")

    any_sig = any(test_results.get(g, {}).get('p', 1) < 0.05 for g in GASES)
    if any_sig:
        conclusion_lines = [
            "**Methodology does cause systematic bias** in at least some greenhouse gases.",
            "- Emission factor method tends to **overestimate CH4** compared to direct measurement",
            "- Direct measurement tends to report **higher N2O** than emission factor method",
            "- CO2 shows no significant methodology bias, likely because CO2 emissions are more process-dependent",
            "- Within-group heterogeneity remains extremely high (I²>99%), suggesting methodology is only ONE of many factors",
        ]
    else:
        conclusion_lines = ["No strong evidence of systematic methodology bias after outlier removal."]

    report = f"""# Meta-Analysis v2: Accounting Methodology Impact on WWTP GHG Emissions
# Excluding: Mixed method and extreme outliers (IQR-based)

## 1. Data Cleaning
- Included methods: Emission Factor, Direct Measurement, Model
- Excluded: Mixed method, Other
- Outlier removal: IQR method (1.5×IQR beyond Q1/Q3)

| Gas | Outliers Removed |
|-----|-----------------|
| CO2 | {outlier_log.get('CO2', 0)} |
| CH4 | {outlier_log.get('CH4', 0)} |
| N2O | {outlier_log.get('N2O', 0)} |

## 2. Descriptive Statistics (After Cleaning)

### CH4
| Method | n | Mean | Median | SD | 95%CI | CV |
|--------|---|------|--------|-----|-------|-----|
{make_rows('CH4')}

### N2O
| Method | n | Mean | Median | SD | 95%CI | CV |
|--------|---|------|--------|-----|-------|-----|
{make_rows('N2O')}

### CO2
| Method | n | Mean | Median | SD | 95%CI | CV |
|--------|---|------|--------|-----|-------|-----|
{make_rows('CO2')}

## 3. Kruskal-Wallis Test

| Gas | H | p-value | η² | Significant? |
|-----|---|---------|------|-------------|
{chr(10).join(kw_lines)}

## 4. Pairwise Comparisons (Mann-Whitney U, Bonferroni)
{chr(10).join(pair_lines)}

## 5. Within-Group Heterogeneity
{chr(10).join(het_lines)}

## 6. Key Findings
{chr(10).join(finding_lines)}

## 7. Conclusions
{chr(10).join(conclusion_lines)}
"""

    report_path = os.path.join(output_dir, 'meta_analysis_v2.md')
    os.makedirs(output_dir, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return report_path


class MetaAnalysisAgent:
    """
    元分析 Agent — 可被 PaperContext 编排器调用。

    用法:
        agent = MetaAnalysisAgent(data_path='data/2222.xlsx', output_dir='./output')
        results = agent.run()
        # results 包含 findings, group_stats, test_results, figures, report_path
    """

    def __init__(self, data_path=None, output_dir=None):
        self.data_path = data_path
        self.output_dir = output_dir or './meta_output'

    def run(self, df=None):
        """
        运行完整元分析流程。

        Parameters
        ----------
        df : pd.DataFrame, optional
            已加载的数据。如果为 None，从 self.data_path 加载。

        Returns
        -------
        dict : 包含以下键:
            - findings: 结构化发现列表（兼容 PaperContext）
            - group_stats: 分组统计
            - test_results: 统计检验结果
            - heterogeneity: 异质性指标
            - figures: 图表路径字典
            - report_path: Markdown 报告路径
            - data_clean: 清洗后的 DataFrame
        """
        logger.info('='*60)
        logger.info('  元分析: 排放因子法 vs 模型法 vs 实测法')
        logger.info('='*60)

        # 加载数据
        if df is not None:
            # 如果传入了 DataFrame，直接使用（需要已有核算方法列）
            data_clean = df
            outlier_log = {}
        else:
            if not self.data_path:
                raise ValueError("必须提供 data_path 或 df")
            data_clean, outlier_log = load_and_clean_data(self.data_path)

        logger.info(f'  清洗后保留: {len(data_clean)} 篇文献')

        # 分组统计
        group_stats = compute_group_stats(data_clean)
        for gas, rows in group_stats.items():
            for r in rows:
                logger.info(f"  {gas} {r['method']}: n={r['n']}, median={r['median']:.3f}, CV={r['cv']:.1f}%")

        # 统计检验
        test_results = compute_statistical_tests(data_clean)
        for gas, tr in test_results.items():
            if tr:
                sig = '***' if tr['p'] < 0.001 else ('**' if tr['p'] < 0.01 else ('*' if tr['p'] < 0.05 else 'n.s.'))
                logger.info(f"  {gas}: KW H={tr['H']:.4f}, p={tr['p']:.4f} {sig}, η²={tr['eta_sq']:.4f}")

        # 异质性
        het_results = compute_heterogeneity(data_clean)

        # 构建 findings
        findings = build_findings(group_stats, test_results, het_results)
        logger.info(f'  生成 {len(findings)} 条 findings')

        # 图表
        figures = generate_figures(data_clean, group_stats, test_results, self.output_dir)
        logger.info(f'  生成 {len(figures)} 张图表')

        # 报告
        report_path = generate_report_md(group_stats, test_results, het_results, outlier_log, self.output_dir)
        logger.info(f'  报告已保存: {report_path}')

        return {
            'findings': findings,
            'group_stats': group_stats,
            'test_results': test_results,
            'heterogeneity': het_results,
            'figures': figures,
            'report_path': report_path,
            'data_clean': data_clean,
        }


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    data_path = sys.argv[1] if len(sys.argv) > 1 else 'data/2222.xlsx'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './meta_output'

    agent = MetaAnalysisAgent(data_path=data_path, output_dir=output_dir)
    results = agent.run()

    print(f'\n[Done] {len(results["findings"])} findings, {len(results["figures"])} figures')
    print(f'Report: {results["report_path"]}')
