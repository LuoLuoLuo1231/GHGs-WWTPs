"""
通用文献批量阅读系统 v4.0

特点：
1. 通用化设计：支持任意领域的文献阅读
2. 可配置方法库：通过配置文件定义领域特定方法
3. 可扩展架构：轻松添加新领域和新方法
4. 智能识别：自动识别常见方法，支持自定义方法
5. 多领域支持：环境、医学、工程、社会科学等

使用方式：
1. 选择预设领域配置
2. 或创建自定义领域配置
3. 运行批量阅读
4. 生成领域报告
"""

import os
import sys
import json
import re
import logging
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Any

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 领域配置系统
# ============================================================

class DomainConfig:
    """领域配置管理器"""

    # 预设领域配置
    PRESET_DOMAINS = {
        "environmental_ghg": {
            "name": "环境-温室气体排放",
            "description": "污水处理、温室气体排放、碳足迹相关研究",
            "keywords": ["greenhouse gas", "GHG", "wastewater", "emission", "carbon footprint", "CO2", "CH4", "N2O"],
            "method_categories": {
                "emission_accounting": {
                    "name": "排放核算",
                    "methods": {
                        "IPCC method": {
                            "keywords": ["IPCC", "IPCC guidelines", "emission factor"],
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
                    }
                },
            }
        },

        "sewer_carbon": {
            "name": "污水管网碳排放",
            "description": "污水管网系统碳排放、甲烷排放、碳转化相关研究",
            "keywords": ["sewer", "pipeline", "drainage", "methane", "carbon emission", "fugitive emission"],
            "method_categories": {
                "emission_measurement": {
                    "name": "排放测量",
                    "methods": {
                        "floating chamber": {
                            "keywords": ["floating chamber", "flux chamber", "hood method"],
                            "usage_patterns": [
                                r"(?:was|were|using|measured|collected|applied).*?(?:floating chamber|flux chamber|hood)",
                            ]
                        },
                        "eddy covariance": {
                            "keywords": ["eddy covariance", "eddy correlation"],
                            "usage_patterns": [
                                r"(?:was|were|using|measured|applied).*?(?:eddy covariance|eddy correlation)",
                            ]
                        },
                        "tracer gas": {
                            "keywords": ["tracer gas", "SF6", "N2O tracer"],
                            "usage_patterns": [
                                r"(?:was|were|using|measured|applied).*?(?:tracer gas|SF6|N2O\s+tracer)",
                            ]
                        },
                        "direct measurement": {
                            "keywords": ["direct measurement", "direct monitoring", "continuous monitoring"],
                            "usage_patterns": [
                                r"(?:was|were|using|measured|conducted|performed).*?(?:direct measurement|direct monitoring|continuous monitoring)",
                            ]
                        },
                    }
                },
                "process_modeling": {
                    "name": "过程建模",
                    "methods": {
                        "sewage process model": {
                            "keywords": ["sewage process model", "SPM", "biofilm model"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|applied|implemented).*?(?:sewage process model|SPM|biofilm model)",
                            ]
                        },
                        "ASM": {
                            "keywords": ["activated sludge model", "ASM1", "ASM2", "ASM3"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|applied|implemented).*?(?:activated sludge model|ASM[123]?)",
                            ]
                        },
                        "CFD": {
                            "keywords": ["computational fluid dynamics", "CFD"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|applied|implemented).*?(?:computational fluid dynamics|CFD)",
                            ]
                        },
                    }
                },
            }
        },

        "medical_clinical": {
            "name": "医学-临床研究",
            "description": "临床试验、队列研究、病例对照研究等",
            "keywords": ["clinical trial", "cohort", "case-control", "randomized", "patient", "treatment"],
            "method_categories": {
                "study_design": {
                    "name": "研究设计",
                    "methods": {
                        "RCT": {
                            "keywords": ["randomized controlled trial", "RCT", "randomized trial"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|designed).*?(?:randomized controlled trial|RCT|randomized trial)",
                            ]
                        },
                        "cohort study": {
                            "keywords": ["cohort study", "prospective cohort", "retrospective cohort"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|designed).*?(?:cohort study|prospective cohort|retrospective cohort)",
                            ]
                        },
                        "case-control": {
                            "keywords": ["case-control study", "case control"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|designed).*?(?:case-control study|case control)",
                            ]
                        },
                        "meta-analysis": {
                            "keywords": ["meta-analysis", "systematic review"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|designed).*?(?:meta-analysis|systematic review)",
                            ]
                        },
                    }
                },
                "statistical_methods": {
                    "name": "统计方法",
                    "methods": {
                        "survival analysis": {
                            "keywords": ["survival analysis", "Kaplan-Meier", "Cox regression"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:survival analysis|Kaplan-Meier|Cox regression)",
                            ]
                        },
                        "logistic regression": {
                            "keywords": ["logistic regression", "odds ratio"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:logistic regression|odds ratio)",
                            ]
                        },
                        "propensity score": {
                            "keywords": ["propensity score", "PSM", "propensity matching"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:propensity score|PSM|propensity matching)",
                            ]
                        },
                    }
                },
            }
        },

        "engineering_optimization": {
            "name": "工程优化",
            "description": "工艺优化、参数优化、多目标优化等",
            "keywords": ["optimization", "process optimization", "parameter", "response surface", "Taguchi"],
            "method_categories": {
                "optimization_methods": {
                    "name": "优化方法",
                    "methods": {
                        "RSM": {
                            "keywords": ["response surface methodology", "RSM", "response surface"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:response surface methodology|RSM|response surface)",
                            ]
                        },
                        "Taguchi": {
                            "keywords": ["Taguchi method", "Taguchi design", "orthogonal array"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:Taguchi method|Taguchi design|orthogonal array)",
                            ]
                        },
                        "genetic algorithm": {
                            "keywords": ["genetic algorithm", "GA", "evolutionary algorithm"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:genetic algorithm|GA|evolutionary algorithm)",
                            ]
                        },
                        "particle swarm": {
                            "keywords": ["particle swarm optimization", "PSO"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:particle swarm optimization|PSO)",
                            ]
                        },
                    }
                },
                "experimental_design": {
                    "name": "实验设计",
                    "methods": {
                        "factorial design": {
                            "keywords": ["factorial design", "full factorial", "fractional factorial"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:factorial design|full factorial|fractional factorial)",
                            ]
                        },
                        "central composite": {
                            "keywords": ["central composite design", "CCD"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:central composite design|CCD)",
                            ]
                        },
                        "Box-Behnken": {
                            "keywords": ["Box-Behnken design", "BBD"],
                            "usage_patterns": [
                                r"(?:was|were|using|conducted|performed|applied).*?(?:Box-Behnken design|BBD)",
                            ]
                        },
                    }
                },
            }
        },

        "machine_learning": {
            "name": "机器学习/AI",
            "description": "机器学习、深度学习、数据挖掘等",
            "keywords": ["machine learning", "deep learning", "neural network", "prediction", "classification"],
            "method_categories": {
                "ml_methods": {
                    "name": "机器学习方法",
                    "methods": {
                        "random forest": {
                            "keywords": ["random forest", "RF", "Random Forest"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:random forest|RF model|RF algorithm)",
                                r"(?:random forest|RF).*?(?:regression|classification|model|predictor)",
                            ]
                        },
                        "neural network": {
                            "keywords": ["neural network", "ANN", "artificial neural network"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:neural network|ANN)",
                            ]
                        },
                        "deep learning": {
                            "keywords": ["deep learning", "CNN", "RNN", "LSTM", "GRU", "transformer"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:deep learning|CNN|RNN|LSTM|GRU|transformer)",
                            ]
                        },
                        "SVM": {
                            "keywords": ["support vector machine", "SVM", "SVR"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:support vector|SVM|SVR)",
                            ]
                        },
                        "gradient boosting": {
                            "keywords": ["gradient boosting", "XGBoost", "LightGBM", "GBM"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:gradient boosting|XGBoost|LightGBM|GBM)",
                            ]
                        },
                    }
                },
                "deep_learning": {
                    "name": "深度学习",
                    "methods": {
                        "CNN": {
                            "keywords": ["convolutional neural network", "CNN"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:convolutional neural network|CNN)",
                            ]
                        },
                        "RNN/LSTM": {
                            "keywords": ["recurrent neural network", "RNN", "LSTM", "GRU"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:recurrent neural network|RNN|LSTM|GRU)",
                            ]
                        },
                        "Transformer": {
                            "keywords": ["transformer", "attention mechanism", "BERT", "GPT"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:transformer|attention mechanism|BERT|GPT)",
                            ]
                        },
                        "GAN": {
                            "keywords": ["generative adversarial network", "GAN"],
                            "usage_patterns": [
                                r"(?:was|were|using|developed|trained|built|implemented|applied).*?(?:generative adversarial network|GAN)",
                            ]
                        },
                    }
                },
            }
        },

        "statistics_general": {
            "name": "通用统计方法",
            "description": "通用统计检验、回归分析等（适用于所有领域）",
            "keywords": [],  # 通用，不限定关键词
            "method_categories": {
                "statistical_tests": {
                    "name": "统计检验",
                    "methods": {
                        "ANOVA": {
                            "keywords": ["ANOVA", "analysis of variance"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied|employed).*?(?:ANOVA|analysis of variance)",
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
                            ]
                        },
                        "Chi-square": {
                            "keywords": ["chi-square", "χ²"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied).*?(?:chi-square|χ²)",
                            ]
                        },
                        "Shapiro-Wilk": {
                            "keywords": ["Shapiro-Wilk"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied).*?Shapiro",
                            ]
                        },
                    }
                },
                "regression": {
                    "name": "回归分析",
                    "methods": {
                        "linear regression": {
                            "keywords": ["linear regression", "OLS"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied|fitted|developed).*?(?:linear regression|OLS)",
                            ]
                        },
                        "multiple regression": {
                            "keywords": ["multiple regression"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied|fitted|developed).*?multiple\s+regression",
                            ]
                        },
                        "logistic regression": {
                            "keywords": ["logistic regression"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied|fitted|developed).*?logistic\s+regression",
                            ]
                        },
                        "polynomial regression": {
                            "keywords": ["polynomial regression"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied|fitted|developed).*?polynomial\s+regression",
                            ]
                        },
                    }
                },
                "dimensionality_reduction": {
                    "name": "降维方法",
                    "methods": {
                        "PCA": {
                            "keywords": ["PCA", "principal component analysis"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied).*?(?:PCA|principal component)",
                            ]
                        },
                        "factor analysis": {
                            "keywords": ["factor analysis"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied).*?factor\s+analysis",
                            ]
                        },
                    }
                },
                "uncertainty": {
                    "name": "不确定性分析",
                    "methods": {
                        "Monte Carlo": {
                            "keywords": ["Monte Carlo"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied).*?Monte\s+Carlo",
                            ]
                        },
                        "sensitivity analysis": {
                            "keywords": ["sensitivity analysis"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied).*?sensitivity\s+analysis",
                            ]
                        },
                        "bootstrap": {
                            "keywords": ["bootstrap"],
                            "usage_patterns": [
                                r"(?:was|were|using|performed|conducted|applied).*?bootstrap",
                            ]
                        },
                    }
                },
            }
        },
    }

    @classmethod
    def get_domain_config(cls, domain_name: str) -> Dict:
        """获取领域配置"""
        if domain_name in cls.PRESET_DOMAINS:
            return cls.PRESET_DOMAINS[domain_name]
        else:
            raise ValueError(f"未知领域: {domain_name}，可用领域: {list(cls.PRESET_DOMAINS.keys())}")

    @classmethod
    def list_domains(cls) -> List[str]:
        """列出所有可用领域"""
        return list(cls.PRESET_DOMAINS.keys())

    @classmethod
    def get_domain_info(cls, domain_name: str) -> str:
        """获取领域描述"""
        if domain_name in cls.PRESET_DOMAINS:
            config = cls.PRESET_DOMAINS[domain_name]
            return f"{config['name']}: {config['description']}"
        return "未知领域"

    @classmethod
    def create_custom_config(cls, name: str, description: str, keywords: List[str],
                             method_categories: Dict) -> Dict:
        """创建自定义领域配置"""
        return {
            "name": name,
            "description": description,
            "keywords": keywords,
            "method_categories": method_categories,
        }

    @classmethod
    def load_custom_config(cls, config_file: str) -> Dict:
        """从文件加载自定义配置"""
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def load_domain_from_domains_dir(cls, domain_name: str, domains_dir: str = None) -> Dict:
        """
        从domains目录加载领域配置

        Parameters:
        -----------
        domain_name : str
            领域名称（不含.json后缀）
        domains_dir : str, optional
            domains目录路径，默认为脚本所在目录下的domains文件夹

        Returns:
        --------
        Dict
            领域配置
        """
        if domains_dir is None:
            # 默认使用脚本所在目录下的domains文件夹
            script_dir = os.path.dirname(os.path.abspath(__file__))
            domains_dir = os.path.join(script_dir, "domains")

        config_file = os.path.join(domains_dir, f"{domain_name}.json")

        if not os.path.exists(config_file):
            # 如果domains目录下没有，检查预设领域
            if domain_name in cls.PRESET_DOMAINS:
                return cls.PRESET_DOMAINS[domain_name]
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        return cls.load_custom_config(config_file)

    @classmethod
    def save_custom_config(cls, config: Dict, config_file: str):
        """保存自定义配置到文件"""
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

