"""
元分析 Meta-Analysis: 不同核算方法是否导致系统性偏差
基于污水处理厂温室气体排放文献数据
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

# ========== 1. 数据加载与清洗 ==========
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

# ========== 2. 方法学分类标准化 ==========
def classify_method(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if '实测' in s or '现场' in s or '通量' in s or '气相色谱' in s:
        return '实测法'
    elif '排放因子' in s or 'IPCC' in s or '排放因子法' in s:
        return '排放因子法'
    elif '模型' in s:
        return '模型法'
    elif '混' in s:
        return '混合法'
    else:
        return '其他'

data['核算方法'] = data['方法学_参考'].apply(classify_method)

# 也用第一列补充
for i, row in data.iterrows():
    if pd.isna(row['核算方法']):
        m1 = classify_method(row['方法学'])
        if not pd.isna(m1):
            data.at[i, '核算方法'] = m1

output_dir = r'C:\Users\21766\Desktop\analysis_output'
os.makedirs(output_dir, exist_ok=True)

print('='*70)
print('  元分析 Meta-Analysis: 核算方法对温室气体排放的影响')
print('='*70)

# ========== 3. 方法学分布 ==========
print('\n[1] 核算方法分类分布')
print('-'*50)
method_dist = data['核算方法'].value_counts(dropna=True)
print(method_dist.to_string())

for method in method_dist.index:
    group = data[data['核算方法'] == method]
    print(f'\n  {method} (n={len(group)}):')
    for gas in ['CO2', 'CH4', 'N2O']:
        vals = group[gas].dropna()
        if len(vals) > 0:
            print(f'    {gas}: n={len(vals)}, mean={vals.mean():.3f}, median={vals.median():.3f}, std={vals.std():.3f}')

# ========== 4. 各气体的分组统计 ==========
print('\n[2] 各气体按核算方法分组统计')
print('-'*50)

group_stats = {}
for gas in ['CO2', 'CH4', 'N2O']:
    print(f'\n  === {gas} ===')
    stats_rows = []
    for method in ['排放因子法', '实测法', '模型法', '混合法']:
        group = data[data['核算方法'] == method][gas].dropna()
        if len(group) >= 2:
            row = {
                '方法': method,
                'n': len(group),
                'mean': group.mean(),
                'median': group.median(),
                'std': group.std(),
                'se': group.std() / np.sqrt(len(group)),
                'ci_lower': group.mean() - 1.96 * group.std() / np.sqrt(len(group)),
                'ci_upper': group.mean() + 1.96 * group.std() / np.sqrt(len(group)),
                'cv': group.std() / group.mean() * 100 if group.mean() != 0 else 0,
            }
            stats_rows.append(row)
            print(f"    {method}: n={row['n']}, mean={row['mean']:.3f}, "
                  f"95%CI=[{row['ci_lower']:.3f}, {row['ci_upper']:.3f}], CV={row['cv']:.1f}%")
    group_stats[gas] = pd.DataFrame(stats_rows)

# ========== 5. 统计检验: 不同方法间是否存在系统性偏差 ==========
print('\n[3] 统计检验: 方法间系统性偏差')
print('-'*50)

test_results = {}
for gas in ['CO2', 'CH4', 'N2O']:
    print(f'\n  === {gas} ===')
    groups_for_test = []
    group_labels = []
    for method in ['排放因子法', '实测法', '模型法', '混合法']:
        vals = data[data['核算方法'] == method][gas].dropna().values
        if len(vals) >= 2:
            groups_for_test.append(vals)
            group_labels.append(method)

    if len(groups_for_test) >= 2:
        # Kruskal-Wallis H 检验 (非参数，适合非正态数据)
        H, p_kw = stats.kruskal(*groups_for_test)
        print(f'    Kruskal-Wallis H检验: H={H:.4f}, p={p_kw:.4f}')
        if p_kw < 0.05:
            print(f'    结论: 不同核算方法对{gas}存在显著差异 (p<0.05)')
        else:
            print(f'    结论: 不同核算方法对{gas}无显著差异 (p>=0.05)')

        # 效应量 (Eta-squared)
        all_vals = np.concatenate(groups_for_test)
        grand_mean = all_vals.mean()
        ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups_for_test)
        ss_total = sum((v - grand_mean)**2 for v in all_vals)
        eta_sq = ss_between / ss_total if ss_total > 0 else 0
        print(f'    效应量 eta-squared: {eta_sq:.4f}')
        if eta_sq < 0.01:
            effect_desc = '极小'
        elif eta_sq < 0.06:
            effect_desc = '小'
        elif eta_sq < 0.14:
            effect_desc = '中等'
        else:
            effect_desc = '大'
        print(f'    效应大小: {effect_desc}')

        # Mann-Whitney U 两两比较 (如果Kruskal-Wallis显著)
        if p_kw < 0.05 and len(groups_for_test) >= 2:
            print(f'\n    两两比较 (Mann-Whitney U, Bonferroni校正):')
            n_comparisons = len(groups_for_test) * (len(groups_for_test) - 1) // 2
            alpha_adj = 0.05 / n_comparisons
            for i in range(len(groups_for_test)):
                for j in range(i+1, len(groups_for_test)):
                    U, p_mw = stats.mannwhitneyu(groups_for_test[i], groups_for_test[j],
                                                  alternative='two-sided')
                    sig = '***' if p_mw < 0.001 else ('**' if p_mw < 0.01 else ('*' if p_mw < alpha_adj else 'n.s.'))
                    print(f'      {group_labels[i]} vs {group_labels[j]}: U={U:.1f}, p={p_mw:.4f} {sig}')

        test_results[gas] = {'H': H, 'p': p_kw, 'eta_sq': eta_sq}
    else:
        print(f'    数据不足，跳过检验')
        test_results[gas] = None

# ========== 6. 异质性分析 (I-squared) ==========
print('\n[4] 组内异质性分析')
print('-'*50)

for gas in ['CO2', 'CH4', 'N2O']:
    print(f'\n  === {gas} ===')
    for method in ['排放因子法', '实测法', '模型法', '混合法']:
        group = data[data['核算方法'] == method][gas].dropna()
        if len(group) >= 3:
            # Q统计量 (Cochran's Q)
            weights = 1 / (group.std()**2 / len(group))
            weighted_mean = (weights * group).sum() / weights.sum()
            Q = (weights * (group - weighted_mean)**2).sum()
            df_q = len(group) - 1
            p_het = 1 - stats.chi2.cdf(Q, df_q)
            I2 = max(0, (Q - df_q) / Q * 100) if Q > 0 else 0
            print(f'    {method}: Q={Q:.2f}, df={df_q}, p={p_het:.4f}, I2={I2:.1f}%')

# ========== 7. 图表: 森林图 (Forest Plot) ==========
print('\n[5] 生成森林图...')

fig, axes = plt.subplots(1, 3, figsize=(16, 8))
gas_names = {'CO2': 'CO2', 'CH4': 'CH4', 'N2O': 'N2O'}

for idx, gas in enumerate(['CO2', 'CH4', 'N2O']):
    ax = axes[idx]
    gs = group_stats.get(gas)
    if gs is None or len(gs) == 0:
        ax.text(0.5, 0.5, 'Insufficient data', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(gas)
        continue

    y_positions = range(len(gs))
    colors = ['#E15759', '#4E79A7', '#F28E2B', '#76B7B2']

    for i, (_, row) in enumerate(gs.iterrows()):
        color = colors[i % len(colors)]
        # 均值点
        ax.plot(row['mean'], i, 'o', color=color, markersize=10, zorder=5)
        # 95% CI 线
        ax.plot([row['ci_lower'], row['ci_upper']], [i, i], '-', color=color, linewidth=2, zorder=4)
        # CI端点
        ax.plot(row['ci_lower'], i, '|', color=color, markersize=10, linewidth=2)
        ax.plot(row['ci_upper'], i, '|', color=color, markersize=10, linewidth=2)
        # 标注
        ax.text(row['ci_upper'] + (gs['ci_upper'].max() - gs['ci_lower'].min()) * 0.02, i,
                f"n={row['n']}, mean={row['mean']:.2f}",
                va='center', fontsize=8)

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(gs['方法'].tolist(), fontsize=10)
    ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.set_xlabel(f'{gas} (ton CO2eq/10k m3)', fontsize=10)
    ax.set_title(f'{gas} by Methodology', fontsize=12)
    ax.invert_yaxis()

    # 添加统计检验结果
    tr = test_results.get(gas)
    if tr:
        p_text = 'p={:.4f}'.format(tr['p'])
        sig = '*' if tr['p'] < 0.05 else 'n.s.'
        ax.text(0.02, 0.98, f"KW H-test: {p_text} {sig}\neta2={tr['eta_sq']:.3f}",
               transform=ax.transAxes, va='top', fontsize=8,
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'forest_plot.png'), dpi=300, bbox_inches='tight')
plt.close()
print('  森林图已保存')

# ========== 8. 图表: 箱线图比较 ==========
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
methods_order = ['排放因子法', '实测法', '模型法', '混合法']
colors_box = ['#E15759', '#4E79A7', '#F28E2B', '#76B7B2']

for idx, gas in enumerate(['CO2', 'CH4', 'N2O']):
    ax = axes[idx]
    box_data = []
    box_labels = []
    for method in methods_order:
        vals = data[data['核算方法'] == method][gas].dropna()
        if len(vals) >= 2:
            box_data.append(vals.values)
            box_labels.append(method)

    if box_data:
        bp = ax.boxplot(box_data, vert=True, patch_artist=True, labels=box_labels)
        for i, patch in enumerate(bp['boxes']):
            patch.set_facecolor(colors_box[i % len(colors_box)])
            patch.set_alpha(0.7)

        # 添加散点
        for i, d in enumerate(box_data):
            x = np.random.normal(i + 1, 0.04, size=len(d))
            ax.scatter(x, d, alpha=0.4, s=15, color='black', zorder=5)

    ax.set_title(f'{gas}', fontsize=12)
    ax.set_ylabel('ton CO2eq/10k m3')

    # 添加p值
    tr = test_results.get(gas)
    if tr:
        sig = '***' if tr['p'] < 0.001 else ('**' if tr['p'] < 0.01 else ('*' if tr['p'] < 0.05 else 'n.s.'))
        ax.text(0.5, 0.95, f"p={tr['p']:.4f} {sig}", transform=ax.transAxes,
               ha='center', va='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.suptitle('GHG Emissions by Accounting Methodology', fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'method_comparison_boxplot.png'), dpi=300, bbox_inches='tight')
plt.close()
print('  方法比较箱线图已保存')

# ========== 9. 图表: 标准化效应量比较 ==========
fig, ax = plt.subplots(figsize=(10, 6))
gas_list = ['CO2', 'CH4', 'N2O']
methods_with_data = []
for method in methods_order:
    has_data = any(len(data[data['核算方法'] == method][gas].dropna()) >= 2 for gas in gas_list)
    if has_data:
        methods_with_data.append(method)

# 计算Cohen's d (以排放因子法为基准)
baseline = '排放因子法'
x_pos = np.arange(len(gas_list))
bar_width = 0.2
colors_eff = ['#E15759', '#4E79A7', '#F28E2B', '#76B7B2']

for m_idx, method in enumerate(methods_with_data):
    if method == baseline:
        continue
    cohens_d = []
    for gas in gas_list:
        g1 = data[data['核算方法'] == baseline][gas].dropna()
        g2 = data[data['核算方法'] == method][gas].dropna()
        if len(g1) >= 2 and len(g2) >= 2:
            pooled_std = np.sqrt(((len(g1)-1)*g1.std()**2 + (len(g2)-1)*g2.std()**2) / (len(g1)+len(g2)-2))
            d = (g2.mean() - g1.mean()) / pooled_std if pooled_std > 0 else 0
            cohens_d.append(d)
        else:
            cohens_d.append(0)

    offset = (m_idx - 0.5) * bar_width
    bars = ax.bar(x_pos + offset, cohens_d, bar_width,
                  label=f'{method} vs {baseline}',
                  color=colors_eff[m_idx], alpha=0.7, edgecolor='black', linewidth=0.5)

ax.set_xticks(x_pos)
ax.set_xticklabels(gas_list, fontsize=11)
ax.set_ylabel("Cohen's d (standardized mean difference)", fontsize=10)
ax.set_title('Effect Size: Methodology Differences (Baseline = Emission Factor Method)', fontsize=12)
ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
ax.axhline(y=0.2, color='green', linestyle=':', linewidth=0.5, alpha=0.5)
ax.axhline(y=0.5, color='orange', linestyle=':', linewidth=0.5, alpha=0.5)
ax.axhline(y=0.8, color='red', linestyle=':', linewidth=0.5, alpha=0.5)
ax.text(len(gas_list)-0.5, 0.2, 'Small', fontsize=7, color='green', ha='right')
ax.text(len(gas_list)-0.5, 0.5, 'Medium', fontsize=7, color='orange', ha='right')
ax.text(len(gas_list)-0.5, 0.8, 'Large', fontsize=7, color='red', ha='right')
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'effect_size.png'), dpi=300, bbox_inches='tight')
plt.close()
print('  效应量图已保存')

# ========== 10. 规模等级与方法学交叉分析 ==========
print('\n[6] 规模等级 x 核算方法 交叉分析')
print('-'*50)

cross_results = {}
for gas in ['CH4', 'N2O']:
    print(f'\n  === {gas} ===')
    for level in ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ']:
        level_data = data[data['规模等级'] == level]
        if len(level_data) < 3:
            continue
        print(f'    规模{level}:')
        for method in ['排放因子法', '实测法']:
            vals = level_data[level_data['核算方法'] == method][gas].dropna()
            if len(vals) >= 1:
                print(f'      {method}: n={len(vals)}, mean={vals.mean():.3f}, median={vals.median():.3f}')

# ========== 11. 综合报告 ==========
report = """# Meta-Analysis Report: Impact of Accounting Methodology on WWTP GHG Emissions
# 元分析报告: 核算方法对污水处理厂温室气体排放的影响

