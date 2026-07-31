# coding: utf-8
"""按编号顺序重新整理final_112.txt"""
import re

with open(r"d:\VScode\firstcc\temp_papers\final_112.txt", "r", encoding="utf-8") as f:
    content = f.read()

# 提取每一篇论文的完整段落
# 模式：以（数字）开头的一行，直到下一个（数字）或分隔线
papers = {}

# 找到所有以"（数字）"开头的行
pattern = r'(（\d+）[^\n]*\n(?:.*?(?=\n（\d+）|\n={10,}|\n-{10,}|\Z)))'
# 简化：按行扫描，聚合每篇的完整内容

lines = content.split('\n')
current_num = None
current_lines = []

for line in lines:
    m = re.match(r'^（(\d+)）', line)
    if m:
        # 保存上一篇
        if current_num is not None and current_lines:
            papers[current_num] = '\n'.join(current_lines)
        current_num = int(m.group(1))
        current_lines = [line]
    else:
        if current_num is not None:
            current_lines.append(line)

# 保存最后一篇
if current_num is not None and current_lines:
    papers[current_num] = '\n'.join(current_lines)

print(f"Extracted {len(papers)} papers")

# 按编号排序输出
output_path = r"d:\VScode\firstcc\temp_papers\final_112_sorted.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write("112篇污水处理厂温室气体排放论文 - 研究方法系统提取结果（按编号排序）\n")
    f.write("=" * 80 + "\n")
    f.write("编号范围：1-118（不连续，缺27/31/37/47/53/79），共112篇\n")
    f.write("生成日期：2026-06-16\n")
    f.write("=" * 80 + "\n\n")

    for num in sorted(papers.keys()):
        f.write(papers[num] + "\n\n")

    # 统计摘要
    f.write("\n" + "=" * 80 + "\n")
    f.write("研究方法统计摘要\n")
    f.write("=" * 80 + "\n")

print(f"Done: {output_path}")

# 验证
with open(output_path, "r", encoding="utf-8") as f:
    c = f.read()
ids = set(int(m.group(1)) for m in re.finditer(r'（(\d+)）', c) if int(m.group(1)) <= 118)
target = set(range(1,27))|set(range(28,31))|set(range(32,37))|set(range(38,47))|set(range(48,53))|set(range(54,79))|set(range(80,119))
missing = sorted(target - ids)
print(f"Covered: {len(ids)}/112, Missing: {missing}")
print("ALL OK!" if len(missing) == 0 else "ISSUES!")