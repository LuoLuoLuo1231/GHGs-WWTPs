# Comprehensive Analysis Report: WWTP GHG Emissions
# CO2 / CH4 / N2O - Emission Factor vs Direct Measurement vs Model

## 1. Data Overview

| Gas | Total | Emission Factor | Direct Measurement | Model |
|-----|-------|-----------------|-------------------|-------|
| CO$_2$ | 32 | 17 | 12 | 3 |
| CH$_4$ | 84 | 51 | 25 | 8 |
| N$_2$O | 80 | 47 | 25 | 8 |

## 2. Descriptive Statistics (After Outlier Removal)

### CO2
| Method | n | Mean | Median | SD | IQR | CV% | 95%CI |
|--------|---|------|--------|-----|-----|-----|-------|
| Emission Factor | 16 | 1.699 | 1.391 | 1.597 | 2.915 | 94.0% | [0.917, 2.482] |
| Direct Measurement | 10 | 0.574 | 0.084 | 1.075 | 0.589 | 187.2% | [-0.092, 1.241] |
| Model | 3 | 2.764 | 2.002 | 3.194 | 3.125 | 115.6% | [-0.850, 6.378] |

### CH4
| Method | n | Mean | Median | SD | IQR | CV% | 95%CI |
|--------|---|------|--------|-----|-----|-----|-------|
| Emission Factor | 43 | 2.364 | 0.645 | 3.488 | 3.283 | 147.6% | [1.321, 3.406] |
| Direct Measurement | 21 | 0.289 | 0.119 | 0.388 | 0.220 | 134.6% | [0.122, 0.455] |
| Model | 8 | 0.870 | 0.628 | 0.983 | 1.262 | 113.0% | [0.189, 1.551] |

### N2O
| Method | n | Mean | Median | SD | IQR | CV% | 95%CI |
|--------|---|------|--------|-----|-----|-----|-------|
| Emission Factor | 43 | 1.834 | 0.690 | 2.279 | 2.772 | 124.3% | [1.153, 2.515] |
| Direct Measurement | 20 | 0.470 | 0.156 | 0.765 | 0.446 | 162.6% | [0.135, 0.805] |
| Model | 7 | 0.443 | 0.488 | 0.484 | 0.536 | 109.2% | [0.085, 0.802] |

## 3. Kruskal-Wallis Test
| Gas | H | p-value | eta2 | Significant? |
|-----|---|---------|------|-------------|
| CO$_2$ | 5.2828 | 0.0713 | 0.1667 | No |
| CH$_4$ | 8.0110 | 0.0182 | 0.1116 | Yes |
| N$_2$O | 11.2654 | 0.0036 | 0.1191 | Yes |

## 4. Pairwise Comparisons (Mann-Whitney U, Bonferroni)
- **CH$_4$**: Emission Factor vs Direct Measurement: p=0.0067, r=0.339
- **CH$_4$**: Emission Factor vs Model: p=0.2090, r=0.176
- **CH$_4$**: Direct Measurement vs Model: p=0.4009, r=0.156
- **N$_2$O**: Emission Factor vs Direct Measurement: p=0.0018, r=0.393
- **N$_2$O**: Emission Factor vs Model: p=0.0641, r=0.262
- **N$_2$O**: Direct Measurement vs Model: p=1.0000, r=0.000

## 5. Levene Test (Variance Homogeneity)
| Gas | W | p-value | Significant? |
|-----|---|---------|-------------|
| CO$_2$ | 3.8491 | 0.0343 | Yes |
| CH$_4$ | 4.5445 | 0.0140 | Yes |
| N$_2$O | 3.8903 | 0.0252 | Yes |

## 6. Variance Decomposition
| Gas | Between-method | Within-method |
|-----|---------------|---------------|
| CO$_2$ | 16.7% | 83.3% |
| CH$_4$ | 11.2% | 88.8% |
| N$_2$O | 11.9% | 88.1% |

## 7. Key Findings
1. **CO$_2$**: No significant methodology bias (p=0.0713)
1. **CH$_4$**: Significant methodology bias (p=0.0182, eta2=0.1116)
1. **N$_2$O**: Significant methodology bias (p=0.0036, eta2=0.1191)

**General:**
- Emission factor method systematically overestimates vs direct measurement
- CO2: 16.6x, CH4: 5.4x, N2O: 4.4x overestimation
- Model method shows no significant difference from either method
- Methodology explains 11-17% of total variance

## 8. Conclusions
1. Emission factor method significantly overestimates CH4 and N2O compared to direct measurement
2. Direct measurement is most reliable but has highest CV (captures real variability)
3. Model method is intermediate, no significant difference from either method
4. Methodology explains 11-17% of total variance; process/scale/climate factors dominate
5. All distributions are right-skewed; median(IQR) recommended over mean(SD)


---
Generated: 2026-06-10