## 1. 研究设计
- **研究类型**: 文献元分析 (Meta-analysis)
- **数据来源**: {total}篇文献
- **主要变量**: 核算方法学 (排放因子法/实测法/模型法/混合法)
- **结果变量**: CO2, CH4, N2O 排放量 (吨CO2eq/万立方米污水)

## 2. 核算方法分类

| 核算方法 | 文献数量 | 占比 |
|----------|----------|------|
| 排放因子法 | {ef_n} | {ef_pct:.1f}% |
| 实测法 | {dm_n} | {dm_pct:.1f}% |
| 模型法 | {mod_n} | {mod_pct:.1f}% |
| 混合法 | {mix_n} | {mix_pct:.1f}% |

## 3. 分组统计

### CH4排放
{ch4_table}

### N2O排放
{n2o_table}

### CO2排放
{co2_table}

## 4. 统计检验结果

### Kruskal-Wallis H检验 (非参数方差分析)
{kw_table}

### 关键发现
{findings}

## 5. 异质性分析
{het_table}

## 6. 效应量分析 (Cohen's d)
以排放因子法为基准，比较其他方法的标准化均值差异:
{effect_table}

- |d| < 0.2: 无实际差异
- 0.2 <= |d| < 0.5: 小效应
- 0.5 <= |d| < 0.8: 中等效应
- |d| >= 0.8: 大效应

