"""
文献批量阅读系统 - 优化版 v3.0

优化内容：
1. 年份识别：多种策略组合，提高准确性
2. 方法识别：严格上下文匹配，区分"使用"和"提及"
3. 错误处理：完善的异常捕获和日志记录
4. 断点续传：支持中断后继续处理
5. 数据验证：自动检查数据质量
6. 进度显示：详细的处理进度和统计
"""

import os
import sys
import json
import re
import logging
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 日志配置
# ============================================================
def setup_logging(log_dir: str) -> logging.Logger:
    """配置日志系统"""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"literature_reader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logger = logging.getLogger('LiteratureReader')
    logger.setLevel(logging.INFO)

    # 文件处理器
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.INFO)

    # 控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    # 格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

# ============================================================
# PDF解析模块
# ============================================================
class PDFParser:
    """PDF解析器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
        except ImportError:
            self.logger.error("请安装 pdfplumber: pip install pdfplumber")
            raise

    def extract_text(self, pdf_path: str, max_pages: int = 20) -> str:
        """提取PDF全文"""
        try:
            with self.pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for i, page in enumerate(pdf.pages[:max_pages]):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                return "\n\n".join(text_parts)
        except Exception as e:
            self.logger.error(f"PDF解析失败 {pdf_path}: {e}")
            return ""

    def extract_tables(self, pdf_path: str, max_pages: int = 20) -> List[Dict]:
        """提取PDF中的表格"""
        tables_data = []
        try:
            with self.pdfplumber.open(pdf_path) as pdf:
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
        except Exception as e:
            self.logger.warning(f"表格提取失败 {pdf_path}: {e}")
        return tables_data

    def extract_sections(self, text: str) -> Dict[str, str]:
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

        # 章节标题模式
        section_patterns = {
            'abstract': r'(?i)(?:^|\n)\s*(?:Abstract|ABSTRACT|摘要)\s*(?:\n|:)',
            'introduction': r'(?i)(?:^|\n)\s*(?:1\.?\s*)?Introduction\s*(?:\n|:)',
            'methods': r'(?i)(?:^|\n)\s*(?:2\.?\s*)?(?:Methods?|Materials?\s*(?:and|&)\s*Methods?|Methodology|Experimental)\s*(?:\n|:)',
            'results': r'(?i)(?:^|\n)\s*(?:3\.?\s*)?(?:Results?(?:\s*(?:and|&)\s*Discussion)?)\s*(?:\n|:)',
            'discussion': r'(?i)(?:^|\n)\s*(?:4\.?\s*)?Discussion\s*(?:\n|:)',
            'conclusion': r'(?i)(?:^|\n)\s*(?:5\.?\s*)?(?:Conclusions?|Summary)\s*(?:\n|:)',
            'references': r'(?i)(?:^|\n)\s*(?:References?|Bibliography)\s*(?:\n|:)',
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

            sections[section_name] = section_text[:10000]

        # 如果没有找到明确的methods，尝试更宽松的匹配
        if not sections['methods']:
            method_paragraphs = []
            paragraphs = text.split('\n\n')
            for para in paragraphs:
                if re.search(r'(?i)(?:method|experimental|procedure|sampling|analysis)', para[:200]):
                    method_paragraphs.append(para)
            if method_paragraphs:
                sections['methods'] = '\n\n'.join(method_paragraphs[:5])

        return sections

# ============================================================
# 元数据提取模块
# ============================================================
class MetadataExtractor:
    """元数据提取器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def extract(self, text: str, filename: str) -> Dict:
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

        # 标题
        lines = text.split("\n")
        clean_lines = [l.strip() for l in lines if l.strip()]
        for line in clean_lines[:10]:
            if len(line) > 20 and not line.startswith("http") and "doi" not in line.lower():
                meta["title"] = line[:200]
                break

        # 年份 - 使用多策略组合
        meta["year"] = self._extract_year(text, filename)

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

    def _extract_year(self, text: str, filename: str) -> str:
        """提取年份 - 多策略组合"""
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

        # 策略2：匹配期刊引用格式
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

        # 策略3：匹配版权年份
        if not year:
            copyright_patterns = [
                r'©\s*(\d{4})',
                r'Copyright.*?(\d{4})',
            ]
            for pat in copyright_patterns:
                m = re.search(pat, text[:8000], re.IGNORECASE)
                if m:
                    candidate = int(m.group(1))
                    if 2020 <= candidate <= 2026:
                        year = str(candidate)
                        break

        # 策略4：从文件名中提取年份
        if not year:
            fname_patterns = [
                r'\((\d{4})\)',
                r'(\d{4})\.pdf',
            ]
            for pat in fname_patterns:
                m = re.search(pat, filename)
                if m:
                    candidate = int(m.group(1))
                    if 2020 <= candidate <= 2026:
                        year = str(candidate)
                        break

        # 策略5：在文本中查找最近的年份（更保守）
        if not year:
            search_text = text[:10000]
            for y in range(2026, 2019, -1):
                y_str = str(y)
                if y_str in search_text:
                    idx = search_text.find(y_str)
                    context = search_text[max(0, idx-20):idx+20]
                    if not re.search(r'\[\d+\]|\(\d{4}\)|References|Bibliography', context):
                        year = y_str
                        break

        return year or ""

