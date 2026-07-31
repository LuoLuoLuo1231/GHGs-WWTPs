"""
增强版批量文献阅读 - 提取详细研究方法信息
基于 GHGs-WWTPs/scripts/batch_read_papers.py 改进
"""
import os
import sys
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

import pdfplumber

PDF_DIR = r"D:\下载\文献数据整理\论文写作技巧学习—agent训练"
OUT_DIR = r"D:\VScode\firstcc\paper_method_analysis\results"
os.makedirs(OUT_DIR, exist_ok=True)


def extract_text(pdf_path, max_pages=15):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            parts = []
            for page in pdf.pages[:max_pages]:
                t = page.extract_text()
                if t:
                    parts.append(t)
            return "\n\n".join(parts)
    except Exception as e:
        return ""


def extract_methods_detailed(text, filename):
    """提取详细研究方法信息 - 上下文感知"""
    results = []
    text_lower = text.lower()

    # === 1. 排放因子法 ===
    ef_patterns = {
        "IPCC 2006": r'ipcc.{0,30}(2006|tier\s*1|tier\s*2|tier\s*3)',
        "IPCC 2019": r'ipcc.{0,30}2019',
        "IPCC 2014": r'ipcc.{0,30}2014',
        "IPCC默认排放因子": r'ipcc.{0,30}(default|recommended).{0,30}(emission factor|ef)',
        "工艺特定排放因子": r'(process-specific|technology-specific|工艺特定).{0,30}(emission factor|ef|排放因子)',
        "本地化排放因子": r'(localized|local|country-specific|本地化).{0,30}(emission factor|ef|排放因子)',
        "自定义排放因子": r'(custom|own|developed|自定义|建立).{0,30}(emission factor|ef|排放因子)',
        "排放因子法": r'emission factor',
        "排放因子法(中)": r'排放因子',
    }
    for name, pat in ef_patterns.items():
        if re.search(pat, text_lower):
            # 找上下文
            ctx = _find_context(text, pat, text_lower)
            results.append({"method": "排放因子法", "detail": name, "context": ctx})

    # === 2. 实测法 ===
    measurement_patterns = {
        "密闭室法/通量室法": r'(closed|static|floating).{0,20}(chamber|flux)',
        "密闭室法(中)": r'(密闭室|静态箱|通量箱|通量室)',
        "开路法": r'open.?path|open.?circuit|开路',
        "涡度相关法": r'eddy covariance|涡度相关',
        "移动测量": r'(mobile|vehicle).{0,20}(lab|measurement|monitoring)',
        "移动实验室(中)": r'移动(实验室|测量|监测)',
        "羽流测量": r'plume.{0,20}(measurement|mapping)',
        "遥感": r'remote sensing|遥感|LiDAR|lidar',
        "FTIR": r'FTIR|fourier transform infrared',
        "GC-FID": r'GC.?FID|gas chromatograph.{0,30}flame ionization',
        "GC-ECD": r'GC.?ECD|gas chromatograph.{0,30}electron capture',
        "GC-MS": r'GC.?MS|gas chromatograph.{0,30}mass spec',
        "气相色谱(中)": r'气相色谱|GC分析',
        "Picarro": r'picarro|cavity ring.down|CRDS',
        "激光分析": r'(laser|tunable diode|TDLAS)',
        "Off-gas法": r'off.?gas|废气分析',
        "顶空平衡法": r'headspace.{0,20}(equilibration|equilibrium)|顶空平衡',
        "微电极": r'microsensor|microelectrode|unisense|微电极',
        "在线监测": r'online.{0,20}monitor|continuous.{0,20}monitor|在线监测',
    }
    for name, pat in measurement_patterns.items():
        if re.search(pat, text_lower):
            ctx = _find_context(text, pat, text_lower)
            results.append({"method": "实测法", "detail": name, "context": ctx})

    # === 3. 模型法 ===
    model_patterns = {
        "LCA生命周期评价": r'life cycle assess|LCA|生命周期评价',
        "SimaPro": r'simapro',
        "GaBi": r'gabi\s',
        "ASM活性污泥模型": r'ASM[123d]|activated sludge model',
        "GPS-X": r'gps.?x',
        "SUMO": r'sumo\s|sumo\d|dynamita',
        "ADM厌氧消化模型": r'ADM[12]|anaerobic digestion model',
        "蒙特卡洛模拟": r'monte carlo',
        "机器学习": r'machine learning|ML model',
        "人工神经网络ANN": r'artificial neural|ANN|neural network',
        "随机森林RF": r'random forest|RF\b',
        "LSTM": r'LSTM|long short.term memory',
        "支持向量机SVR": r'support vector|SVR|SVM',
        "GAN生成对抗网络": r'generative adversarial|GAN',
        "AERMOD扩散模型": r'AERMOD',
        "高斯扩散模型": r'gaussian.{0,20}(plume|dispersion|model)',
        "系统动力学": r'STELLA|system dynamics|系统动力学',
        "CGE模型": r'CGE|computable general equilibrium',
        "DEA数据包络分析": r'data envelopment|DEA',
        "结构方程模型SEM": r'structural equation|SEM\b',
        "ECAM工具": r'ECAM',
        "物料平衡": r'mass balance|物料平衡|质量平衡',
        "碳平衡": r'carbon balance|碳平衡',
        "化学计量模型": r'stoichiometric|化学计量',
        "IPAT模型": r'IPAT',
        "LMDI分解": r'LMDI|logarithmic mean divisia',
        "情景分析": r'scenario.{0,20}analysis|情景分析',
        "敏感性分析": r'sensitivity analysis|敏感性分析',
        "不确定性分析": r'uncertainty analysis|不确定性分析',
        "回归分析": r'regression.{0,20}analysis|回归分析',
    }
    for name, pat in model_patterns.items():
        if re.search(pat, text_lower):
            ctx = _find_context(text, pat, text_lower)
            results.append({"method": "模型法", "detail": name, "context": ctx})

    # === 4. 统计分析方法 ===
    stat_patterns = {
        "Pearson相关分析": r'pearson.{0,20}correlat',
        "Spearman相关分析": r'spearman.{0,20}correlat',
        "ANOVA方差分析": r'ANOVA|analysis of variance|方差分析',
        "t检验": r't.?test',
        "Mann-Whitney U检验": r'mann.?whitney',
        "Kruskal-Wallis检验": r'kruskal.?wallis',
        "Shapiro-Wilk检验": r'shapiro.?wilk',
        "Tukey事后检验": r'tukey',
        "Wilcoxon检验": r'wilcoxon',
        "主成分分析PCA": r'PCA|principal component',
        "冗余分析RDA": r'redundancy analysis|RDA',
        "聚类分析": r'cluster analysis|HCA|层次聚类',
    }
    for name, pat in stat_patterns.items():
        if re.search(pat, text_lower):
            results.append({"method": "统计分析", "detail": name, "context": ""})

    # === 5. 其他方法 ===
    other_patterns = {
        "文献综述": r'(systematic )?literature review|systematic review|综述',
        "Meta分析": r'meta.?analysis',
        "碳足迹分析": r'carbon footprint',
        "16S rRNA测序": r'16S rRNA|16S.{0,10}sequencing',
        "FISH荧光原位杂交": r'FISH|fluorescence in situ',
        "呼吸测量OUR": r'OUR|oxygen uptake rate|呼吸测量',
        "同位素示踪": r'isotope|isotopic|同位素',
    }
    for name, pat in other_patterns.items():
        if re.search(pat, text_lower):
            results.append({"method": "其他方法", "detail": name, "context": ""})

    # 去重
    seen = set()
    unique = []
    for r in results:
        key = r["detail"]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


