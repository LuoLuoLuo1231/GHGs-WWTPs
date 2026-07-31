"""
文献学习工作流 — 批量阅读并提取写作、数据分析、绘图知识

工作流程:
1. 批量解析117篇PDF，提取结构化信息
2. 深度分析写作模式（句式、段落结构、逻辑链）
3. 识别数据分析方法（统计方法、模型、可视化）
4. 提取绘图技巧（图表类型、配色、标注）
5. 生成综合学习报告
6. 存入知识库供后续写作使用
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# PDF解析
try:
    import pdfplumber
except ImportError:
    print("请安装 pdfplumber: pip install pdfplumber")
    sys.exit(1)

# ============================================================
# 配置
# ============================================================
LITERATURE_DIR = r"D:\下载\文献数据整理\artical learning-agent train"
OUTPUT_DIR = r"D:\VScode\firstcc\GHGs-WWTPs\output\literature_learning"
KNOWLEDGE_DIR = r"D:\VScode\firstcc\GHGs-WWTPs\knowledge_store"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 1. PDF 文本提取
# ============================================================

def extract_full_text(pdf_path, max_pages=20):
    """提取PDF全文（最多20页）"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            for i, page in enumerate(pdf.pages[:max_pages]):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
    except Exception as e:
        return f"[ERROR: {e}]"


def extract_tables_from_pdf(pdf_path, max_pages=20):
    """提取PDF中的表格"""
    tables_data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table and len(table) > 1:
                        tables_data.append({
                            'page': i + 1,
                            'rows': len(table),
                            'cols': len(table[0]) if table else 0,
                            'headers': table[0] if table else [],
                            'sample': table[:3] if len(table) > 3 else table
                        })
    except Exception:
        pass
    return tables_data


# ============================================================
# 2. 元数据提取
# ============================================================

def extract_metadata(text, filename):
    """提取论文元数据"""
    meta = {
        "filename": filename,
        "title": "",
        "authors": "",
        "journal": "",
        "year": "",
        "abstract": "",
        "keywords": [],
        "doi": "",
    }

    lines = text.split("\n")
    clean_lines = [l.strip() for l in lines if l.strip()]

    # 标题
    for line in clean_lines[:10]:
        if len(line) > 20 and not line.startswith("http") and "doi" not in line.lower():
            meta["title"] = line[:200]
            break

    # 年份
    year_match = re.search(r'(?:19|20)\d{2}', text[:3000])
    if year_match:
        meta["year"] = year_match.group()

    # DOI
    doi_match = re.search(r'(?:doi|DOI)[:\s]*(10\.\d{4,}/[^\s]+)', text[:3000])
    if doi_match:
        meta["doi"] = doi_match.group(1)

    # 期刊
    journal_patterns = [
        r'(?:Published in|Journal|期刊)[:\s]*(.{10,100}?)(?:\n|,)',
        r'(?:Water Research|Environmental Science|Science of the Total Environment|Chemosphere|Journal of Cleaner Production)',
    ]
    for pat in journal_patterns:
        m = re.search(pat, text[:5000], re.IGNORECASE)
        if m:
            meta["journal"] = m.group(0)[:100]
            break

    # 摘要
    abstract_patterns = [
        r'(?:Abstract|ABSTRACT|摘要)[:\s]*\n?(.*?)(?:\n\n|Keywords|KEYWORDS|Introduction|1\.|1\s)',
        r'(?:Abstract|ABSTRACT)[:\s]*(.{100,2000}?)(?:\n\n|\nKeywords)',
    ]
    for pat in abstract_patterns:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            meta["abstract"] = m.group(1).strip()[:1500]
            break

    # 关键词
    kw_match = re.search(r'(?:Keywords?|KEYWORDS?|关键词)[:\s]*(.*?)(?:\n\n|\n(?:1\.|Introduction))', text, re.DOTALL | re.IGNORECASE)
    if kw_match:
        kw_text = kw_match.group(1).strip()
        kws = re.split(r'[,;，；]', kw_text)
        meta["keywords"] = [k.strip() for k in kws if len(k.strip()) > 2][:10]

    return meta


# ============================================================
# 3. 写作模式分析
# ============================================================

