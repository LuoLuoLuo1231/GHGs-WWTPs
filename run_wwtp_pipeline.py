# -*- coding: utf-8 -*-
"""
WWTPs GHG 元分析 + 论文生成 统一管线

用法:
    # 全流程（分析+写作+审稿+排版）
    python run_wwtp_pipeline.py

    # 仅分析
    python run_wwtp_pipeline.py --analyze-only

    # 仅写作（基于已有分析结果）
    python run_wwtp_pipeline.py --write-only

    # 指定数据文件
    python run_wwtp_pipeline.py --data data/2222.xlsx

    # 指定输出目录
    python run_wwtp_pipeline.py --output ./my_output

    # 快速模式（离线，不调用 Claude CLI）
    python run_wwtp_pipeline.py --quick
"""

import argparse
import os
import sys
import logging

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('WWTPs-Pipeline')


def run_analysis_only(data_path, output_dir):
    """仅运行分析（元分析 + 离散分析）"""
    from meta_analysis_module import MetaAnalysisAgent
    from dispersion_analysis_module import DispersionAnalysisAgent

    print('\n' + '='*70)
    print('  WWTPs GHG 元分析管线 — 分析模式')
    print('='*70)

    # 元分析
    print('\n[1/2] 元分析: 排放因子法 vs 实测法 vs 模型法')
    print('-'*50)
    meta_agent = MetaAnalysisAgent(
        data_path=data_path,
        output_dir=os.path.join(output_dir, 'meta_analysis'),
    )
    meta_results = meta_agent.run()

    # 离散分析
    print('\n[2/2] 离散分析: 各方法内部变异特征')
    print('-'*50)
    disp_agent = DispersionAnalysisAgent(
        data_path=data_path,
        output_dir=os.path.join(output_dir, 'dispersion'),
    )
    disp_results = disp_agent.run(df=meta_results['data_clean'])

    # 汇总
    all_findings = meta_results['findings'] + disp_results['findings']
    print('\n' + '='*70)
    print(f'  分析完成: {len(all_findings)} 条发现')
    print(f'  元分析报告: {meta_results["report_path"]}')
    print(f'  图表目录: {os.path.join(output_dir, "meta_analysis")}')
    print(f'  图表目录: {os.path.join(output_dir, "dispersion")}')
    print('='*70)

    return {
        'meta_results': meta_results,
        'disp_results': disp_results,
        'all_findings': all_findings,
    }


def run_full_pipeline(data_path, output_dir, quick=False):
    """运行完整管线（分析+写作+审稿+排版）"""
    from paper_context import PaperContext, PaperOrchestrator

    print('\n' + '='*70)
    print('  WWTPs GHG 元分析管线 — 全流程模式')
    print('='*70)

    # 配置
    ctx = PaperContext(
        data_path=data_path,
        output_dir=output_dir,
        language='zh',
        paper_type='chinese_journal',
        title='污水处理厂温室气体排放核算方法系统性偏差分析',
        domain='wwtps_ghg',
    )

    # 创建编排器
    orchestrator = PaperOrchestrator(ctx)

    # 选择运行模式
    if quick:
        # 快速模式：跳过需要 Claude CLI 的模块
        print('\n  [快速模式] 跳过 AI 写作，使用模板生成')
        steps = [
            'load_data',
            'explorer',
            'meta_analysis',
            'dispersion_analysis',
            'advanced_analysis',
            'assemble',
        ]
    else:
        # 完整模式
        steps = [
            'load_data',
            'explorer',
            'meta_analysis',
            'dispersion_analysis',
            'advanced_analysis',
            'motivation',
            'writer_results',
            'writer_discussion',
            'writer_intro',
            'writer_methods',
            'writer_conclusion',
            'writer_abstract',
            'review',
            'auto_revision',
            'final_check',
            'assemble',
        ]

    # 运行
    orchestrator.run(steps=steps)

    print('\n' + '='*70)
    print(f'  管线完成!')
    print(f'  输出目录: {output_dir}')
    print('='*70)

    return ctx


def main():
    parser = argparse.ArgumentParser(
        description='WWTPs GHG 元分析 + 论文生成管线',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--data', '-d',
        default='data/2222.xlsx',
        help='数据文件路径 (默认: data/2222.xlsx)',
    )
    parser.add_argument(
        '--output', '-o',
        default='./wwtp_output',
        help='输出目录 (默认: ./wwtp_output)',
    )
    parser.add_argument(
        '--analyze-only', '-a',
        action='store_true',
        help='仅运行分析，不生成论文',
    )
    parser.add_argument(
        '--write-only', '-w',
        action='store_true',
        help='仅运行写作（基于已有分析结果）',
    )
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='快速模式（离线，不调用 Claude CLI）',
    )

    args = parser.parse_args()

    # 检查数据文件
    if not os.path.isfile(args.data):
        print(f'错误: 找不到数据文件: {args.data}')
        print(f'请通过 --data 参数指定正确的路径')
        sys.exit(1)

    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)

    # 运行
    if args.analyze_only:
        run_analysis_only(args.data, args.output)
    else:
        run_full_pipeline(args.data, args.output, quick=args.quick)


if __name__ == '__main__':
    main()
