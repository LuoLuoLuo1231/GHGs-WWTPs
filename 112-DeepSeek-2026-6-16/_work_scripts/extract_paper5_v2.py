"""提取论文(5)的文本 - 使用os.scandir绕过中文路径编码问题"""
import os
import fitz

pdf_dir = r"D:\下载\文献数据整理\论文写作技巧学习—agent训练"
txt_dir = r"d:\VScode\firstcc\temp_papers"

# 使用scandir获取准确的DirEntry
found = False
with os.scandir(pdf_dir) as entries:
    for entry in entries:
        if entry.is_file() and '5' in entry.name and 'empirical' in entry.name.lower():
            print(f"Found: {entry.path}")
            # 直接使用entry.path打开
            doc = fitz.open(entry.path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            txt_name = entry.name.replace('.pdf', '.txt')
            txt_path = os.path.join(txt_dir, txt_name)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            print(f"Extracted {len(text)} chars -> {txt_path}")
            print("First 600 chars:")
            print(text[:600])
            found = True
            break

if not found:
    print("File not found!")