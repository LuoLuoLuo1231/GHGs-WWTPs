"""
=============================================================================
GHGs-WWTPs 统一系统入口
污水处理厂温室气体排放研究全流程平台
=============================================================================

功能模块：
1. 文献阅读 → 知识库
2. 数据分析 → 元分析
3. 图表生成 → 可视化
4. 论文写作 → 各章节
5. 论文审阅 → 审阅报告
6. AI优化 → 最终论文

使用方式：
    python ghgs_wwtp_system.py                    # 交互式菜单
    python ghgs_wwtp_system.py --all              # 运行全流程
    python ghgs_wwtp_system.py --literature       # 只运行文献阅读
    python ghgs_wwtp_system.py --analysis         # 只运行数据分析
    python ghgs_wwtp_system.py --writing          # 只运行论文写作
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# 设置编码
sys.stdout.reconfigure(encoding='utf-8')

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)


# ============================================================================
# 系统配置
# ============================================================================
class SystemConfig:
    """系统配置"""

    # 目录配置
    LITERATURE_DIR = r"D:\下载\文献数据整理\artical learning-agent train"
    DATA_DIR = r"D:\下载\文献数据整理\数据分析\数据分析2026.6.8"
    OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
    KNOWLEDGE_DIR = os.path.join(SCRIPT_DIR, "knowledge_store")
    DOMAINS_DIR = os.path.join(SCRIPT_DIR, "domains")

    # 输出子目录
    LITERATURE_OUTPUT = os.path.join(OUTPUT_DIR, "literature_learning")
    ANALYSIS_OUTPUT = os.path.join(OUTPUT_DIR, "analysis")
    FIGURES_OUTPUT = os.path.join(OUTPUT_DIR, "figures")
    PAPER_OUTPUT = os.path.join(OUTPUT_DIR, "paper")
    REVIEW_OUTPUT = os.path.join(OUTPUT_DIR, "review")

    # 默认配置
    DEFAULT_DOMAIN = "environmental_ghg"
    DEFAULT_LANGUAGE = "zh"

    @classmethod
    def init_dirs(cls):
        """初始化所有目录"""
        for dir_path in [cls.OUTPUT_DIR, cls.LITERATURE_OUTPUT, cls.ANALYSIS_OUTPUT,
                         cls.FIGURES_OUTPUT, cls.PAPER_OUTPUT, cls.REVIEW_OUTPUT]:
            os.makedirs(dir_path, exist_ok=True)


# ============================================================================
# 模块1: 文献阅读
# ============================================================================
class LiteratureModule:
    """文献阅读模块"""

    @staticmethod
    def run(literature_dir: str = None, domain: str = None, max_papers: int = None):
        """
        运行文献阅读

        Parameters:
        -----------
        literature_dir : str
            文献目录
        domain : str
            领域名称
        max_papers : int
            最大处理论文数
        """
        print("\n" + "=" * 70)
        print("  模块1: 文献批量阅读")
        print("=" * 70)

        literature_dir = literature_dir or SystemConfig.LITERATURE_DIR
        domain = domain or SystemConfig.DEFAULT_DOMAIN

        try:
            from literature_batch_reader_universal import UniversalLiteratureReader, DomainConfig

            # 加载领域配置
            try:
                domain_config = DomainConfig.load_domain_from_domains_dir(domain, SystemConfig.DOMAINS_DIR)
            except:
                domain_config = DomainConfig.get_domain_config(domain)

            # 创建阅读器
            reader = UniversalLiteratureReader(
                literature_dir=literature_dir,
                output_dir=SystemConfig.LITERATURE_OUTPUT,
                knowledge_dir=SystemConfig.KNOWLEDGE_DIR,
                custom_config=domain_config
            )

            # 运行
            results = reader.run(max_papers=max_papers)

            print(f"\n✓ 文献阅读完成: {len(results)} 篇")
            return results

        except ImportError as e:
            print(f"\n✗ 文献阅读模块不可用: {e}")
            return []
        except Exception as e:
            print(f"\n✗ 文献阅读失败: {e}")
            return []


# ============================================================================
# 模块2: 数据分析
# ============================================================================
class AnalysisModule:
    """数据分析模块"""

    @staticmethod
    def run(data_path: str = None, group_col: str = "Method", value_cols: list = None):
        """
        运行数据分析

        Parameters:
        -----------
        data_path : str
            数据文件路径
        group_col : str
            分组列名
        value_cols : list
            数值列名列表
        """
        print("\n" + "=" * 70)
        print("  模块2: 数据分析")
        print("=" * 70)

        data_path = data_path or os.path.join(SystemConfig.DATA_DIR, "2222.xlsx")
        value_cols = value_cols or ["CH4", "N2O", "CO2"]

        try:
            import pandas as pd
            from scientific_analysis_agent import MetaAnalysisIntegrator

            # 加载数据
            print(f"\n  加载数据: {data_path}")
            df = pd.read_excel(data_path)
            print(f"  数据规模: {df.shape[0]} 行 × {df.shape[1]} 列")

            # 创建分析器
            integrator = MetaAnalysisIntegrator(df, SystemConfig.ANALYSIS_OUTPUT)

            # 运行基础分析
            print("\n  [1/2] 运行基础分析...")
            from scientific_analysis_agent import ScientificAnalysisAgent
            agent = ScientificAnalysisAgent(data_path, SystemConfig.ANALYSIS_OUTPUT)
            agent.load_data()
            agent.run(language='zh')

            # 运行元分析
            print("\n  [2/2] 运行元分析...")
            meta_results = integrator.run_multi_gas_analysis(
                gas_cols=value_cols,
                method_col=group_col,
                exclude_groups=["混法"]  # 排除样本量太少的组
            )

            # 方法比较
            comparison = integrator.compare_methods(
                method_col=group_col,
                value_cols=value_cols
            )

            # 保存比较结果
            comparison_path = os.path.join(SystemConfig.ANALYSIS_OUTPUT, "method_comparison.csv")
            comparison.to_csv(comparison_path, index=False, encoding='utf-8-sig')

            print(f"\n✓ 数据分析完成")
            print(f"  分析报告: {SystemConfig.ANALYSIS_OUTPUT}")

            return meta_results

        except ImportError as e:
            print(f"\n✗ 分析模块不可用: {e}")
            return {}
        except Exception as e:
            print(f"\n✗ 数据分析失败: {e}")
            return {}


# ============================================================================
# 模块3: 可视化
# ============================================================================
class VisualizationModule:
    """可视化模块"""

    @staticmethod
    def run(data_path: str = None, style: str = "sci"):
        """
        运行可视化

        Parameters:
        -----------
        data_path : str
            数据文件路径
        style : str
            样式 (sci/nature/chinese)
        """
        print("\n" + "=" * 70)
        print("  模块3: 数据可视化")
        print("=" * 70)

        data_path = data_path or os.path.join(SystemConfig.DATA_DIR, "2222.xlsx")

        try:
            from scientific_visualization_agent import visualize

            print(f"\n  样式: {style}")
            print(f"  数据: {data_path}")

            # 生成图表
            fig = visualize(data_path, style=style, output_dir=SystemConfig.FIGURES_OUTPUT)

            print(f"\n✓ 可视化完成")
            print(f"  图表目录: {SystemConfig.FIGURES_OUTPUT}")

            return fig

        except ImportError as e:
            print(f"\n✗ 可视化模块不可用: {e}")
            return None
        except Exception as e:
            print(f"\n✗ 可视化失败: {e}")
            return None


# ============================================================================
# 模块4: 论文写作
# ============================================================================
class WritingModule:
    """论文写作模块"""

    @staticmethod
    def run(topic: str = None, field: str = None, variables: dict = None):
        """
        运行论文写作

        Parameters:
        -----------
        topic : str
            研究主题
        field : str
            研究领域
        variables : dict
            变量配置
        """
        print("\n" + "=" * 70)
        print("  模块4: 论文写作")
        print("=" * 70)

        topic = topic or "污水处理厂温室气体排放方法学差异研究"
        field = field or "环境科学"
        variables = variables or {
            'gas': ['CH4', 'CO2', 'N2O'],
            'method': ['排放因子法', '模型法', '实测法']
        }

        try:
            from paper_writing_agent import write_paper, ResearchDirection

            # 配置研究方向
            direction = ResearchDirection(
                field=field,
                topic=topic,
                object_name="污水处理厂",
                variables=variables
            )

            print(f"\n  主题: {topic}")
            print(f"  领域: {field}")

            # 生成论文
            paper = write_paper(direction=direction)

            print(f"\n✓ 论文写作完成")
            print(f"  输出目录: {SystemConfig.PAPER_OUTPUT}")

            return paper

        except ImportError as e:
            print(f"\n✗ 写作模块不可用: {e}")
            return None
        except Exception as e:
            print(f"\n✗ 论文写作失败: {e}")
            return None


# ============================================================================
# 模块5: 论文审阅
# ============================================================================
class ReviewModule:
    """论文审阅模块"""

    @staticmethod
    def run(paper_path: str = None):
        """
        运行论文审阅

        Parameters:
        -----------
        paper_path : str
            论文文件路径
        """
        print("\n" + "=" * 70)
        print("  模块5: 论文审阅")
        print("=" * 70)

        # 默认查找最新生成的论文
        if not paper_path:
            paper_files = list(Path(SystemConfig.PAPER_OUTPUT).glob("*.docx"))
            if paper_files:
                paper_path = str(max(paper_files, key=lambda p: p.stat().st_mtime))
            else:
                print("\n✗ 未找到论文文件")
                return None

        try:
            from academic_review_agent import review_paper

            print(f"\n  论文: {paper_path}")

            # 审阅论文
            report = review_paper(paper_path)

            # 生成报告
            report_path = os.path.join(SystemConfig.REVIEW_OUTPUT, "review_report.md")
            report.generate_report(report_path)

            print(f"\n✓ 论文审阅完成")
            print(f"  审阅报告: {report_path}")

            return report

        except ImportError as e:
            print(f"\n✗ 审阅模块不可用: {e}")
            return None
        except Exception as e:
            print(f"\n✗ 论文审阅失败: {e}")
            return None


# ============================================================================
# 模块6: AI优化
# ============================================================================
class AIOptimizer:
    """AI优化模块"""

    @staticmethod
    def run(section: str = "discussion", data: dict = None):
        """
        运行AI优化

        Parameters:
        -----------
        section : str
            要优化的章节
        data : dict
            分析结果数据
        """
        print("\n" + "=" * 70)
        print("  模块6: AI优化")
        print("=" * 70)

        try:
            from claude_writer import ClaudeWriter

            writer = ClaudeWriter()

            print(f"\n  优化章节: {section}")

            # 根据章节类型调用不同的写作方法
            output_path = os.path.join(SystemConfig.PAPER_OUTPUT, f"section_{section}_optimized.md")

            if section == "introduction":
                writer.write_introduction(
                    topic="污水处理厂温室气体排放方法学差异",
                    output_path=output_path
                )
            elif section == "methods":
                writer.write_methods(
                    methods=data or {},
                    output_path=output_path
                )
            elif section == "results":
                writer.write_results(
                    data=data or {},
                    output_path=output_path
                )
            elif section == "discussion":
                writer.write_discussion(
                    results=data or {},
                    output_path=output_path
                )
            elif section == "abstract":
                writer.write_abstract(
                    paper=data or {},
                    output_path=output_path
                )
            elif section == "conclusion":
                writer.write_conclusion(
                    results=data or {},
                    output_path=output_path
                )
            else:
                print(f"\n✗ 不支持的章节: {section}")
                return None

            print(f"\n✓ AI优化完成")
            print(f"  输出文件: {output_path}")

            return output_path

        except ImportError as e:
            print(f"\n✗ AI优化模块不可用: {e}")
            return None
        except Exception as e:
            print(f"\n✗ AI优化失败: {e}")
            return None


# ============================================================================
# 全流程运行
# ============================================================================
class FullPipeline:
    """全流程运行"""

    @staticmethod
    def run(config: dict = None):
        """
        运行全流程

        Parameters:
        -----------
        config : dict
            配置参数
        """
        config = config or {}

        print("\n" + "=" * 70)
        print("  GHGs-WWTPs 全流程运行")
        print("=" * 70)
        print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 初始化目录
        SystemConfig.init_dirs()

        results = {}

        # Step 1: 文献阅读
        if config.get('literature', True):
            results['literature'] = LiteratureModule.run(
                literature_dir=config.get('literature_dir'),
                domain=config.get('domain'),
                max_papers=config.get('max_papers')
            )

        # Step 2: 数据分析
        if config.get('analysis', True):
            results['analysis'] = AnalysisModule.run(
                data_path=config.get('data_path'),
                group_col=config.get('group_col', 'Method'),
                value_cols=config.get('value_cols', ['CH4', 'N2O', 'CO2'])
            )

        # Step 3: 可视化
        if config.get('visualization', True):
            results['visualization'] = VisualizationModule.run(
                data_path=config.get('data_path'),
                style=config.get('style', 'sci')
            )

        # Step 4: 论文写作
        if config.get('writing', True):
            results['writing'] = WritingModule.run(
                topic=config.get('topic'),
                field=config.get('field'),
                variables=config.get('variables')
            )

        # Step 5: 论文审阅
        if config.get('review', True):
            results['review'] = ReviewModule.run(
                paper_path=config.get('paper_path')
            )

        # 打印总结
        print("\n" + "=" * 70)
        print("  全流程完成!")
        print("=" * 70)
        print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n  输出目录:")
        print(f"    文献学习: {SystemConfig.LITERATURE_OUTPUT}")
        print(f"    数据分析: {SystemConfig.ANALYSIS_OUTPUT}")
        print(f"    图表: {SystemConfig.FIGURES_OUTPUT}")
        print(f"    论文: {SystemConfig.PAPER_OUTPUT}")
        print(f"    审阅: {SystemConfig.REVIEW_OUTPUT}")

        return results


# ============================================================================
# 交互式菜单
# ============================================================================
def interactive_menu():
    """交互式菜单"""

    print("\n" + "=" * 70)
    print("  GHGs-WWTPs 污水处理厂温室气体排放研究系统")
    print("=" * 70)

    # 初始化目录
    SystemConfig.init_dirs()

    while True:
        print("\n" + "-" * 40)
        print("  主菜单")
        print("-" * 40)
        print("  1. 文献批量阅读")
        print("  2. 数据分析 (含元分析)")
        print("  3. 数据可视化")
        print("  4. 论文写作")
        print("  5. 论文审阅")
        print("  6. AI优化")
        print("  7. 全流程运行")
        print("  0. 退出")
        print("-" * 40)

        choice = input("\n请选择功能 [0-7]: ").strip()

        if choice == '0':
            print("\n再见!")
            break

        elif choice == '1':
            LiteratureModule.run()

        elif choice == '2':
            AnalysisModule.run()

        elif choice == '3':
            style = input("选择样式 (sci/nature/chinese) [sci]: ").strip() or "sci"
            VisualizationModule.run(style=style)

        elif choice == '4':
            topic = input("研究主题 [污水处理厂温室气体排放方法学差异研究]: ").strip()
            WritingModule.run(topic=topic or None)

        elif choice == '5':
            ReviewModule.run()

        elif choice == '6':
            section = input("优化章节 (introduction/methods/results/discussion/abstract/conclusion) [discussion]: ").strip()
            AIOptimizer.run(section=section or "discussion")

        elif choice == '7':
            confirm = input("确认运行全流程? (y/n) [y]: ").strip()
            if confirm.lower() != 'n':
                FullPipeline.run()

        else:
            print("\n无效选择，请重试")


# ============================================================================
# 命令行入口
# ============================================================================
def main():
    """命令行入口"""

    parser = argparse.ArgumentParser(
        description="GHGs-WWTPs 污水处理厂温室气体排放研究系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ghgs_wwtp_system.py                    # 交互式菜单
  python ghgs_wwtp_system.py --all              # 运行全流程
  python ghgs_wwtp_system.py --literature       # 只运行文献阅读
  python ghgs_wwtp_system.py --analysis         # 只运行数据分析
  python ghgs_wwtp_system.py --visualization    # 只运行可视化
  python ghgs_wwtp_system.py --writing          # 只运行论文写作
  python ghgs_wwtp_system.py --review           # 只运行论文审阅
  python ghgs_wwtp_system.py --optimize discussion  # AI优化指定章节
        """
    )

    parser.add_argument('--all', action='store_true', help='运行全流程')
    parser.add_argument('--literature', action='store_true', help='运行文献阅读')
    parser.add_argument('--analysis', action='store_true', help='运行数据分析')
    parser.add_argument('--visualization', action='store_true', help='运行可视化')
    parser.add_argument('--writing', action='store_true', help='运行论文写作')
    parser.add_argument('--review', action='store_true', help='运行论文审阅')
    parser.add_argument('--optimize', type=str, help='AI优化指定章节')

    parser.add_argument('--data', type=str, help='数据文件路径')
    parser.add_argument('--literature-dir', type=str, help='文献目录')
    parser.add_argument('--domain', type=str, help='领域名称')
    parser.add_argument('--style', type=str, default='sci', help='可视化样式')
    parser.add_argument('--topic', type=str, help='研究主题')

    args = parser.parse_args()

    # 如果没有参数，显示交互式菜单
    if len(sys.argv) == 1:
        interactive_menu()
        return

    # 初始化目录
    SystemConfig.init_dirs()

    # 根据参数运行
    if args.all:
        FullPipeline.run({
            'literature_dir': args.literature_dir,
            'domain': args.domain,
            'data_path': args.data,
            'style': args.style,
            'topic': args.topic,
        })
    else:
        if args.literature:
            LiteratureModule.run(args.literature_dir, args.domain)
        if args.analysis:
            AnalysisModule.run(args.data)
        if args.visualization:
            VisualizationModule.run(args.data, args.style)
        if args.writing:
            WritingModule.run(args.topic)
        if args.review:
            ReviewModule.run()
        if args.optimize:
            AIOptimizer.run(args.optimize)


if __name__ == "__main__":
    main()