def _find_context(text, pattern, text_lower):
    """找到关键词周围的上下文"""
    m = re.search(pattern, text_lower)
    if not m:
        return ""
    start = max(0, m.start() - 100)
    end = min(len(text), m.end() + 200)
    ctx = text[start:end].replace('\n', ' ').strip()
    # 清理
    ctx = re.sub(r'\s+', ' ', ctx)
    return ctx[:300]


def extract_purpose(text, methods):
    """根据方法和全文提取应用目的"""
    text_lower = text.lower()
    purposes = []

    # 从摘要中提取目的
    abstract_m = re.search(r'(?:abstract|摘要)[:\s]*(.{100,1500}?)(?:\n\n|keywords|1\.|introduction)', text, re.DOTALL | re.IGNORECASE)
    if abstract_m:
        abstract = abstract_m.group(1).strip()
        # 找目的句
        purpose_patterns = [
            r'(?:this study|this paper|this research|本文|本研究).{0,30}(?:aim|purpose|objective|evaluate|assess|investigate|quantif|estimat|analyz|develop|propos).{0,300}',
            r'(?:aim|purpose|objective)[:\s]*([^.]*(?:\.|$)){1,3}',
        ]
        for pat in purpose_patterns:
            pm = re.search(pat, abstract, re.IGNORECASE)
            if pm:
                purposes.append(pm.group(0).strip()[:200])
                break

    return purposes