def analyze_writing_patterns(text):
    """分析写作模式"""
    patterns = {
        "sentence_structures": [],
        "transition_words": [],
        "hedging_phrases": [],
        "emphasis_phrases": [],
        "logical_connectors": [],
        "data_reporting_patterns": [],
        "citation_patterns": [],
    }

    # 过渡词
    transition_words = [
        'however', 'moreover', 'furthermore', 'in addition', 'consequently',
        'therefore', 'thus', 'nevertheless', 'in contrast', 'on the other hand',
        'similarly', 'likewise', 'in particular', 'specifically', 'for example',
        'for instance', 'in fact', 'indeed', 'notably', 'significantly',
        '相反', '然而', '此外', '另外', '因此', '所以', '同时', '其中',
        '特别是', '具体而言', '例如', '事实上', '值得注意的是',
    ]

    # 学术模糊语（hedging）
    hedging_phrases = [
        'may', 'might', 'could', 'suggest', 'indicate', 'appear to',
        'it is likely', 'it is possible', 'to some extent', 'relatively',
        'approximately', 'roughly', 'about', 'around', 'estimated',
        '可能', '或许', '表明', '显示', '似乎', '大概', '约', '估计',
    ]

    # 强调语
    emphasis_phrases = [
        'clearly', 'obviously', 'evidently', 'significantly', 'remarkably',
        'notably', 'importantly', 'crucially', 'particularly', 'especially',
        'clearly', 'it is clear that', '毫无疑问', '显著', '明显',
        '特别', '尤其', '重要的是',
    ]

    # 数据报告模式
    data_patterns = [
        r'(?:mean|average|median)\s*(?:±|±|\+/-)\s*(?:SD|standard deviation)',
        r'\d+\.?\d*\s*(?:±|±|\+/-)\s*\d+\.?\d*',
        r'(?:p\s*[<>]\s*0?\.\d+)',
        r'(?:r\s*=\s*-?\d+\.?\d*)',
        r'(?:R²\s*=\s*0?\.\d+)',
        r'(?:CI|confidence interval)\s*(?:=|:)\s*\d+',
        r'(?:IQR|interquartile range)',
        r'(?:n\s*=\s*\d+)',
        r'\d+\.?\d*\s*(?:mg/L|kg/d|t/d|g/m²|%|°C|m³/d)',
    ]

    text_lower = text.lower()

    # 统计各类模式出现次数
    for word in transition_words:
        count = text_lower.count(word.lower())
        if count > 0:
            patterns["transition_words"].append({"word": word, "count": count})

    for phrase in hedging_phrases:
        count = text_lower.count(phrase.lower())
        if count > 0:
            patterns["hedging_phrases"].append({"phrase": phrase, "count": count})

    for phrase in emphasis_phrases:
        count = text_lower.count(phrase.lower())
        if count > 0:
            patterns["emphasis_phrases"].append({"phrase": phrase, "count": count})

    # 数据报告模式
    for pat in data_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            patterns["data_reporting_patterns"].append({
                "pattern": pat,
                "count": len(matches),
                "examples": matches[:3]
            })

    # 引用模式
    citation_patterns = [
        r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}\)',  # (Author, 2020)
        r'\[\d+(?:[-,]\d+)*\]',  # [1] or [1-3] or [1,2]
        r'(?:et\s+al\.?\s+\(\d{4}\))',  # et al. (2020)
    ]
    for pat in citation_patterns:
        matches = re.findall(pat, text)
        if matches:
            patterns["citation_patterns"].append({
                "pattern": pat,
                "count": len(matches),
                "examples": matches[:3]
            })

    return patterns


# ============================================================
# 4. 数据分析方法识别
# ============================================================

