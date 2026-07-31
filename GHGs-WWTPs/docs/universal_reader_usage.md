# 通用文献批量阅读系统 - 使用指南

## 系统特点

1. **通用化设计**：支持任意领域的文献阅读
2. **可配置方法库**：通过配置文件定义领域特定方法
3. **可扩展架构**：轻松添加新领域和新方法
4. **智能识别**：自动识别常见方法，支持自定义方法
5. **多领域支持**：环境、医学、工程、社会科学等

## 预设领域

| 领域代码 | 名称 | 适用范围 |
|----------|------|----------|
| `environmental_ghg` | 环境-温室气体排放 | 污水处理、温室气体排放、碳足迹 |
| `sewer_carbon` | 污水管网碳排放 | 污水管网系统碳排放、甲烷排放 |
| `medical_clinical` | 医学-临床研究 | 临床试验、队列研究、病例对照研究 |
| `engineering_optimization` | 工程优化 | 工艺优化、参数优化、多目标优化 |
| `machine_learning` | 机器学习/AI | 机器学习、深度学习、数据挖掘 |
| `statistics_general` | 通用统计方法 | 通用统计检验、回归分析 |

## 使用方法

### 方法1：使用预设领域

```python
from literature_batch_reader_universal import UniversalLiteratureReader

# 创建阅读器
reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\污水管网文献",
    output_dir=r"D:\VScode\firstcc\output\sewer_carbon",
    knowledge_dir=r"D:\VScode\firstcc\knowledge_store",
    domain_name="sewer_carbon"  # 选择预设领域
)

# 运行
results = reader.run()
```

### 方法2：使用自定义配置

```python
from literature_batch_reader_universal import UniversalLiteratureReader, DomainConfig

# 自定义配置
custom_config = {
    "name": "污水管网碳排放",
    "description": "污水管网系统碳排放、甲烷排放、碳转化相关研究",
    "keywords": ["sewer", "pipeline", "drainage", "methane", "carbon emission"],
    "method_categories": {
        "emission_measurement": {
            "name": "排放测量",
            "methods": {
                "floating chamber": {
                    "keywords": ["floating chamber", "flux chamber"],
                    "usage_patterns": [
                        r"(?:was|were|using|measured|collected).*?(?:floating chamber|flux chamber)",
                    ]
                },
                "eddy covariance": {
                    "keywords": ["eddy covariance"],
                    "usage_patterns": [
                        r"(?:was|were|using|measured|applied).*?eddy covariance",
                    ]
                },
            }
        },
        "process_modeling": {
            "name": "过程建模",
            "methods": {
                "sewage process model": {
                    "keywords": ["sewage process model", "SPM"],
                    "usage_patterns": [
                        r"(?:was|were|using|developed|applied).*?(?:sewage process model|SPM)",
                    ]
                },
                "ASM": {
                    "keywords": ["activated sludge model", "ASM"],
                    "usage_patterns": [
                        r"(?:was|were|using|developed|applied).*?(?:activated sludge model|ASM)",
                    ]
                },
            }
        },
    }
}

# 创建阅读器
reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\污水管网文献",
    output_dir=r"D:\VScode\firstcc\output\sewer_carbon",
    knowledge_dir=r"D:\VScode\firstcc\knowledge_store",
    custom_config=custom_config
)

# 运行
results = reader.run()
```

### 方法3：从配置文件加载

```python
from literature_batch_reader_universal import UniversalLiteratureReader, DomainConfig

# 从文件加载配置
config = DomainConfig.load_custom_config("my_domain_config.json")

# 创建阅读器
reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\文献目录",
    output_dir=r"D:\输出目录",
    knowledge_dir=r"D:\知识库目录",
    custom_config=config
)

# 运行
results = reader.run()
```

### 方法4：创建并保存自定义配置

```python
from literature_batch_reader_universal import DomainConfig

# 创建自定义配置
config = DomainConfig.create_custom_config(
    name="我的研究领域",
    description="研究领域描述",
    keywords=["keyword1", "keyword2", "keyword3"],
    method_categories={
        "my_methods": {
            "name": "方法类别",
            "methods": {
                "method1": {
                    "keywords": ["method1", "Method 1"],
                    "usage_patterns": [
                        r"(?:was|were|using|applied).*?method1",
                    ]
                },
            }
        },
    }
)

# 保存到文件
DomainConfig.save_custom_config(config, "my_domain_config.json")
```

## 添加新领域

### 方法1：直接修改代码

在 `DomainConfig.PRESET_DOMAINS` 中添加新领域：

```python
PRESET_DOMAINS = {
    # ... 现有领域 ...

    "my_new_domain": {
        "name": "我的新领域",
        "description": "领域描述",
        "keywords": ["keyword1", "keyword2"],
        "method_categories": {
            "category1": {
                "name": "方法类别1",
                "methods": {
                    "method1": {
                        "keywords": ["method1"],
                        "usage_patterns": [
                            r"(?:was|were|using|applied).*?method1",
                        ]
                    },
                }
            },
        }
    },
}
```

### 方法2：使用配置文件

```python
from literature_batch_reader_universal import DomainConfig

# 创建配置
config = {
    "name": "我的新领域",
    "description": "领域描述",
    "keywords": ["keyword1", "keyword2"],
    "method_categories": {
        "category1": {
            "name": "方法类别1",
            "methods": {
                "method1": {
                    "keywords": ["method1"],
                    "usage_patterns": [
                        r"(?:was|were|using|applied).*?method1",
                    ]
                },
            }
        },
    }
}

# 保存
DomainConfig.save_custom_config(config, "my_domain.json")

# 使用时加载
config = DomainConfig.load_custom_config("my_domain.json")
reader = UniversalLiteratureReader(..., custom_config=config)
```

