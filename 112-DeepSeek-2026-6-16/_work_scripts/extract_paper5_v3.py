"""通过内存读取PDF - 绕过中文路径问题"""
import os, fitz

pdf_dir = r"D:\下载\文献数据整理\论文写作技巧学习—agent训练"
target = None

# scandir获取DirEntry，通过entry读文件数据
with os.scandir(pdf_dir) as entries:
    for entry in entries:
        if entry.is_file() and entry.name.startswith('\uff085\uff09') and 'empirical' in entry.name.lower():
            target = entry
            break

if not target:
    print("Not found via scandir")
    exit(1)

print(f"Found: {target.name}")

# 读取文件原始字节
# Windows下通过 \\\\?\\ 前缀处理长路径
try:
    with open(target.path, 'rb') as f:
        data = f.read()
except Exception as e:
    # fallback: try via short path
    import subprocess
    result = subprocess.run(['cmd', '/c', 'dir', '/x', '/b', target.path.replace('\uff08', '(').replace('\uff09', ')')], 
                          capture_output=True, text=True, shell=True)
    print(f"Short name attempt: {result.stdout}")
    raise e

print(f"Read {len(data)} bytes")

# 从内存打开PDF
doc = fitz.open("pdf", data)
text = ""
for page in doc:
    text += page.get_text()
doc.close()

out_path = r"d:\VScode\firstcc\temp_papers\paper_5_extracted.txt"
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(text)

print(f"OK: {len(text)} chars -> {out_path}")
print("--- First 1000 chars ---")
print(text[:1000])