def identify_analysis_methods(text):
    """识别论文中使用的数据分析方法"""
    methods = {
        "statistical_tests": [],
        "regression_methods": [],
        "machine_learning": [],
        "uncertainty_methods": [],
        "emission_accounting": [],
        "visualization_methods": [],
        "data_processing": [],
    }

    method_keywords = {
        "statistical_tests": {
            "t-test": ["t-test", "student's t", "paired t", "independent t"],
            "ANOVA": ["ANOVA", "analysis of variance", "one-way ANOVA", "two-way ANOVA"],
            "Mann-Whitney U": ["Mann-Whitney", "Wilcoxon"],
            "Kruskal-Wallis": ["Kruskal-Wallis", "Kruskal Wallis"],
            "Chi-square": ["chi-square", "χ²", "chi square"],
            "Shapiro-Wilk": ["Shapiro-Wilk", "Shapiro Wilk", "normality test"],
            "Kolmogorov-Smirnov": ["Kolmogorov-Smirnov", "K-S test"],
            "Levene test": ["Levene", "Levene's test"],
            "Bartlett test": ["Bartlett"],
            "Fisher's exact": ["Fisher's exact"],
            "paired test": ["paired", "paired comparison"],
        },
        "regression_methods": {
            "linear regression": ["linear regression", "OLS", "ordinary least squares"],
            "multiple regression": ["multiple regression", "multivariate regression"],
            "logistic regression": ["logistic regression"],
            "polynomial regression": ["polynomial regression"],
            "nonlinear regression": ["nonlinear regression", "non-linear regression"],
            "stepwise regression": ["stepwise", "stepwise regression"],
            "ridge/lasso": ["ridge", "lasso", "regularization"],
            "geographically weighted regression": ["GWR", "geographically weighted"],
        },
        "machine_learning": {
            "random forest": ["random forest", "RF"],
            "neural network": ["neural network", "ANN", "artificial neural network"],
            "deep learning": ["deep learning", "CNN", "RNN", "LSTM", "transformer"],
            "SVM": ["support vector", "SVM"],
            "gradient boosting": ["gradient boosting", "XGBoost", "LightGBM", "GBM"],
            "GAN": ["generative adversarial", "GAN"],
            "clustering": ["k-means", "clustering", "cluster analysis"],
            "PCA": ["PCA", "principal component", "factor analysis"],
            "decision tree": ["decision tree", "CART"],
        },
        "uncertainty_methods": {
            "Monte Carlo": ["Monte Carlo", "MC simulation"],
            "sensitivity analysis": ["sensitivity analysis", "sensitivity"],
            "bootstrap": ["bootstrap", "bootstrapping"],
            "confidence interval": ["confidence interval", "CI"],
            "error propagation": ["error propagation", "uncertainty propagation"],
            "Bayesian": ["Bayesian", "Bayes"],
        },
        "emission_accounting": {
            "IPCC method": ["IPCC", "IPCC guidelines", "emission factor"],
            "LCA": ["life cycle assessment", "LCA", "life cycle analysis"],
            "carbon footprint": ["carbon footprint"],
            "mass balance": ["mass balance", "material balance"],
            "carbon balance": ["carbon balance"],
            "energy balance": ["energy balance"],
            "operational data": ["operational data", "ODIM"],
        },
        "visualization_methods": {
            "box plot": ["box plot", "boxplot", "box-and-whisker"],
            "violin plot": ["violin plot"],
            "scatter plot": ["scatter plot", "scatter plot", "correlation plot"],
            "heatmap": ["heatmap", "heat map"],
            "bar chart": ["bar chart", "bar plot", "column chart"],
            "line chart": ["line chart", "line plot", "time series"],
            "pie chart": ["pie chart", "donut chart"],
            "forest plot": ["forest plot"],
            "funnel plot": ["funnel plot"],
            "Sankey diagram": ["Sankey", "flow diagram"],
            "radar chart": ["radar chart", "spider chart"],
            "3D plot": ["3D", "three-dimensional", "surface plot"],
            "map/GIS": ["GIS", "geographic", "spatial", "map"],
        },
        "data_processing": {
            "normalization": ["normalization", "normalize", "standardization"],
            "log transformation": ["log transformation", "log-transform", "ln("],
            "interpolation": ["interpolation", "interpolate"],
            "smoothing": ["smoothing", "moving average", "LOESS"],
            "outlier detection": ["outlier", "anomaly detection"],
            "missing data": ["missing data", "imputation", "data gap"],
            "data cleaning": ["data cleaning", "data quality", "preprocessing"],
        },
    }

    text_lower = text.lower()

    for category, methods_dict in method_keywords.items():
        for method_name, keywords in methods_dict.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    if method_name not in methods[category]:
                        methods[category].append(method_name)
                    break

    return methods


# ============================================================
# 5. 图表信息提取
# ============================================================