# ============================================================
# 方法识别模块
# ============================================================
class MethodIdentifier:
    """方法识别器 - 严格模式"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

        # 方法定义：关键词 + 使用语境模式
        self.method_definitions = {
            "statistical_tests": {
                "ANOVA": {
                    "keywords": ["ANOVA", "analysis of variance"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|employed).*?(?:ANOVA|analysis of variance)",
                        r"(?:ANOVA|analysis of variance).*?(?:was|were|used|performed|conducted)",
                        r"(?:one-way|two-way|factorial)\s+(?:ANOVA|analysis of variance)",
                    ]
                },
                "t-test": {
                    "keywords": ["t-test", "Student's t-test"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?(?:t-test|t test)",
                        r"(?:paired|independent|Student's)\s+t-?test",
                    ]
                },
                "Mann-Whitney U": {
                    "keywords": ["Mann-Whitney", "Wilcoxon"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?(?:Mann-Whitney|Wilcoxon)",
                        r"(?:Mann-Whitney|Wilcoxon).*?(?:test|rank)",
                    ]
                },
                "Kruskal-Wallis": {
                    "keywords": ["Kruskal-Wallis"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?Kruskal-Wallis",
                        r"Kruskal-Wallis.*?(?:test|H\s*test)",
                    ]
                },
                "Chi-square": {
                    "keywords": ["chi-square", "χ²"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?(?:chi-square|χ²)",
                    ]
                },
                "Shapiro-Wilk": {
                    "keywords": ["Shapiro-Wilk", "Shapiro Wilk"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?Shapiro",
                        r"Shapiro.*?(?:test|normality)",
                    ]
                },
                "Levene test": {
                    "keywords": ["Levene"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?Levene",
                        r"Levene.*?(?:test|equality of variances)",
                    ]
                },
            },
            "regression_methods": {
                "linear regression": {
                    "keywords": ["linear regression", "OLS"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|fitted|developed|built).*?(?:linear regression|OLS)",
                        r"(?:simple|multiple|multivariate)\s+linear\s+regression",
                    ]
                },
                "multiple regression": {
                    "keywords": ["multiple regression", "multivariate regression"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|fitted|developed).*?(?:multiple|multivariate)\s+regression",
                    ]
                },
                "stepwise regression": {
                    "keywords": ["stepwise"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|fitted).*?stepwise",
                        r"stepwise.*?(?:selection|regression)",
                    ]
                },
            },
            "machine_learning": {
                "random forest": {
                    "keywords": ["random forest", "Random Forest", "RF model"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:random forest|RF model)",
                        r"(?:random forest|RF model).*?(?:was|were|used|performed|conducted|applied|developed|trained)",
                        r"(?:random forest|RF).*?(?:regression|classification|model|predictor)",
                    ]
                },
                "neural network": {
                    "keywords": ["neural network", "ANN", "artificial neural network"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:neural network|ANN)",
                        r"(?:artificial|deep|convolutional|recurrent)\s+neural\s+network",
                    ]
                },
                "deep learning": {
                    "keywords": ["deep learning", "CNN", "RNN", "LSTM", "GRU"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:deep learning|CNN|RNN|LSTM|GRU)",
                    ]
                },
                "gradient boosting": {
                    "keywords": ["gradient boosting", "XGBoost", "LightGBM"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:gradient boosting|XGBoost|LightGBM)",
                    ]
                },
                "SVM": {
                    "keywords": ["support vector", "SVM", "SVR"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|developed|trained|built|constructed|implemented).*?(?:support vector|SVM|SVR)",
                    ]
                },
                "PCA": {
                    "keywords": ["PCA", "principal component analysis"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|employed).*?(?:PCA|principal component)",
                    ]
                },
                "clustering": {
                    "keywords": ["k-means", "clustering", "cluster analysis"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|employed).*?(?:k-means|clustering|cluster analysis)",
                    ]
                },
            },
            "uncertainty_methods": {
                "Monte Carlo": {
                    "keywords": ["Monte Carlo"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|employed|run|ran).*?Monte Carlo",
                    ]
                },
                "sensitivity analysis": {
                    "keywords": ["sensitivity analysis"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|employed).*?sensitivity\s+analysis",
                    ]
                },
                "bootstrap": {
                    "keywords": ["bootstrap"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied|employed).*?bootstrap",
                    ]
                },
                "confidence interval": {
                    "keywords": ["confidence interval", "95% CI"],
                    "usage_patterns": [
                        r"(?:was|were|using|calculated|computed|estimated|reported).*?(?:confidence interval|95% CI)",
                    ]
                },
            },
            "emission_accounting": {
                "IPCC method": {
                    "keywords": ["IPCC", "IPCC guidelines", "emission factor method"],
                    "usage_patterns": [
                        r"(?:was|were|using|based on|applied|adopted|followed|employed).*?(?:IPCC|emission factor)",
                        r"(?:IPCC|Tier \d).*?(?:methodology|approach|method|guideline)",
                    ]
                },
                "LCA": {
                    "keywords": ["life cycle assessment", "LCA"],
                    "usage_patterns": [
                        r"(?:was|were|using|based on|applied|adopted|conducted|performed).*?(?:life cycle assessment|LCA)",
                    ]
                },
                "carbon footprint": {
                    "keywords": ["carbon footprint"],
                    "usage_patterns": [
                        r"(?:was|were|using|calculated|computed|estimated|assessed|evaluated).*?carbon\s+footprint",
                    ]
                },
                "mass balance": {
                    "keywords": ["mass balance"],
                    "usage_patterns": [
                        r"(?:was|were|using|based on|applied|adopted).*?mass\s+balance",
                    ]
                },
                "operational data": {
                    "keywords": ["operational data", "ODIM"],
                    "usage_patterns": [
                        r"(?:was|were|using|based on|applied|adopted).*?(?:operational data|ODIM)",
                    ]
                },
            },
            "data_processing": {
                "normalization": {
                    "keywords": ["normalization", "standardization"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?(?:normalization|standardization)",
                    ]
                },
                "log transformation": {
                    "keywords": ["log transformation", "log-transform"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?(?:log transformation|log-transform)",
                        r"(?:data|values?|variables?).*?(?:were|was)\s+log-?transformed",
                    ]
                },
                "outlier detection": {
                    "keywords": ["outlier detection", "outlier removal"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?outlier",
                        r"outlier.*?(?:was|were|detected|removed|identified|excluded)",
                    ]
                },
                "missing data imputation": {
                    "keywords": ["imputation", "missing data", "gap filling"],
                    "usage_patterns": [
                        r"(?:was|were|using|performed|conducted|applied).*?(?:imputation|missing data|gap filling)",
                        r"(?:missing|gap).*?(?:data|values?).*?(?:were|was)\s+(?:imputed|filled|interpolated)",
                    ]
                },
            },
        }

    def identify(self, text: str, sections: Dict[str, str]) -> Dict[str, List[str]]:
        """识别论文中实际使用的方法"""
        methods = {
            "statistical_tests": [],
            "regression_methods": [],
            "machine_learning": [],
            "uncertainty_methods": [],
            "emission_accounting": [],
            "data_processing": [],
        }

        # 优先在Methods部分搜索
        methods_text = sections.get('methods', '')

        # 排除引用部分的文本
        text_without_refs = re.sub(r'(?i)References?.*$', '', text, flags=re.DOTALL)

        for category, method_defs in self.method_definitions.items():
            for method_name, method_info in method_defs.items():
                found = False

                # 策略1：在Methods部分搜索使用语境
                if methods_text:
                    for pattern in method_info['usage_patterns']:
                        if re.search(pattern, methods_text, re.IGNORECASE):
                            methods[category].append(method_name)
                            found = True
                            break

                # 策略2：如果Methods部分没找到，在全文中搜索严格语境
                if not found:
                    for pattern in method_info['usage_patterns']:
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
# 写作模式分析模块
# ============================================================
class WritingPatternAnalyzer:
    """写作模式分析器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

        # 过渡词
        self.transition_words = [
            'however', 'moreover', 'furthermore', 'in addition', 'consequently',
            'therefore', 'thus', 'nevertheless', 'in contrast', 'on the other hand',
            'similarly', 'likewise', 'in particular', 'specifically', 'for example',
            'for instance', 'in fact', 'indeed', 'notably', 'significantly',
        ]

        # 学术模糊语
        self.hedging_phrases = [
            'may', 'might', 'could', 'suggest', 'indicate', 'appear to',
            'it is likely', 'it is possible', 'to some extent', 'relatively',
            'approximately', 'roughly', 'about', 'around', 'estimated',
        ]

        # 强调语
        self.emphasis_phrases = [
            'clearly', 'obviously', 'evidently', 'significantly', 'remarkably',
            'notably', 'importantly', 'crucially', 'particularly', 'especially',
        ]

    def analyze(self, text: str) -> Dict:
        """分析写作模式"""
        patterns = {
            "transition_words": [],
            "hedging_phrases": [],
            "emphasis_phrases": [],
            "citation_patterns": [],
        }

        text_lower = text.lower()

        # 统计过渡词
        for word in self.transition_words:
            count = text_lower.count(word.lower())
            if count > 0:
                patterns["transition_words"].append({"word": word, "count": count})

        # 统计模糊语
        for phrase in self.hedging_phrases:
            count = text_lower.count(phrase.lower())
            if count > 0:
                patterns["hedging_phrases"].append({"phrase": phrase, "count": count})

        # 统计强调语
        for phrase in self.emphasis_phrases:
            count = text_lower.count(phrase.lower())
            if count > 0:
                patterns["emphasis_phrases"].append({"phrase": phrase, "count": count})

        # 引用模式
        citation_patterns = [
            (r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}\)', "Author (Year)"),
            (r'\[\d+(?:[-,]\d+)*\]', "[Number]"),
        ]
        for pat, fmt_name in citation_patterns:
            matches = re.findall(pat, text)
            if matches:
                patterns["citation_patterns"].append({
                    "format": fmt_name,
                    "count": len(matches),
                    "examples": matches[:3]
                })

        return patterns

