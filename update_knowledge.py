"""更新知识库：添加118篇文献的经验"""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 更新 review_rules.json
with open('knowledge_store/review_rules.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

new_entries = {
    'high_quality_paper_checklist': {
        'value': {
            'name_zh': '高质量论文检查清单',
            'name_en': 'High-Quality Paper Checklist',
            'description': 'Based on 118 papers review',
            'must_have': [
                'IMRAD structure (100% papers)',
                'Figure references (99%)',
                'Statistical tests with p-values (97%)',
                'Cite IPCC/standard methods (92%)',
                'Clear research objectives'
            ],
            'should_have': [
                'Discuss limitations (51% papers)',
                'Sensitivity analysis (23%)',
                'Uncertainty analysis (21%)',
                'Literature comparison in Discussion',
                'Mechanism explanation'
            ],
            'common_rejection_reasons': [
                'Discussion just repeats Results',
                'No limitations discussed',
                'No literature comparison',
                'Methods not clearly described',
                'Poor figure quality',
                'Insufficient or outdated references'
            ]
        },
        'confidence': 0.95,
        'source': 'literature_review_118papers',
        'updated': '2026-06-09T00:00:00+00:00',
        'version': 1
    },
    'discussion_quality_rules': {
        'value': {
            'name_zh': 'Discussion质量检查规则',
            'name_en': 'Discussion Quality Check Rules',
            'rules': [
                'Every finding must have mechanism explanation',
                'Must compare with literature (consistent or different)',
                'Must have data support (not just qualitative)',
                'Must discuss limitations (51% papers include)',
                'Propose future research directions'
            ],
            'good_pattern': 'Finding(1 sentence) + Mechanism(2-3 sentences) + Literature comparison(1-2 sentences) + Data support',
            'mechanism_keywords_en': ['because', 'due to', 'attributed to', 'resulted from', 'mechanism', 'pathway', 'process', 'metabolism', 'anaerobic', 'aerobic', 'microbial', 'degradation'],
            'mechanism_keywords_zh': ['because', 'due to', 'attributed to', 'mechanism', 'pathway', 'process', 'anaerobic', 'aerobic', 'microbial']
        },
        'confidence': 0.95,
        'source': 'literature_review_118papers',
        'updated': '2026-06-09T00:00:00+00:00',
        'version': 1
    },
    'data_visualization_rules': {
        'value': {
            'name_zh': 'Data Visualization Rules',
            'name_en': 'Data Visualization Rules',
            'rules': [
                'Figure reference format: (Fig. X) not "as shown in Fig. X"',
                'Boxplot preferred over bar chart (shows distribution)',
                'Must mark statistical significance (*, **, ***)',
                'Must mark sample size (n)',
                'Must mark units',
                'Color-blind friendly palette (Okabe-Ito/Tableau 10)'
            ],
            'figure_types': {
                'boxplot': 'Distribution and group comparison (preferred)',
                'heatmap': 'Correlation matrix',
                'scatter': 'Two-variable relationship + regression line',
                'forest_plot': 'Meta-analysis effect size',
                'bar_chart': 'Mean comparison (secondary, cannot show distribution)'
            }
        },
        'confidence': 0.95,
        'source': 'literature_review_118papers',
        'updated': '2026-06-09T00:00:00+00:00',
        'version': 1
    }
}

data['entries'].update(new_entries)
data['meta']['version'] = data['meta'].get('version', 0) + 1
data['meta']['updated'] = '2026-06-09T00:00:00+00:00'

with open('knowledge_store/review_rules.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'review_rules.json updated: {len(data["entries"])} entries')

# 更新版本号
for fname in ['methods.json', 'writing_templates.json', 'domain_terms.json']:
    with open(f'knowledge_store/{fname}', 'r', encoding='utf-8') as f:
        d = json.load(f)
    d['meta']['version'] = d['meta'].get('version', 0) + 1
    d['meta']['updated'] = '2026-06-09T00:00:00+00:00'
    with open(f'knowledge_store/{fname}', 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f'{fname} version updated to v{d["meta"]["version"]}')