## 7. 结论

{conclusions}

## 8. 局限性
1. 部分方法学分组样本量较小，统计检验力有限
2. 文献异质性高，不同研究的边界条件差异大
3. 排放因子法和实测法的定义在不同文献中可能有差异
4. 未考虑发表偏倚的影响

---
Generated: 2026-06-09
Methodology: Non-parametric meta-analysis (Kruskal-Wallis + Mann-Whitney U + Cohen's d)
"""

# 填充报告
total = len(data)
ef_n = len(data[data['核算方法'] == '排放因子法'])
dm_n = len(data[data['核算方法'] == '实测法'])
mod_n = len(data[data['核算方法'] == '模型法'])
mix_n = len(data[data['核算方法'] == '混合法'])

# CH4表
ch4_rows = []
for method in methods_order:
    g = data[data['核算方法'] == method]['CH4'].dropna()
    if len(g) >= 2:
        ch4_rows.append(f"| {method} | {len(g)} | {g.mean():.3f} | {g.median():.3f} | {g.std():.3f} | {g.std()/np.sqrt(len(g)):.3f} |")
ch4_table = "| Method | n | Mean | Median | SD | SE |\n|--------|---|------|--------|-----|-----|\n" + '\n'.join(ch4_rows)

# N2O表
n2o_rows = []
for method in methods_order:
    g = data[data['核算方法'] == method]['N2O'].dropna()
    if len(g) >= 2:
        n2o_rows.append(f"| {method} | {len(g)} | {g.mean():.3f} | {g.median():.3f} | {g.std():.3f} | {g.std()/np.sqrt(len(g)):.3f} |")
n2o_table = "| Method | n | Mean | Median | SD | SE |\n|--------|---|------|--------|-----|-----|\n" + '\n'.join(n2o_rows)

# CO2表
co2_rows = []
for method in methods_order:
    g = data[data['核算方法'] == method]['CO2'].dropna()
    if len(g) >= 2:
        co2_rows.append(f"| {method} | {len(g)} | {g.mean():.3f} | {g.median():.3f} | {g.std():.3f} | {g.std()/np.sqrt(len(g)):.3f} |")
co2_table = "| Method | n | Mean | Median | SD | SE |\n|--------|---|------|--------|-----|-----|\n" + '\n'.join(co2_rows) if co2_rows else "No sufficient data"

# KW表
kw_rows = []
for gas in ['CO2', 'CH4', 'N2O']:
    tr = test_results.get(gas)
    if tr:
        sig = 'Yes (p<0.05)' if tr['p'] < 0.05 else 'No (p>=0.05)'
        kw_rows.append(f"| {gas} | {tr['H']:.4f} | {tr['p']:.4f} | {tr['eta_sq']:.4f} | {sig} |")
kw_table = "| Gas | H-statistic | p-value | Eta-squared | Significant? |\n|-----|-------------|---------|-------------|-------------|\n" + '\n'.join(kw_rows)

# 发现
findings_list = []
for gas in ['CO2', 'CH4', 'N2O']:
    tr = test_results.get(gas)
    if tr:
        if tr['p'] < 0.05:
            findings_list.append(f"- **{gas}**: Different methodologies show SIGNIFICANT differences (H={tr['p']:.4f}, p={tr['p']:.4f}, eta2={tr['eta_sq']:.4f})")
        else:
            findings_list.append(f"- **{gas}**: No significant difference between methodologies (p={tr['p']:.4f})")
findings = '\n'.join(findings_list)

# 异质性表
het_rows = []
for gas in ['CO2', 'CH4', 'N2O']:
    for method in methods_order:
        g = data[data['核算方法'] == method][gas].dropna()
        if len(g) >= 3:
            weights = 1 / (g.std()**2 / len(g))
            wm = (weights * g).sum() / weights.sum()
            Q = (weights * (g - wm)**2).sum()
            df_q = len(g) - 1
            I2 = max(0, (Q - df_q) / Q * 100) if Q > 0 else 0
            het_rows.append(f"| {gas} | {method} | {len(g)} | {Q:.2f} | {df_q} | {I2:.1f}% |")
het_table = "| Gas | Method | n | Q | df | I2 |\n|-----|--------|---|---|----|----|\n" + '\n'.join(het_rows) if het_rows else "Insufficient data"

# 效应量表
effect_rows = []
for gas in gas_list:
    g1 = data[data['核算方法'] == baseline][gas].dropna()
    for method in methods_with_data:
        if method == baseline:
            continue
        g2 = data[data['核算方法'] == method][gas].dropna()
        if len(g1) >= 2 and len(g2) >= 2:
            pooled_std = np.sqrt(((len(g1)-1)*g1.std()**2 + (len(g2)-1)*g2.std()**2) / (len(g1)+len(g2)-2))
            d = (g2.mean() - g1.mean()) / pooled_std if pooled_std > 0 else 0
            mag = 'Large' if abs(d) >= 0.8 else ('Medium' if abs(d) >= 0.5 else ('Small' if abs(d) >= 0.2 else 'Negligible'))
            effect_rows.append(f"| {gas} | {method} vs {baseline} | {d:.3f} | {mag} |")
effect_table = "| Gas | Comparison | Cohen's d | Magnitude |\n|-----|-----------|-----------|-----------|\n" + '\n'.join(effect_rows) if effect_rows else "Insufficient data"

# 结论
conclusion_lines = []
for gas in ['CO2', 'CH4', 'N2O']:
    tr = test_results.get(gas)
    if tr:
        if tr['p'] < 0.05:
            conclusion_lines.append(f"1. **{gas}**: Accounting methodology causes systematic bias (p={tr['p']:.4f}, effect size eta2={tr['eta_sq']:.4f})")
        else:
            conclusion_lines.append(f"1. **{gas}**: No evidence of systematic bias from methodology (p={tr['p']:.4f})")

# 补充总结
any_sig = any(test_results.get(g, {}).get('p', 1) < 0.05 for g in ['CO2', 'CH4', 'N2O'])
if any_sig:
    conclusion_lines.append("\n**Overall conclusion**: There IS evidence that different accounting methodologies lead to systematic differences in reported GHG emissions. Researchers should account for methodology when comparing emissions across studies.")
else:
    conclusion_lines.append("\n**Overall conclusion**: No strong evidence that accounting methodology alone causes systematic bias. Other factors (process type, scale, climate) may be more important drivers of emission variability.")

conclusions = '\n'.join(conclusion_lines)

report_filled = report.format(
    total=total,
    ef_n=ef_n, ef_pct=ef_n/total*100,
    dm_n=dm_n, dm_pct=dm_n/total*100,
    mod_n=mod_n, mod_pct=mod_n/total*100,
    mix_n=mix_n, mix_pct=mix_n/total*100,
    ch4_table=ch4_table,
    n2o_table=n2o_table,
    co2_table=co2_table,
    kw_table=kw_table,
    findings=findings,
    het_table=het_table,
    effect_table=effect_table,
    conclusions=conclusions,
)

report_path = os.path.join(output_dir, 'meta_analysis_report.md')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_filled)

print(f'\n[完成] 元分析报告已保存: {report_path}')
print(f'输出目录: {output_dir}')
for f_name in sorted(os.listdir(output_dir)):
    print(f'  - {f_name}')
