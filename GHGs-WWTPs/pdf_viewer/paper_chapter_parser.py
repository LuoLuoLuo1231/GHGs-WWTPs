"""
论文章节解析器

核心功能：
1. 完整读取PDF，保留结构
2. 识别论文章节（Introduction, Methods, Results, Discussion, Conclusion等）
3. 对每个章节分别进行详细概括
4. 输出结构化的章节摘要
"""

import re
import fitz  # PyMuPDF
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


# 常见的论文章节标题模式
CHAPTER_PATTERNS = [
    # 英文章节
    r'^(?:\d+\.?\s*)?(?:abstract|summary)',
    r'^(?:\d+\.?\s*)?(?:introduction|intro)',
    r'^(?:\d+\.?\s*)?(?:literature\s+review|background)',
    r'^(?:\d+\.?\s*)?(?:materials?\s+and\s+methods?|methods?|methodology|experimental)',
    r'^(?:\d+\.?\s*)?(?:results?\s+(?:and\s+)?(?:discussion)?|findings?)',
    r'^(?:\d+\.?\s*)?(?:discussion)',
    r'^(?:\d+\.?\s*)?(?:conclusions?|concluding\s+remarks)',
    r'^(?:\d+\.?\s*)?(?:references?|bibliography)',
    r'^(?:\d+\.?\s*)?(?:acknowledgments?|acknowledgements?)',
    r'^(?:\d+\.?\s*)?(?:supplementary|appendix|appendices)',
    # 中文章节
    r'^(?:\d+\.?\s*)?(?:摘要|摘\s+要)',
    r'^(?:\d+\.?\s*)?(?:引言|前言|绪论)',
    r'^(?:\d+\.?\s*)?(?:文献综述|研究背景)',
    r'^(?:\d+\.?\s*)?(?:材料与方法|实验方法|研究方法|方法)',
    r'^(?:\d+\.?\s*)?(?:结果|实验结果|研究结果)',
    r'^(?:\d+\.?\s*)?(?:讨论|分析与讨论)',
    r'^(?:\d+\.?\s*)?(?:结论|总结|结论与展望)',
    r'^(?:\d+\.?\s*)?(?:参考文献)',
    r'^(?:\d+\.?\s*)?(?:致谢)',
]


@dataclass
class Chapter:
    """论文章节"""
    title: str
    content: str
    chapter_type: str  # abstract, introduction, methods, results, discussion, conclusion, other
    summary: str = ""
    page_start: int = 0
    page_end: int = 0


@dataclass
class PaperStructure:
    """论文结构化数据"""
    file_path: str
    file_name: str
    title: str = ""
    authors: str = ""
    abstract: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    full_text: str = ""
    page_count: int = 0
    char_count: int = 0

    def to_dict(self):
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "chapters": [asdict(ch) for ch in self.chapters],
            "page_count": self.page_count,
            "char_count": self.char_count,
        }