def extract_figure_info(text, tables_data):
    """提取图表信息"""
    figures = {
        "figure_count": 0,
        "table_count": 0,
        "figure_types": [],
        "table_complexity": [],
        "figure_descriptions": [],
    }

    # 统计图表数量
    fig_patterns = [
        r'(?:Fig\.|Figure|FIG\.|fig\.)\s*(\d+)',
        r'(?:图|表)\s*(\d+)',
    ]

    fig_numbers = set()
    for pat in fig_patterns:
        matches = re.findall(pat, text)
        fig_numbers.update(matches)

    # 统计表格
    tab_patterns = [
        r'(?:Table|TABLE|Tab\.)\s*(\d+)',
        r'表\s*(\d+)',
    ]

    tab_numbers = set()
    for pat in tab_patterns:
        matches = re.findall(pat, text)
        tab_numbers.update(matches)

    figures["figure_count"] = len(fig_numbers)
    figures["table_count"] = len(tab_numbers) + len(tables_data)

    # 识别图表类型描述
    fig_type_patterns = {
        "box plot": r'box\s*plot|boxplot|箱线图',
        "scatter plot": r'scatter\s*plot|散点图',
        "bar chart": r'bar\s*(?:chart|plot)|柱状图',
        "line chart": r'line\s*(?:chart|plot)|折线图',
        "heatmap": r'heat\s*map|热图|热力图',
        "pie chart": r'pie\s*chart|饼图',
        "violin plot": r'violin\s*plot|小提琴图',
        "forest plot": r'forest\s*plot|森林图',
        "Sankey diagram": r'Sankey|桑基图',
        "contour plot": r'contour|等高线',
        "surface plot": r'surface\s*plot|3D\s*plot',
        "radar chart": r'radar|spider\s*chart|雷达图',
        "waterfall chart": r'waterfall',
        "stacked bar": r'stacked\s*bar',
        "grouped bar": r'grouped\s*bar',
    }

    text_lower = text.lower()
    for fig_type, pattern in fig_type_patterns.items():
        if re.search(pattern, text_lower):
            figures["figure_types"].append(fig_type)

    # 提取表格复杂度信息
    for table in tables_data:
        complexity = {
            "rows": table["rows"],
            "cols": table["cols"],
            "has_statistics": False,
        }
        # 检查是否包含统计信息
        headers_str = " ".join(str(h) for h in table.get("headers", []))
        if any(kw in headers_str.lower() for kw in ['mean', 'sd', '±', 'p-value', 'r²', 'ci', '%']):
            complexity["has_statistics"] = True
        figures["table_complexity"].append(complexity)

    return figures


# ============================================================
# 6. 综合论文分析
# ============================================================

def analyze_single_paper(pdf_path, index, total):
    """分析单篇论文"""
    filename = os.path.basename(pdf_path)
    print(f"\n  [{index}/{total}] {filename[:60]}...", end=" ", flush=True)

    # 提取全文
    text = extract_full_text(pdf_path, max_pages=20)
    if text.startswith("[ERROR") or len(text) < 200:
        print(f"SKIP ({len(text)} chars)")
        return None

    # 提取表格
    tables_data = extract_tables_from_pdf(pdf_path, max_pages=20)

    # 提取元数据
    meta = extract_metadata(text, filename)

    # 分析写作模式
    writing_patterns = analyze_writing_patterns(text)

    # 识别分析方法
    analysis_methods = identify_analysis_methods(text)

    # 提取图表信息
    figure_info = extract_figure_info(text, tables_data)

    # 统计单词数
    word_count = len(text.split())

    result = {
        "index": index,
        "metadata": meta,
        "word_count": word_count,
        "char_count": len(text),
        "writing_patterns": writing_patterns,
        "analysis_methods": analysis_methods,
        "figure_info": figure_info,
        "tables_raw": tables_data[:5],  # 保存前5个表格的原始数据
    }

    methods_str = ", ".join(analysis_methods.get("statistical_tests", [])[:3])
    print(f"OK ({word_count} words, {len(tables_data)} tables, methods: {methods_str or 'N/A'})")

    return result


# ============================================================
# 7. 知识汇总与报告生成
# ============================================================

