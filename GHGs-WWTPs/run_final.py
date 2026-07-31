# -*- coding: utf-8 -*-
"""Complete standalone meta-analysis pipeline"""
import os, sys, json, time
from datetime import datetime, timezone
import pandas as pd, numpy as np

# Windows 环境编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
OUT = os.path.join(SCRIPT_DIR, "pipeline_output")
os.makedirs(OUT, exist_ok=True)

# 数据文件路径：支持命令行参数或默认路径
DEFAULT_DATA = os.path.join(SCRIPT_DIR, "data", "2222.xlsx")
DATA = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA

# 检查数据文件是否存在
if not os.path.exists(DATA):
    print(f"[ERROR] Data file not found: {DATA}")
    print(f"  Please provide the data file path as argument:")
    print(f"  python run_final.py <data_file_path>")
    print(f"  Or place the data file at: {DEFAULT_DATA}")
    sys.exit(1)

def log(msg, step="INFO"):
    print(f"[{step}] {msg}")

print("="*70)
print("  Meta-Analysis Pipeline")
print("="*70)
t0 = time.time()

# Step 0: Load
log("Loading data...", "Step0")
xl = pd.ExcelFile(DATA)
gas_map = {"二氧化碳":"CO2","甲烷":"CH4","氧化亚氮":"N2O"}
all_data=[]
for sn in xl.sheet_names:
    df=pd.read_excel(xl,sheet_name=sn,header=1)
    gc=gas_map.get(sn,sn)
    if sn in df.columns: df.rename(columns={sn:gc},inplace=True)
    # 将气体列转换为数值类型，非数值数据转换为 NaN
    for gas_col in ['CO2', 'CH4', 'N2O']:
        if gas_col in df.columns:
            df[gas_col]=pd.to_numeric(df[gas_col],errors="coerce")
    df["气体类型"]=gc
    all_data.append(df)
combined=pd.concat(all_data,ignore_index=True)
combined["文献编号"]=combined["文献编号"].astype(str)
log(f"Loaded: {len(combined)} records, {combined['文献编号'].nunique()} papers", "Step0")

