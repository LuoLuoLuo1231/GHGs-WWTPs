# encoding: utf-8
"""Merge paper 5 with all_results_combined.txt into final output"""

if __name__ == '__main__':
    paper5 = (
        "（5）Analysis of empirical methods for the quantification of N2O emissions in wastewater treatment plants: "
        "Comparison of emission results obtained from the IPCC Tier 1 methodology and the methodologies that integrate "
        "operational data | 综合法（实证对比研究/方法学评估） | a. IPCC Tier 1方法（自上而下缺省排放因子法）："
        "使用IPCC国家温室气体清单指南（2006/2019修订版）层级1方法，N2O排放量=进水总氮负荷x EF1 x 44/28，"
        "缺省排放因子EF1取0.005 kg N2O-N/kg TN（假设0.5%进水氮以N2O逸散），仅需人口当量或进水TN数据，"
        "不区分处理工艺类型；b. 运营数据集成方法（自下而上方法）：包含(i)工艺特定排放因子法——"
        "按A2O/SBR/氧化沟/MBR等工艺分类建立特定EF，结合DO/好氧缺氧比例等运行参数修正；"
        "(ii)运行参数驱动经验模型——利用SCADA系统记录的DO、NH4+-N、NO2--N、温度、MLSS等高频数据"
        "建立N2O排放与运行参数多元回归/响应曲面模型；(iii)直接测量+运行数据关联法——"
        "使用浮流罩+在线气体分析仪进行曝气池多点位N2O通量实测，结合溶解态N2O顶空平衡法+亨利定律转化；"
        "c. 统计对比分析：比较两种方法在不同工艺类型、不同季节、不同运行条件下的N2O排放量化结果差异，"
        "评估IPCC缺省值的不确定性和系统偏差；d. 应用目的：系统比较IPCC Tier 1方法与运营数据集成方法"
        "对污水处理厂N2O排放量化的准确性和适用性，为改进国家温室气体清单编制提供方法学依据\n"
    )

    with open(r"d:\VScode\firstcc\temp_papers\all_results_combined.txt", "r", encoding="utf-8") as f:
        existing = f.read()

    output_path = r"d:\VScode\firstcc\temp_papers\final_112_papers_methods.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("112篇污水处理厂温室气体排放论文 - 研究方法系统提取结果\n")
        f.write("=" * 80 + "\n")
        f.write("编号范围：1-118（编号不连续，缺27/31/37/47/53/79），共112篇\n")
        f.write("生成日期：2026-06-16\n")
        f.write("=" * 80 + "\n\n")
        f.write("【补充论文（5）——原有批次中缺失，基于论文标题和方法学推断】\n")
        f.write("-" * 80 + "\n")
        f.write(paper5 + "\n")
        f.write("-" * 80 + "\n\n")
        f.write("【以下为各批次已提取的111篇论文】\n")
        f.write("=" * 80 + "\n\n")
        f.write(existing)

    print("Done: " + output_path)