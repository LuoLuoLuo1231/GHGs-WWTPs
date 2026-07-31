# 领域配置目录

本目录存放各领域的配置文件，用于通用文献批量阅读系统。

## 文件结构

```
domains/
├── README.md                    # 本文档
├── environmental_ghg.json       # 环境-温室气体排放
├── sewer_carbon.json            # 污水管网碳排放
├── medical_clinical.json        # 医学-临床研究（待创建）
├── engineering_optimization.json # 工程优化（待创建）
├── machine_learning.json        # 机器学习/AI（待创建）
└── custom_template.json         # 自定义配置模板
```

## 使用方法

### 方法1：直接使用配置文件

```python
from literature_batch_reader_universal import UniversalLiteratureReader, DomainConfig

# 加载配置文件
config = DomainConfig.load_custom_config("domains/sewer_carbon.json")

# 创建阅读器
reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\污水管网文献",
    output_dir=r"D:\输出目录",
    knowledge_dir=r"D:\知识库目录",
    custom_config=config
)

# 运行
results = reader.run()
```

### 方法2：使用预设领域名称

```python
reader = UniversalLiteratureReader(
    literature_dir=r"D:\下载\污水管网文献",
    output_dir=r"D:\输出目录",
    knowledge_dir=r"D:\知识库目录",
    domain_name="sewer_carbon"  # 自动从domains目录加载
)
results = reader.run()
```

### 方法3：创建新的领域配置

1. 复制 `custom_template.json`
2. 修改配置内容
3. 保存为新的JSON文件
4. 使用时加载

## 配置文件格式

```json
{
  "name": "领域名称",
  "description": "领域描述",
  "keywords": ["关键词1", "关键词2"],
  "method_categories": {
    "category1": {
      "name": "方法类别名称",
      "methods": {
        "method1": {
          "keywords": ["方法关键词1", "方法关键词2"],
          "usage_patterns": [
            r"(?:was|were|using|applied).*?方法关键词"
          ]
        }
      }
    }
  }
}
```

## 配置说明

### name
领域名称，用于显示和日志记录。

### description
领域描述，说明该领域的研究范围。

### keywords
领域关键词列表，用于计算文献与领域的相关度。
- 关键词应是该领域常见的英文术语
- 建议包含10-20个关键词
- 关键词不区分大小写

### method_categories
方法类别，包含多个方法组。

#### category
方法类别，如"排放测量"、"统计方法"等。

##### name
类别名称，用于显示。

##### methods
具体方法列表。

###### method
单个方法的配置。

- **keywords**: 方法的关键词，用于初步匹配
- **usage_patterns**: 使用语境的正则表达式模式，用于严格匹配

## 正则表达式说明

`usage_patterns` 中使用正则表达式来匹配方法的使用语境：

```json
"usage_patterns": [
    r"(?:was|were|using|applied|conducted).*?方法关键词",
    r"(?:we|this study).*?(?:used|applied).*?方法关键词"
]
```

常用模式：
- `(?:was|were)` - 被动语态
- `(?:using|applied|conducted)` - 使用动词
- `(?:we|this study)` - 主语
- `.*?` - 匹配任意字符（非贪婪）
- `(?:A|B)` - 匹配A或B

## 添加新领域

1. 在 `domains` 目录下创建新的JSON文件
2. 按照格式填写配置
3. 测试配置是否正确
4. 使用时加载配置

## 配置示例

### 简单配置

```json
{
  "name": "土壤修复",
  "description": "土壤污染修复技术研究",
  "keywords": ["soil", "remediation", "contamination"],
  "method_categories": {
    "remediation": {
      "name": "修复技术",
      "methods": {
        "phytoremediation": {
          "keywords": ["phytoremediation"],
          "usage_patterns": [
            r"(?:was|were|using|applied).*?phytoremediation"
          ]
        }
      }
    }
  }
}
```

### 完整配置

```json
{
  "name": "污水管网碳排放",
  "description": "污水管网系统碳排放、甲烷排放、碳转化相关研究",
  "keywords": ["sewer", "pipeline", "methane", "carbon emission"],
  "method_categories": {
    "emission_measurement": {
      "name": "排放测量方法",
      "methods": {
        "floating chamber": {
          "keywords": ["floating chamber", "flux chamber"],
          "usage_patterns": [
            r"(?:was|were|using|measured|collected).*?(?:floating chamber|flux chamber)"
          ]
        },
        "eddy covariance": {
          "keywords": ["eddy covariance"],
          "usage_patterns": [
            r"(?:was|were|using|measured|applied).*?eddy covariance"
          ]
        }
      }
    },
    "process_modeling": {
      "name": "过程建模方法",
      "methods": {
        "ASM": {
          "keywords": ["activated sludge model", "ASM"],
          "usage_patterns": [
            r"(?:was|were|using|developed|applied).*?(?:activated sludge model|ASM)"
          ]
        }
      }
    }
  }
}
```

## 常见问题

### Q: 如何测试配置是否正确？

A: 使用配置创建阅读器，处理几篇文献，检查方法识别结果。

### Q: 正则表达式不生效怎么办？

A: 检查正则表达式语法，确保转义字符正确。可以使用在线正则表达式测试工具。

### Q: 如何添加新的方法类别？

A: 在 `method_categories` 中添加新的类别，包含 `name` 和 `methods`。

### Q: 关键词应该选哪些？

A: 选择该领域最常见的英文术语，包括：
- 研究对象名称
- 常用方法名称
- 核心概念
- 相关技术术语

## 更新日志

### v1.0 (2024-06-25)
- 创建配置目录
- 添加 environmental_ghg.json
- 添加 sewer_carbon.json
- 添加使用说明