# ============================================================
# 通用方法识别器
# ============================================================

class UniversalMethodIdentifier:
    """通用方法识别器"""

    def __init__(self, domain_config: Dict, logger: logging.Logger):
        self.domain_config = domain_config
        self.logger = logger
        self.method_categories = domain_config.get('method_categories', {})

    def identify(self, text: str, sections: Dict[str, str]) -> Dict[str, List[str]]:
        """识别论文中实际使用的方法"""
        methods = {}
        for category in self.method_categories:
            methods[category] = []

        # 优先在Methods部分搜索
        methods_text = sections.get('methods', '')

        # 排除引用部分的文本
        text_without_refs = re.sub(r'(?i)References?.*$', '', text, flags=re.DOTALL)

        for category, category_config in self.method_categories.items():
            for method_name, method_config in category_config.get('methods', {}).items():
                found = False

                # 策略1：在Methods部分搜索使用语境
                if methods_text:
                    for pattern in method_config.get('usage_patterns', []):
                        if re.search(pattern, methods_text, re.IGNORECASE):
                            methods[category].append(method_name)
                            found = True
                            break

                # 策略2：如果Methods部分没找到，在全文中搜索严格语境
                if not found:
                    for pattern in method_config.get('usage_patterns', []):
                        strict_patterns = [
                            r"(?:we|this study|the present study).*?(?:used|applied|employed|adopted|performed|conducted|developed|trained|built|implemented).*?" + re.escape(method_name),
                            r"(?:was|were).*?(?:used|applied|employed|adopted|performed|conducted|developed|trained|built|implemented).*?" + re.escape(method_name),
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
# 通用PDF解析器
# ============================================================

class UniversalPDFParser:
    """通用PDF解析器"""

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
        """提取论文各章节

        优化点：
        1. 放宽正则匹配条件，支持更多格式
        2. 处理PDF提取中常见的字母间空格问题（如"A B S T R A C T"）
        3. 增加章节内容长度限制到20000字符
        4. 支持数字编号和无编号的章节标题
        """
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

        # 预处理：处理PDF提取中常见的字母间空格问题
        # 例如 "A B S T R A C T" -> "ABSTRACT"
        # 但要小心不要破坏正常的单词
        def normalize_text(text):
            """规范化文本，处理PDF提取的格式问题"""
            # 处理常见的带空格的标题
            replacements = {
                'A R T I C L E  I N F O': 'ARTICLE INFO',
                'A B S T R A C T': 'ABSTRACT',
                'I N T R O D U C T I O N': 'INTRODUCTION',
                'M E T H O D S': 'METHODS',
                'R E S U L T S': 'RESULTS',
                'D I S C U S S I O N': 'DISCUSSION',
                'C O N C L U S I O N': 'CONCLUSION',
                'R E F E R E N C E S': 'REFERENCES',
                'M A T E R I A L S  A N D  M E T H O D S': 'MATERIALS AND METHODS',
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text

        text = normalize_text(text)

        # 优化后的正则表达式：放宽匹配条件
        section_patterns = {
            'abstract': [
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?Abstract\s*',
                r'(?i)Abstract\s*(?:\n|:)',
                r'(?i)(?:^|\n)\s*摘要',
            ],
            'introduction': [
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?Introduction\s*',
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?INTRODUCTION\s*',
            ],
            'methods': [
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?(?:Methods?|Materials?\s*(?:and|&)\s*Methods?|Methodology|Experimental)\s*',
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?(?:MATERIALS?\s+AND\s+METHODS?)\s*',
            ],
            'results': [
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?(?:Results?(?:\s*(?:and|&)\s*Discussion)?)\s*',
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?RESULTS?\s*',
            ],
            'discussion': [
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?Discussion\s*',
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?DISCUSSION\s*',
            ],
            'conclusion': [
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?(?:Conclusions?|Summary|Concluding\s+Remarks)\s*',
                r'(?i)(?:^|\n)\s*(?:\d+\.?\s*)?(?:CONCLUSIONS?|SUMMARY)\s*',
            ],
            'references': [
                r'(?i)(?:^|\n)\s*(?:References?|Bibliography|REFERENCES?)\s*',
            ],
        }

        # 找到所有章节标题的位置
        positions = []
        for section_name, patterns in section_patterns.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, text))
                if matches:
                    # 取第一个匹配
                    start = matches[0].start()
                    # 放宽验证条件：PDF提取的文本格式不太规整
                    # 允许：行首、换行后、空格后、标点符号后、或者紧跟在其他内容后面
                    # 主要目的是避免在单词中间匹配（如"methods"在"measurements"中间）
                    if start == 0 or text[start-1] in '\n\r \t.,;:()[]{}':
                        positions.append((start, section_name))
                        break  # 找到就跳出，不再尝试其他模式
                    # 额外检查：如果前面是字母，检查是否是完整的单词
                    elif text[start-1].isalpha():
                        # 检查前面是否是完整的单词
                        word_before = ''
                        idx = start - 1
                        while idx >= 0 and text[idx].isalpha():
                            word_before = text[idx] + word_before
                            idx -= 1
                        # 如果前面的单词是常见的非标题词，跳过
                        skip_words = ['the', 'and', 'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by']
                        if word_before.lower() not in skip_words:
                            positions.append((start, section_name))
                            break

        # 按位置排序
        positions.sort(key=lambda x: x[0])

        # 去重：同一章节只保留第一个
        seen = set()
        unique_positions = []
        for pos, name in positions:
            if name not in seen:
                seen.add(name)
                unique_positions.append((pos, name))

        # 提取各章节内容
        for i, (start, section_name) in enumerate(unique_positions):
            if i + 1 < len(unique_positions):
                end = unique_positions[i + 1][0]
            else:
                # 最后一个章节，取到references之前或文本末尾
                ref_match = re.search(r'(?i)\b(?:References?|Bibliography|REFERENCES?)\b', text[start+100:])
                if ref_match:
                    end = start + 100 + ref_match.start()
                else:
                    end = len(text)

            section_text = text[start:end].strip()

            # 去掉章节标题行
            lines = section_text.split('\n', 1)
            if len(lines) > 1:
                section_text = lines[1].strip()

            # 增加长度限制到20000字符
            sections[section_name] = section_text[:20000]

        # 如果methods为空，尝试用关键词提取
        if not sections['methods']:
            method_paragraphs = []
            paragraphs = text.split('\n\n')
            for para in paragraphs:
                if re.search(r'(?i)(?:method|experimental|procedure|sampling|analysis|样品|实验|方法)', para[:300]):
                    method_paragraphs.append(para)
            if method_paragraphs:
                sections['methods'] = '\n\n'.join(method_paragraphs[:10])

        # 如果abstract为空，尝试更灵活的提取方式
        if not sections['abstract']:
            # 策略1：查找Introduction之前的内容
            intro_patterns = [r'(?i)\bIntroduction\b', r'(?i)\bINTRODUCTION\b', r'(?i)\n\s*1\.\s+Introduction']
            for pattern in intro_patterns:
                intro_match = re.search(pattern, text)
                if intro_match:
                    intro_pos = intro_match.start()
                    pre_intro = text[:intro_pos].strip()
                    # 在Introduction之前查找Abstract
                    abstract_patterns = [r'(?i)\bAbstract\b', r'(?i)\bABSTRACT\b', r'(?i)摘要']
                    for abs_pattern in abstract_patterns:
                        abs_match = re.search(abs_pattern, pre_intro)
                        if abs_match:
                            abstract_text = pre_intro[abs_match.end():].strip()
                            # 去掉可能的冒号开头
                            if abstract_text.startswith(':'):
                                abstract_text = abstract_text[1:].strip()
                            sections['abstract'] = abstract_text[:5000]
                            break
                    break

        return sections

