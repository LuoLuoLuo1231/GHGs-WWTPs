"""
提取缺失的7篇PDF文献文本，并保存到temp_papers目录
缺失编号: (5), (27), (31), (37), (47), (53), (79)
"""
import os
import sys

source_dir = r"D:\下载\文献数据整理\论文写作技巧学习—agent训练"
output_dir = r"d:\VScode\firstcc\temp_papers"

# 缺失的PDF文件名
missing_papers = [
    "（5）Analysis of empirical methods for the quantification of N2O emissions in wastewater treatment plants Comparison of emission results obtained from the IPCC Tier 1 methodology and the methodologies that integrate operational data.pdf",
    "（27）.pdf",
    "（31）.pdf",
    "（37）.pdf",
    "（47）.pdf",
    "（53）.pdf",
    "（79）.pdf",
]

# 尝试使用 PyMuPDF (fitz)
try:
    import fitz
    print("Using PyMuPDF (fitz) for PDF extraction...")
    
    for pdf_name in missing_papers:
        pdf_path = os.path.join(source_dir, pdf_name)
        txt_name = pdf_name.replace('.pdf', '.txt')
        txt_path = os.path.join(output_dir, txt_name)
        
        if not os.path.exists(pdf_path):
            print(f"NOT FOUND: {pdf_path}")
            continue
        
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            print(f"OK: {txt_name} - {len(text)} chars")
        except Exception as e:
            print(f"ERROR: {pdf_name} - {e}")

except ImportError:
    print("PyMuPDF not available, trying PyPDF2...")
    try:
        from PyPDF2 import PdfReader
        
        for pdf_name in missing_papers:
            pdf_path = os.path.join(source_dir, pdf_name)
            txt_name = pdf_name.replace('.pdf', '.txt')
            txt_path = os.path.join(output_dir, txt_name)
            
            if not os.path.exists(pdf_path):
                print(f"NOT FOUND: {pdf_path}")
                continue
            
            try:
                reader = PdfReader(pdf_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                print(f"OK: {txt_name} - {len(text)} chars")
            except Exception as e:
                print(f"ERROR: {pdf_name} - {e}")
    except ImportError:
        print("No PDF library available. Trying pdfplumber...")
        try:
            import pdfplumber
            
            for pdf_name in missing_papers:
                pdf_path = os.path.join(source_dir, pdf_name)
                txt_name = pdf_name.replace('.pdf', '.txt')
                txt_path = os.path.join(output_dir, txt_name)
                
                if not os.path.exists(pdf_path):
                    print(f"NOT FOUND: {pdf_path}")
                    continue
                
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        text = ""
                        for page in pdf.pages:
                            t = page.extract_text()
                            if t:
                                text += t + "\n"
                    
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    
                    print(f"OK: {txt_name} - {len(text)} chars")
                except Exception as e:
                    print(f"ERROR: {pdf_name} - {e}")
        except ImportError:
            print("No PDF extraction library available!")
            print("Available options: pip install PyMuPDF  OR  pip install PyPDF2  OR  pip install pdfplumber")
            sys.exit(1)

print("\nDone!")