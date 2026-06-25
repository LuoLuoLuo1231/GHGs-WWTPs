# -*- coding: utf-8 -*-
"""
离散分析模块 - Dispersion Analysis Module
分析各核算方法内部的离散程度、变异来源、稳定性

从 scripts/dispersion_analysis.py 改造，接入 PaperContext 编排系统。
"""

import pandas as pd
import numpy as np
import os
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

logger = logging.getLogger(__name__)

# 复用元分析模块的数据加载和分类函数
from meta_analysis_module import (
    load_and_clean_data, METHODS, COLORS, GASES,
    extract_number, classify_method, remove_outliers_iqr,
)


def compute_dispersion_stats(data_clean):
    """计算各方法的基础离散指标"""
    dispersion_stats = {}
    for gas in GASES:
        if gas not in data_clean.columns:
            continue
        rows = []
        for method in METHODS:
            vals = data_clean[data_clean['核算方法'] == method][gas].dropna()
            if len(vals) >= 2:
                n = len(vals)
                mean = vals.mean()
                median = vals.median()
                std = vals.std()
                q1 = vals.quantile(0.25)
                q3 = vals.quantile(0.75)
                iqr = q3 - q1
                cv = std / mean * 100 if mean != 0 else 0
                mad = np.median(np.abs(vals - median))
                robust_cv = iqr / median * 100 if median != 0 else 0
                skew = vals.skew()
                kurt = vals.kurtosis()
                rows.append({
                    'method': method, 'n': n, 'mean': mean, 'median': median,
                    'std': std, 'iqr': iqr, 'cv': cv, 'mad': mad,
                    'robust_cv': robust_cv, 'skew': skew, 'kurtosis': kurt,
                    'range': vals.max() - vals.min(),
                    'q1': q1, 'q3': q3, 'min': vals.min(), 'max': vals.max(),
                })
        dispersion_stats[gas] = rows
    return dispersion_stats


def compute_levene_test(data_clean):
    """Levene 方差齐性检验"""
    levene_results = {}
    for gas in GASES:
        if gas not in data_clean.columns:
            continue
        groups = []
        for method in METHODS:
            vals = data_clean[data_clean['核算方法'] == method][gas].dropna().values
            if len(vals) >= 2:
                groups.append(vals)
        if len(groups) >= 2:
            W, p = stats.levene(*groups, center='median')
            levene_results[gas] = {'W': W, 'p': p}
        else:
            levene_results[gas] = None
    return levene_results


def compute_variance_decomposition(data_clean):
    """方差分解：组间(Method) vs 组内(Within)"""
    decomp_results = {}
    for gas in GASES:
        if gas not in data_clean.columns:
            continue
        all_vals = []
        group_means = []
        group_sizes = []
        for method in METHODS:
            vals = data_clean[data_clean['核算方法'] == method][gas].dropna().values
            if len(vals) >= 2:
                all_vals.extend(vals)
                group_means.append(vals.mean())
                group_sizes.append(len(vals))
        if len(group_means) >= 2:
            grand_mean = np.mean(all_vals)
            ss_between = sum(n * (m - grand_mean)**2 for n, m in zip(group_sizes, group_means))
            ss_within = 0
            for method in METHODS:
                vals = data_clean[data_clean['核算方法'] == method][gas].dropna().values
                if len(vals) >= 2:
                    ss_within += sum((v - vals.mean())**2 for v in vals)
            ss_total = ss_between + ss_within
            pct_between = ss_between / ss_total * 100 if ss_total > 0 else 0
            pct_within = ss_within / ss_total * 100 if ss_total > 0 else 0
            decomp_results[gas] = {
                'pct_between': pct_between,
                'pct_within': pct_within,
                'ss_between': ss_between,
                'ss_within': ss_within,
                'df_between': len(group_means) - 1,
                'df_within': sum(group_sizes) - len(group_sizes),
            }
    return decomp_results


