"""Extract paper (5) from PDF to text"""
import fitz  # PyMuPDF
import os

pdf_dir = r"D:\下载\文献数据整理\论文写作技巧学习—agent训练"
pdf_path = ""
txt_path = ""

# Try to find the actual file
for f in os.listdir(pdf_dir):
    if f.startswith('\uff085') and 'Analysis of empirical methods' in f:
        pdf_path = os.path.join(pdf_dir, f)
        txt_name = f.replace('.pdf', '.txt')
        txt_path = os.path.join(r"d:\VScode\firstcc\temp_papers", txt_name)
        print(f"Found: {pdf_path}")
        break

if not pdf_path:
    print("File not found!")
    exit(1)

doc = fitz.open(pdf_path)
text = ""
for page in doc:
    text += page.get_text()
doc.close()

with open(txt_path, 'w', encoding='utf-8') as f:
    f.write(text)

print(f"Extracted {len(text)} chars to {txt_path}")
print("First 500 chars:")
print(text[:500])