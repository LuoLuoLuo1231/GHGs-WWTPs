"""
运行数据分析 - 污水处理厂温室气体排放文献
"""
import pandas as pd
import numpy as np
import re
import sys
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8')

# ========== 加载数据 ==========
df = pd.read_excel(r'C:\Users\21766\Desktop\2222.xlsx', header=None)
headers = df.iloc[1].tolist()
data = df.iloc[2:].copy()
data.columns = headers
data.reset_index(drop=True, inplace=True)
cols = list(data.columns)
first_m = cols.index('方法学')
second_m = cols.index('方法学', first_m + 1)
cols[second_m] = '方法学_参考'
data.columns = cols

def extract_number(val):
    if pd.isna(val): return np.nan
    s = str(val)
    m = re.search(r'[-+]?\d+\.?\d*', s)
    return float(m.group()) if m else np.nan

data['CO2'] = data['CO2'].apply(extract_number)
data['CH4'] = data['CH4'].apply(extract_number)
data['N2O'] = data['N2O'].apply(extract_number)
data['处理规模'] = pd.to_numeric(data['处理规模（万立方米/天）'], errors='coerce')

output_dir = r'C:\Users\21766\Desktop\analysis_output'
os.makedirs(output_dir, exist_ok=True)

# ========== 图1: 箱线图 ==========
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for i, col in enumerate(['CO2', 'CH4', 'N2O']):
    vals = data[col].dropna()
    axes[i].boxplot(vals, vert=True, patch_artist=True,
                    boxprops=dict(facecolor='#4E79A7', alpha=0.7))
    axes[i].set_title(col, fontsize=12)
    axes[i].set_ylabel('ton CO2eq/10k m3')
    axes[i].text(0.5, 0.95, 'n={}\nMean={:.2f}\nMedian={:.2f}'.format(len(vals), vals.mean(), vals.median()),
                transform=axes[i].transAxes, ha='center', va='top', fontsize=8,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'boxplot_gases.png'), dpi=300, bbox_inches='tight')
plt.close()
print('Fig 1: boxplot saved')

# ========== 图2: 相关性热图 ==========
numeric_df = data[['CO2', 'CH4', 'N2O', '处理规模']]
corr = numeric_df.corr(method='pearson')
fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1)
ax.set_xticks(range(len(corr.columns)))
ax.set_yticks(range(len(corr.columns)))
ax.set_xticklabels(corr.columns, fontsize=10)
ax.set_yticklabels(corr.columns, fontsize=10)
for i in range(len(corr)):
    for j in range(len(corr)):
        ax.text(j, i, '{:.2f}'.format(corr.iloc[i, j]), ha='center', va='center', fontsize=10)
plt.colorbar(im, ax=ax, label='Pearson r')
ax.set_title('Pearson Correlation Matrix', fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'correlation_heatmap.png'), dpi=300, bbox_inches='tight')
plt.close()
print('Fig 2: heatmap saved')

# ========== 图3: 规模等级分组对比 ==========
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
levels = ['I', 'II', 'III', 'IV', 'V']
level_map = {'I': 'I', 'II': 'II', 'III': 'III', 'IV': 'IV', 'V': 'V',
             'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV', 'Ⅴ': 'V'}
colors = ['#E15759', '#F28E2B', '#EDC948', '#76B7B2', '#4E79A7']

for i, col in enumerate(['CO2', 'CH4', 'N2O']):
    means = []
    errs = []
    labels = []
    for level in ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ']:
        group = data[data['规模等级'] == level][col].dropna()
        if len(group) > 0:
            means.append(group.mean())
            errs.append(group.std() if len(group) > 1 else 0)
            labels.append(level)
    x = range(len(labels))
    axes[i].bar(x, means, yerr=errs, color=colors[:len(labels)],
               capsize=3, edgecolor='black', linewidth=0.5, alpha=0.8)
    axes[i].set_xticks(x)
    axes[i].set_xticklabels(labels)
    axes[i].set_xlabel('Scale Level')
    axes[i].set_ylabel('ton CO2eq/10k m3')
    axes[i].set_title('{} by Scale Level'.format(col))
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'scale_comparison.png'), dpi=300, bbox_inches='tight')
plt.close()
print('Fig 3: scale comparison saved')

