# GHGs-WWTPs: Wastewater Treatment Plant Greenhouse Gas Emissions Meta-Analysis

污水处理厂温室气体排放元分析

## 项目简介

基于文献综述数据，系统分析不同核算方法（排放因子法、实测法、模型法）对污水处理厂温室气体（CO2、CH4、N2O）排放估算的影响，检验是否存在系统性偏差。

## 目录结构

```
GHGs-WWTPs/
├── README.md                           # 项目说明
├── data/
│   ├── 2222.xlsx                       # 原始数据（105篇文献）
│   └── methods_knowledge.json          # 分析方法知识库
├── scripts/
│   ├── basic_analysis.py               # 基础描述统计分析
│   ├── meta_analysis_v1.py             # 元分析v1（含混合法）
│   ├── meta_analysis_v2.py             # 元分析v2（剔除异常值）
│   └── dispersion_analysis.py          # 离散分析
├── output/
│   ├── meta_analysis_v2_report.md      # 元分析报告
│   └── dispersion_analysis_report.md   # 离散分析报告
└── figures/
    ├── boxplot_v2.png                  # 箱线图
    ├── forest_plot_v2.png              # 森林图
    ├── effect_size_v2.png              # 效应量图
    ├── dispersion_cv_v2.png            # CV对比图
    ├── dispersion_boxplot_v2.png       # 离散箱线图
    ├── variance_decomposition_v2.png   # 方差分解图
    ├── skew_kurtosis_v2.png            # 偏度-峰度图
    ├── std_vs_mad_v2.png               # Std vs MAD图
    ├── region_method_v2.png            # 区域-方法分布
    └── scale_method_v2.png             # 规模-方法交互
```

## 分析内容

### 1. 基础分析 (`basic_analysis.py`)
- 描述性统计（均值、标准差、CV）
- 正态性检验（Shapiro-Wilk）
- Pearson相关性分析
- PCA主成分分析
- 按规模等级分组分析
- 研究区域分布

### 2. 元分析 (`meta_analysis_v2.py`)
- **研究问题**: 不同核算方法是否导致系统性偏差？
- **方法**: Kruskal-Wallis H检验 + Mann-Whitney U两两比较 + Bonferroni校正
- **效应量**: eta-squared + Cohen's d
- **异质性**: Cochran Q + I-squared

**核心结论**:
- CH4和N2O存在显著方法学偏差 (p<0.01)
- 排放因子法系统性偏高（CH4高估3.4倍，N2O高估4.1倍）
- CO2不受方法学影响
- 方法学仅解释9-17%的总变异

### 3. 离散分析 (`dispersion_analysis.py`)
- **研究问题**: 各方法内部的变异特征如何？
- **指标**: CV、MAD、IQR、Robust CV、偏度、峰度
- **检验**: Levene方差齐性检验 + Bartlett检验
- **方差分解**: 组间(Method) vs 组内(Within)

**核心结论**:
- 实测法CV最高但最真实（捕获真实工况变异）
- 排放因子法CV最低但可能失真（统一因子压缩变异）
- 方法学仅解释9-17%变异，83-91%来自其他因素
- 所有分布均右偏，建议使用中位数和IQR

## 依赖

```bash
pip install pandas numpy scipy matplotlib seaborn openpyxl
```

## 使用方法

```bash
# 基础分析
python scripts/basic_analysis.py

# 元分析
python scripts/meta_analysis_v2.py

# 离散分析
python scripts/dispersion_analysis.py
```

## 引用

如需引用本分析，请参考：
- 数据来源: WOS文献检索 (greenhouse gases, wastewater treatment plants)
- 分析方法: 非参数元分析 (Kruskal-Wallis + Mann-Whitney U + Cohen's d)
- 离散分析: CV/MAD/IQR + Levene检验 + 方差分解

## License

MIT
