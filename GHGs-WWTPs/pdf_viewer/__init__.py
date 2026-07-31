"""
PDF文献章节解析模块

功能：
1. PDF文本提取
2. 章节识别（Introduction, Methods, Results, Conclusion等）
3. AI概括（专业学术格式）
4. 批量处理
"""

from .paper_chapter_parser import parse_and_summarize, PaperStructure, Chapter

__version__ = '1.0.0'
__all__ = [
    'parse_and_summarize',
    'PaperStructure',
    'Chapter',
]