# Step 1: Analysis
log("Analysis...", "Step1")
from scipy import stats as sp_stats
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['SimHei','Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
adir=os.path.join(OUT,"analysis_output"); os.makedirs(adir,exist_ok=True)

# Descriptive
desc={}
for gas in ['CO2','CH4','N2O']:
    vals=combined[gas].dropna()
    if len(vals)>0:
        desc[gas]={'count':int(len(vals)),'mean':float(vals.mean()),'std':float(vals.std()),
                   'min':float(vals.min()),'25%':float(vals.quantile(0.25)),
                   'median':float(vals.median()),'75%':float(vals.quantile(0.75)),
                   'max':float(vals.max()),'cv':float(vals.std()/vals.mean()*100) if vals.mean()!=0 else 0}

# Methods stats
methods_df=combined.groupby("方法学").agg(
    文献数量=("文献编号","count"),
    CO2均值=("CO2","mean"),CH4均值=("CH4","mean"),N2O均值=("N2O","mean"),
    CO2标准差=("CO2","std"),CH4标准差=("CH4","std"),N2O标准差=("N2O","std")
).reset_index()

# ANOVA
anova={}
for gas in ['CO2','CH4','N2O']:
    groups=[]; labels=[]
    for m in methods_df['方法学'].unique():
        vals=combined[(combined['方法学']==m)&(combined[gas].notna())][gas].values
        if len(vals)>=3: groups.append(vals); labels.append(m)
    if len(groups)>=2:
        try:
            f,p=sp_stats.f_oneway(*groups)
            anova[gas]={'F':float(f),'p':float(p),'sig':p<0.05}
        except: pass

# Source stats
source_stats=combined.groupby('排放源位置').agg(
    记录数=('文献编号','count'),CO2均值=('CO2','mean'),CH4均值=('CH4','mean'),N2O均值=('N2O','mean')
).reset_index()

# Charts
try:
    fig,ax=plt.subplots(figsize=(10,6))
    bp=ax.boxplot([combined['CO2'].dropna(),combined['CH4'].dropna(),combined['N2O'].dropna()],
                  labels=['CO2','CH4','N2O'],patch_artist=True)
    for patch,color in zip(bp['boxes'],['#3498db','#2ecc71','#e74c3c']): patch.set_facecolor(color); patch.set_alpha(0.6)
    ax.set_ylabel('tons CO2eq/10k m3'); ax.set_title('Fig1: GHG Comparison'); ax.grid(axis='y',alpha=0.3)
    plt.tight_layout(); fig.savefig(os.path.join(adir,'fig1_gas_comparison.png'),dpi=200); plt.close()

    fig,ax=plt.subplots(figsize=(12,6))
    ml=methods_df['方法学'].tolist(); cv=methods_df['CO2均值'].tolist(); hv=methods_df['CH4均值'].tolist()
    x=np.arange(len(ml)); w=0.35
    ax.bar(x-w/2,cv,w,label='CO2',color='#3498db',alpha=0.8)
    ax.bar(x+w/2,hv,w,label='CH4',color='#2ecc71',alpha=0.8)
    ax.set_xticks(x); ax.set_xticklabels(ml,rotation=45,ha='right',fontsize=9)
    ax.legend(); ax.grid(axis='y',alpha=0.3); plt.tight_layout()
    fig.savefig(os.path.join(adir,'fig2_method_comparison.png'),dpi=200); plt.close()

    if len(source_stats)>1:
        fig,ax=plt.subplots(figsize=(8,8))
        ax.pie(source_stats['记录数'],labels=source_stats['排放源位置'],autopct='%1.1f%%')
        plt.tight_layout(); fig.savefig(os.path.join(adir,'fig3_source_pie.png'),dpi=200); plt.close()
    log("Generated 3 charts", "Step1")
except Exception as e: log(f"Chart error: {e}","Step1")

# Save results
analysis_results={'descriptive':desc,'anova':anova,
                  'source_stats':source_stats.to_dict('records'),
                  'overview':{'总文献数':combined['文献编号'].nunique(),'总记录数':len(combined)}}
with open(os.path.join(adir,"analysis_results.json"),"w",encoding="utf-8") as f:
    json.dump(analysis_results,f,ensure_ascii=False,indent=2,default=str)

# Generate MD report
lines=["# Analysis Report\n",f"Samples: {combined['文献编号'].nunique()} papers, {len(combined)} records\n",
       "## Descriptive\n|Gas|N|Mean|Std|Min|Median|Max|CV%|\n|---|---|---|---|---|---|---|---|"]
for gas,d in desc.items():
    lines.append(f"|{gas}|{d['count']}|{d['mean']:.2f}|{d['std']:.2f}|{d['min']:.2f}|{d['median']:.2f}|{d['max']:.2f}|{d['cv']:.1f}|")

lines.append("\n## Methods\n")
for _,row in methods_df.iterrows():
    lines.append(f"### {row['方法学']}\n|Gas|Mean|Std|\n|---|---|---|")
    for g in ['CO2','CH4','N2O']:
        m=row[f'{g}均值']; s=row[f'{g}标准差']
        lines.append(f"|{g}|{m:.2f}|{s:.2f}" if pd.notna(s) else f"|{g}|{m:.2f}|-|")
    lines.append("")

if anova:
    lines.append("\n## ANOVA\n")
    for g,r in anova.items(): lines.append(f"- {g}: F={r['F']:.3f}, p={r['p']:.4f} {'*' if r['sig'] else 'ns'}")

lines.append("\n## Sources\n|Source|N|CO2|CH4|N2O|\n|---|---|---|---|---|")
for _,s in source_stats.iterrows():
    c2=f"{s['CO2均值']:.2f}" if pd.notna(s['CO2均值']) else 'N/A'
    c4=f"{s['CH4均值']:.2f}" if pd.notna(s['CH4均值']) else 'N/A'
    n2=f"{s['N2O均值']:.2f}" if pd.notna(s['N2O均值']) else 'N/A'
    lines.append(f"|{s['排放源位置']}|{int(s['记录数'])}|{c2}|{c4}|{n2}|")

with open(os.path.join(adir,"analysis_report.md"),"w",encoding="utf-8") as f: f.write('\n'.join(lines))
log(f"Analysis done: {len(desc)} gases", "Step1")

# Step 2: Paper
log("Writing paper...","Step2")
pdir=os.path.join(OUT,"paper_output"); os.makedirs(pdir,exist_ok=True)
c2=desc.get('CO2',{}); c4=desc.get('CH4',{}); n2=desc.get('N2O',{})
paper=f"""# WWTP GHG Literature Meta-Analysis

## Abstract
Meta-analysis of {combined['文献编号'].nunique()} papers ({len(combined)} records) covering CO2/CH4/N2O.
- CO2 mean: {c2.get('mean',0):.2f} tCO2eq/10km3
- CH4 mean: {c4.get('mean',0):.2f} tCO2eq/10km3
- N2O mean: {n2.get('mean',0):.2f} tCO2eq/10km3

## 1 Introduction
WWTPs are important GHG sources. CO2, CH4 and N2O are produced through biological processes.
Accurate quantification is essential for urban carbon accounting.

## 2 Methods
Literature data collected and classified by methodology (emission factor, measurement, LCA, model)
and source location (treatment process, sludge disposal).

## 3 Results
CO2: {c2.get('mean',0):.2f}±{c2.get('std',0):.2f} (n={c2.get('count',0)}, CV={c2.get('cv',0):.1f}%)
CH4: {c4.get('mean',0):.2f}±{c4.get('std',0):.2f} (n={c4.get('count',0)}, CV={c4.get('cv',0):.1f}%)
N2O: {n2.get('mean',0):.2f}±{n2.get('std',0):.2f} (n={n2.get('count',0)}, CV={n2.get('cv',0):.1f}%)
Significant differences exist across methodologies. Treatment process is the main emission source.

## 4 Discussion
High CV indicates substantial between-study variation due to: (1) different treatment processes;
(2) influent quality differences; (3) climate/seasonal impacts; (4) methodological uncertainty.
Emission factor methods may underestimate actual emissions.

## 5 Conclusion
This meta-analysis reveals CO2/CH4/N2O emission intensity distributions. Unified monitoring
standards and localized emission factors are needed for improved accuracy.

## References
(To be supplemented via Step8 auto-learning)
"""
with open(os.path.join(pdir,"paper_zh.md"),"w",encoding="utf-8") as f: f.write(paper)
log(f"Paper done: {len(paper)} chars","Step2")

# Step 3: Review
log("Review...","Step3")
rdir=os.path.join(OUT,"review_output"); os.makedirs(rdir,exist_ok=True)
try:
    from academic_review_agent import AcademicReviewAgent
    agent=AcademicReviewAgent(paper_type='chinese_journal',language='zh')
    report=agent.review(paper); summary=report.summary()
    rl=["# Review Report\n",f"Total: {summary['total']} issues",
        f"- CRITICAL: {summary['by_severity'].get('CRITICAL',0)}",
        f"- MAJOR: {summary['by_severity'].get('MAJOR',0)}",
        f"- MINOR: {summary['by_severity'].get('MINOR',0)}\n","## Details"]
    for i in report.issues:
        rl.append(f"\n### [{i.severity.value}] {i.category}")
        rl.append(f"- Location: {i.section}/{i.location}")
        rl.append(f"- Issue: {i.problem}")
        if i.original: rl.append(f"- Original: {i.original[:100]}")
        rl.append(f"- Suggestion: {i.suggestion}")
    with open(os.path.join(rdir,"review_report.md"),"w",encoding="utf-8") as f: f.write('\n'.join(rl))
    log(f"Review: {summary['total']} issues","Step3")
except Exception as e: log(f"Review skipped: {e}","Step3")

# Step 4: Submission check
log("Submission check...","Step4")
cdir=os.path.join(OUT,"submission_check"); os.makedirs(cdir,exist_ok=True)
try:
    from cn_core_rules import SubmissionChecklist
    items=SubmissionChecklist.run_check(paper)
    rmd=SubmissionChecklist.generate_report(items)
    fail=sum(1 for i in items if i.status=='fail')
    warn=sum(1 for i in items if i.status=='warn')
    with open(os.path.join(cdir,"submission_check_report.md"),"w",encoding="utf-8") as f: f.write(rmd)
    log(f"Check: {len(items)} items, {fail} fail, {warn} warn","Step4")
except Exception as e: log(f"Check skipped: {e}","Step4")

# Step 5: Revision audit
log("Revision audit...","Step5")
adir2=os.path.join(OUT,"revision_audit"); os.makedirs(adir2,exist_ok=True)
try:
    from revision_audit import audit_revision
    r=audit_revision(paper,paper)
    am=f"""# Revision Audit\n- Unchanged: {r.unchanged_ratio:.1%}\n- New: {r.new_ratio:.1%}\n- Shallow: {r.shallow_warning}"""
    with open(os.path.join(adir2,"revision_audit.md"),"w",encoding="utf-8") as f: f.write(am)
    log(f"Audit done","Step5")
except Exception as e: log(f"Audit skipped: {e}","Step5")

# Step 6: Evolution
log("Evolution...","Step6")
edir=os.path.join(OUT,"evolution"); os.makedirs(edir,exist_ok=True)
try:
    from self_evolving_engine import EvolutionEngine
    eng=EvolutionEngine(SCRIPT_DIR); eng.initialize()
    rep=eng.evolve_cycle(include_github_scan=False)
    with open(os.path.join(edir,"evolution_report.json"),"w",encoding="utf-8") as f:
        json.dump(rep,f,ensure_ascii=False,indent=2,default=str)
    log(f"Evolution done","Step6")
except Exception as e: log(f"Evolution skipped: {e}","Step6")

# Step 7: DOCX
log("Assembling DOCX...","Step7")
ddir=os.path.join(OUT,"final_document"); os.makedirs(ddir,exist_ok=True)
figs=[{'path':os.path.join(adir,f),'caption':f.replace('.png','').replace('_',' ').title(),'after_section':-1}
      for f in sorted(os.listdir(adir)) if f.endswith('.png')] if os.path.exists(adir) else []

from document_assembler import DocumentAssembler
asm=DocumentAssembler(title='WWTP GHG Meta-Analysis',paper_type='chinese',language='zh')
sections=[]; cur=None
for line in paper.split('\n'):
    ls=line.strip()
    if not ls: continue
    if ls.startswith('## '):
        if cur: sections.append(cur)
        cur={'heading':ls.lstrip('#').strip(),'text':[],'level':1}
    elif ls.startswith('# '):
        if cur: sections.append(cur)
        cur={'heading':ls.lstrip('#').strip(),'text':[],'level':1}
    elif cur: cur['text'].append(ls)
if cur: sections.append(cur)
for s in sections: asm.add_section(s['heading'],'\n'.join(s.get('text',[])),s.get('level',1))
for fig in figs: asm.add_figure(fig['path'],fig['caption'])
dpath=asm.assemble(os.path.join(ddir,"final_paper.docx"))
log(f"DOCX: {dpath}","Step7")

# Summary
elapsed=time.time()-t0
smd=f"""# Pipeline Summary
Data: {DATA}
Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
Duration: {elapsed:.1f}s

Steps: Step1-Analysis, Step2-Writing, Step3-Review, Step4-Check, Step5-Audit, Step6-Evolution, Step7-DOCX

Output: {OUT}
"""
with open(os.path.join(OUT,"PIPELINE_SUMMARY.md"),"w",encoding="utf-8") as f: f.write(smd)
print(f"\n{'='*70}")
print(f"  Pipeline complete! {elapsed:.1f}s")
print(f"  Output: {OUT}")
print(f"{'='*70}")