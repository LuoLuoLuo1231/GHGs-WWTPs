"""
批量读取文献 PDF，提取结构化信息，形成经验报告
"""
import os
import sys
import json
import re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# PDF解析
import pdfplumber

LITERATURE_DIR = r"D:\下载\文献数据整理\论文写作技巧学习"
OUTPUT_DIR = r"D:\VScode\firstcc\GHGs-WWTPs\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_text_from_pdf(pdf_path, max_pages=15):
    """提取PDF前N页文本"""
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


def extract_metadata(text, filename):
    """从文本中提取元数据"""
    meta = {
        "filename": filename,
        "title": "",
        "authors": "",
        "journal": "",
        "year": "",
        "abstract": "",
        "keywords": [],
        "methods": [],
        "key_findings": [],
        "writing_patterns": [],
    }

    lines = text.split("\n")
    clean_lines = [l.strip() for l in lines if l.strip()]

    # 提取标题（通常在前几行，较长的行）
    for line in clean_lines[:10]:
        if len(line) > 20 and not line.startswith("http") and "doi" not in line.lower():
            meta["title"] = line[:200]
            break

    # 提取年份
    year_match = re.search(r'(?:19|20)\d{2}', text[:2000])
    if year_match:
        meta["year"] = year_match.group()

    # 提取摘要
    abstract_patterns = [
        r'(?:Abstract|ABSTRACT|摘要)[:\s]*\n?(.*?)(?:\n\n|Keywords|KEYWORDS|Introduction|1\.|1\s)',
        r'(?:Abstract|ABSTRACT)[:\s]*(.{100,2000}?)(?:\n\n|\nKeywords)',
    ]
    for pat in abstract_patterns:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            meta["abstract"] = m.group(1).strip()[:1000]
            break

    # 提取关键词
    kw_match = re.search(r'(?:Keywords?|KEYWORDS?|关键词)[:\s]*(.*?)(?:\n\n|\n(?:1\.|Introduction))', text, re.DOTALL | re.IGNORECASE)
    if kw_match:
        kw_text = kw_match.group(1).strip()
        kws = re.split(r'[,;，；]', kw_text)
        meta["keywords"] = [k.strip() for k in kws if len(k.strip()) > 2][:10]

    # 识别研究方法
    method_keywords = {
        "IPCC": "IPCC排放因子法",
        "emission factor": "排放因子法",
        "排放因子": "排放因子法",
        "direct measurement": "实测法",
        "direct monitoring": "实测法",
        "实测": "实测法",
        "on-site": "实测法",
        "field measurement": "实测法",
        "model": "模型法",
        "modeling": "模型法",
        "model-based": "模型法",
        "Monte Carlo": "蒙特卡洛模拟",
        "life cycle": "生命周期评价(LCA)",
        "LCA": "生命周期评价(LCA)",
        "carbon footprint": "碳足迹分析",
        "PCA": "主成分分析",
        "principal component": "主成分分析",
        "regression": "回归分析",
        "correlation": "相关性分析",
        "ANOVA": "方差分析",
        "Mann-Whitney": "非参数检验",
        "t-test": "t检验",
        "Shapiro": "正态性检验",
        "sensitivity analysis": "敏感性分析",
        "uncertainty": "不确定性分析",
        "scenario": "情景分析",
        "machine learning": "机器学习",
        "neural network": "神经网络",
        "random forest": "随机森林",
        "deep learning": "深度学习",
        "GAN": "生成对抗网络(GAN)",
        "remote sensing": "遥感",
        "isotope": "同位素示踪",
        "tracer": "示踪剂",
        "mass balance": "质量平衡",
        "carbon balance": "碳平衡",
    }

    text_lower = text.lower()
    for kw, method_name in method_keywords.items():
        if kw.lower() in text_lower:
            if method_name not in meta["methods"]:
                meta["methods"].append(method_name)

    # 识别关键发现模式
    finding_patterns = [
        r'(?:results? (?:showed?|indicated?|revealed?|demonstrated?|suggested?))[:\s]*([^.]*(?:\.|$)){1,3}',
        r'(?:findings?|conclusions?)[:\s]*([^.]*(?:\.|$)){1,3}',
        r'(?:我们|本研究|本)(?:发现|结果表明|揭示)[:\s]*([^。]*(?:。|$)){1,3}',
    ]
    for pat in finding_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches[:3]:
            finding = m.strip()
            if 20 < len(finding) < 300:
                meta["key_findings"].append(finding)

    # 识别写作模式
    writing_patterns = {
        "uses IMRAD structure": r'(?:Introduction|Methods?|Results?|Discussion)',
        "has carbon balance": r'carbon.{0,20}balance',
        "compares methods": r'compar.{0,30}method',
        "includes uncertainty": r'uncertainty.{0,30}analysis',
        "has sensitivity analysis": r'sensitivity.{0,30}analysis',
        "discusses limitations": r'limitation',
        "provides policy implications": r'policy.{0,20}implication',
        "uses statistical tests": r'(?:p\s*[<>]|statistical|significant)',
        "has figure references": r'(?:Fig\.|Figure|图)\s*\d',
        "cites IPCC": r'IPCC',
    }
    for pattern_name, pat in writing_patterns.items():
        if re.search(pat, text, re.IGNORECASE):
            meta["writing_patterns"].append(pattern_name)

    return meta


def batch_read():
    """批量读取所有PDF"""
    pdf_files = sorted([
        f for f in os.listdir(LITERATURE_DIR) if f.endswith('.pdf')
    ])

    print(f"=" * 70)
    print(f"  文献批量阅读系统")
    print(f"  目录: {LITERATURE_DIR}")
    print(f"  文献数: {len(pdf_files)}")
    print(f"=" * 70)

    all_meta = []
    errors = []

    for i, filename in enumerate(pdf_files, 1):
        pdf_path = os.path.join(LITERATURE_DIR, filename)
        print(f"\n  [{i}/{len(pdf_files)}] {filename[:60]}...", end=" ")

        # 提取文本
        text = extract_text_from_pdf(pdf_path, max_pages=12)
        if text.startswith("[ERROR"):
            print(f"FAIL: {text}")
            errors.append(filename)
            continue

        if len(text) < 100:
            print(f"SKIP (too short: {len(text)} chars)")
            errors.append(filename)
            continue

        # 提取元数据
        meta = extract_metadata(text, filename)
        all_meta.append(meta)

        methods_str = ", ".join(meta["methods"][:3]) if meta["methods"] else "未识别"
        print(f"OK ({len(text)} chars, methods: {methods_str})")

    # 保存结构化数据
    json_path = os.path.join(OUTPUT_DIR, "literature_metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_meta, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 70}")
    print(f"  解析完成")
    print(f"  成功: {len(all_meta)} 篇")
    print(f"  失败: {len(errors)} 篇")
    print(f"  数据已保存: {json_path}")

    return all_meta, errors


if __name__ == "__main__":
    all_meta, errors = batch_read()