def build_dispersion_findings(dispersion_stats, levene_results, decomp_results):
    """构建结构化 findings 列表"""
    findings = []
    for gas in GASES:
        rows = dispersion_stats.get(gas, [])
        if not rows:
            continue

        # 最稳定和最不稳定方法
        most_stable = min(rows, key=lambda x: x['cv'])
        least_stable = max(rows, key=lambda x: x['cv'])
        findings.append({
            'type': 'dispersion',
            'variable': gas,
            'importance': 'high',
            'detail': (f'{gas} 稳定性排名: 最稳定={most_stable["method"]}(CV={most_stable["cv"]:.1f}%), '
                       f'最不稳定={least_stable["method"]}(CV={least_stable["cv"]:.1f}%)'),
            'data': {'gas': gas, 'most_stable': most_stable, 'least_stable': least_stable, 'all': rows},
        })

        # Levene 检验
        lr = levene_results.get(gas)
        if lr:
            if lr['p'] < 0.05:
                findings.append({
                    'type': 'variance_heterogeneity',
                    'variable': gas,
                    'importance': 'high',
                    'detail': f'{gas} 方差齐性检验显著 (W={lr["W"]:.2f}, p={lr["p"]:.4f}): 方法间离散度存在显著差异',
                    'data': {'gas': gas, **lr},
                })

        # 方差分解
        decomp = decomp_results.get(gas)
        if decomp:
            findings.append({
                'type': 'variance_decomposition',
                'variable': gas,
                'importance': 'critical' if decomp['pct_between'] > 30 else 'high',
                'detail': (f'{gas} 方差分解: 方法学解释{decomp["pct_between"]:.1f}%变异, '
                           f'其他因素解释{decomp["pct_within"]:.1f}%变异'),
                'data': {'gas': gas, **decomp},
            })

        # 分布形态
        for r in rows:
            if abs(r['skew']) > 1:
                skew_desc = '右偏' if r['skew'] > 0 else '左偏'
                findings.append({
                    'type': 'distribution_shape',
                    'variable': f'{gas}_{r["method"]}',
                    'importance': 'medium',
                    'detail': f'{gas} {r["method"]} 分布{skew_desc} (skew={r["skew"]:.2f}), 建议使用中位数和IQR',
                    'data': {'gas': gas, 'method': r['method'], 'skew': r['skew'], 'kurtosis': r['kurtosis']},
                })

    return findings


