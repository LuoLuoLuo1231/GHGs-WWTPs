"""
文献学习工作流 v2 — 修正版：严格识别实际使用的方法

修正内容：
1. 只识别Methods部分中实际使用的方法
2. 使用更严格的上下文匹配，排除仅仅"提到"的情况
3. 区分"使用"(used)和"提及"(mentioned)
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

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
    """提取PDF全文"""
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


def extract_sections(text):
    """提取论文各章节"""
    sections = {
        'abstract': '',
        'introduction': '',
        'methods': '',
        'results': '',
        'discussion': '',
        'conclusion': '',
        'references': '',
        'other': ''
    }

    # 常见章节标题模式
    section_patterns = {
        'abstract': r'(?i)(?:^|\n)\s*(?:Abstract|ABSTRACT|摘要)\s*(?:\n|:)',
        'introduction': r'(?i)(?:^|\n)\s*(?:1\.?\s*)?Introduction\s*(?:\n|:)',
        'methods': r'(?i)(?:^|\n)\s*(?:2\.?\s*)?(?:Methods?|Materials?\s*(?:and|&)\s*Methods?|Methodology|Experimental|实验方法|材料与方法)\s*(?:\n|:)',
        'results': r'(?i)(?:^|\n)\s*(?:3\.?\s*)?(?:Results?(?:\s*(?:and|&)\s*Discussion)?)\s*(?:\n|:)',
        'discussion': r'(?i)(?:^|\n)\s*(?:4\.?\s*)?Discussion\s*(?:\n|:)',
        'conclusion': r'(?i)(?:^|\n)\s*(?:5\.?\s*)?(?:Conclusions?|Summary|总结|结论)\s*(?:\n|:)',
        'references': r'(?i)(?:^|\n)\s*(?:References?|Bibliography|参考文献)\s*(?:\n|:)',
    }

    # 找到所有章节标题的位置
    positions = []
    for section_name, pattern in section_patterns.items():
        matches = list(re.finditer(pattern, text))
        if matches:
            positions.append((matches[0].start(), section_name))

    # 按位置排序
    positions.sort(key=lambda x: x[0])

    # 提取各章节内容
    for i, (start, section_name) in enumerate(positions):
        if i + 1 < len(positions):
            end = positions[i + 1][0]
        else:
            end = len(text)

        section_text = text[start:end].strip()
        # 去掉标题行
        lines = section_text.split('\n', 1)
        if len(lines) > 1:
            section_text = lines[1].strip()

        sections[section_name] = section_text[:10000]  # 限制长度

    # 如果没有找到明确的章节，尝试更宽松的匹配
    if not sections['methods']:
        # 尝试找包含"method"的段落
        method_paragraphs = []
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if re.search(r'(?i)(?:method|experimental|procedure|sampling|analysis)', para[:200]):
                method_paragraphs.append(para)
        if method_paragraphs:
            sections['methods'] = '\n\n'.join(method_paragraphs[:5])

    return sections


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

    # 年份 - 使用多种策略，优先匹配发表年份
    year = None

    # 策略1：匹配明确的发表日期格式
    pub_patterns = [
        r'(?:Published|Available\s+online|Received|Accepted|Revised)[:\s]*(?:\d{1,2}\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        r'(?:Published|Available\s+online|Received|Accepted|Revised)[:\s]*(\d{4})',
        r'(?:Published\s+in\s+)(\d{4})',
    ]
    for pat in pub_patterns:
        m = re.search(pat, text[:8000], re.IGNORECASE)
        if m:
            candidate = int(m.group(1))
            if 2020 <= candidate <= 2026:
                year = str(candidate)
                break

    # 策略2：匹配期刊引用格式如 "Journal Name XXX (2024) XXX-XXX"
    if not year:
        journal_cite_patterns = [
            r'(?:Journal|Water|Science|Environmental|Applied|Chemical|Process|Energy|Resources|Ecological|Bioresource|Atmospheric|Critical|International).*?\((\d{4})\)',
            r'\((\d{4})\)\s*\d+[-–]\d+',
            r'Vol\.\s*\d+.*?\((\d{4})\)',
        ]
        for pat in journal_cite_patterns:
            m = re.search(pat, text[:6000], re.IGNORECASE)
            if m:
                candidate = int(m.group(1))
                if 2020 <= candidate <= 2026:
                    year = str(candidate)
                    break

    # 策略3：匹配DOI中的年份
    if not year:
        doi_patterns = [
            r'10\.\d{4,}\/.*?\.(\d{4})',
            r'doi.*?(\d{4})',
        ]
        for pat in doi_patterns:
            m = re.search(pat, text[:5000], re.IGNORECASE)
            if m:
                candidate = int(m.group(1))
                if 2020 <= candidate <= 2026:
                    year = str(candidate)
                    break

    # 策略4：匹配版权年份
    if not year:
        copyright_patterns = [
            r'©\s*(\d{4})',
            r'Copyright.*?(\d{4})',
            r'©.*?(\d{4})',
        ]
        for pat in copyright_patterns:
            m = re.search(pat, text[:8000], re.IGNORECASE)
            if m:
                candidate = int(m.group(1))
                if 2020 <= candidate <= 2026:
                    year = str(candidate)
                    break

    # 策略5：从文件名中提取年份（如果文件名包含明确的年份）
    if not year:
        # 检查文件名中是否有明确的年份格式
        fname_patterns = [
            r'\((\d{4})\)',  # 格式如 (2024)
            r'(\d{4})\.pdf',  # 格式如 2024.pdf
        ]
        for pat in fname_patterns:
            m = re.search(pat, filename)
            if m:
                candidate = int(m.group(1))
                if 2020 <= candidate <= 2026:
                    year = str(candidate)
                    break

    # 策略6：在文本中查找最近的2020-2026年份（更保守的方法）
    if not year:
        # 只在前10000字符中查找，避免匹配到参考文献中的年份
        search_text = text[:10000]
        # 按年份从新到旧查找
        for y in range(2026, 2019, -1):
            y_str = str(y)
            # 检查年份是否出现在合理的上下文中
            if y_str in search_text:
                # 避免匹配到参考文献列表中的年份
                # 检查年份前后的上下文
                idx = search_text.find(y_str)
                context = search_text[max(0, idx-20):idx+20]
                # 如果上下文中包含参考文献的特征，跳过
                if not re.search(r'\[\d+\]|\(\d{4}\)|References|Bibliography', context):
                    year = y_str
                    break

    if year:
        meta["year"] = year

    # DOI
    doi_match = re.search(r'(?:doi|DOI)[:\s]*(10\.\d{4,}/[^\s]+)', text[:3000])
    if doi_match:
        meta["doi"] = doi_match.group(1)

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
# 3. 写作模式分析（保留原有逻辑）
# ============================================================

def analyze_writing_patterns(text):
    """分析写作模式"""
    patterns = {
        "transition_words": [],
        "hedging_phrases": [],
        "emphasis_phrases": [],
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

    # 学术模糊语
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
        '明显', '显著', '特别', '尤其', '重要的是',
    ]

    # 数据报告模式
    data_patterns = [
        r'(?:mean|average|median)\s*(?:±|±|\+/-)\s*(?:SD|standard deviation)',
        r'\d+\.?\d*\s*(?:±|±|\+/-)\s*\d+\.?\d*',
        r'(?:p\s*[<>]\s*0?\.\d+)',
        r'(?:r\s*=\s*-?\d+\.?\d*)',
        r'(?:R²\s*=\s*0?\.\d+)',
        r'(?:n\s*=\s*\d+)',
        r'\d+\.?\d*\s*(?:mg/L|kg/d|t/d|g/m²|%|°C|m³/d)',
    ]

    text_lower = text.lower()

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
        r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}\)',
        r'\[\d+(?:[-,]\d+)*\]',
        r'(?:et\s+al\.?\s+\(\d{4}\))',
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
# 4. 数据分析方法识别（修正版：严格识别实际使用）
# ============================================================

def identify_analysis_methods_strict(text, sections):
    """
    严格识别论文中实际使用的数据分析方法

    关键改进：
    1. 优先在Methods部分搜索
    2. 使用上下文匹配，寻找"使用"语境而非"提及"
    3. 排除引用和讨论中的提及
    """

    methods = {
        "statistical_tests": [],
        "regression_methods": [],
        "machine_learning": [],
        "uncertainty_methods": [],
        "emission_accounting": [],
        "data_processing": [],
    }

    # 方法定义：关键词 + 使用语境模式
    # 使用语境模式：这些词出现时才算是"使用"了该方法
    method_definitions = {
        "statistical_tests": {
            "ANOVA": {
                "keywords": ["ANOVA", "analysis of variance"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|employed).*?(?:ANOVA|analysis of variance)",
                    r"(?:ANOVA|analysis of variance).*?(?:was|were|used|performed|conducted)",
                    r"(?:one-way|two-way|factorial)\s+(?:ANOVA|analysis of variance)",
                    r"(?:ANOVA|analysis of variance).*?(?:test|analysis|compare)",
                ]
            },
            "t-test": {
                "keywords": ["t-test", "Student's t-test", "paired t-test", "independent t-test"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?(?:t-test|t test)",
                    r"(?:t-test|t test).*?(?:was|were|used|performed|conducted)",
                    r"(?:paired|independent|Student's)\s+t-?test",
                ]
            },
            "Mann-Whitney U": {
                "keywords": ["Mann-Whitney", "Wilcoxon"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?(?:Mann-Whitney|Wilcoxon)",
                    r"(?:Mann-Whitney|Wilcoxon).*?(?:was|were|used|performed|conducted)",
                    r"(?:Mann-Whitney|Wilcoxon).*?(?:test|rank)",
                ]
            },
            "Kruskal-Wallis": {
                "keywords": ["Kruskal-Wallis"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?Kruskal-Wallis",
                    r"Kruskal-Wallis.*?(?:was|were|used|performed|conducted)",
                    r"Kruskal-Wallis.*?(?:test|H\s*test)",
                ]
            },
            "Chi-square": {
                "keywords": ["chi-square", "χ²", "chi square"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?(?:chi-square|χ²)",
                    r"(?:chi-square|χ²).*?(?:was|were|used|performed|conducted)",
                ]
            },
            "Shapiro-Wilk": {
                "keywords": ["Shapiro-Wilk", "Shapiro Wilk"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?Shapiro",
                    r"Shapiro.*?(?:was|were|used|performed|conducted)",
                    r"Shapiro.*?(?:test|normality)",
                ]
            },
            "Levene test": {
                "keywords": ["Levene"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?Levene",
                    r"Levene.*?(?:was|were|used|performed|conducted)",
                    r"Levene.*?(?:test|equality of variances)",
                ]
            },
        },
        "regression_methods": {
            "linear regression": {
                "keywords": ["linear regression", "OLS", "ordinary least squares"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|fitted|developed|built|constructed).*?(?:linear regression|OLS)",
                    r"(?:linear regression|OLS).*?(?:was|were|used|performed|conducted|applied)",
                    r"(?:simple|multiple|multivariate)\s+linear\s+regression",
                ]
            },
            "multiple regression": {
                "keywords": ["multiple regression", "multivariate regression"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|fitted|developed).*?(?:multiple|multivariate)\s+regression",
                    r"(?:multiple|multivariate)\s+regression.*?(?:was|were|used|performed|conducted)",
                ]
            },
            "polynomial regression": {
                "keywords": ["polynomial regression"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|fitted).*?polynomial\s+regression",
                    r"polynomial\s+regression.*?(?:was|were|used|performed|conducted)",
                ]
            },
            "stepwise regression": {
                "keywords": ["stepwise", "stepwise regression"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|fitted).*?stepwise",
                    r"stepwise.*?(?:was|were|used|performed|conducted|selection)",
                ]
            },
        },
        "machine_learning": {
            "random forest": {
                "keywords": ["random forest", "Random Forest", "RF model", "RF algorithm"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:random forest|RF model|RF algorithm)",
                    r"(?:random forest|RF model|RF algorithm).*?(?:was|were|used|performed|conducted|applied|developed|trained)",
                    r"(?:random forest|RF).*?(?:regression|classification|model|predictor)",
                ]
            },
            "neural network": {
                "keywords": ["neural network", "ANN", "artificial neural network", "MLP", "feedforward"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:neural network|ANN|MLP)",
                    r"(?:neural network|ANN|MLP).*?(?:was|were|used|performed|conducted|applied|developed|trained)",
                    r"(?:artificial|deep|convolutional|recurrent)\s+neural\s+network",
                ]
            },
            "deep learning": {
                "keywords": ["deep learning", "CNN", "RNN", "LSTM", "GRU", "transformer"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:deep learning|CNN|RNN|LSTM|GRU|transformer)",
                    r"(?:deep learning|CNN|RNN|LSTM|GRU|transformer).*?(?:was|were|used|performed|conducted|applied|developed|trained)",
                ]
            },
            "gradient boosting": {
                "keywords": ["gradient boosting", "XGBoost", "LightGBM", "GBM", "GBDT"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:gradient boosting|XGBoost|LightGBM|GBM|GBDT)",
                    r"(?:gradient boosting|XGBoost|LightGBM|GBM|GBDT).*?(?:was|were|used|performed|conducted|applied|developed|trained)",
                ]
            },
            "SVM": {
                "keywords": ["support vector", "SVM", "SVR"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:support vector|SVM|SVR)",
                    r"(?:support vector|SVM|SVR).*?(?:was|were|used|performed|conducted|applied|developed|trained)",
                ]
            },
            "PCA": {
                "keywords": ["PCA", "principal component analysis", "principal component"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|employed).*?(?:PCA|principal component)",
                    r"(?:PCA|principal component).*?(?:was|were|used|performed|conducted|applied)",
                ]
            },
            "clustering": {
                "keywords": ["k-means", "clustering", "cluster analysis", "hierarchical clustering"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|employed).*?(?:k-means|clustering|cluster analysis)",
                    r"(?:k-means|clustering|cluster analysis).*?(?:was|were|used|performed|conducted|applied)",
                ]
            },
        },
        "uncertainty_methods": {
            "Monte Carlo": {
                "keywords": ["Monte Carlo", "MC simulation"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|employed|run|ran).*?(?:Monte Carlo|MC simulation)",
                    r"(?:Monte Carlo|MC simulation).*?(?:was|were|used|performed|conducted|applied)",
                ]
            },
            "sensitivity analysis": {
                "keywords": ["sensitivity analysis"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|employed).*?sensitivity\s+analysis",
                    r"sensitivity\s+analysis.*?(?:was|were|used|performed|conducted|applied)",
                ]
            },
            "bootstrap": {
                "keywords": ["bootstrap", "bootstrapping"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied|employed).*?(?:bootstrap|bootstrapping)",
                    r"(?:bootstrap|bootstrapping).*?(?:was|were|used|performed|conducted|applied)",
                ]
            },
            "confidence interval": {
                "keywords": ["confidence interval", "95% CI", "95% confidence"],
                "usage_patterns": [
                    r"(?:was|were|using|calculated|computed|estimated|reported).*?(?:confidence interval|95% CI|95% confidence)",
                    r"(?:confidence interval|95% CI|95% confidence).*?(?:was|were|calculated|computed|estimated|reported)",
                ]
            },
        },
        "emission_accounting": {
            "IPCC method": {
                "keywords": ["IPCC", "IPCC guidelines", "IPCC methodology", "emission factor method"],
                "usage_patterns": [
                    r"(?:was|were|using|based on|applied|adopted|followed|employed).*?(?:IPCC|IPCC guidelines|emission factor)",
                    r"(?:IPCC|IPCC guidelines|emission factor).*?(?:was|were|used|applied|adopted|followed|employed)",
                    r"(?:IPCC|Tier \d).*?(?:methodology|approach|method|guideline)",
                ]
            },
            "LCA": {
                "keywords": ["life cycle assessment", "LCA", "life cycle analysis"],
                "usage_patterns": [
                    r"(?:was|were|using|based on|applied|adopted|conducted|performed).*?(?:life cycle assessment|LCA|life cycle analysis)",
                    r"(?:life cycle assessment|LCA|life cycle analysis).*?(?:was|were|used|applied|adopted|conducted|performed)",
                ]
            },
            "carbon footprint": {
                "keywords": ["carbon footprint"],
                "usage_patterns": [
                    r"(?:was|were|using|calculated|computed|estimated|assessed|evaluated).*?carbon\s+footprint",
                    r"carbon\s+footprint.*?(?:was|were|calculated|computed|estimated|assessed|evaluated)",
                ]
            },
            "mass balance": {
                "keywords": ["mass balance", "material balance"],
                "usage_patterns": [
                    r"(?:was|were|using|based on|applied|adopted).*?(?:mass balance|material balance)",
                    r"(?:mass balance|material balance).*?(?:was|were|used|applied|adopted|method|approach)",
                ]
            },
            "operational data": {
                "keywords": ["operational data", "ODIM", "operational data integrated method"],
                "usage_patterns": [
                    r"(?:was|were|using|based on|applied|adopted).*?(?:operational data|ODIM)",
                    r"(?:operational data|ODIM).*?(?:was|were|used|applied|adopted)",
                ]
            },
        },
        "data_processing": {
            "normalization": {
                "keywords": ["normalization", "normalize", "standardization", "standardize"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?(?:normalization|normalize|standardization|standardize)",
                    r"(?:normalization|normalize|standardization|standardize).*?(?:was|were|used|performed|conducted|applied)",
                ]
            },
            "log transformation": {
                "keywords": ["log transformation", "log-transform", "log-transformed", "ln transformation"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?(?:log transformation|log-transform)",
                    r"(?:log transformation|log-transform|log-transformed).*?(?:was|were|used|performed|conducted|applied)",
                    r"(?:data|values?|variables?).*?(?:were|was)\s+log-?transformed",
                ]
            },
            "outlier detection": {
                "keywords": ["outlier detection", "outlier removal", "outliers were"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?outlier",
                    r"outlier.*?(?:was|were|detected|removed|identified|excluded)",
                ]
            },
            "missing data imputation": {
                "keywords": ["imputation", "missing data", "data imputation", "gap filling"],
                "usage_patterns": [
                    r"(?:was|were|using|performed|conducted|applied).*?(?:imputation|missing data|gap filling)",
                    r"(?:imputation|missing data|gap filling).*?(?:was|were|used|performed|conducted|applied)",
                    r"(?:missing|gap).*?(?:data|values?).*?(?:were|was)\s+(?:imputed|filled|interpolated)",
                ]
            },
        },
    }

    # 优先在Methods部分搜索
    methods_text = sections.get('methods', '')
    full_text = text

    # 搜索策略：先在Methods部分找，如果没找到再在全文中用严格模式找
    for category, method_defs in method_definitions.items():
        for method_name, method_info in method_defs.items():
            found = False

            # 策略1：在Methods部分搜索使用语境
            if methods_text:
                for pattern in method_info['usage_patterns']:
                    if re.search(pattern, methods_text, re.IGNORECASE):
                        methods[category].append(method_name)
                        found = True
                        break

            # 策略2：如果Methods部分没找到，在全文中搜索更严格的使用语境
            if not found:
                # 只在非引用、非讨论部分搜索
                # 排除引用部分
                text_without_refs = re.sub(r'(?i)References?.*$', '', full_text, flags=re.DOTALL)
                # 排除讨论部分的比较语句（如 "previous studies used..."）
                # 只保留方法和结果部分
                for pattern in method_info['usage_patterns']:
                    # 使用更严格的模式：主语是 "we" 或 "this study" 或被动语态
                    strict_patterns = [
                        r"(?:we|this study|the present study).*?(?:used|applied|employed|adopted|performed|conducted).*?" + re.escape(method_name),
                        r"(?:was|were).*?(?:used|applied|employed|adopted|performed|conducted).*?" + re.escape(method_name),
                    ]
                    for sp in strict_patterns:
                        if re.search(sp, text_without_refs, re.IGNORECASE):
                            methods[category].append(method_name)
                            found = True
                            break
                    if found:
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
    }

    # 统计图表数量
    fig_numbers = set()
    for pat in [r'(?:Fig\.|Figure|FIG\.|fig\.)\s*(\d+)', r'图\s*(\d+)']:
        fig_numbers.update(re.findall(pat, text))

    tab_numbers = set()
    for pat in [r'(?:Table|TABLE|Tab\.)\s*(\d+)', r'表\s*(\d+)']:
        tab_numbers.update(re.findall(pat, text))

    figures["figure_count"] = len(fig_numbers)
    figures["table_count"] = len(tab_numbers) + len(tables_data)

    # 识别图表类型
    fig_type_patterns = {
        "box plot": r'box\s*plot|boxplot|箱线图',
        "scatter plot": r'scatter\s*plot|散点图',
        "bar chart": r'bar\s*(?:chart|plot)|柱状图',
        "line chart": r'line\s*(?:chart|plot)|折线图',
        "heatmap": r'heat\s*map|热图|热力图',
        "pie chart": r'pie\s*chart|饼图',
        "violin plot": r'violin\s*plot|小提琴图',
        "forest plot": r'forest\s*plot|森林图',
        "radar chart": r'radar|spider\s*chart|雷达图',
    }

    text_lower = text.lower()
    for fig_type, pattern in fig_type_patterns.items():
        if re.search(pattern, text_lower):
            figures["figure_types"].append(fig_type)

    # 表格复杂度
    for table in tables_data:
        complexity = {
            "rows": table["rows"],
            "cols": table["cols"],
            "has_statistics": False,
        }
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

    # 提取章节
    sections = extract_sections(text)

    # 分析写作模式
    writing_patterns = analyze_writing_patterns(text)

    # 识别分析方法（严格版）
    analysis_methods = identify_analysis_methods_strict(text, sections)

    # 提取图表信息
    figure_info = extract_figure_info(text, tables_data)

    # 统计单词数
    word_count = len(text.split())

    # 计算方法使用总数
    total_methods = sum(len(v) for v in analysis_methods.values())

    result = {
        "index": index,
        "metadata": meta,
        "word_count": word_count,
        "char_count": len(text),
        "sections_available": {k: bool(v) for k, v in sections.items()},
        "writing_patterns": writing_patterns,
        "analysis_methods": analysis_methods,
        "figure_info": figure_info,
        "tables_raw": tables_data[:5],
    }

    methods_list = []
    for cat, mlist in analysis_methods.items():
        methods_list.extend(mlist)
    methods_str = ", ".join(methods_list[:5])
    print(f"OK ({word_count} words, {len(tables_data)} tables, methods: {methods_str or 'none detected'})")

    return result


# ============================================================
# 7. 知识汇总与报告生成
# ============================================================

def generate_learning_report(all_results):
    """生成综合学习报告"""
    report_lines = []
    report_lines.append("# 文献学习报告 v2 — 修正版")
    report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"分析文献数: {len(all_results)} 篇")
    report_lines.append("\n**重要说明**: 本报告采用严格的方法识别逻辑，只统计论文中实际使用的方法，而非仅仅提到的方法。\n")

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

    # 引用格式
    report_lines.append("\n### 1.4 引用格式统计\n")
    citation_formats = Counter()
    for r in all_results:
        for cp in r.get("writing_patterns", {}).get("citation_patterns", []):
            if "A-Z" in cp["pattern"] or "Author" in cp["pattern"]:
                citation_formats["Author (Year)"] += cp["count"]
            elif "\\d" in cp["pattern"]:
                citation_formats["[Number]"] += cp["count"]

    for fmt, count in citation_formats.most_common():
        report_lines.append(f"- **{fmt}**: {count} 次")

    # ========== 2. 数据分析方法汇总 ==========
    report_lines.append("\n\n## 二、数据分析方法汇总（修正版）\n")
    report_lines.append("**说明**: 以下统计仅包含论文中实际使用的方法，排除了仅在文献综述或讨论中提到的方法。\n")

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

        report_lines.append(f"\n### 2.{method_categories.index((category, title)) + 1} {title}\n")

        if method_counter:
            report_lines.append("| 方法 | 使用论文数 | 使用率 |")
            report_lines.append("|------|------------|--------|")
            for method, count in method_counter.most_common(15):
                rate = f"{count / len(all_results) * 100:.1f}%"
                report_lines.append(f"| {method} | {count} | {rate} |")
        else:
            report_lines.append("*未检测到明确使用该类方法的论文*")

    # ========== 3. 图表使用汇总 ==========
    report_lines.append("\n\n## 三、图表使用分析\n")

    fig_type_counter = Counter()
    for r in all_results:
        for ft in r.get("figure_info", {}).get("figure_types", []):
            fig_type_counter[ft] += 1

    report_lines.append("### 3.1 常用图表类型\n")
    if fig_type_counter:
        report_lines.append("| 图表类型 | 使用论文数 | 使用率 |")
        report_lines.append("|----------|------------|--------|")
        for fig_type, count in fig_type_counter.most_common(15):
            rate = f"{count / len(all_results) * 100:.1f}%"
            report_lines.append(f"| {fig_type} | {count} | {rate} |")
    else:
        report_lines.append("*未检测到明确的图表类型*")

    fig_counts = [r.get("figure_info", {}).get("figure_count", 0) for r in all_results]
    tab_counts = [r.get("figure_info", {}).get("table_count", 0) for r in all_results]

    report_lines.append("\n### 3.2 图表数量统计\n")
    report_lines.append(f"- **平均图片数**: {sum(fig_counts) / len(fig_counts):.1f} 张/篇")
    report_lines.append(f"- **平均表格数**: {sum(tab_counts) / len(tab_counts):.1f} 个/篇")
    report_lines.append(f"- **最多图片数**: {max(fig_counts)} 张")
    report_lines.append(f"- **最多表格数**: {max(tab_counts)} 个")

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
""")

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
        "version": "v2_strict",
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

    writing_path = os.path.join(KNOWLEDGE_DIR, "learned_writing_patterns_v2.json")
    with open(writing_path, "w", encoding="utf-8") as f:
        json.dump(writing_knowledge, f, ensure_ascii=False, indent=2)
    print(f"  写作模式已保存: {writing_path}")

    # 分析方法知识（严格版）
    methods_knowledge = {
        "last_updated": datetime.now().isoformat(),
        "papers_analyzed": len(all_results),
        "version": "v2_strict",
        "description": "仅统计论文中实际使用的方法，排除仅提到的方法",
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

    methods_path = os.path.join(KNOWLEDGE_DIR, "learned_analysis_methods_v2.json")
    with open(methods_path, "w", encoding="utf-8") as f:
        json.dump(methods_knowledge, f, ensure_ascii=False, indent=2)
    print(f"  分析方法已保存: {methods_path}")

    # 图表知识
    figure_knowledge = {
        "last_updated": datetime.now().isoformat(),
        "papers_analyzed": len(all_results),
        "version": "v2",
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

    figure_path = os.path.join(KNOWLEDGE_DIR, "learned_figure_design_v2.json")
    with open(figure_path, "w", encoding="utf-8") as f:
        json.dump(figure_knowledge, f, ensure_ascii=False, indent=2)
    print(f"  图表知识已保存: {figure_path}")


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 70)
    print("  文献学习系统 v2 — 修正版（严格方法识别）")
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
    raw_data_path = os.path.join(OUTPUT_DIR, "all_papers_analysis_v2.json")
    with open(raw_data_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  原始数据已保存: {raw_data_path}")

    # 生成学习报告
    print("\n  生成学习报告...")
    report = generate_learning_report(all_results)

    report_path = os.path.join(OUTPUT_DIR, "literature_learning_report_v2.md")
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

    # 打印方法使用统计摘要
    print("\n  方法使用统计摘要:")
    for r in all_results:
        am = r.get("analysis_methods", {})
        for category, methods in am.items():
            if methods:
                print(f"    {category}: {', '.join(methods)}")

    return all_results, report_path


if __name__ == "__main__":
    main()