def generate_learning_report(all_results):
    """生成综合学习报告"""
    report_lines = []
    report_lines.append("# 文献学习报告 — 写作、数据分析与绘图方法总结")
    report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"分析文献数: {len(all_results)} 篇\n")

    # ========== 1. 写作模式汇总 ==========
    report_lines.append("\n## 一、写作模式分析\n")

    # 过渡词统计
    all_transitions = Counter()
    for r in all_results:
        for tw in r.get("writing_patterns", {}).get("transition_words", []):
            all_transitions[tw["word"]] += tw["count"]

    report_lines.append("### 1.1 高频过渡词（Top 20）\n")
    report_lines.append("| 过渡词 | 出现次数 | 使用频率 |")
    report_lines.append("|--------|----------|----------|")
    for word, count in all_transitions.most_common(20):
        freq = f"{count / len(all_results):.1f} 次/篇"
        report_lines.append(f"| {word} | {count} | {freq} |")

    # 学术模糊语
    all_hedging = Counter()
    for r in all_results:
        for hp in r.get("writing_patterns", {}).get("hedging_phrases", []):
            all_hedging[hp["phrase"]] += hp["count"]

    report_lines.append("\n### 1.2 学术模糊语（Hedging）使用频率\n")
    report_lines.append("| 模糊语 | 出现次数 | 频率 |")
    report_lines.append("|--------|----------|------|")
    for phrase, count in all_hedging.most_common(15):
        freq = f"{count / len(all_results):.1f} 次/篇"
        report_lines.append(f"| {phrase} | {count} | {freq} |")

    # 强调语
    all_emphasis = Counter()
    for r in all_results:
        for ep in r.get("writing_patterns", {}).get("emphasis_phrases", []):
            all_emphasis[ep["phrase"]] += ep["count"]

    report_lines.append("\n### 1.3 强调语使用频率\n")
    report_lines.append("| 强调语 | 出现次数 | 频率 |")
    report_lines.append("|--------|----------|------|")
    for phrase, count in all_emphasis.most_common(10):
        freq = f"{count / len(all_results):.1f} 次/篇"
        report_lines.append(f"| {phrase} | {count} | {freq} |")

    # 数据报告模式
    all_data_patterns = Counter()
    for r in all_results:
        for dp in r.get("writing_patterns", {}).get("data_reporting_patterns", []):
            all_data_patterns[dp["pattern"]] += dp["count"]

    report_lines.append("\n### 1.4 数据报告常用句式\n")
    report_lines.append("以下是文献中常见的数据报告表达方式：\n")
    for r in all_results[:10]:
        for dp in r.get("writing_patterns", {}).get("data_reporting_patterns", []):
            if dp.get("examples"):
                for ex in dp["examples"][:1]:
                    report_lines.append(f"- \"{ex}\"")

    # 引用格式
    report_lines.append("\n### 1.5 引用格式统计\n")
    citation_formats = Counter()
    for r in all_results:
        for cp in r.get("writing_patterns", {}).get("citation_patterns", []):
            if "A-Z" in cp["pattern"] or "Author" in cp["pattern"]:
                citation_formats["Author (Year)"] += cp["count"]
            elif "\\d" in cp["pattern"]:
                citation_formats["[Number]"] += cp["count"]
            elif "et al" in cp["pattern"]:
                citation_formats["et al. (Year)"] += cp["count"]

    for fmt, count in citation_formats.most_common():
        report_lines.append(f"- **{fmt}**: {count} 次")

    # ========== 2. 数据分析方法汇总 ==========
    report_lines.append("\n\n## 二、数据分析方法汇总\n")

    method_categories = [
        ("statistical_tests", "统计检验"),
        ("regression_methods", "回归分析"),
        ("machine_learning", "机器学习"),
        ("uncertainty_methods", "不确定性分析"),
        ("emission_accounting", "排放核算"),
        ("data_processing", "数据处理"),
    ]

    for category, title in method_categories:
        method_counter = Counter()
        for r in all_results:
            for method in r.get("analysis_methods", {}).get(category, []):
                method_counter[method] += 1

        if method_counter:
            report_lines.append(f"\n### 2.{method_categories.index((category, title)) + 1} {title}\n")
            report_lines.append("| 方法 | 使用论文数 | 使用率 |")
            report_lines.append("|------|------------|--------|")
            for method, count in method_counter.most_common(15):
                rate = f"{count / len(all_results) * 100:.1f}%"
                report_lines.append(f"| {method} | {count} | {rate} |")

    # ========== 3. 图表使用汇总 ==========
    report_lines.append("\n\n## 三、图表使用分析\n")

    # 图表类型统计
    fig_type_counter = Counter()
    for r in all_results:
        for ft in r.get("figure_info", {}).get("figure_types", []):
            fig_type_counter[ft] += 1

    report_lines.append("### 3.1 常用图表类型\n")
    report_lines.append("| 图表类型 | 使用论文数 | 使用率 |")
    report_lines.append("|----------|------------|--------|")
    for fig_type, count in fig_type_counter.most_common(15):
        rate = f"{count / len(all_results) * 100:.1f}%"
        report_lines.append(f"| {fig_type} | {count} | {rate} |")

    # 图表数量统计
    fig_counts = [r.get("figure_info", {}).get("figure_count", 0) for r in all_results]
    tab_counts = [r.get("figure_info", {}).get("table_count", 0) for r in all_results]

    report_lines.append("\n### 3.2 图表数量统计\n")
    report_lines.append(f"- **平均图片数**: {sum(fig_counts) / len(fig_counts):.1f} 张/篇")
    report_lines.append(f"- **平均表格数**: {sum(tab_counts) / len(tab_counts):.1f} 个/篇")
    report_lines.append(f"- **最多图片数**: {max(fig_counts)} 张")
    report_lines.append(f"- **最多表格数**: {max(tab_counts)} 个")

    # 表格复杂度
    complex_tables = 0
    total_tables = 0
    for r in all_results:
        for tc in r.get("figure_info", {}).get("table_complexity", []):
            total_tables += 1
            if tc.get("has_statistics"):
                complex_tables += 1

    if total_tables > 0:
        report_lines.append(f"\n- **含统计信息的表格**: {complex_tables}/{total_tables} ({complex_tables/total_tables*100:.1f}%)")

    # ========== 4. 写作经验总结 ==========
    report_lines.append("\n\n## 四、写作经验总结\n")

    report_lines.append("""
### 4.1 摘要写作要点
- 摘要长度通常在 150-300 词
- 结构：背景 → 目的 → 方法 → 结果 → 结论
- 结果部分要包含具体数据（数值、p值、相关系数）
- 避免引用文献和缩写（首次出现除外）

### 4.2 引言写作模式
- 漏斗结构：大背景 → 具体问题 → 研究空白 → 本研究目的
- 常用逻辑：已有研究 → 但是不足 → 因此本研究
- 引用密度：每段 3-5 篇文献

### 4.3 方法描述规范
- 顺序：采样/实验设计 → 分析方法 → 统计方法
- 必须说明：样本量、重复次数、显著性水平
- 公式和参数要完整列出

### 4.4 结果呈现技巧
- 先文字描述，再引用图表
- 报告格式：均值 ± 标准差 (n=X)
- 统计结果格式：F(df1, df2) = X.XX, p = 0.XX
- 效应量报告：Cohen's d, η², R²

### 4.5 讨论写作框架
- 与已有研究对比（一致/不一致 + 原因分析）
- 机制解释（为什么会出现这个结果）
- 研究局限性（2-3 点）
- 实际意义/政策建议

### 4.6 常用句式库
""")

    # 从文献中提取典型句子
    sample_sentences = defaultdict(list)
    for r in all_results[:20]:
        meta = r.get("metadata", {})
        if meta.get("abstract"):
            abstract = meta["abstract"]
            # 提取结果句
            result_sentences = re.findall(r'(?:Results?|findings?|showed?|indicated?|revealed?)[:\s]*([^.]+\.)', abstract, re.IGNORECASE)
            for sent in result_sentences[:2]:
                if 30 < len(sent) < 200:
                    sample_sentences["结果描述"].append(sent.strip())

    for category, sentences in sample_sentences.items():
        report_lines.append(f"\n**{category}句式示例：**\n")
        for sent in sentences[:5]:
            report_lines.append(f"- \"{sent}\"")

    # ========== 5. 参考文献列表 ==========
    report_lines.append("\n\n## 五、分析文献列表\n")
    report_lines.append("| 序号 | 文件名 | 标题 | 年份 |")
    report_lines.append("|------|--------|------|------|")
    for r in all_results:
        meta = r.get("metadata", {})
        title = meta.get("title", "")[:50]
        year = meta.get("year", "N/A")
        report_lines.append(f"| {r['index']} | {meta.get('filename', '')[:30]} | {title} | {year} |")

    return "\n".join(report_lines)


