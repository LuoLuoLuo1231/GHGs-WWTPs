# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

def load_meta_analysis_data(fp):
    """Load meta analysis data from 3-sheet Excel file with gas columns"""
    xl = pd.ExcelFile(fp)
    gas_map = {"二氧化碳": "CO2", "甲烷": "CH4", "氧化亚氮": "N2O"}
    all_data = []
    for sn in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sn, header=1)
        gc = gas_map.get(sn, sn)
        if sn in df.columns:
            df.rename(columns={sn: gc}, inplace=True)
        if gc in df.columns:
            df[gc] = pd.to_numeric(df[gc], errors="coerce")
        df["gas_type"] = gc
        all_data.append(df)
    c = pd.concat(all_data, ignore_index=True)
    c["文献编号"] = c["文献编号"].astype(str)
    md = c.groupby("方法学").agg(
        文献数量=("文献编号", "count"),
        CO2均值=("CO2", "mean"),
        CH4均值=("CH4", "mean"),
        N2O均值=("N2O", "mean"),
        CO2标准差=("CO2", "std"),
        CH4标准差=("CH4", "std"),
        N2O标准差=("N2O", "std"),
    ).reset_index()
    s = {"总文献数": c["文献编号"].nunique(), "总记录数": len(c)}
    for g in ["CO2", "CH4", "N2O"]:
        s[f"{g}记录数"] = int(c[g].notna().sum()) if g in c.columns else 0
    return c, md, s