class ChapterParser:
    """论文章节解析器"""

    def __init__(self):
        """初始化解析器"""
        self.chapter_patterns = []
        for pattern in CHAPTER_PATTERNS:
            self.chapter_patterns.append((re.compile(pattern, re.IGNORECASE), pattern))

    def parse_pdf(self, pdf_path: str) -> PaperStructure:
        """
        解析PDF，提取章节结构

        Parameters
        ----------
        pdf_path : str, PDF文件路径

        Returns
        -------
        PaperStructure, 论文结构化数据
        """
        path = Path(pdf_path)
        doc = fitz.open(str(path))

        structure = PaperStructure(
            file_path=str(path),
            file_name=path.name,
            page_count=doc.page_count,
        )

        # 提取每一页的文本
        page_texts = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            page_texts.append((page_num + 1, text))

        doc.close()

        # 合并全文
        structure.full_text = '\n'.join([t for _, t in page_texts])
        structure.char_count = len(structure.full_text)

        # 提取标题和作者（通常在第一页）
        if page_texts:
            structure.title, structure.authors = self._extract_title_authors(page_texts[0][1])

        # 识别章节
        structure.chapters = self._identify_chapters(page_texts)

        # 如果没有识别到章节，使用智能分割
        if not structure.chapters:
            structure.chapters = self._smart_split(structure.full_text)

        return structure

    def _extract_title_authors(self, first_page_text: str) -> Tuple[str, str]:
        """从第一页提取标题和作者"""
        lines = first_page_text.strip().split('\n')

        # 简单启发式：前几行通常是标题和作者
        title = ""
        authors = ""

        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if not line:
                continue

            # 跳过页眉页脚
            if len(line) < 5 or line.isdigit():
                continue

            # 第一个非空、非数字的长行可能是标题
            if not title and len(line) > 10:
                title = line
                continue

            # 下一个非空行可能是作者
            if title and not authors and len(line) > 5:
                authors = line
                break

        return title, authors

    def _identify_chapters(self, page_texts: List[Tuple[int, str]]) -> List[Chapter]:
        """识别论文章节"""
        chapters = []
        current_chapter = None
        current_content = []

        for page_num, page_text in page_texts:
            lines = page_text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    if current_chapter:
                        current_content.append('')
                    continue

                # 检查是否是章节标题
                is_chapter_title = False
                chapter_type = "other"

                for pattern, _ in self.chapter_patterns:
                    if pattern.match(line):
                        is_chapter_title = True
                        chapter_type = self._classify_chapter(line)
                        break

                # 也检查全大写的英文行（可能是章节标题）
                if not is_chapter_title and line.isupper() and 10 < len(line) < 80:
                    is_chapter_title = True
                    chapter_type = self._classify_chapter(line)

                # 也检查数字开头的标题（如 "1. Introduction"）
                if not is_chapter_title and re.match(r'^\d+\.?\s+[A-Z]', line):
                    is_chapter_title = True
                    chapter_type = self._classify_chapter(line)

                if is_chapter_title:
                    # 保存当前章节
                    if current_chapter:
                        current_chapter.content = '\n'.join(current_content).strip()
                        chapters.append(current_chapter)

                    # 开始新章节
                    current_chapter = Chapter(
                        title=line,
                        content="",
                        chapter_type=chapter_type,
                        page_start=page_num,
                    )
                    current_content = []
                else:
                    current_content.append(line)

        # 保存最后一个章节
        if current_chapter:
            current_chapter.content = '\n'.join(current_content).strip()
            current_chapter.page_end = page_texts[-1][0] if page_texts else 0
            chapters.append(current_chapter)

        return chapters

    def _classify_chapter(self, title: str) -> str:
        """分类章节类型"""
        title_lower = title.lower()

        if any(kw in title_lower for kw in ['abstract', 'summary', '摘要', '摘 要']):
            return 'abstract'
        elif any(kw in title_lower for kw in ['introduction', 'intro', '引言', '前言', '绪论', 'background']):
            return 'introduction'
        elif any(kw in title_lower for kw in ['method', 'methodology', 'experiment', 'materials', '材料', '方法', '实验']):
            return 'methods'
        elif any(kw in title_lower for kw in ['result', 'finding', '结果', '发现']):
            return 'results'
        elif any(kw in title_lower for kw in ['discussion', '分析', '讨论']):
            return 'discussion'
        elif any(kw in title_lower for kw in ['conclusion', 'summary', '结论', '总结', '展望']):
            return 'conclusion'
        elif any(kw in title_lower for kw in ['reference', 'bibliography', '参考文献']):
            return 'references'
        elif any(kw in title_lower for kw in ['acknowledgment', '致谢']):
            return 'acknowledgments'
        else:
            return 'other'

    def _smart_split(self, text: str) -> List[Chapter]:
        """智能分割：当无法识别章节时，按段落分割"""
        chapters = []

        # 按双换行分割段落
        paragraphs = re.split(r'\n\s*\n', text)

        # 合并短段落
        merged = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < 1000:
                current += "\n" + para
            else:
                if current:
                    merged.append(current.strip())
                current = para
        if current:
            merged.append(current.strip())

        # 创建章节
        for i, content in enumerate(merged[:10]):  # 最多10个章节
            if content:
                chapters.append(Chapter(
                    title=f"段落 {i+1}",
                    content=content,
                    chapter_type="other",
                ))

        return chapters