# ============================================================
# 通用元数据提取器
# ============================================================

class UniversalMetadataExtractor:
    """通用元数据提取器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def extract(self, text: str, filename: str, domain_keywords: List[str] = None) -> Dict:
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
            "domain_relevance": 0.0,
        }

        # 标题
        lines = text.split("\n")
        clean_lines = [l.strip() for l in lines if l.strip()]
        for line in clean_lines[:10]:
            if len(line) > 20 and not line.startswith("http") and "doi" not in line.lower():
                meta["title"] = line[:200]
                break

        # 年份
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

        # 计算领域相关度
        if domain_keywords:
            meta["domain_relevance"] = self._calculate_relevance(text, domain_keywords)

        return meta

    def _extract_year(self, text: str, filename: str) -> str:
        """提取年份"""
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
                if 1990 <= candidate <= 2030:  # 放宽年份范围
                    year = str(candidate)
                    break

        # 策略2：匹配期刊引用格式
        if not year:
            journal_cite_patterns = [
                r'\((\d{4})\)\s*\d+[-–]\d+',
                r'Vol\.\s*\d+.*?\((\d{4})\)',
            ]
            for pat in journal_cite_patterns:
                m = re.search(pat, text[:6000], re.IGNORECASE)
                if m:
                    candidate = int(m.group(1))
                    if 1990 <= candidate <= 2030:
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
                    if 1990 <= candidate <= 2030:
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
                    if 1990 <= candidate <= 2030:
                        year = str(candidate)
                        break

        return year or ""

    def _calculate_relevance(self, text: str, keywords: List[str]) -> float:
        """计算领域相关度（0-1）"""
        if not keywords:
            return 1.0

        text_lower = text.lower()
        match_count = 0
        for kw in keywords:
            if kw.lower() in text_lower:
                match_count += 1

        return match_count / len(keywords) if keywords else 1.0

# ============================================================
# 通用写作模式分析器
# ============================================================

class UniversalWritingAnalyzer:
    """通用写作模式分析器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

        self.transition_words = [
            'however', 'moreover', 'furthermore', 'in addition', 'consequently',
            'therefore', 'thus', 'nevertheless', 'in contrast', 'on the other hand',
            'similarly', 'likewise', 'in particular', 'specifically', 'for example',
            'for instance', 'in fact', 'indeed', 'notably', 'significantly',
        ]

        self.hedging_phrases = [
            'may', 'might', 'could', 'suggest', 'indicate', 'appear to',
            'it is likely', 'it is possible', 'to some extent', 'relatively',
            'approximately', 'roughly', 'about', 'around', 'estimated',
        ]

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

        for word in self.transition_words:
            count = text_lower.count(word.lower())
            if count > 0:
                patterns["transition_words"].append({"word": word, "count": count})

        for phrase in self.hedging_phrases:
            count = text_lower.count(phrase.lower())
            if count > 0:
                patterns["hedging_phrases"].append({"phrase": phrase, "count": count})

        for phrase in self.emphasis_phrases:
            count = text_lower.count(phrase.lower())
            if count > 0:
                patterns["emphasis_phrases"].append({"phrase": phrase, "count": count})

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
                })

        return patterns

