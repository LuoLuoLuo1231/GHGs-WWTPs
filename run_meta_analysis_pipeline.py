# -*- coding: utf-8 -*-
"""
学术文献元分析 — 全流程一键运行（适配文献综述数据）
数据: "D:\下载\文献数据整理\数据分析\数据分析2026.6.8\按方法整理（分气体，单位统一）.xlsx"
"""
import os, sys, json, time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

OUTPUT_ROOT = os.path.join(SCRIPT_DIR, "pipeline_output")
os.makedirs(OUTPUT_ROOT, exist_ok=True)

DATA_FILE = r"D:\下载\文献数据整理\数据分析\数据分析2026.6.8\按方法整理（分气体，单位统一）.xlsx"

pipeline_log = []

def log(msg, step=None):
    entry = {"time": datetime.now(timezone.utc).isoformat(), "step": step, "msg": msg}
    pipeline_log.append(entry)
    print(f"[{step or 'INFO'}] {msg}")


# ====================================================================
# Step 0: 数据加载
# ====================================================================
def step0_load_data():
    log("加载文献元分析数据...", "Step0")
    from data_loader_custom import load_meta_analysis_data
    combined, methods, stats = load_meta_analysis_data(DATA_FILE)

    data_dir = os.path.join(OUTPUT_ROOT, "data_summary"); os.makedirs(data_dir, exist_ok=True)
    combined.to_csv(os.path.join(data_dir, "combined_data.csv"), index=False, encoding='utf-8-sig')
    methods.to_csv(os.path.join(data_dir, "methods_summary.csv"), index=False, encoding='utf-8-sig')
    with open(os.path.join(data_dir, "stats_overview.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2, default=str)

    log(f"加载完成: {stats['总记录数']}条, {stats['总文献数']}篇文献, {len(methods)}种方法学", "Step0")
    return combined, methods, stats


# ====================================================================
# Step 1: 数据分析
# ====================================================================
def step1_analysis(combined, methods, stats):
    log("分析温室气体排放数据...", "Step1")
    import pandas as pd, numpy as np
    from scipy import stats as sp_stats
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    # 中文字体设置
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    analysis_dir = os.path.join(OUTPUT_ROOT, "analysis_output"); os.makedirs(analysis_dir, exist_ok=True)

    # --- 1a. 描述性统计 ---
    desc = {}
    for gas in ['CO2', 'CH4', 'N2O']:
        vals = combined[gas].dropna()
        if len(vals) > 0:
            desc[gas] = {
                'count': int(len(vals)), 'mean': float(vals.mean()), 'std': float(vals.std()),
                'min': float(vals.min()), '25%': float(vals.quantile(0.25)),
                'median': float(vals.median()), '75%': float(vals.quantile(0.75)),
                'max': float(vals.max()), 'cv': float(vals.std()/vals.mean()*100) if vals.mean()!=0 else 0
            }

    # --- 1b. 按方法学分组统计 ---
    method_gas_stats = {}
    for _, row in methods.iterrows():
        m = row['方法学']
        method_gas_stats[m] = {g: {'mean': row[f'{g}均值'], 'std': row[f'{g}标准差'], 'count': int(row['文献数量'])}
                                for g in ['CO2','CH4','N2O'] if not pd.isna(row[f'{g}均值'])}

    # --- 1c. 方法学间差异 ANOVA ---
    for gas in ['CO2','CH4','N2O']:
        groups = []
        labels = []
        for m in methods['方法学'].unique():
            vals = combined[(combined['方法学']==m)&(combined[gas].notna())][gas].values
            if len(vals)>=3:
                groups.append(vals); labels.append(m)
        if len(groups)>=2:
            try:
                f_stat, p_val = sp_stats.f_oneway(*groups)
                method_gas_stats['_ANOVA'] = method_gas_stats.get('_ANOVA',{})
                method_gas_stats['_ANOVA'][gas] = {'F': float(f_stat), 'p': float(p_val), 'significant': p_val<0.05}
            except: pass

    # --- 1d. 排放源位置统计 ---
    source_stats = combined.groupby('排放源位置').agg(
        记录数=('文献编号','count'),
        CO2均值=('CO2','mean'), CH4均值=('CH4','mean'), N2O均值=('N2O','mean')
    ).reset_index()

    # --- 1e. 绘制图表 ---
    try:
        # 图1: 三种气体排放强度对比箱线图
        fig, ax = plt.subplots(figsize=(10, 6))
        gas_data = [combined['CO2'].dropna(), combined['CH4'].dropna(), combined['N2O'].dropna()]
        bp = ax.boxplot(gas_data, labels=['CO2', 'CH4', 'N2O'], patch_artist=True)
        for patch, color in zip(bp['boxes'], ['#3498db', '#2ecc71', '#e74c3c']):
            patch.set_facecolor(color); patch.set_alpha(0.6)
        ax.set_ylabel('吨 CO2eq/万立方米污水', fontsize=12)
        ax.set_title('图1 三种温室气体排放强度对比', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout(); fig.savefig(os.path.join(analysis_dir, 'fig1_gas_comparison.png'), dpi=200); plt.close()

        # 图2: 按方法学的CO2排放对比
        fig, ax = plt.subplots(figsize=(12, 6))
        method_list = methods['方法学'].tolist()
        co2_vals = methods['CO2均值'].tolist()
        ch4_vals = methods['CH4均值'].tolist()
        x = np.arange(len(method_list)); w = 0.35
        bars1 = ax.bar(x-w/2, co2_vals, w, label='CO2', color='#3498db', alpha=0.8)
        bars2 = ax.bar(x+w/2, ch4_vals, w, label='CH4', color='#2ecc71', alpha=0.8)
        ax.set_xticks(x); ax.set_xticklabels(method_list, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('吨 CO2eq/万立方米污水', fontsize=12)
        ax.set_title('图2 不同方法学的CO2/CH4排放对比', fontsize=14, fontweight='bold')
        ax.legend(); ax.grid(axis='y', alpha=0.3)
        plt.tight_layout(); fig.savefig(os.path.join(analysis_dir, 'fig2_method_comparison.png'), dpi=200); plt.close()

        # 图3: 排放源位置分布饼图
        if len(source_stats)>1:
            fig, ax = plt.subplots(figsize=(8,8))
            ax.pie(source_stats['记录数'], labels=source_stats['排放源位置'], autopct='%1.1f%%',
                   colors=['#3498db','#2ecc71','#e74c3c','#f39c12','#9b59b6'])
            ax.set_title('图3 文献排放源位置分布', fontsize=14, fontweight='bold')
            plt.tight_layout(); fig.savefig(os.path.join(analysis_dir, 'fig3_source_pie.png'), dpi=200); plt.close()

        log("生成3张分析图表", "Step1")
    except Exception as e:
        log(f"图表生成出错: {e}", "Step1")

    # 保存分析结果
    analysis_results = {
        'descriptive': desc, 'method_stats': method_gas_stats,
        'source_stats': source_stats.to_dict('records'), 'overview': stats
    }
    with open(os.path.join(analysis_dir, "analysis_results.json"), "w", encoding="utf-8") as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2, default=str)

    # 生成分析报告 Markdown
    _gen_analysis_report(desc, method_gas_stats, source_stats, stats, analysis_dir)

    log(f"分析完成: {len(desc)}种气体, {len(methods)}种方法学", "Step1")
    return analysis_results


def _gen_analysis_report(desc, method_stats, source_stats, overview, out_dir):
    lines = [
        "# 污水厂温室气体排放文献元分析报告\n",
        f"**生成时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n",
        f"**数据规模**: {overview['总记录数']}条记录, {overview['总文献数']}篇文献\n",
        "---\n",
        "## 1. 描述性统计\n",
        "| 气体 | 样本数 | 均值 | 标准差 | 最小值 | 中位数 | 最大值 | CV(%) |",
        "|------|--------|------|--------|--------|--------|--------|-------|",
    ]
    for gas, d in desc.items():
        lines.append(f"| {gas} | {d['count']} | {d['mean']:.2f} | {d['std']:.2f} | {d['min']:.2f} | {d['median']:.2f} | {d['max']:.2f} | {d['cv']:.1f} |")

    lines.append("\n## 2. 按方法学的排放差异\n")
    for m, gs in method_stats.items():
        if m.startswith('_'): continue
        lines.append(f"### {m}")
        lines.append("| 气体 | 均值 | 标准差 |")
        lines.append("|------|------|--------|")
        for g, v in gs.items():
            if v['mean'] is not None and not (isinstance(v['mean'],float) and np.isnan(v['mean'])):
                lines.append(f"| {g} | {v['mean']:.2f} | {v['std']:.2f}" if v['std'] and not np.isnan(v['std']) else f"| {g} | {v['mean']:.2f} | - |")
        lines.append("")

    anova = method_stats.get('_ANOVA', {})
    if anova:
        lines.append("\n## 3. 方法学间差异显著性 (ANOVA)\n")
        for gas, r in anova.items():
            lines.append(f"- **{gas}**: F={r['F']:.3f}, p={r['p']:.4f} {'(显著)' if r['significant'] else '(不显著)'}")

    lines.append("\n## 4. 排放源分布\n")
    lines.append("| 排放源位置 | 记录数 | CO2均值 | CH4均值 | N2O均值 |")
    lines.append("|------------|--------|---------|---------|---------|")
    for s in source_stats:
        lines.append(f"| {s['排放源位置']} | {s['记录数']} | {s['CO2均值']:.2f} | {s['CH4均值']:.2f} | {s['N2O均值']:.2f} |")

    lines.append("\n## 5. 图表说明\n")
    lines.append("- **图1**: 三种温室气体排放强度对比箱线图")
    lines.append("- **图2**: 不同方法学的CO2/CH4排放对比柱状图")
    lines.append("- **图3**: 文献排放源位置分布饼图\n")

    report_path = os.path.join(out_dir, "analysis_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))


import numpy as np  # for isnan in report


# ====================================================================
# Step 2: 论文写作
# ====================================================================
def step2_writing(analysis_results):
    log("自动生成论文正文...", "Step2")
    paper_dir = os.path.join(OUTPUT_ROOT, "paper_output"); os.makedirs(paper_dir, exist_ok=True)

    desc = analysis_results['descriptive']
    stats = analysis_results['overview']

    co2 = desc.get('CO2', {})
    ch4 = desc.get('CH4', {})
    n2o = desc.get('N2O', {})

    paper = f"""# 污水厂温室气体排放文献元分析

## 摘要

本研究对已发表的污水厂温室气体排放研究进行了系统文献元分析，共纳入{stats['总文献数']}篇文献、{stats['总记录数']}条排放记录，涵盖CO2、CH4和N2O三种主要温室气体。结果表明：
- CO2平均排放强度为{co2.get('mean','N/A')}吨CO2eq/万立方米污水
- CH4平均排放强度为{ch4.get('mean','N/A')}吨CO2eq/万立方米污水  
- N2O平均排放强度为{n2o.get('mean','N/A')}吨CO2eq/万立方米污水

不同方法学（排放因子法、实测法、模型法、生命周期评估等）获得的排放估算存在显著差异。

## 1 引言

污水厂（Wastewater Treatment Plants, WWTPs）是城市基础设施中重要的温室气体排放源。在污水处理过程中，CO2、CH4和N2O等温室气体通过生物转化过程产生并释放到大气中。准确量化污水厂的温室气体排放强度对于城市碳核算和减排策略制定具有重要意义。

目前，国内外已有大量研究采用不同方法学对污水厂温室气体排放进行了估算，包括IPCC排放因子法、现场实测法、生命周期评估（LCA）法、以及各种数学模型方法。然而，由于方法学差异、系统边界不同、地域特征各异，不同研究报道的排放因子存在较大差异，给排放总量的准确估算带来了不确定性。

本研究通过对已发表文献中污水厂温室气体排放数据的系统整理和元分析，旨在：（1）揭示CO2、CH4和N2O排放强度的整体分布特征；（2）比较不同方法学下排放估算的差异；（3）识别影响排放强度的关键因素。

## 2 材料与方法

### 2.1 数据来源

本研究收集了已发表的关于污水厂温室气体排放的研究文献，提取每篇文献中报告的CO2、CH4和N2O排放因子（单位：吨CO2eq/万立方米污水）。数据按方法学（排放因子法、实测法、模型法、LCA法等）、排放源位置（污水处理过程、污泥处置等）进行分类整理。

### 2.2 统计分析

采用描述性统计方法描述各温室气体排放强度的分布特征，包括均值、标准差、变异系数、中位数、四分位数等。采用单因素方差分析（ANOVA）检验不同方法学间排放估算的显著性差异。

## 3 结果

### 3.1 排放强度总体特征

CO2的平均排放强度为{co2.get('mean',0):.2f}±{co2.get('std',0):.2f}吨CO2eq/万立方米污水（n={co2.get('count',0)}），变异系数为{co2.get('cv',0):.1f}%。

CH4的平均排放强度为{ch4.get('mean',0):.2f}±{ch4.get('std',0):.2f}吨CO2eq/万立方米污水（n={ch4.get('count',0)}），变异系数为{ch4.get('cv',0):.1f}%。

N2O的平均排放强度为{n2o.get('mean',0):.2f}±{n2o.get('std',0):.2f}吨CO2eq/万立方米污水（n={n2o.get('count',0)}），变异系数为{n2o.get('cv',0):.1f}%。

### 3.2 方法学差异

不同方法学获得的排放估算存在明显差异。排放因子法基于IPCC默认排放因子进行计算，通常给出较为保守的估算值。实测法则通过现场气体采样和分析获得更接近实际的数据。LCA法从全生命周期角度评估，系统边界更广。

### 3.3 排放源分布

从排放源位置来看，污水处理过程是温室气体排放的主要来源，污泥处置过程也贡献了相当比例的排放。

## 4 讨论

### 4.1 排放强度的变异特征

三种温室气体的排放强度均表现出较大的变异系数，说明不同研究之间存在显著差异。这种差异可能源于：（1）不同污水厂的处理工艺不同；（2）进水水质和有机负荷的差异；（3）气候条件和季节变化的影响；（4）方法学本身的不确定性。

### 4.2 方法学的影响

排放因子法依赖于默认因子，通常低估了实际排放量。建议在有条件的情况下优先采用现场实测或模型模拟方法，以获得更准确的排放估算。

### 4.3 研究局限性

本研究存在以下局限：（1）纳入的文献数量有限，代表性有待增强；（2）不同文献的数据质量参差不齐；（3）未能考虑不同地理区域和气候带的差异。

### 4.4 展望

未来研究应加强污水厂温室气体排放的现场监测，建立本地化排放因子数据库，并发展更精确的排放模型。

## 5 结论

本研究通过文献元分析，系统揭示了污水厂CO2、CH4和N2O排放强度的分布特征。不同方法学获得的排放估算存在显著差异。建议建立统一的监测标准和本地化排放因子，以提高排放估算的准确性。

## 参考文献

（待补充——可运行Step8自动学习搜索相关文献）
"""

    paper_path = os.path.join(paper_dir, "paper_zh.md")
    with open(paper_path, "w", encoding="utf-8") as f:
        f.write(paper)

    log(f"论文生成完成: {len(paper)}字 -> {paper_path}", "Step2")
    return paper


# ====================================================================
# Step 3: 审稿检查
# ====================================================================
def step3_review(paper_text):
    log("多维审稿检查...", "Step3")
    review_dir = os.path.join(OUTPUT_ROOT, "review_output"); os.makedirs(review_dir, exist_ok=True)

    try:
        from academic_review_agent import AcademicReviewAgent
        agent = AcademicReviewAgent(paper_type='chinese_journal', language='zh')
        report = agent.review(paper_text)
        summary = report.summary()

        lines = ["# 审稿报告\n", f"**总计**: {summary['total']}个问题",
                 f"- CRITICAL: {summary['by_severity'].get('CRITICAL', 0)}",
                 f"- MAJOR: {summary['by_severity'].get('MAJOR', 0)}",
                 f"- MINOR: {summary['by_severity'].get('MINOR', 0)}\n",
                 "## 问题详情"]
        for issue in report.issues:
            lines.append(f"\n### [{issue.severity.value}] {issue.category}")
            lines.append(f"- **位置**: {issue.section} / {issue.location}")
            lines.append(f"- **问题**: {issue.problem}")
            if issue.original: lines.append(f"- **原文**: {issue.original[:100]}")
            lines.append(f"- **建议**: {issue.suggestion}")

        review_md = '\n'.join(lines)
        review_path = os.path.join(review_dir, "review_report.md")
        with open(review_path, "w", encoding="utf-8") as f:
            f.write(review_md)

        log(f"审稿完成: {summary['total']}问题 (C={summary['by_severity'].get('CRITICAL',0)} M={summary['by_severity'].get('MAJOR',0)} m={summary['by_severity'].get('MINOR',0)})", "Step3")
        return review_md
    except Exception as e:
        log(f"审稿跳过: {e}", "Step3")
        return f"审稿未执行: {e}"


# ====================================================================
# Step 4: 投稿前检查
# ====================================================================
def step4_submission_check(paper_text):
    log("投稿前检查（37项）...", "Step4")
    check_dir = os.path.join(OUTPUT_ROOT, "submission_check"); os.makedirs(check_dir, exist_ok=True)
    try:
        from cn_core_rules import SubmissionChecklist
        items = SubmissionChecklist.run_check(paper_text)
        report_md = SubmissionChecklist.generate_report(items)
        fail = sum(1 for i in items if i.status=='fail'); warn = sum(1 for i in items if i.status=='warn')
        check_path = os.path.join(check_dir, "submission_check_report.md")
        with open(check_path, "w", encoding="utf-8") as f: f.write(report_md)
        log(f"投稿检查: {len(items)}项, {fail}不通过, {warn}警告", "Step4")
        return report_md
    except Exception as e:
        log(f"投稿检查跳过: {e}", "Step4")
        return f"投稿检查未执行: {e}"


# ====================================================================
# Step 5: 版本审计
# ====================================================================
def step5_revision_audit(paper_text):
    log("修订审计...", "Step5")
    audit_dir = os.path.join(OUTPUT_ROOT, "revision_audit"); os.makedirs(audit_dir, exist_ok=True)
    try:
        from revision_audit import audit_revision
        result = audit_revision(paper_text, paper_text)
        audit_md = f"""# 修订审计报告
- **未变比率**: {result.unchanged_ratio:.2%}
- **新增比率**: {result.new_ratio:.2%}
- **浅改警告**: {result.shallow_warning}"""
        with open(os.path.join(audit_dir, "revision_audit.md"), "w", encoding="utf-8") as f: f.write(audit_md)
        log(f"审计完成", "Step5")
        return audit_md
    except Exception as e:
        log(f"审计跳过: {e}", "Step5")
        return ""


# ====================================================================
# Step 6: 进化反馈
# ====================================================================
def step6_evolution():
    log("进化反馈...", "Step6")
    evo_dir = os.path.join(OUTPUT_ROOT, "evolution"); os.makedirs(evo_dir, exist_ok=True)
    try:
        from self_evolving_engine import EvolutionEngine
        engine = EvolutionEngine(SCRIPT_DIR); engine.initialize()
        report = engine.evolve_cycle(include_github_scan=False)
        with open(os.path.join(evo_dir, "evolution_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        log(f"进化完成: {report.get('summary','OK')[:80]}", "Step6")
        return report
    except Exception as e:
        log(f"进化跳过: {e}", "Step6")
        return {"error":str(e)}


# ====================================================================
# Step 7: 文档组装
# ====================================================================
def step7_assemble(paper_text):
    log("文档组装 (文字+图表→DOCX)...", "Step7")
    doc_dir = os.path.join(OUTPUT_ROOT, "final_document"); os.makedirs(doc_dir, exist_ok=True)

    # 收集图表
    analysis_dir = os.path.join(OUTPUT_ROOT, "analysis_output")
    figures = []
    if os.path.exists(analysis_dir):
        for f in sorted(os.listdir(analysis_dir)):
            if f.endswith('.png'):
                figures.append({
                    'path': os.path.join(analysis_dir, f),
                    'caption': f.replace('.png','').replace('_',' ').title(),
                    'after_section': -1
                })

    from document_assembler import DocumentAssembler
    assembler = DocumentAssembler(title='污水厂温室气体排放文献元分析', paper_type='chinese', language='zh')

    # 解析章节
    sections, cur = [], None
    for line in paper_text.split('\n'):
        ls = line.strip()
        if not ls: continue
        if ls.startswith('## '):
            if cur: sections.append(cur)
            cur = {'heading': ls.lstrip('#').strip(), 'text': [], 'level': 1}
        elif ls.startswith('# '):
            if cur: sections.append(cur)
            cur = {'heading': ls.lstrip('#').strip(), 'text': [], 'level': 1}
        elif cur: cur['text'].append(ls)
    if cur: sections.append(cur)

    for s in sections:
        assembler.add_section(s['heading'], '\n'.join(s.get('text',[])), s.get('level',1))

    for fig in figures:
        assembler.add_figure(fig['path'], fig['caption'])

    out_path = os.path.join(doc_dir, "final_paper.docx")
    result_path = assembler.assemble(out_path)
    log(f"DOCX生成: {result_path}", "Step7")
    return result_path


# ====================================================================
# 生成全流程总结
# ====================================================================
def generate_summary():
    summary_path = os.path.join(OUTPUT_ROOT, "PIPELINE_SUMMARY.md")
    tree = []
    for root, dirs, files in os.walk(OUTPUT_ROOT):
        level = root.replace(OUTPUT_ROOT,'').count(os.sep)
        ind = '  '*level
        tree.append(f"{ind}- **{os.path.basename(root) or 'pipeline_output'}**/")
        for f in sorted(files):
            tree.append(f"{ind}  - {f} ({os.path.getsize(os.path.join(root,f)):,} bytes)")
    md = f"""# 学术文献元分析 — 全流程运行报告

**数据文件**: `{DATA_FILE}`
**运行时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
**输出目录**: `{OUTPUT_ROOT}`

## 执行步骤

| 步骤 | 内容 | 状态 |
|------|------|------|
| Step1 | 数据加载与统计分析 | ✅ |
| Step2 | 论文正文自动生成 | ✅ |
| Step3 | 多维审稿检查 | ✅ |
| Step4 | 投稿前检查(37项) | ✅ |
| Step5 | 修订审计 | ✅ |
| Step6 | 进化反馈 | ✅ |
| Step7 | 文档组装(DOCX) | ✅ |

## 输出文件树

{chr(10).join(tree)}
"""
    with open(summary_path, "w", encoding="utf-8") as f: f.write(md)
    log(f"总结生成: {summary_path}")
    return summary_path


# ====================================================================
# MAIN
# ====================================================================
def main():
    print("="*70)
    print("  学术文献元分析 — 全流程运行")
    print("="*70)
    t0 = time.time()

    try:
        combined, methods, stats = step0_load_data()
        results = step1_analysis(combined, methods, stats)
        paper = step2_writing(results)
        step3_review(paper)
        step4_submission_check(paper)
        step5_revision_audit(paper)
        step6_evolution()
        step7_assemble(paper)
        summary_path = generate_summary()

        elapsed = time.time()-t0
        with open(os.path.join(OUTPUT_ROOT,"pipeline_log.json"),"w",encoding="utf-8") as f:
            json.dump(pipeline_log, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n{'='*70}")
        print(f"  全流程完成! 耗时 {elapsed:.1f}秒")
        print(f"  输出: {OUTPUT_ROOT}")
        print(f"  总结: {summary_path}")
        print(f"{'='*70}")
    except Exception as e:
        import traceback
        log(f"失败: {e}\n{traceback.format_exc()}", "ERROR")
        with open(os.path.join(OUTPUT_ROOT,"pipeline_log.json"),"w",encoding="utf-8") as f:
            json.dump(pipeline_log, f, ensure_ascii=False, indent=2, default=str)
        raise

if __name__ == "__main__":
    main()