## 输出文件

### all_papers_analysis.json

包含所有论文的详细分析结果：

```json
{
  "index": 1,
  "metadata": {
    "filename": "paper.pdf",
    "title": "论文标题",
    "year": "2024",
    "abstract": "摘要内容",
    "keywords": ["keyword1", "keyword2"],
    "domain_relevance": 0.85
  },
  "word_count": 8000,
  "writing_patterns": {
    "transition_words": [{"word": "however", "count": 5}],
    "hedging_phrases": [{"phrase": "may", "count": 3}]
  },
  "analysis_methods": {
    "emission_measurement": ["floating chamber"],
    "process_modeling": ["ASM"]
  },
  "figure_info": {
    "figure_count": 6,
    "table_count": 4,
    "figure_types": ["box plot", "heatmap"]
  }
}
```

### domain_config.json

保存使用的领域配置：

```json
{
  "name": "污水管网碳排放",
  "description": "...",
  "keywords": ["sewer", "pipeline", ...],
  "method_categories": {...}
}
```

### learned_writing_patterns.json

写作模式统计：

```json
{
  "domain": "污水管网碳排放",
  "transition_words": {
    "however": 100,
    "therefore": 80
  },
  "hedging_phrases": {
    "may": 150,
    "could": 120
  }
}
```

### learned_analysis_methods.json

方法使用统计：

```json
{
  "domain": "污水管网碳排放",
  "methods_frequency": {
    "emission_measurement": {
      "floating chamber": 15,
      "eddy covariance": 8
    },
    "process_modeling": {
      "ASM": 12,
      "sewage process model": 5
    }
  }
}
```

## 使用示例

### 示例1：污水管网碳排放文献

```python
from literature_batch_reader_universal import UniversalLiteratureReader

reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\污水管网碳排放文献",
    output_dir=r"D:\VScode\firstcc\output\sewer_carbon",
    knowledge_dir=r"D:\VScode\firstcc\knowledge_store",
    domain_name="sewer_carbon"
)

results = reader.run()
```

### 示例2：医学临床研究文献

```python
reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\临床研究文献",
    output_dir=r"D:\VScode\firstcc\output\clinical",
    knowledge_dir=r"D:\VScode\firstcc\knowledge_store",
    domain_name="medical_clinical"
)

results = reader.run()
```

### 示例3：机器学习文献

```python
reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\机器学习文献",
    output_dir=r"D:\VScode\firstcc\output\ml",
    knowledge_dir=r"D:\VScode\firstcc\knowledge_store",
    domain_name="machine_learning"
)

results = reader.run()
```

### 示例4：自定义领域

```python
# 先创建配置
from literature_batch_reader_universal import DomainConfig

config = DomainConfig.create_custom_config(
    name="土壤修复",
    description="土壤污染修复技术研究",
    keywords=["soil", "remediation", "contamination", "heavy metal"],
    method_categories={
        "remediation_technology": {
            "name": "修复技术",
            "methods": {
                "phytoremediation": {
                    "keywords": ["phytoremediation", "phytoextraction"],
                    "usage_patterns": [
                        r"(?:was|were|using|applied|conducted).*?phytoremediation",
                    ]
                },
                "bioremediation": {
                    "keywords": ["bioremediation", "biodegradation"],
                    "usage_patterns": [
                        r"(?:was|were|using|applied|conducted).*?bioremediation",
                    ]
                },
                "chemical stabilization": {
                    "keywords": ["chemical stabilization", "immobilization"],
                    "usage_patterns": [
                        r"(?:was|were|using|applied|conducted).*?(?:chemical stabilization|immobilization)",
                    ]
                },
            }
        },
    }
)

# 保存配置
DomainConfig.save_custom_config(config, "soil_remediation.json")

# 使用
reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\土壤修复文献",
    output_dir=r"D:\VScode\firstcc\output\soil",
    knowledge_dir=r"D:\VScode\firstcc\knowledge_store",
    custom_config=config
)

results = reader.run()
```

## 常见问题

### Q: 如何添加新的方法识别？

A: 在配置的 `method_categories` 中添加新的方法定义，包括 `keywords` 和 `usage_patterns`。

### Q: 如何修改年份识别范围？

A: 在 `UniversalMetadataExtractor._extract_year` 方法中修改年份范围判断（如 `1990 <= candidate <= 2030`）。

### Q: 如何提高方法识别的准确性？

A: 1) 确保 `usage_patterns` 中的正则表达式准确；2) 在 Methods 部分搜索；3) 使用严格的上下文匹配。

### Q: 支持哪些语言的文献？

A: 系统支持英文和中文文献，但主要针对英文文献优化。中文支持正在改进中。

### Q: 如何批量处理多个领域的文献？

A: 为每个领域创建单独的阅读器实例，分别处理。

## 依赖

```bash
pip install pdfplumber python-docx
```

## 更新日志

### v4.0 (2024-06-25)
- 通用化设计，支持任意领域
- 可配置方法库
- 添加6个预设领域
- 支持自定义领域配置
- 领域相关度计算

### v3.0 (2024-06-24)
- 优化年份识别算法
- 优化方法识别算法
- 添加断点续传功能
- 添加日志系统

### v2.0 (2024-06-23)
- 添加方法识别功能
- 添加图表分析功能
- 生成Word报告

### v1.0 (2024-06-22)
- 初始版本
- 基础PDF解析
- 元数据提取