class ChapterSummarizer:
    """章节概括器"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model

    def summarize_chapter(self, chapter: Chapter, paper_title: str = "") -> str:
        """
        概括单个章节

        Parameters
        ----------
        chapter : Chapter, 章节数据
        paper_title : str, 论文标题

        Returns
        -------
        str, 章节概括
        """
        if not chapter.content or len(chapter.content) < 50:
            return "内容过少，无法概括"

        # 根据章节类型设置不同的概括重点（专业学术格式）
        prompts = {
            'abstract': f'''请用中文概括这篇论文的摘要，严格按照以下格式：

核心观点：（研究的重要性和背景，1-2句话）
工作概述：（研究做了什么，用什么方法）
关键创新：（本文的主要创新点）
主要结果：（最重要的发现和数据）
核心结论：（最终结论）

论文标题：{paper_title}''',

            'introduction': f'''请用中文概括这篇论文的引言部分，严格按照以下格式：

1.1 研究背景：（问题的重要性、现状、关键数据）
1.2 机理/理论基础：（相关机理或理论框架）
1.3 已有研究的局限性：（现有方法的不足和研究空白）
1.4 本文研究目标：（本文要解决什么问题、采用什么方法）

论文标题：{paper_title}''',

            'methods': f'''请用中文概括这篇论文的研究方法，严格按照以下格式：

2.1 数据来源：（数据描述、采样方式、数据量）
2.2 研究设计：（整体研究框架）
2.3 核心方法/算法/模型：（主要技术方法，包括关键参数）
2.4 方法创新点：（本文方法的改进之处）

论文标题：{paper_title}''',

            'results': f'''请用中文概括这篇论文的结果与讨论，严格按照以下格式：

3.1 主要结果：（关键数据和发现，包含具体数值）
3.2 模型/方法对比：（不同方法的性能对比，优劣分析）
3.3 机理解释：（结果的工艺/科学机理解释）
3.4 与已有研究对比：（本文结果与文献的异同）

论文标题：{paper_title}''',

            'discussion': f'''请用中文概括这篇论文的讨论部分，严格按照以下格式：

3.1 结果解释：（对主要结果的深入分析）
3.2 与已有研究的比较：（异同点分析）
3.3 理论/实践意义：（研究的应用价值）
3.4 研究局限性：（本研究的不足之处）

论文标题：{paper_title}''',

            'conclusion': f'''请用中文概括这篇论文的结论与展望，严格按照以下格式：

4.1 主要结论：（3-5条核心结论，每条1-2句话）
4.2 创新点：（本文的主要贡献）
4.3 未来研究方向：（后续研究建议）

论文标题：{paper_title}''',

            'other': f'''请用中文概括这段内容的核心要点，分点列出：

核心要点：
1. ...
2. ...
3. ...

论文标题：{paper_title}''',
        }

        prompt = prompts.get(chapter.chapter_type, prompts['other'])

        # 截取前4000字符避免超长
        content = chapter.content[:4000]

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": '''你是一个专业的学术论文分析助手。请严格按照指定格式概括论文章节内容。

要求：
1. 用中文回答
2. 条理清晰，分点概括
3. 引用具体数据和数值
4. 准确识别研究方法、结果、结论
5. 不要编造内容，只基于提供的文本'''},
                        {"role": "user", "content": f"{prompt}\n\n章节内容：\n{content}"},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1500,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"概括失败: {str(e)}"

    def summarize_all_chapters(self, structure: PaperStructure) -> PaperStructure:
        """
        概括所有章节

        Parameters
        ----------
        structure : PaperStructure, 论文结构

        Returns
        -------
        PaperStructure, 带有概括的论文结构
        """
        for chapter in structure.chapters:
            print(f"  概括章节: {chapter.title[:50]}...")
            chapter.summary = self.summarize_chapter(chapter, structure.title)

        return structure


def parse_and_summarize(pdf_path: str, api_key: str, base_url: str = None, model: str = None) -> PaperStructure:
    """
    完整流程：解析PDF + 概括所有章节

    Parameters
    ----------
    pdf_path : str, PDF文件路径
    api_key : str, API密钥
    base_url : str, API地址
    model : str, 模型名称

    Returns
    -------
    PaperStructure, 完整的论文结构和概括
    """
    # 解析PDF
    parser = ChapterParser()
    structure = parser.parse_pdf(pdf_path)

    print(f"解析完成: {structure.file_name}")
    print(f"  页数: {structure.page_count}")
    print(f"  字符数: {structure.char_count}")
    print(f"  识别章节: {len(structure.chapters)}")

    # 概括章节
    summarizer = ChapterSummarizer(
        api_key=api_key,
        base_url=base_url or "https://api.deepseek.com/v1",
        model=model or "deepseek-v4-flash",
    )

    structure = summarizer.summarize_all_chapters(structure)

    return structure


if __name__ == "__main__":
    # 测试
    import sys
    import os

    # 从环境变量获取API密钥
    API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = r"D:\西北大学\作业\环境反应工程\参考文献\1-s2.0-S004565351530446X-main.pdf"

    structure = parse_and_summarize(pdf_path, API_KEY)

    # 输出结果
    print("\n" + "=" * 60)
    print(f"论文标题: {structure.title}")
    print(f"作者: {structure.authors}")
    print("=" * 60)

    for chapter in structure.chapters:
        print(f"\n{'=' * 40}")
        print(f"【{chapter.chapter_type.upper()}】{chapter.title}")
        print(f"{'=' * 40}")
        print(f"内容摘要:\n{chapter.summary}")