def batch_extract():
    """批量提取所有论文的研究方法"""
    pdf_files = sorted([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')])
    print(f"共 {len(pdf_files)} 个 PDF 文件")

    all_results = []
    for i, fname in enumerate(pdf_files):
        pdf_path = os.path.join(PDF_DIR, fname)
        text = extract_text(pdf_path, max_pages=12)
        if not text or len(text) < 100:
            print(f"[{i+1}] SKIP: {fname[:50]}")
            continue

        methods = extract_methods_detailed(text, fname)
        purposes = extract_purpose(text, methods)

        # 提取标题
        title = ""
        for line in text.split("\n")[:10]:
            line = line.strip()
            if len(line) > 20 and 'doi' not in line.lower():
                title = line[:150]
                break

        # 提取年份
        year_m = re.search(r'(?:19|20)\d{2}', text[:2000])
        year = year_m.group() if year_m else ""

        entry = {
            "index": i + 1,
            "filename": fname,
            "title": title,
            "year": year,
            "methods": methods,
            "purposes": purposes,
        }
        all_results.append(entry)

        m_count = len(methods)
        m_names = [m["detail"] for m in methods[:5]]
        print(f"[{i+1}/{len(pdf_files)}] {fname[:45]} | {m_count}种方法: {', '.join(m_names)}")

    # 保存 JSON
    json_path = os.path.join(OUT_DIR, "methods_extracted.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 生成文本报告
    report_path = os.path.join(OUT_DIR, "研究方法提取报告.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("112篇污水处理厂温室气体排放论文 — 研究方法详细提取报告\n")
        f.write("=" * 80 + "\n")
        f.write(f"提取日期: 2026-06-16\n")
        f.write(f"论文总数: {len(all_results)}\n")
        f.write("=" * 80 + "\n\n")

        for entry in all_results:
            fname = entry["filename"]
            # 提取编号
            num_m = re.search(r'（(\d+)）', fname)
            num = num_m.group(1) if num_m else str(entry["index"])

            f.write(f"（{num}）{entry['title'][:100]}\n")
            f.write(f"  年份: {entry['year']}\n")

            if entry['methods']:
                # 按大类分组
                by_cat = {}
                for m in entry['methods']:
                    cat = m['method']
                    if cat not in by_cat:
                        by_cat[cat] = []
                    by_cat[cat].append(m)

                for cat, mlist in by_cat.items():
                    details = [m['detail'] for m in mlist]
                    f.write(f"  {cat}: {', '.join(details)}\n")
                    for m in mlist:
                        if m.get('context'):
                            ctx = m['context'][:150]
                            f.write(f"    → 上下文: {ctx}\n")
            else:
                f.write(f"  研究方法: 未识别\n")

            if entry['purposes']:
                for p in entry['purposes']:
                    f.write(f"  应用目的: {p}\n")

            f.write("\n")

    print(f"\nJSON: {json_path}")
    print(f"报告: {report_path}")
    return all_results


if __name__ == "__main__":
    batch_extract()