def generate_dispersion_figures(data_clean, dispersion_stats, levene_results, decomp_results, output_dir):
    """生成离散分析图表"""
    os.makedirs(output_dir, exist_ok=True)
    figures = {}

    # 图1: CV对比
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    for idx, gas in enumerate(GASES):
        ax = axes[idx]
        rows = dispersion_stats.get(gas, [])
        if not rows:
            continue
        x = range(len(rows))
        cv_vals = [r['cv'] for r in rows]
        robust_cv_vals = [r['robust_cv'] for r in rows]
        method_names = [r['method'] for r in rows]
        w = 0.35
        bars1 = ax.bar([i - w/2 for i in x], cv_vals, w, label='CV (%)',
                        color='#4E79A7', alpha=0.7, edgecolor='black', linewidth=0.5)
        bars2 = ax.bar([i + w/2 for i in x], robust_cv_vals, w, label='Robust CV (%)',
                        color='#F28E2B', alpha=0.7, edgecolor='black', linewidth=0.5)
        ax.set_xticks(list(x))
        ax.set_xticklabels(method_names, fontsize=10)
        ax.set_ylabel('%', fontsize=11)
        ax.set_title(f'{gas} - Dispersion Comparison', fontsize=13, fontweight='bold')
        ax.legend(fontsize=9)
        for bar in bars1:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h, f'{h:.1f}', ha='center', va='bottom', fontsize=8)
        for bar in bars2:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h, f'{h:.1f}', ha='center', va='bottom', fontsize=8)
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'dispersion_cv_v2.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    figures['dispersion_cv'] = fig_path

    # 图2: 箱线图+IQR
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
                            widths=0.5, showmeans=True,
                            meanprops=dict(marker='D', markerfacecolor='white', markersize=6, markeredgecolor='black'),
                            flierprops=dict(marker='o', markersize=3, alpha=0.5))
            for i, patch in enumerate(bp['boxes']):
                patch.set_facecolor(box_colors[i])
                patch.set_alpha(0.6)
            for i, d in enumerate(box_data):
                q1, q3 = np.percentile(d, [25, 75])
                iqr = q3 - q1
                ax.text(i + 1, ax.get_ylim()[1] * 0.95, f'IQR={iqr:.2f}', ha='center', fontsize=8, style='italic')
        ax.set_title(gas, fontsize=13, fontweight='bold')
        ax.set_ylabel('ton CO2eq/10k m3')
        lr = levene_results.get(gas)
        if lr:
            sig = '***' if lr['p'] < 0.001 else ('**' if lr['p'] < 0.01 else ('*' if lr['p'] < 0.05 else 'n.s.'))
            ax.text(0.5, 0.95, f"Levene p={lr['p']:.4f} {sig}", transform=ax.transAxes,
                    ha='center', va='top', fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    plt.suptitle('Dispersion by Methodology (Outliers Removed)', fontsize=14, y=1.02)
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'dispersion_boxplot_v2.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    figures['dispersion_boxplot'] = fig_path

    # 图3: 方差分解
    fig, ax = plt.subplots(figsize=(8, 5))
    gas_list = GASES
    between_pcts = [decomp_results.get(g, {}).get('pct_between', 0) for g in gas_list]
    within_pcts = [decomp_results.get(g, {}).get('pct_within', 0) for g in gas_list]
    x = np.arange(len(gas_list))
    ax.bar(x, between_pcts, 0.5, label='Between-method (Methodology)', color='#E15759', alpha=0.7, edgecolor='black')
    ax.bar(x, within_pcts, 0.5, bottom=between_pcts, label='Within-method (Other factors)', color='#4E79A7', alpha=0.7, edgecolor='black')
    for i, (b, w) in enumerate(zip(between_pcts, within_pcts)):
        ax.text(i, b/2, f'{b:.1f}%', ha='center', va='center', fontsize=10, fontweight='bold', color='white')
        ax.text(i, b + w/2, f'{w:.1f}%', ha='center', va='center', fontsize=10, fontweight='bold', color='white')
    ax.set_xticks(x)
    ax.set_xticklabels(gas_list, fontsize=12)
    ax.set_ylabel('Variance Explained (%)', fontsize=11)
    ax.set_title('Variance Decomposition: Methodology vs Other Factors', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.set_ylim(0, 105)
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'variance_decomposition_v2.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    figures['variance_decomposition'] = fig_path

    # 图4: 偏度-峰度散点图
    fig, ax = plt.subplots(figsize=(8, 6))
    for gas in GASES:
        rows = dispersion_stats.get(gas, [])
        for r in rows:
            marker = {'排放因子法': 'o', '实测法': 's', '模型法': 'D'}.get(r['method'], 'o')
            ax.scatter(r['skew'], r['kurtosis'], c=COLORS[r['method']], marker=marker,
                       s=150, edgecolors='black', linewidth=0.5, zorder=5,
                       label=f"{r['method']} ({gas})")
            ax.annotate(gas, (r['skew'], r['kurtosis']), textcoords="offset points", xytext=(8, 5), fontsize=7)
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.axvline(x=1, color='orange', linestyle=':', linewidth=0.5, alpha=0.5)
    ax.axvline(x=-1, color='orange', linestyle=':', linewidth=0.5, alpha=0.5)
    ax.axhline(y=1, color='red', linestyle=':', linewidth=0.5, alpha=0.5)
    ax.axhline(y=-1, color='red', linestyle=':', linewidth=0.5, alpha=0.5)
    ax.text(1.5, -2, 'Right skewed', fontsize=8, color='orange')
    ax.text(-2.5, -2, 'Left skewed', fontsize=8, color='orange')
    ax.text(0, 2, 'Leptokurtic', fontsize=8, color='red')
    ax.text(0, -2, 'Platykurtic', fontsize=8, color='red')
    ax.set_xlabel('Skewness', fontsize=11)
    ax.set_ylabel('Kurtosis', fontsize=11)
    ax.set_title('Distribution Shape: Skewness vs Kurtosis', fontsize=13, fontweight='bold')
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), fontsize=7, loc='upper left')
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'skew_kurtosis_v2.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    figures['skew_kurtosis'] = fig_path

    # 图5: MAD vs Std
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for idx, gas in enumerate(GASES):
        ax = axes[idx]
        rows = dispersion_stats.get(gas, [])
        if not rows:
            continue
        x = range(len(rows))
        std_vals = [r['std'] for r in rows]
        mad_vals = [r['mad'] for r in rows]
        method_names = [r['method'] for r in rows]
        w = 0.35
        ax.bar([i - w/2 for i in x], std_vals, w, label='Std Dev', color='#4E79A7', alpha=0.7, edgecolor='black')
        ax.bar([i + w/2 for i in x], mad_vals, w, label='MAD', color='#F28E2B', alpha=0.7, edgecolor='black')
        ax.set_xticks(list(x))
        ax.set_xticklabels(method_names, fontsize=9)
        ax.set_ylabel('ton CO2eq/10k m3')
        ax.set_title(gas, fontsize=13, fontweight='bold')
        ax.legend(fontsize=8)
        for i, r in enumerate(rows):
            ratio = r['std'] / r['mad'] if r['mad'] > 0 else 0
            ax.text(i, max(r['std'], r['mad']) * 1.05, f'Std/MAD={ratio:.1f}', ha='center', fontsize=7, style='italic')
    plt.suptitle('Standard Deviation vs MAD (Robustness Check)', fontsize=14, y=1.02)
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'std_vs_mad_v2.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    figures['std_vs_mad'] = fig_path

    return figures


