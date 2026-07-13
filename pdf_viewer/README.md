# PDF文献章节解析模块

## 功能

1. **PDF文本提取** - 使用PyMuPDF提取论文文本
2. **章节识别** - 自动识别Introduction、Methods、Results、Conclusion等章节
3. **AI概括** - 对每个章节进行专业学术格式的概括
4. **批量处理** - 支持批量处理多篇论文

## 使用方法

### 单篇论文处理

```python
from pdf_viewer.paper_chapter_parser import parse_and_summarize

# 处理论文
structure = parse_and_summarize(
    pdf_path="paper.pdf",
    api_key="your-api-key"
)

# 查看结果
for chapter in structure.chapters:
    if chapter.summary:
        print(f"【{chapter.chapter_type}】{chapter.title}")
        print(chapter.summary)
```

### 批量处理

```python
from pdf_viewer.process_mimo import batch_process_papers

# 批量处理目录下的所有PDF
batch_process_papers(
    pdf_dir="D:/文献目录",
    output_dir="D:/输出目录"
)
```

## 输出格式

### 摘要（Abstract）
```
核心观点：（研究的重要性和背景）
工作概述：（研究做了什么）
关键创新：（本文的主要创新点）
主要结果：（最重要的发现和数据）
核心结论：（最终结论）
```

### 引言（Introduction）
```
1.1 研究背景：（问题的重要性、现状、关键数据）
1.2 机理/理论基础：（相关机理或理论框架）
1.3 已有研究的局限性：（现有方法的不足和研究空白）
1.4 本文研究目标：（本文要解决什么问题、采用什么方法）
```

### 方法（Methods）
```
2.1 数据来源：（数据描述、采样方式、数据量）
2.2 研究设计：（整体研究框架）
2.3 核心方法/算法/模型：（主要技术方法，包括关键参数）
2.4 方法创新点：（本文方法的改进之处）
```

### 结果（Results）
```
3.1 主要结果：（关键数据和发现，包含具体数值）
3.2 模型/方法对比：（不同方法的性能对比，优劣分析）
3.3 机理解释：（结果的工艺/科学机理解释）
3.4 与已有研究对比：（本文结果与文献的异同）
```

### 结论（Conclusion）
```
4.1 主要结论：（3-5条核心结论，每条1-2句话）
4.2 创新点：（本文的主要贡献）
4.3 未来研究方向：（后续研究建议）
```

## 依赖

- PyMuPDF (fitz)
- requests
- python-docx (可选，用于输出Word)

## 配置

使用前需要设置API密钥：

```python
# MIMO API
API_KEY = "your-mimo-api-key"
BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
MODEL = "mimo-v2.5"
```