# ============================================================
# 图表分析模块
# ============================================================
class FigureAnalyzer:
    """图表分析器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

        self.fig_type_patterns = {
            "box plot": r'box\s*plot|boxplot',
            "scatter plot": r'scatter\s*plot',
            "bar chart": r'bar\s*(?:chart|plot)',
            "line chart": r'line\s*(?:chart|plot)',
            "heatmap": r'heat\s*map',
            "pie chart": r'pie\s*chart',
            "violin plot": r'violin\s*plot',
            "forest plot": r'forest\s*plot',
        }

    def analyze(self, text: str, tables_data: List[Dict]) -> Dict:
        """分析图表信息"""
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
        text_lower = text.lower()
        for fig_type, pattern in self.fig_type_patterns.items():
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
# 主系统
# ============================================================
class LiteratureBatchReader:
    """文献批量阅读系统 - 优化版"""

    def __init__(self, literature_dir: str, output_dir: str, knowledge_dir: str):
        self.literature_dir = literature_dir
        self.output_dir = output_dir
        self.knowledge_dir = knowledge_dir

        # 创建目录
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(knowledge_dir, exist_ok=True)

        # 初始化日志
        self.logger = setup_logging(output_dir)

        # 初始化组件
        self.pdf_parser = PDFParser(self.logger)
        self.metadata_extractor = MetadataExtractor(self.logger)
        self.method_identifier = MethodIdentifier(self.logger)
        self.writing_analyzer = WritingPatternAnalyzer(self.logger)
        self.figure_analyzer = FigureAnalyzer(self.logger)

        # 断点续传文件
        self.checkpoint_file = os.path.join(output_dir, "checkpoint.json")

    def run(self, year_mapping: Optional[Dict] = None):
        """运行批量阅读"""
        self.logger.info("=" * 70)
        self.logger.info("文献批量阅读系统启动")
        self.logger.info(f"文献目录: {self.literature_dir}")
        self.logger.info("=" * 70)

        # 获取所有PDF文件
        pdf_files = sorted([
            os.path.join(self.literature_dir, f)
            for f in os.listdir(self.literature_dir)
            if f.endswith('.pdf')
        ])

        self.logger.info(f"发现 {len(pdf_files)} 篇PDF文献")

        # 加载断点
        checkpoint = self._load_checkpoint()
        start_idx = checkpoint.get('last_processed_idx', -1) + 1

        if start_idx > 0:
            self.logger.info(f"从断点继续: 第 {start_idx+1} 篇")

        # 批量分析
        all_results = checkpoint.get('results', [])
        errors = checkpoint.get('errors', [])

        for i, pdf_path in enumerate(pdf_files[start_idx:], start_idx + 1):
            result = self._analyze_single_paper(pdf_path, i, len(pdf_files))
            if result:
                all_results.append(result)
            else:
                errors.append(os.path.basename(pdf_path))

            # 每10篇保存一次断点
            if i % 10 == 0:
                self._save_checkpoint(i, all_results, errors)

        # 应用手动年份映射
        if year_mapping:
            self._apply_year_mapping(all_results, year_mapping)

        # 保存结果
        self._save_results(all_results, errors)

        # 打印总结
        self._print_summary(all_results, errors)

        return all_results

    def _analyze_single_paper(self, pdf_path: str, index: int, total: int) -> Optional[Dict]:
        """分析单篇论文"""
        filename = os.path.basename(pdf_path)
        self.logger.info(f"[{index}/{total}] 处理: {filename}")

        try:
            # 提取全文
            text = self.pdf_parser.extract_text(pdf_path, max_pages=20)
            if not text or len(text) < 200:
                self.logger.warning(f"[{index}/{total}] 文本过短，跳过: {filename}")
                return None

            # 提取表格
            tables_data = self.pdf_parser.extract_tables(pdf_path, max_pages=20)

            # 提取元数据
            meta = self.metadata_extractor.extract(text, filename)

            # 提取章节
            sections = self.pdf_parser.extract_sections(text)

            # 分析写作模式
            writing_patterns = self.writing_analyzer.analyze(text)

            # 识别分析方法
            analysis_methods = self.method_identifier.identify(text, sections)

            # 提取图表信息
            figure_info = self.figure_analyzer.analyze(text, tables_data)

            # 统计单词数
            word_count = len(text.split())

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

            # 输出成功信息
            methods_list = []
            for cat, mlist in analysis_methods.items():
                methods_list.extend(mlist)
            methods_str = ", ".join(methods_list[:5])

            self.logger.info(f"[{index}/{total}] 成功: {filename} ({word_count} 词, {len(tables_data)} 表格, 方法: {methods_str or 'none'})")

            return result

        except Exception as e:
            self.logger.error(f"[{index}/{total}] 处理失败 {filename}: {e}")
            return None

    def _load_checkpoint(self) -> Dict:
        """加载断点"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载断点失败: {e}")
        return {'last_processed_idx': -1, 'results': [], 'errors': []}

    def _save_checkpoint(self, last_idx: int, results: List, errors: List):
        """保存断点"""
        try:
            checkpoint = {
                'last_processed_idx': last_idx,
                'results': results,
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"保存断点失败: {e}")

    def _apply_year_mapping(self, results: List, year_mapping: Dict):
        """应用手动年份映射"""
        self.logger.info("应用手动年份映射...")
        fixed_count = 0

        for r in results:
            filename = r['metadata']['filename']

            # 尝试从文件名中提取编号
            for key, year in year_mapping.items():
                if key in filename:
                    old_year = r['metadata'].get('year', '')
                    r['metadata']['year'] = str(year)
                    if old_year != str(year):
                        self.logger.info(f"  年份修正: {r['index']}. {filename[:40]} {old_year} -> {year}")
                        fixed_count += 1
                    break

        self.logger.info(f"年份修正完成: {fixed_count} 篇")

    def _save_results(self, all_results: List, errors: List):
        """保存结果"""
        # 保存原始数据
        raw_data_path = os.path.join(self.output_dir, "all_papers_analysis.json")
        with open(raw_data_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        self.logger.info(f"原始数据已保存: {raw_data_path}")

        # 保存到知识库
        self._save_to_knowledge_store(all_results)

        # 删除断点文件
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            self.logger.info("断点文件已清理")

    def _save_to_knowledge_store(self, all_results: List):
        """保存到知识库"""
        # 写作模式
        writing_knowledge = {
            "last_updated": datetime.now().isoformat(),
            "papers_analyzed": len(all_results),
            "transition_words": {},
            "hedging_phrases": {},
            "emphasis_phrases": {},
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

        writing_path = os.path.join(self.knowledge_dir, "learned_writing_patterns.json")
        with open(writing_path, "w", encoding="utf-8") as f:
            json.dump(writing_knowledge, f, ensure_ascii=False, indent=2)
        self.logger.info(f"写作模式已保存: {writing_path}")

        # 分析方法
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

        methods_path = os.path.join(self.knowledge_dir, "learned_analysis_methods.json")
        with open(methods_path, "w", encoding="utf-8") as f:
            json.dump(methods_knowledge, f, ensure_ascii=False, indent=2)
        self.logger.info(f"分析方法已保存: {methods_path}")

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

        figure_path = os.path.join(self.knowledge_dir, "learned_figure_design.json")
        with open(figure_path, "w", encoding="utf-8") as f:
            json.dump(figure_knowledge, f, ensure_ascii=False, indent=2)
        self.logger.info(f"图表知识已保存: {figure_path}")

    def _print_summary(self, all_results: List, errors: List):
        """打印总结"""
        print("\n" + "=" * 70)
        print("  文献批量阅读完成!")
        print("=" * 70)
        print(f"  成功处理: {len(all_results)} 篇")
        print(f"  处理失败: {len(errors)} 篇")
        print(f"  输出目录: {self.output_dir}")
        print("=" * 70)

        # 年份分布
        year_counts = {}
        for r in all_results:
            year = r.get('metadata', {}).get('year', 'N/A')
            year_counts[year] = year_counts.get(year, 0) + 1

        print("\n  年份分布:")
        for y in sorted(year_counts.keys()):
            print(f"    {y}: {year_counts[y]} 篇")

        # 方法使用统计
        method_counts = {}
        for r in all_results:
            for cat, methods in r.get("analysis_methods", {}).items():
                for method in methods:
                    method_counts[method] = method_counts.get(method, 0) + 1

        if method_counts:
            print("\n  方法使用统计 (Top 10):")
            for method, count in sorted(method_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"    {method}: {count} 篇 ({count/len(all_results)*100:.1f}%)")

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 配置
    LITERATURE_DIR = r"D:\下载\文献数据整理\artical learning-agent train"
    OUTPUT_DIR = r"D:\VScode\firstcc\GHGs-WWTPs\output\literature_learning"
    KNOWLEDGE_DIR = r"D:\VScode\firstcc\GHGs-WWTPs\knowledge_store"

    # 年份映射（可选，用于手动修正）
    YEAR_MAPPING = {
        "(1)": 2020, "(2)": 2020, "(3)": 2020, "(4)": 2020, "(5)": 2020,
        "(6)": 2020, "(7)": 2020, "(8)": 2020,
        "(9)": 2021, "(10)": 2021, "(11)": 2021, "(12)": 2021, "(13)": 2021,
        "(14)": 2021, "(15)": 2021, "(16)": 2021, "(17)": 2021, "(18)": 2021,
        "(19)": 2021,
        "(20)": 2021, "(21)": 2022, "(22)": 2022, "(23)": 2022, "(24)": 2022,
        "(25)": 2022, "(26)": 2022, "(27)": 2022, "(28)": 2022, "(29)": 2022,
        "(30)": 2022, "(31)": 2022, "(32)": 2022, "(33)": 2022, "(34)": 2022,
        "(35)": 2023, "(36)": 2023, "(37)": 2023, "(38)": 2023, "(39)": 2023,
        "(40)": 2023, "(41)": 2023, "(42)": 2023, "(43)": 2023, "(44)": 2023,
        "(45)": 2023, "(46)": 2023, "(47)": 2023, "(48)": 2023, "(49)": 2023,
        "(50)": 2023, "(51)": 2023, "(52)": 2023, "(53)": 2023,
        "(54)": 2024, "(55)": 2024, "(56)": 2024, "(57)": 2024, "(58)": 2024,
        "(59)": 2024, "(60)": 2024, "(61)": 2024, "(62)": 2024, "(63)": 2024,
        "(64)": 2023, "(65)": 2024, "(66)": 2024, "(67)": 2024, "(68)": 2024,
        "(69)": 2024, "(70)": 2024, "(71)": 2024, "(72)": 2024, "(73)": 2024,
        "(74)": 2024, "(75)": 2024, "(76)": 2024, "(77)": 2024, "(78)": 2024,
        "(79)": 2024, "(80)": 2024,
        "(81)": 2025, "(82)": 2025, "(83)": 2025, "(84)": 2025, "(85)": 2025,
        "(86)": 2025, "(87)": 2025, "(88)": 2025, "(89)": 2025, "(90)": 2025,
        "(91)": 2025, "(92)": 2025, "(93)": 2025, "(94)": 2025, "(95)": 2025,
        "(96)": 2025, "(97)": 2025, "(98)": 2025, "(99)": 2025, "(100)": 2025,
        "(101)": 2025, "(102)": 2025, "(103)": 2025, "(104)": 2025, "(105)": 2025,
        "(106)": 2025, "(107)": 2025, "(108)": 2025, "(109)": 2025, "(110)": 2025,
        "(111)": 2026, "(112)": 2026, "(113)": 2026, "(114)": 2026, "(115)": 2026,
        "(116)": 2026, "(117)": 2026,
    }

    # 运行
    reader = LiteratureBatchReader(LITERATURE_DIR, OUTPUT_DIR, KNOWLEDGE_DIR)
    results = reader.run(year_mapping=YEAR_MAPPING)
