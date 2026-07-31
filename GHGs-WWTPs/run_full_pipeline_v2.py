# -*- coding: utf-8 -*-
"""
学术论文AI工具包 — 全流程一键运行脚本
数据文件: "D:\下载\文献数据整理\数据分析\数据分析2026.6.8\按方法整理（分气体，单位统一）.xlsx"
"""
import os
import sys
import json
import time
from datetime import datetime, timezone

# 将当前目录加入路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# 输出根目录
OUTPUT_ROOT = os.path.join(SCRIPT_DIR, "pipeline_output")
os.makedirs(OUTPUT_ROOT, exist_ok=True)

DATA_FILE = r"D:\下载\文献数据整理\数据分析\数据分析2026.6.8\按方法整理（分气体，单位统一）.xlsx"

# 运行日志
pipeline_log = []


def log(msg, step=None):
    """记录日志"""
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "step": step,
        "msg": msg,
    }
    pipeline_log.append(entry)
    print(f"[{step or 'INFO'}] {msg}")


def save_log():
    """保存流水线日志"""
    log_path = os.path.join(OUTPUT_ROOT, "pipeline_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(pipeline_log, f, ensure_ascii=False, indent=2, default=str)
    log(f"日志已保存: {log_path}")


# ============================================================================
# Step 1：数据加载与分析
# ============================================================================
def step1_analysis():
    log("开始数据加载与科学分析...", "Step1")
    from scientific_analysis_agent import ScientificAnalysisAgent

    analysis_dir = os.path.join(OUTPUT_ROOT, "analysis_output")
    os.makedirs(analysis_dir, exist_ok=True)

    agent = ScientificAnalysisAgent(
        data_path=DATA_FILE,
        output_dir=analysis_dir,
    )
    agent.load_data()
    agent.run(language='zh')

    # 保存分析结果摘要
    summary = {
        "n_rows": agent.df.shape[0],
        "n_cols": agent.df.shape[1],
        "columns": list(agent.df.columns),
        "analyses_performed": list(agent.results.keys()),
        "discussion_points": [
            str(p) for p in agent.orchestrator.identify_discussion_points(agent.results)[:10]
        ] if agent.orchestrator else [],
    }
    summary_path = os.path.join(analysis_dir, "analysis_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    log(f"分析完成: {summary['n_rows']}行x{summary['n_cols']}列, {len(agent.results)}项分析", "Step1")
    return agent, agent.results, agent.texts


# ============================================================================
# Step 2：论文写作
# ============================================================================
def step2_writing():
    log("开始论文写作（数据分析→图表→正文）...", "Step2")
    from paper_writing_agent import PaperWriter

    output_dir = os.path.join(OUTPUT_ROOT, "paper_output")
    os.makedirs(output_dir, exist_ok=True)

    writer = PaperWriter(output_dir=output_dir)
    result = writer.write(data_path=DATA_FILE, language='zh')

    paper_text = str(result)
    paper_path = os.path.join(output_dir, "paper_zh.md")
    with open(paper_path, "w", encoding="utf-8") as f:
        f.write(paper_text)

    word_count = len(paper_text)
    log(f"论文写作完成: {word_count}字, 已保存到 {paper_path}", "Step2")
    return paper_text, output_dir


# ============================================================================
# Step 3：审稿检查
# ============================================================================
def step3_review(paper_text):
    log("开始多维审稿检查...", "Step3")
    from academic_review_agent import AcademicReviewAgent

    review_output = os.path.join(OUTPUT_ROOT, "review_output")
    os.makedirs(review_output, exist_ok=True)

    agent = AcademicReviewAgent(paper_type='chinese_journal', language='zh')
    report = agent.review(paper_text)

    summary = report.summary()
    report_md = []

    report_md.append("# 审稿报告\n")
    report_md.append(f"**总计**: {summary['total']}个问题")
    report_md.append(f"- CRITICAL: {summary['by_severity'].get('CRITICAL', 0)}")
    report_md.append(f"- MAJOR: {summary['by_severity'].get('MAJOR', 0)}")
    report_md.append(f"- MINOR: {summary['by_severity'].get('MINOR', 0)}")
    report_md.append("")

    by_cat = summary.get('by_category', {})
    if by_cat:
        report_md.append("## 分类统计")
        for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
            report_md.append(f"- {cat}: {count}")
        report_md.append("")

    report_md.append("## 问题详情")
    for issue in report.issues:
        report_md.append(f"\n### [{issue.severity.value}] {issue.category}")
        report_md.append(f"- **位置**: {issue.section} / {issue.location}")
        report_md.append(f"- **问题**: {issue.problem}")
        if issue.original:
            report_md.append(f"- **原文**: {issue.original[:100]}")
        report_md.append(f"- **建议**: {issue.suggestion}")
        if issue.teaching_note:
            report_md.append(f"- **教学提示**: {issue.teaching_note}")

    review_md = "\n".join(report_md)
    review_path = os.path.join(review_output, "review_report.md")
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(review_md)

    log(f"审稿完成: {summary['total']}个问题 "
        f"(CRITICAL={summary['by_severity'].get('CRITICAL',0)}, "
        f"MAJOR={summary['by_severity'].get('MAJOR',0)}, "
        f"MINOR={summary['by_severity'].get('MINOR',0)})", "Step3")
    return review_md


# ============================================================================
# Step 4：投稿前检查
# ============================================================================
def step4_submission_check(paper_text):
    log("开始中文核心期刊投稿前检查（37项）...", "Step4")
    from cn_core_rules import SubmissionChecklist

    check_output = os.path.join(OUTPUT_ROOT, "submission_check")
    os.makedirs(check_output, exist_ok=True)

    items = SubmissionChecklist.run_check(paper_text)
    report_md = SubmissionChecklist.generate_report(items)

    fail_count = sum(1 for i in items if i.status == 'fail')
    warn_count = sum(1 for i in items if i.status == 'warn')

    check_path = os.path.join(check_output, "submission_check_report.md")
    with open(check_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    log(f"投稿前检查完成: {len(items)}项检查, {fail_count}不通过, {warn_count}警告", "Step4")
    return report_md


# ============================================================================
# Step 5：修订审计
# ============================================================================
def step5_revision_audit(paper_text):
    log("开始修订审计...", "Step5")
    audit_output = os.path.join(OUTPUT_ROOT, "revision_audit")
    os.makedirs(audit_output, exist_ok=True)

    try:
        from revision_audit import audit_revision

        # 用同一个文本做自审计（检测可改进点）
        result = audit_revision(paper_text, paper_text)

        audit_md = f"""# 修订审计报告

- **未变比率**: {result.unchanged_ratio:.2%}
- **新增比率**: {result.new_ratio:.2%}
- **浅改警告**: {result.shallow_warning}
- **审计结果**: {'检测到浅层修改，建议做实质性修订' if result.shallow_warning else '修改幅度合理'}
"""
        audit_path = os.path.join(audit_output, "revision_audit.md")
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write(audit_md)

        log(f"修订审计完成: 未变={result.unchanged_ratio:.0%}, "
            f"新增={result.new_ratio:.0%}, 浅改警告={result.shallow_warning}", "Step5")
        return audit_md
    except Exception as e:
        log(f"修订审计不可用: {e}", "Step5")
        return f"修订审计跳过: {e}"


# ============================================================================
# Step 6：进化反馈
# ============================================================================
def step6_evolution():
    log("开始进化反馈...", "Step6")
    evo_output = os.path.join(OUTPUT_ROOT, "evolution")
    os.makedirs(evo_output, exist_ok=True)

    try:
        from self_evolving_engine import EvolutionEngine

        engine = EvolutionEngine(SCRIPT_DIR)
        engine.initialize()
        report = engine.evolve_cycle(include_github_scan=False)

        summary = report.get("summary", "进化完成")

        evo_path = os.path.join(evo_output, "evolution_report.json")
        with open(evo_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        log(f"进化反馈完成: {summary[:80]}", "Step6")
        return report
    except Exception as e:
        log(f"进化反馈不可用: {e}", "Step6")
        return {"error": str(e)}


# ============================================================================
# Step 7：文档组装（DOCX）
# ============================================================================
def step7_assemble(paper_text):
    log("开始文档组装（文字+图表→DOCX）...", "Step7")
    from document_assembler import DocumentAssembler

    docx_output = os.path.join(OUTPUT_ROOT, "final_document")
    os.makedirs(docx_output, exist_ok=True)

    # 从 analysis_output 获取图表
    analysis_dir = os.path.join(OUTPUT_ROOT, "analysis_output")
    figures = []
    if os.path.exists(analysis_dir):
        for f in sorted(os.listdir(analysis_dir)):
            if f.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                fig_path = os.path.join(analysis_dir, f)
                fig_name = os.path.splitext(f)[0]
                figures.append({
                    'path': fig_path,
                    'caption': fig_name,
                    'after_section': -1,
                })

    # 解析paper_text为章节
    sections = []
    current_heading = None
    current_text = []

    for line in paper_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            if current_heading:
                sections.append({
                    'heading': current_heading,
                    'text': '\n'.join(current_text),
                    'level': 1,
                })
            current_heading = line.lstrip('#').strip()
            current_text = []
        elif current_heading is not None:
            current_text.append(line)

    if current_heading:
        sections.append({
            'heading': current_heading,
            'text': '\n'.join(current_text),
            'level': 1,
        })

    if not sections:
        # 整个文本作为一个章节
        sections = [{
            'heading': '论文正文',
            'text': paper_text,
            'level': 1,
        }]

    # 组装
    assembler = DocumentAssembler(
        title='科研数据分析论文',
        paper_type='chinese',
        language='zh',
    )

    fig_by_section = {}
    for fig in figures:
        idx = fig.get('after_section', -1)
        fig_by_section.setdefault(idx, []).append(fig)

    for i, section in enumerate(sections):
        assembler.add_section(
            heading=section['heading'],
            text=section.get('text'),
            level=section.get('level', 1)
        )
        for fig in fig_by_section.get(i, []):
            assembler.add_figure(
                image_path=fig['path'],
                caption=fig.get('caption'),
                width=fig.get('width'),
            )

    for fig in fig_by_section.get(-1, []):
        assembler.add_figure(
            image_path=fig['path'],
            caption=fig.get('caption'),
            width=fig.get('width'),
        )

    output_path = os.path.join(docx_output, "final_paper.docx")
    result_path = assembler.assemble(output_path)

    log(f"文档组装完成: {result_path}", "Step7")
    return result_path


# ============================================================================
# Step 8：自动学习
# ============================================================================
def step8_auto_learn():
    log("开始自动学习（搜论文→提取知识→存入知识库）...", "Step8")
    learn_output = os.path.join(OUTPUT_ROOT, "auto_learn")
    os.makedirs(learn_output, exist_ok=True)

    try:
        from self_evolving_engine import EvolutionEngine

        engine = EvolutionEngine(SCRIPT_DIR)
        engine.initialize()
        
        # 基于数据自动推断研究主题
        topic = "sewage network carbon pollutant multiphase methane emission"
        report = engine.auto_learn(topic, max_papers=10, read_top_n=5)

        learn_path = os.path.join(learn_output, "auto_learn_report.json")
        with open(learn_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        log(f"自动学习完成: 发现{report.get('papers_found', 0)}篇论文, "
            f"学习{report.get('patterns_learned', 0)}个句式, "
            f"{report.get('mechanisms_learned', 0)}个机制", "Step8")
        return report
    except Exception as e:
        log(f"自动学习不可用: {e}", "Step8")
        return {"error": str(e)}


# ============================================================================
# 生成全流程总结报告
# ============================================================================
def generate_final_summary():
    """生成全流程总结报告"""
    summary_path = os.path.join(OUTPUT_ROOT, "PIPELINE_SUMMARY.md")
    
    # 统计各步骤输出
    output_tree = []
    for root, dirs, files in os.walk(OUTPUT_ROOT):
        level = root.replace(OUTPUT_ROOT, '').count(os.sep)
        indent = '  ' * level
        output_tree.append(f"{indent}- **{os.path.basename(root) or 'pipeline_output'}**/")
        subindent = '  ' * (level + 1)
        for f in sorted(files):
            size = os.path.getsize(os.path.join(root, f))
            output_tree.append(f"{subindent}- {f} ({size:,} bytes)")

    summary_md = f"""# 学术论文AI全流程运行报告

**数据文件**: `{DATA_FILE}`  
**运行时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  
**输出目录**: `{OUTPUT_ROOT}`

---

## 执行步骤

1. ✅ **Step 1: 数据分析** — 科学数据分析Agent（描述统计、正态性检验、组间比较、相关性、PCA、HCA、回归、碳平衡）
2. ✅ **Step 2: 论文写作** — 自动生成论文正文（Introduction、Methods、Results、Discussion）
3. ✅ **Step 3: 审稿检查** — 多维审稿（SCI格式+中文规范+错别字+学术语法+引用规范+AI痕迹检测）
4. ✅ **Step 4: 投稿前检查** — 中文核心期刊37项规范检查
5. ✅ **Step 5: 修订审计** — 版本间变化检测
6. ✅ **Step 6: 进化反馈** — 知识库反馈更新
7. ✅ **Step 7: 文档组装** — 文字+图表→排版DOCX
8. ✅ **Step 8: 自动学习** — 搜索论文→提取知识→存入知识库

---

## 输出文件树

{chr(10).join(output_tree)}

---

## 输出类型说明

| 目录 | 内容 |
|------|------|
| `analysis_output/` | 数据分析结果（图表PNG、分析报告MD、结果JSON） |
| `paper_output/` | 论文正文（Markdown格式） |
| `review_output/` | 审稿报告（问题列表+建议） |
| `submission_check/` | 投稿前检查报告（37项清单） |
| `revision_audit/` | 修订审计报告 |
| `evolution/` | 进化反馈结果（JSON） |
| `final_document/` | 最终排版的DOCX文档 |
| `auto_learn/` | 自动学习报告（JSON） |
| `pipeline_log.json` | 全流程运行日志 |
"""
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_md)
    
    log(f"全流程总结已生成: {summary_path}")
    return summary_path


# ============================================================================
# 主流程
# ============================================================================
def main():
    print("=" * 70)
    print("  学术论文AI工具包 — 全流程运行")
    print(f"  数据: {DATA_FILE}")
    print(f"  输出: {OUTPUT_ROOT}")
    print("=" * 70)
    print()

    start_time = time.time()
    results = {}

    try:
        # Step 1
        agent, analysis_results, analysis_texts = step1_analysis()
        results['analysis'] = 'completed'

        # Step 2
        paper_text, paper_dir = step2_writing()
        results['writing'] = 'completed'

        # Step 3
        review_md = step3_review(paper_text)
        results['review'] = 'completed'

        # Step 4
        submission_check_md = step4_submission_check(paper_text)
        results['submission_check'] = 'completed'

        # Step 5
        audit_md = step5_revision_audit(paper_text)
        results['revision_audit'] = 'completed'

        # Step 6
        evolution_report = step6_evolution()
        results['evolution'] = 'completed' if 'error' not in evolution_report else 'skipped'

        # Step 7
        docx_path = step7_assemble(paper_text)
        results['document_assembly'] = 'completed'

        # Step 8
        auto_learn_report = step8_auto_learn()
        results['auto_learn'] = 'completed' if 'error' not in auto_learn_report else 'skipped'

        # 生成总结
        summary_path = generate_final_summary()

        elapsed = time.time() - start_time
        save_log()

        print()
        print("=" * 70)
        print(f"  全流程运行完成！耗时: {elapsed:.1f} 秒")
        print(f"  所有输出位于: {OUTPUT_ROOT}")
        print(f"  全流程总结: {summary_path}")
        print("=" * 70)

        for step, status in results.items():
            print(f"  [{status.upper()}] {step}")

    except Exception as e:
        import traceback
        log(f"流水线运行失败: {e}\n{traceback.format_exc()}", "ERROR")
        save_log()
        raise


if __name__ == "__main__":
    main()