# ============================================================
# 通用图表分析器
# ============================================================

class UniversalFigureAnalyzer:
    """通用图表分析器"""

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
            "radar chart": r'radar|spider\s*chart',
            "contour plot": r'contour',
            "3D plot": r'3D\s*plot|surface\s*plot',
            "flow chart": r'flow\s*(?:chart|diagram)',
            "schematic": r'schematic|diagram',
        }

    def analyze(self, text: str, tables_data: List[Dict]) -> Dict:
        """分析图表信息"""
        figures = {
            "figure_count": 0,
            "table_count": 0,
            "figure_types": [],
            "table_complexity": [],
        }

        fig_numbers = set()
        for pat in [r'(?:Fig\.|Figure|FIG\.|fig\.)\s*(\d+)', r'图\s*(\d+)']:
            fig_numbers.update(re.findall(pat, text))

        tab_numbers = set()
        for pat in [r'(?:Table|TABLE|Tab\.)\s*(\d+)', r'表\s*(\d+)']:
            tab_numbers.update(re.findall(pat, text))

        figures["figure_count"] = len(fig_numbers)
        figures["table_count"] = len(tab_numbers) + len(tables_data)

        text_lower = text.lower()
        for fig_type, pattern in self.fig_type_patterns.items():
            if re.search(pattern, text_lower):
                figures["figure_types"].append(fig_type)

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
# 通用文献批量阅读系统
# ============================================================