# ============================================================
# 8. 知识库存储
# ============================================================

def save_to_knowledge_store(all_results):
    """保存分析结果到知识库"""
    # 写作模式知识
    writing_knowledge = {
        "last_updated": datetime.now().isoformat(),
        "papers_analyzed": len(all_results),
        "transition_words": {},
        "hedging_phrases": {},
        "emphasis_phrases": {},
        "data_reporting_examples": [],
    }

    for r in all_results:
        wp = r.get("writing_patterns", {})
        for tw in wp.get("transition_words", []):
            word = tw["word"]
            writing_knowledge["transition_words"][word] = \
                writing_knowledge["transition_words"].get(word, 0) + tw["count"]

        for hp in wp.get("hedging_phrases", []):
            phrase = hp["phrase"]
            writing_knowledge["hedging_phrases"][phrase] = \
                writing_knowledge["hedging_phrases"].get(phrase, 0) + hp["count"]

        for dp in wp.get("data_reporting_patterns", []):
            if dp.get("examples"):
                writing_knowledge["data_reporting_examples"].extend(dp["examples"][:2])

    writing_path = os.path.join(KNOWLEDGE_DIR, "learned_writing_patterns.json")
    with open(writing_path, "w", encoding="utf-8") as f:
        json.dump(writing_knowledge, f, ensure_ascii=False, indent=2)
    print(f"  写作模式已保存: {writing_path}")

    # 分析方法知识
    methods_knowledge = {
        "last_updated": datetime.now().isoformat(),
        "papers_analyzed": len(all_results),
        "methods_frequency": {},
    }

    for r in all_results:
        am = r.get("analysis_methods", {})
        for category, methods in am.items():
            if category not in methods_knowledge["methods_frequency"]:
                methods_knowledge["methods_frequency"][category] = {}
            for method in methods:
                methods_knowledge["methods_frequency"][category][method] = \
                    methods_knowledge["methods_frequency"][category].get(method, 0) + 1

    methods_path = os.path.join(KNOWLEDGE_DIR, "learned_analysis_methods.json")
    with open(methods_path, "w", encoding="utf-8") as f:
        json.dump(methods_knowledge, f, ensure_ascii=False, indent=2)
    print(f"  分析方法已保存: {methods_path}")

    # 图表知识
    figure_knowledge = {
        "last_updated": datetime.now().isoformat(),
        "papers_analyzed": len(all_results),
        "figure_types": {},
        "avg_figures": 0,
        "avg_tables": 0,
    }

    fig_counts = []
    tab_counts = []
    for r in all_results:
        fi = r.get("figure_info", {})
        for ft in fi.get("figure_types", []):
            figure_knowledge["figure_types"][ft] = \
                figure_knowledge["figure_types"].get(ft, 0) + 1
        fig_counts.append(fi.get("figure_count", 0))
        tab_counts.append(fi.get("table_count", 0))

    if fig_counts:
        figure_knowledge["avg_figures"] = sum(fig_counts) / len(fig_counts)
        figure_knowledge["avg_tables"] = sum(tab_counts) / len(tab_counts)

    figure_path = os.path.join(KNOWLEDGE_DIR, "learned_figure_design.json")
    with open(figure_path, "w", encoding="utf-8") as f:
        json.dump(figure_knowledge, f, ensure_ascii=False, indent=2)
    print(f"  图表知识已保存: {figure_path}")


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 70)
    print("  文献学习系统 — 批量阅读与知识提取")
    print(f"  目录: {LITERATURE_DIR}")
    print("=" * 70)

    # 获取所有PDF文件
    pdf_files = sorted([
        os.path.join(LITERATURE_DIR, f)
        for f in os.listdir(LITERATURE_DIR)
        if f.endswith('.pdf')
    ])

    print(f"\n  发现 {len(pdf_files)} 篇PDF文献\n")

    # 批量分析
    all_results = []
    errors = []

    for i, pdf_path in enumerate(pdf_files, 1):
        result = analyze_single_paper(pdf_path, i, len(pdf_files))
        if result:
            all_results.append(result)
        else:
            errors.append(os.path.basename(pdf_path))

    # 保存原始分析数据
    raw_data_path = os.path.join(OUTPUT_DIR, "all_papers_analysis.json")
    with open(raw_data_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  原始数据已保存: {raw_data_path}")

    # 生成学习报告
    print("\n  生成学习报告...")
    report = generate_learning_report(all_results)

    report_path = os.path.join(OUTPUT_DIR, "literature_learning_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  报告已保存: {report_path}")

    # 保存到知识库
    print("\n  保存到知识库...")
    save_to_knowledge_store(all_results)

    # 打印总结
    print(f"\n{'=' * 70}")
    print(f"  文献学习完成!")
    print(f"  成功分析: {len(all_results)} 篇")
    print(f"  失败/跳过: {len(errors)} 篇")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"{'=' * 70}")

    return all_results, report_path


if __name__ == "__main__":
    main()