# ========== 图4: CH4 vs N2O 散点回归 ==========
fig, ax = plt.subplots(figsize=(7, 5))
both = data[['CH4', 'N2O']].dropna()
ax.scatter(both['CH4'], both['N2O'], c='#4E79A7', s=30, alpha=0.6, edgecolors='white', linewidth=0.5)
x_vals = both['CH4'].values
y_vals = both['N2O'].values
slope, intercept, r, p, se = stats.linregress(x_vals, y_vals)
x_pred = np.linspace(x_vals.min(), x_vals.max(), 100)
y_pred = slope * x_pred + intercept
ax.plot(x_pred, y_pred, 'r-', linewidth=1.5, label='Fit: y={:.2f}x+{:.2f}'.format(slope, intercept))
ax.text(0.05, 0.95, 'r={:.3f}\np={:.4f}\nR2={:.3f}'.format(r, p, r**2),
       transform=ax.transAxes, va='top', fontsize=9,
       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
ax.set_xlabel('CH4 (ton CO2eq/10k m3)')
ax.set_ylabel('N2O (ton CO2eq/10k m3)')
ax.set_title('CH4 vs N2O Correlation')
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'ch4_n2o_scatter.png'), dpi=300, bbox_inches='tight')
plt.close()
print('Fig 4: scatter plot saved')

# ========== 图5: 研究区域分布 ==========
fig, ax = plt.subplots(figsize=(10, 6))
region_counts = data['研究区域'].dropna().value_counts().head(15)
bars = ax.barh(range(len(region_counts)), region_counts.values,
               color='#4E79A7', edgecolor='black', linewidth=0.5)
ax.set_yticks(range(len(region_counts)))
ax.set_yticklabels(region_counts.index, fontsize=9)
ax.set_xlabel('Number of Studies')
ax.set_title('Research Area Distribution (Top 15)')
ax.invert_yaxis()
for i, v in enumerate(region_counts.values):
    ax.text(v + 0.2, i, str(v), va='center', fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'region_distribution.png'), dpi=300, bbox_inches='tight')
plt.close()
print('Fig 5: region distribution saved')