class UniversalLiteratureReader:
    """通用文献批量阅读系统"""

    def __init__(self, literature_dir: str, output_dir: str, knowledge_dir: str,
                 domain_name: str = None, custom_config: Dict = None,
                 domains_dir: str = None):
        """
        初始化阅读器

        Parameters:
        -----------
        literature_dir : str
            文献目录
        output_dir : str
            输出目录
        knowledge_dir : str
            知识库目录
        domain_name : str
            预设领域名称（可选）
        custom_config : Dict
            自定义领域配置（可选）
        domains_dir : str, optional
            领域配置目录路径（可选）
        """
        self.literature_dir = literature_dir
        self.output_dir = output_dir
        self.knowledge_dir = knowledge_dir

        # 创建目录
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(knowledge_dir, exist_ok=True)

        # 初始化日志
        self.logger = self._setup_logging()

        # 加载领域配置
        if custom_config:
            self.domain_config = custom_config
        elif domain_name:
            # 优先从domains目录加载
            try:
                self.domain_config = DomainConfig.load_domain_from_domains_dir(domain_name, domains_dir)
                self.logger.info(f"从domains目录加载配置: {domain_name}")
            except FileNotFoundError:
                # 如果domains目录没有，使用预设配置
                self.domain_config = DomainConfig.get_domain_config(domain_name)
                self.logger.info(f"使用预设配置: {domain_name}")
        else:
            # 默认使用通用统计方法
            self.domain_config = DomainConfig.get_domain_config("statistics_general")

        self.logger.info(f"领域配置: {self.domain_config.get('name', '自定义')}")

        # 初始化组件
        self.pdf_parser = UniversalPDFParser(self.logger)
        self.metadata_extractor = UniversalMetadataExtractor(self.logger)
        self.method_identifier = UniversalMethodIdentifier(self.domain_config, self.logger)
        self.writing_analyzer = UniversalWritingAnalyzer(self.logger)
        self.figure_analyzer = UniversalFigureAnalyzer(self.logger)

        # 断点续传文件
        self.checkpoint_file = os.path.join(output_dir, "checkpoint.json")

    def _setup_logging(self) -> logging.Logger:
        """配置日志系统"""
        log_file = os.path.join(self.output_dir, f"reader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        logger = logging.getLogger('UniversalLiteratureReader')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setLevel(logging.INFO)

            ch = logging.StreamHandler()
            ch.setLevel(logging.WARNING)

            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)

            logger.addHandler(fh)
            logger.addHandler(ch)

        return logger

    def run(self, year_mapping: Optional[Dict] = None,
            max_papers: Optional[int] = None) -> List[Dict]:
        """
        运行批量阅读

        Parameters:
        -----------
        year_mapping : Dict, optional
            手动年份映射
        max_papers : int, optional
            最大处理论文数（None表示全部）

        Returns:
        --------
        List[Dict]
            分析结果列表
        """
        self.logger.info("=" * 70)
        self.logger.info("通用文献批量阅读系统启动")
        self.logger.info(f"文献目录: {self.literature_dir}")
        self.logger.info(f"领域: {self.domain_config.get('name', '自定义')}")
        self.logger.info("=" * 70)

        # 获取所有PDF文件
        pdf_files = sorted([
            os.path.join(self.literature_dir, f)
            for f in os.listdir(self.literature_dir)
            if f.endswith('.pdf')
        ])

        if max_papers:
            pdf_files = pdf_files[:max_papers]

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

        try:
            # 提取全文
            text = self.pdf_parser.extract_text(pdf_path)
            if not text or len(text) < 200:
                self.logger.warning(f"[{index}/{total}] 文本过短，跳过: {filename}")
                return None

            # 提取表格
            tables_data = self.pdf_parser.extract_tables(pdf_path)

            # 提取元数据
            domain_keywords = self.domain_config.get('keywords', [])
            meta = self.metadata_extractor.extract(text, filename, domain_keywords)

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
                "sections": sections,  # 保存实际的章节内容
                "sections_available": {k: bool(v) for k, v in sections.items()},  # 同时保留布尔值
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

            self.logger.info(f"[{index}/{total}] 成功: {filename[:40]} ({word_count} 词, 方法: {methods_str or 'none'})")

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
            for key, year in year_mapping.items():
                if key in filename:
                    old_year = r['metadata'].get('year', '')
                    r['metadata']['year'] = str(year)
                    if old_year != str(year):
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

        # 保存领域配置
        config_path = os.path.join(self.output_dir, "domain_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.domain_config, f, ensure_ascii=False, indent=2)

        # 保存到知识库
        self._save_to_knowledge_store(all_results)

        # 删除断点文件
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)

    def _save_to_knowledge_store(self, all_results: List):
        """保存到知识库"""
        # 写作模式
        writing_knowledge = {
            "last_updated": datetime.now().isoformat(),
            "papers_analyzed": len(all_results),
            "domain": self.domain_config.get('name', 'unknown'),
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

        # 分析方法
        methods_knowledge = {
            "last_updated": datetime.now().isoformat(),
            "papers_analyzed": len(all_results),
            "domain": self.domain_config.get('name', 'unknown'),
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

        # 图表知识
        figure_knowledge = {
            "last_updated": datetime.now().isoformat(),
            "papers_analyzed": len(all_results),
            "domain": self.domain_config.get('name', 'unknown'),
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

    def _print_summary(self, all_results: List, errors: List):
        """打印总结"""
        print("\n" + "=" * 70)
        print("  文献批量阅读完成!")
        print("=" * 70)
        print(f"  领域: {self.domain_config.get('name', '自定义')}")
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

        # 领域相关度
        relevance_scores = [r.get('metadata', {}).get('domain_relevance', 0) for r in all_results]
        if relevance_scores:
            avg_relevance = sum(relevance_scores) / len(relevance_scores)
            print(f"\n  平均领域相关度: {avg_relevance:.2%}")

# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  通用文献批量阅读系统 v4.0")
    print("=" * 70)
    print()
    print("可用领域:")
    for domain in DomainConfig.list_domains():
        print(f"  - {domain}: {DomainConfig.get_domain_info(domain)}")
    print()
    print("使用示例:")
    print("""
    from literature_batch_reader_universal import UniversalLiteratureReader

    # 示例1：使用预设领域
    reader = UniversalLiteratureReader(
        literature_dir=r"D:\\文献目录",
        output_dir=r"D:\\输出目录",
        knowledge_dir=r"D:\\知识库目录",
        domain_name="environmental_ghg"  # 或其他领域
    )
    results = reader.run()

    # 示例2：使用自定义配置
    custom_config = {
        "name": "自定义领域",
        "description": "我的研究领域",
        "keywords": ["keyword1", "keyword2"],
        "method_categories": {
            "my_methods": {
                "name": "我的方法",
                "methods": {
                    "method1": {
                        "keywords": ["method1"],
                        "usage_patterns": [r"used method1"]
                    }
                }
            }
        }
    }
    reader = UniversalLiteratureReader(
        literature_dir=r"D:\\文献目录",
        output_dir=r"D:\\输出目录",
        knowledge_dir=r"D:\\知识库目录",
        custom_config=custom_config
    )
    results = reader.run()
    """)