class DispersionAnalysisAgent:
    """
    离散分析 Agent — 可被 PaperContext 编排器调用。

    用法:
        agent = DispersionAnalysisAgent(data_path='data/2222.xlsx', output_dir='./output')
        results = agent.run()
    """

    def __init__(self, data_path=None, output_dir=None):
        self.data_path = data_path
        self.output_dir = output_dir or './dispersion_output'

    def run(self, df=None):
        """
        运行完整离散分析流程。

        Returns
        -------
        dict : 包含 findings, dispersion_stats, levene_results, decomp_results, figures
        """
        logger.info('='*60)
        logger.info('  离散分析: 核算方法内部变异特征')
        logger.info('='*60)

        # 加载数据
        if df is not None:
            data_clean = df
        else:
            if not self.data_path:
                raise ValueError("必须提供 data_path 或 df")
            data_clean, _ = load_and_clean_data(self.data_path)

        # 基础离散指标
        dispersion_stats = compute_dispersion_stats(data_clean)
        for gas, rows in dispersion_stats.items():
            for r in rows:
                logger.info(f"  {gas} {r['method']}: CV={r['cv']:.1f}%, Robust CV={r['robust_cv']:.1f}%, skew={r['skew']:.2f}")

        # Levene 检验
        levene_results = compute_levene_test(data_clean)
        for gas, lr in levene_results.items():
            if lr:
                sig = '***' if lr['p'] < 0.001 else ('**' if lr['p'] < 0.01 else ('*' if lr['p'] < 0.05 else 'n.s.'))
                logger.info(f"  {gas} Levene: W={lr['W']:.4f}, p={lr['p']:.4f} {sig}")

        # 方差分解
        decomp_results = compute_variance_decomposition(data_clean)
        for gas, d in decomp_results.items():
            logger.info(f"  {gas}: 方法学解释 {d['pct_between']:.1f}% 变异")

        # 构建 findings
        findings = build_dispersion_findings(dispersion_stats, levene_results, decomp_results)
        logger.info(f'  生成 {len(findings)} 条 findings')

        # 图表
        figures = generate_dispersion_figures(data_clean, dispersion_stats, levene_results, decomp_results, self.output_dir)
        logger.info(f'  生成 {len(figures)} 张图表')

        return {
            'findings': findings,
            'dispersion_stats': dispersion_stats,
            'levene_results': levene_results,
            'decomp_results': decomp_results,
            'figures': figures,
            'data_clean': data_clean,
        }


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    data_path = sys.argv[1] if len(sys.argv) > 1 else 'data/2222.xlsx'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './dispersion_output'

    agent = DispersionAnalysisAgent(data_path=data_path, output_dir=output_dir)
    results = agent.run()

    print(f'\n[Done] {len(results["findings"])} findings, {len(results["figures"])} figures')