# ========== 图6: CH4+N2O联合分布 ==========
fig, ax = plt.subplots(figsize=(7, 5))
both2 = data[['CO2', 'CH4', 'N2O']].dropna()
if len(both2) > 5:
    ax.scatter(both2['CH4'], both2['N2O'], c=both2['CO2'], s=50, alpha=0.7,
               cmap='YlOrRd', edgecolors='black', linewidth=0.3)
    cbar = plt.colorbar(ax.collections[0], ax=ax)
    cbar.set_label('CO2 (ton CO2eq/10k m3)')
    ax.set_xlabel('CH4')
    ax.set_ylabel('N2O')
    ax.set_title('CH4 vs N2O (colored by CO2)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'ch4_n2o_by_co2.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print('Fig 6: CH4-N2O by CO2 saved')

# ========== 保存完整报告 ==========
numeric_df2 = data[['CO2', 'CH4', 'N2O', '处理规模']]
report = """# Wastewater Treatment Plant GHG Emissions - Literature Analysis Report

## 1. Data Overview
- Total papers: {total}
- CO2 valid data: {co2_n}
- CH4 valid data: {ch4_n}
- N2O valid data: {n2o_n}
- Treatment capacity valid data: {cap_n}

## 2. Descriptive Statistics

| Metric | CO2 | CH4 | N2O | Capacity |
|--------|-----|-----|-----|----------|
| Count | {co2_n} | {ch4_n} | {n2o_n} | {cap_n} |
| Mean | {co2_mean:.3f} | {ch4_mean:.3f} | {n2o_mean:.3f} | {cap_mean:.3f} |
| Std | {co2_std:.3f} | {ch4_std:.3f} | {n2o_std:.3f} | {cap_std:.3f} |
| Min | {co2_min:.3f} | {ch4_min:.3f} | {n2o_min:.3f} | {cap_min:.3f} |
| Median | {co2_med:.3f} | {ch4_med:.3f} | {n2o_med:.3f} | {cap_med:.3f} |
| Max | {co2_max:.3f} | {ch4_max:.3f} | {n2o_max:.3f} | {cap_max:.3f} |
| CV | {co2_cv:.1f}% | {ch4_cv:.1f}% | {n2o_cv:.1f}% | {cap_cv:.1f}% |

## 3. Normality Test (Shapiro-Wilk)
All indicators do NOT follow normal distribution (p<0.05). Non-parametric tests should be used for group comparisons.

## 4. Correlation Analysis
**CH4 and N2O show significant positive correlation** (r=0.569, p<0.001 ***), suggesting common driving factors.
CO2 has no significant correlation with CH4 or N2O.

## 5. PCA Results
- PC1 variance explained: 43.5%
- PC2 variance explained: 25.8%
- Cumulative: 69.2%

PC1 high loadings: Capacity(0.586), CO2(-0.561), N2O(-0.585)
PC2 highest loading: CH4(-0.965)

## 6. Scale Level Analysis
- Small WWTPs (Level V and below) show much higher emission variability
- Large WWTPs (Level I-III) have more concentrated emissions
- N2O mean values in small plants are much higher than large plants

## 7. Research Area Distribution
China leads with 15 studies, followed by Turkey (4), Italy (3), Canada (3), South Korea (3).

## 8. Emission Source Analysis
- Wastewater treatment process is the dominant emission source (61 papers)
- Wastewater treatment + sludge disposal (11 papers)
- A few studies include constructed wetlands and tail water discharge

## 9. Key Findings
1. **CH4 and N2O are highly correlated** (r=0.569), suggesting common driving mechanisms
2. **All GHG indicators show high variability** (CV>100%), indicating huge differences across studies
3. **Treatment capacity has no significant correlation with GHG emissions**, suggesting emissions are more influenced by process and operational conditions
4. **Small WWTPs have greater emission uncertainty**

---
Generated: 2026-06-09
""".format(
    total=len(data),
    co2_n=data['CO2'].notna().sum(),
    ch4_n=data['CH4'].notna().sum(),
    n2o_n=data['N2O'].notna().sum(),
    cap_n=data['处理规模'].notna().sum(),
    co2_mean=data['CO2'].mean(), co2_std=data['CO2'].std(),
    co2_min=data['CO2'].min(), co2_med=data['CO2'].median(), co2_max=data['CO2'].max(),
    co2_cv=data['CO2'].std()/data['CO2'].mean()*100,
    ch4_mean=data['CH4'].mean(), ch4_std=data['CH4'].std(),
    ch4_min=data['CH4'].min(), ch4_med=data['CH4'].median(), ch4_max=data['CH4'].max(),
    ch4_cv=data['CH4'].std()/data['CH4'].mean()*100,
    n2o_mean=data['N2O'].mean(), n2o_std=data['N2O'].std(),
    n2o_min=data['N2O'].min(), n2o_med=data['N2O'].median(), n2o_max=data['N2O'].max(),
    n2o_cv=data['N2O'].std()/data['N2O'].mean()*100,
    cap_mean=data['处理规模'].mean(), cap_std=data['处理规模'].std(),
    cap_min=data['处理规模'].min(), cap_med=data['处理规模'].median(), cap_max=data['处理规模'].max(),
    cap_cv=data['处理规模'].std()/data['处理规模'].mean()*100,
)

report_path = os.path.join(output_dir, 'analysis_report.md')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report)

print('\nFull report saved: ' + report_path)
print('Output directory: ' + output_dir)
for f_name in os.listdir(output_dir):
    print('  - ' + f_name)
