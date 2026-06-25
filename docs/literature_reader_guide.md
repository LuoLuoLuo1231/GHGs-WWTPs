# 文献批量阅读系统 - 使用指南

## 概述

本系统用于批量阅读PDF文献，自动提取元数据、分析写作模式、识别研究方法和图表使用情况。

## 主要优化

### 1. 年份识别优化

**问题**：早期版本会匹配到任何年份（如参考文献中的年份），导致年份识别不准确。

**解决方案**：
- 多策略组合匹配
- 优先匹配发表日期格式（Published, Received, Accepted）
- 匹配期刊引用格式
- 匹配版权年份
- 支持手动年份映射

### 2. 方法识别优化

**问题**：早期版本在全文中搜索关键词，导致仅"提到"的方法被误认为"使用"。

**解决方案**：
- 严格上下文语境匹配
- 需要出现使用动词（was used, was performed, applied等）
- 优先在Methods部分搜索
- 区分"使用"和"提及"

### 3. 错误处理优化

**改进**：
- 完善的异常捕获和日志记录
- 支持断点续传（中断后可继续处理）
- 自动保存处理进度
- 详细的错误信息记录

### 4. 代码结构优化

**改进**：
- 模块化设计（PDF解析、元数据提取、方法识别等独立模块）
- 类型注解
- 详细的文档注释
- 可配置的日志系统

## 文件结构

```
GHGs-WWTPs/
├── literature_batch_reader_optimized.py  # 主程序（优化版）
├── generate_literature_report_v2.py      # Word报告生成
├── fix_years.py                          # 年份修正工具
├── docs/
│   └── literature_reader_guide.md        # 本文档
├── output/
│   └── literature_learning/
│       ├── all_papers_analysis.json      # 分析结果
│       ├── literature_learning_report.md # Markdown报告
│       ├── 文献学习综合分析报告_v3.docx   # Word报告
│       └── checkpoint.json               # 断点文件
└── knowledge_store/
    ├── learned_writing_patterns.json     # 写作模式
    ├── learned_analysis_methods.json     # 分析方法
    └── learned_figure_design.json        # 图表设计
```

## 使用方法

### 基本使用

```python
from literature_batch_reader_optimized import LiteratureBatchReader

# 配置
LITERATURE_DIR = r"D:\下载\文献数据整理\artical learning-agent train"
OUTPUT_DIR = r"D:\VScode\firstcc\GHGs-WWTPs\output\literature_learning"
KNOWLEDGE_DIR = r"D:\VScode\firstcc\GHGs-WWTPs\knowledge_store"

# 创建阅读器
reader = LiteratureBatchReader(LITERATURE_DIR, OUTPUT_DIR, KNOWLEDGE_DIR)

# 运行
results = reader.run()
```

### 使用年份映射

如果自动年份识别不准确，可以提供手动映射：

```python
YEAR_MAPPING = {
    "(1)": 2020,
    "(2)": 2020,
    # ... 更多映射
    "(117)": 2026,
}

results = reader.run(year_mapping=YEAR_MAPPING)
```

### 从断点继续

如果处理中断，再次运行会自动从断点继续：

```python
reader = LiteratureBatchReader(LITERATURE_DIR, OUTPUT_DIR, KNOWLEDGE_DIR)
results = reader.run()  # 自动从上次中断处继续
```

## 输出说明

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
    "keywords": ["keyword1", "keyword2"]
  },
  "word_count": 8000,
  "writing_patterns": {
    "transition_words": [{"word": "however", "count": 5}],
    "hedging_phrases": [{"phrase": "may", "count": 3}]
  },
  "analysis_methods": {
    "statistical_tests": ["ANOVA", "t-test"],
    "machine_learning": ["random forest"],
    "emission_accounting": ["IPCC method"]
  },
  "figure_info": {
    "figure_count": 6,
    "table_count": 4,
    "figure_types": ["box plot", "heatmap"]
  }
}
```

### learned_writing_patterns.json

写作模式统计：

```json
{
  "transition_words": {
    "however": 668,
    "therefore": 488,
    "significantly": 344
  },
  "hedging_phrases": {
    "could": 751,
    "may": 662,
    "estimated": 505
  }
}
```

### learned_analysis_methods.json

方法使用统计：

```json
{
  "methods_frequency": {
    "statistical_tests": {
      "ANOVA": 3,
      "t-test": 2
    },
    "machine_learning": {
      "neural network": 28,
      "random forest": 7
    },
    "emission_accounting": {
      "IPCC method": 51,
      "LCA": 13
    }
  }
}
```

## 日志系统

系统会自动生成日志文件，记录处理过程：

```
2024-06-24 18:30:00 - LiteratureReader - INFO - 文献批量阅读系统启动
2024-06-24 18:30:01 - LiteratureReader - INFO - [1/117] 处理: paper.pdf
2024-06-24 18:30:05 - LiteratureReader - INFO - [1/117] 成功: paper.pdf (8000 词, 4 表格, 方法: IPCC method)
```

## 常见问题

### Q: 年份识别不准确怎么办？

A: 使用手动年份映射，参考 `fix_years.py` 中的示例。

### Q: 方法使用率太高/太低？

A: 检查 `method_definitions` 中的正则表达式，调整匹配严格程度。

### Q: 处理中断了怎么办？

A: 直接重新运行，系统会自动从断点继续。

### Q: 如何添加新的方法识别？

A: 在 `MethodIdentifier` 类的 `method_definitions` 中添加新的方法定义。

## 依赖

```bash
pip install pdfplumber python-docx
```

## 更新日志

### v3.0 (2024-06-24)
- 优化年份识别算法
- 优化方法识别算法（严格上下文匹配）
- 添加断点续传功能
- 添加日志系统
- 模块化重构

### v2.0 (2024-06-23)
- 添加方法识别功能
- 添加图表分析功能
- 生成Word报告

### v1.0 (2024-06-22)
- 初始版本
- 基础PDF解析
- 元数据提取
