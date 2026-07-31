@echo off
chcp 65001 >nul 2>&1
for %%f in ("D:\下载\文献数据整理\论文写作技巧学习—agent训练\（5）*.pdf") do (
    echo Source: "%%f"
    copy "%%f" "d:\VScode\firstcc\temp_papers\paper5_temp.pdf" >nul 2>&1
    if exist "d:\VScode\firstcc\temp_papers\paper5_temp.pdf" (
        echo COPIED SUCCESS
    ) else (
        echo COPY FAILED
    )
)