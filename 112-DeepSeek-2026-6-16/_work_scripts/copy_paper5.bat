@echo off
chcp 65001 >nul
set "SRC=D:\下载\文献数据整理\论文写作技巧学习—agent训练"
set "DST=d:\VScode\firstcc\temp_papers\paper5_temp.pdf"
for %%f in ("%SRC%\*5*mpirical*") do copy "%%f" "%DST%" >nul 2>&1 && echo COPIED: %%f || echo FAILED