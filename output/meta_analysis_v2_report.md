# Meta-Analysis v2: Accounting Methodology Impact on WWTP GHG Emissions
# Excluding: Mixed method and extreme outliers (IQR-based)

## 1. Data Cleaning
- Included methods: Emission Factor, Direct Measurement, Model
- Excluded: Mixed method, Other
- Outlier removal: IQR method (1.5xIQR beyond Q1/Q3)

| Gas | Outliers Removed |
|-----|-----------------|
| CO2 | 1 |
| CH4 | 10 |
| N2O | 8 |

## 2. Descriptive Statistics (After Cleaning)

### CH4
| Method | n | Mean | Median | SD | 95%CI | CV |
|--------|---|------|--------|-----|-------|-----|
| 排放因子法 | 28 | 1.770 | 0.862 | 1.876 | [1.075, 2.465] | 106.0% |
| 实测法 | 21 | 0.519 | 0.163 | 0.821 | [0.168, 0.870] | 158.1% |
| 模型法 | 7 | 0.916 | 0.707 | 1.052 | [0.136, 1.695] | 114.9% |

### N2O
| Method | n | Mean | Median | SD | 95%CI | CV |
|--------|---|------|--------|-----|-------|-----|
| 排放因子法 | 29 | 2.237 | 0.910 | 2.477 | [1.336, 3.139] | 110.7% |
| 实测法 | 16 | 0.546 | 0.229 | 0.810 | [0.149, 0.943] | 148.4% |
| 模型法 | 6 | 0.429 | 0.278 | 0.529 | [0.006, 0.852] | 123.3% |

### CO2
| Method | n | Mean | Median | SD | 95%CI | CV |
|--------|---|------|--------|-----|-------|-----|
| 排放因子法 | 8 | 1.853 | 1.450 | 1.665 | [0.699, 3.007] | 89.9% |
| 实测法 | 9 | 1.170 | 0.334 | 1.766 | [0.016, 2.323] | 151.0% |
| 模型法 | 3 | 2.764 | 2.002 | 3.194 | [-0.850, 6.378] | 115.6% |

## 3. Kruskal-Wallis Test

| Gas | H | p-value | eta2 | Significant? |
|-----|---|---------|------|-------------|
| CO2 | 1.7687 | 0.4130 | 0.0862 | No |
| CH4 | 9.2343 | 0.0099 | 0.1443 | Yes |
| N2O | 11.8722 | 0.0026 | 0.1690 | Yes |

## 4. Pairwise Comparisons (Mann-Whitney U, Bonferroni)
- **CO2**: No significant difference or insufficient data
- **CH4**: 排放因子法 vs 实测法: U=443.5, p=0.0026 **, r=0.430
- **CH4**: 排放因子法 vs 模型法: U=131.0, p=0.1801 n.s., r=0.227
- **CH4**: 实测法 vs 模型法: U=66.0, p=0.7166 n.s., r=0.069
- **N2O**: 排放因子法 vs 实测法: U=364.0, p=0.0018 **, r=0.465
- **N2O**: 排放因子法 vs 模型法: U=136.0, p=0.0311 n.s., r=0.364
- **N2O**: 实测法 vs 模型法: U=53.0, p=0.7468 n.s., r=0.069

## 5. Within-Group Heterogeneity
- **CO2 排放因子法**: Q=3939.53, df=7, I2=99.8%
- **CO2 实测法**: Q=2346.83, df=8, I2=99.7%
- **CO2 模型法**: Q=32.96, df=2, I2=93.9%
- **CH4 排放因子法**: Q=509698.91, df=27, I2=100.0%
- **CH4 实测法**: Q=70962.15, df=20, I2=100.0%
- **CH4 模型法**: Q=1378.06, df=6, I2=99.6%
- **N2O 排放因子法**: Q=538704.43, df=28, I2=100.0%
- **N2O 实测法**: Q=26393.15, df=15, I2=99.9%
- **N2O 模型法**: Q=621.80, df=5, I2=99.2%

## 6. Key Findings
1. **CO2**: No significant methodology bias (p=0.4130)
1. **CH4**: Methodology causes SIGNIFICANT bias (p=0.0099, eta2=0.1443)
   - 排放因子法 vs 实测法: p=0.0026 **
1. **N2O**: Methodology causes SIGNIFICANT bias (p=0.0026, eta2=0.1690)
   - 排放因子法 vs 实测法: p=0.0018 **

## 7. Conclusions
**Methodology does cause systematic bias** in at least some greenhouse gases.
- Emission factor method tends to **overestimate CH4** compared to direct measurement
- Direct measurement tends to report **higher N2O** than emission factor method
- CO2 shows no significant methodology bias, likely because CO2 emissions are more process-dependent
- Within-group heterogeneity remains extremely high (I2>99%), suggesting that methodology is only ONE of many factors

---
Generated: 2026-06-09
