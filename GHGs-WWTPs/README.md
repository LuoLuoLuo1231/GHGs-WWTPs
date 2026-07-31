# GHGs-WWTPs: 污水处理厂温室气体排放研究系统

## 系统概述

本系统是一个完整的污水处理厂温室气体排放研究平台，集成了文献阅读、数据分析、可视化、论文写作和审阅等功能。

## 功能模块

| 模块 | 功能 | 入口 |
|------|------|------|
| 文献阅读 | 批量阅读PDF文献，提取知识 | `LiteratureModule` |
| 数据分析 | 描述统计、元分析、Bootstrap | `AnalysisModule` |
| 数据可视化 | 专业图表生成 | `VisualizationModule` |
| 论文写作 | 自动生成论文各章节 | `WritingModule` |
| 论文审阅 | 全方位论文审阅 | `ReviewModule` |
| AI优化 | AI辅助写作优化 | `AIOptimizer` |

## 快速开始

### 方式1: 交互式菜单

```bash
python ghgs_wwtp_system.py
```

### 方式2: 命令行

```bash
# 运行全流程
python ghgs_wwtp_system.py --all

# 只运行文献阅读
python ghgs_wwtp_system.py --literature

# 只运行数据分析
python ghgs_wwtp_system.py --analysis

# 只运行可视化
python ghgs_wwtp_system.py --visualization

# 只运行论文写作
python ghgs_wwtp_system.py --writing

# 只运行论文审阅
python ghgs_wwtp_system.py --review

# AI优化指定章节
python ghgs_wwtp_system.py --optimize discussion
```

### 方式3: Python代码

```python
from ghgs_wwtp_system import FullPipeline

# 运行全流程
results = FullPipeline.run()

# 或单独运行某个模块
from ghgs_wwtp_system import LiteratureModule, AnalysisModule

LiteratureModule.run()
AnalysisModule.run()
```

## 系统架构

```
ghgs_wwtp_system.py (统一入口)
│
├── LiteratureModule (文献阅读)
│   └── literature_batch_reader_universal.py
│
├── AnalysisModule (数据分析)
│   ├── scientific_analysis_agent.py
│   └── meta_analysis_module_v3.py
│
├── VisualizationModule (可视化)
│   └── scientific_visualization_agent.py
│
├── WritingModule (论文写作)
│   └── paper_writing_agent.py
│
├── ReviewModule (论文审阅)
│   └── academic_review_agent.py
│
└── AIOptimizer (AI优化)
    └── claude_writer.py
```

## 目录结构

```
GHGs-WWTPs/
├── ghgs_wwtp_system.py              # 统一入口 ⭐
├── literature_batch_reader_universal.py  # 通用文献阅读器
├── meta_analysis_module_v3.py       # 元分析模块
├── scientific_analysis_agent.py     # 科学分析代理
├── scientific_visualization_agent.py # 可视化代理
├── paper_writing_agent.py           # 论文写作代理
├── academic_review_agent.py         # 学术审阅代理
├── claude_writer.py                 # AI写作器
├── domains/                         # 领域配置
│   ├── environmental_ghg.json
│   └── sewer_carbon.json
├── knowledge_store/                 # 知识库
├── output/                          # 输出目录
│   ├── literature_learning/
│   ├── analysis/
│   ├── figures/
│   ├── paper/
│   └── review/
└── docs/                            # 文档
```

## 配置说明

### 数据路径配置

在 `ghgs_wwtp_system.py` 中修改 `SystemConfig` 类：

```python
class SystemConfig:
    LITERATURE_DIR = r"D:\下载\文献数据整理\artical learning-agent train"
    DATA_DIR = r"D:\下载\文献数据整理\数据分析\数据分析2026.6.8"
    # ...
```

### 领域配置

在 `domains/` 目录下创建JSON配置文件：

```json
{
  "name": "领域名称",
  "description": "领域描述",
  "keywords": ["keyword1", "keyword2"],
  "method_categories": {
    "category1": {
      "name": "方法类别",
      "methods": {
        "method1": {
          "keywords": ["method1"],
          "usage_patterns": ["used method1"]
        }
      }
    }
  }
}
```

## 使用流程

### 典型工作流程

```
1. 文献阅读 → 提取知识，存入知识库
      ↓
2. 数据分析 → 描述统计、元分析、Bootstrap
      ↓
3. 数据可视化 → 生成专业图表
      ↓
4. 论文写作 → 自动生成各章节
      ↓
5. 论文审阅 → 检查规范、语言、逻辑
      ↓
6. AI优化 → 优化论文质量
```

### 示例：完整研究流程

```python
from ghgs_wwtp_system import FullPipeline

# 配置
config = {
    'literature': True,        # 运行文献阅读
    'analysis': True,          # 运行数据分析
    'visualization': True,     # 运行可视化
    'writing': True,           # 运行论文写作
    'review': True,            # 运行论文审阅

    'literature_dir': r"D:\下载\污水管网文献",
    'data_path': r"D:\数据.xlsx",
    'domain': 'sewer_carbon',
    'style': 'sci',
    'topic': '污水管网碳排放研究',
}

# 运行全流程
results = FullPipeline.run(config)
```

## 依赖

```bash
pip install pandas numpy scipy matplotlib seaborn openpyxl python-docx pdfplumber scikit-learn
```

## 更新日志

### v4.0 (2024-06-25)
- 新增统一入口 `ghgs_wwtp_system.py`
- 新增通用文献阅读系统
- 新增元分析模块 v3
- 新增领域配置系统
- 优化系统架构

### v3.0 (2024-06-24)
- 优化年份识别算法
- 优化方法识别算法
- 添加断点续传功能

### v2.0 (2024-06-23)
- 添加智能代理系统
- 添加可视化功能
- 添加论文审阅功能

### v1.0 (2024-06-22)
- 初始版本
- 基础数据分析功能

## 许可证

MIT

## 联系方式

GitHub: https://github.com/linghunbailan/GHGs-WWTPs
