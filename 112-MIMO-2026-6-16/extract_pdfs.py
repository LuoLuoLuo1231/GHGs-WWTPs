"""批量提取 PDF 论文前10页文本（摘要、引言、方法部分）"""
import pdfplumber
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

PDF_DIR = r"D:\下载\文献数据整理\论文写作技巧学习—agent训练"
OUT_DIR = r"D:\VScode\firstcc\paper_method_analysis\extracted_texts"

files = sorted([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')])
print(f"共找到 {len(files)} 个 PDF 文件")

success, fail = 0, 0
for i, fname in enumerate(files):
    outpath = os.path.join(OUT_DIR, fname.replace('.pdf', '.txt'))
    try:
        with pdfplumber.open(os.path.join(PDF_DIR, fname)) as pdf:
            texts = []
            for j, page in enumerate(pdf.pages[:10]):
                t = page.extract_text()
                if t:
                    texts.append(f"--- Page {j+1} ---\n{t}")
            full = '\n\n'.join(texts)
            with open(outpath, 'w', encoding='utf-8') as f:
                f.write(full)
        success += 1
        print(f"[{i+1}/{len(files)}] OK: {fname[:70]}")
    except Exception as e:
        fail += 1
        print(f"[{i+1}/{len(files)}] FAIL: {fname[:70]} -> {e}")

print(f"\n完成！成功: {success}, 失败: {fail}")
