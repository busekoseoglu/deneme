# %% FINAL EXCEL EXPORT - SADE AMA KAPSAMLI

import pandas as pd
import numpy as np
import os
from datetime import datetime


# =================================================
# 0) HELPERLAR
# =================================================

def ds_key(ds):
    return pd.to_datetime(ds).strftime("%Y-%m-%d")


def normalize_agent(a):
    return str(a).strip()


def safe_solver_value(var, default=0):
    try:
        return solver.Value(var)
    except Exception:
        return default


def get_shift_time(ds, v):
    if "saat" in globals() and (ds, v) in saat:
        return saat[(ds, v)][0], saat[(ds, v)][1]
    return None, None


def safe_day_name(ds):
    gun_map = {
        0: "Pazartesi",
        1: "Salı",
        2: "Çarşamba",
        3: "Perşembe",
        4: "Cuma",
        5: "Cumartesi",
        6: "Pazar",
    }
    return gun_map[pd.to_datetime(ds).weekday()]


def agent_izinli_mi_export(a, ds):
    a = normalize_agent(a)
    izinler = izin_map.get(a, set())

    if izinler is None:
        return False

    if isinstance(izinler, bool):
        return False

    if isinstance(izinler, float) and pd.isna(izinler):
        return False

    if isinstance(izinler, set):
        izin_set = izinler
    elif isinstance(izinler, list):
        izin_set = set(izinler)
    elif isinstance(izinler, tuple):
        izin_set = set(izinler)
    else:
        izin_set = {izinler}

    ds_str = pd.to_datetime(ds).strftime("%Y-%m-%d")
    ds_date = pd.to_datetime(ds).date()
    ds_ts = pd.to_datetime(ds)

    return (
        ds in izin_set
        or ds_str in izin_set
        or ds_date in izin_set
        or ds_ts in izin_set
    )


def df_or_empty(df):
    if isinstance(df, pd.DataFrame):
        return df.copy()
    return pd.DataFrame()


# =================================================
# 1) AGENT INFO
# =================================================

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "working_main_group",
    "line_based_main_group",
    "hamile_flg",
    "sut_izni_flg",
    "mesaiye_kalamaz_flg",
    "sabah_calisir_flg",
]

available_agent_info_cols = [
    c for c in agent_info_cols
    if c in df_tam.columns
]

agent_info_df = df_tam[available_agent_info_cols].copy()
agent_info_df["agent_user_code"] = agent_info_df["agent_user_code"].astype(str).str.strip()
agent_info_df = agent_info_df.drop_duplicates("agent_user_code")

agent_info_map = (
    agent_info_df
    .set_index("agent_user_code")
    .to_dict("index")
)


# =================================================
# 2) ÖZEL GÜN SETLERİ
# =================================================

arife_days_set = set(arife_plan_gunleri) if "arife_plan_gunleri" in globals() else set()
resmi_tatil_days_set = set(resmi_tatil_plan_gunleri) if "resmi_tatil_plan_gunleri" in globals() else set()

if "ozel_tatil_plan_gunleri" in globals():
    ozel_tatil_days_set = set(ozel_tatil_plan_gunleri)
else:
    ozel_tatil_days_set = arife_days_set | resmi_tatil_days_set

arife_ozel_vardiya_kodlari_export = set(
    arife_ozel_vardiya_kodlari
) if "arife_ozel_vardiya_kodlari" in globals() else set()


# Arife mesai atamaları
arife_mesai_assignments = set()

if "arife_mesai" in globals():
    for (a, ds, v), var in arife_mesai.items():
        if safe_solver_value(var) == 1:
            arife_mesai_assignments.add((normalize_agent(a), ds, v))


# Resmi tatil mesai atamaları
resmi_tatil_mesai_assignments = set()

if "resmi_tatil_mesai" in globals():
    for (a, ds, v), var in resmi_tatil_mesai.items():
        if safe_solver_value(var) == 1:
            resmi_tatil_mesai_assignments.add((normalize_agent(a), ds, v))


# Resmi tatil kısıtlı ihlal atamaları
resmi_tatil_ihlal_assignments = set()

if "resmi_tatil_kisitli_ihlal" in globals():
    for (a, ds, v), var in resmi_tatil_kisitli_ihlal.items():
        if safe_solver_value(var) == 1:
            resmi_tatil_ihlal_assignments.add((normalize_agent(a), ds, v))


# =================================================
# 3) AGENT GÜNLÜK PLAN
# =================================================

agent_day_rows = []

for a in AGENTS:
    a = normalize_agent(a)
    info = agent_info_map.get(a, {})

    for ds in PLAN_GUNLER:

        assigned_shift = None
        shift_start = None
        shift_end = None
        assigned = 0

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                assigned_shift = v
                shift_start, shift_end = get_shift_time(ds, v)
                assigned = 1
                break

        wk = day_week.get(ds) if "day_week" in globals() else None
        weekday = pd.to_datetime(ds).weekday()

        is_leave = agent_izinli_mi_export(a, ds)
        is_arife = ds in arife_days_set
        is_resmi_tatil = ds in resmi_tatil_days_set
        is_ozel_gun = ds in ozel_tatil_days_set
        is_weekend = weekday in [5, 6]

        normal_overtime_week = None
        if wk is not None and (a, wk) in overtime_week:
            normal_overtime_week = safe_solver_value(overtime_week[(a, wk)])

        status_label = "OFF"
        special_day_label = ""

        if is_leave:
            status_label = "İZİN"

        if assigned == 1:
            status_label = "WORK"

            if is_arife:
                special_day_label = "ARIFE"

            if is_resmi_tatil:
                special_day_label = "RESMI_TATIL"

            if is_arife and assigned_shift in arife_ozel_vardiya_kodlari_export:
                status_label = "ARIFE_09_13"

            if (a, ds, assigned_shift) in arife_mesai_assignments:
                status_label = "ARIFE_MESAI"

            if (a, ds, assigned_shift) in resmi_tatil_mesai_assignments:
                status_label = "RESMI_TATIL_MESAI"

            if (a, ds, assigned_shift) in resmi_tatil_ihlal_assignments:
                status_label = "RESMI_TATIL_KISITLI_IHLAL"

        agent_day_rows.append({
            "agent_user_code": a,
            "agent_name": info.get("agent_name"),
            "takim": info.get("takim"),
            "teamleader_name": info.get("teamleader_name"),
            "date": ds_key(ds),
            "week": wk,
            "gun": safe_day_name(ds),
            "weekday": weekday,
            "is_weekend": is_weekend,
            "assigned": assigned,
            "status": status_label,
            "assigned_shift": assigned_shift,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "is_leave": is_leave,
            "is_arife": is_arife,
            "is_resmi_tatil": is_resmi_tatil,
            "is_ozel_gun": is_ozel_gun,
            "normal_overtime_week": normal_overtime_week,
        })

agent_day_plan_df = pd.DataFrame(agent_day_rows)


# =================================================
# 4) NORMAL MESAİ GÜNLERİNİ İŞARETLE
# =================================================

normal_mesai_day_set = set()

for a in AGENTS:
    a = normalize_agent(a)

    for wk in WEEKS:

        if (a, wk) not in overtime_week:
            continue

        overtime_val = safe_solver_value(overtime_week[(a, wk)])

        if overtime_val <= 0:
            continue

        worked_normal_days = agent_day_plan_df[
            (agent_day_plan_df["agent_user_code"] == a) &
            (agent_day_plan_df["week"] == wk) &
            (agent_day_plan_df["assigned"] == 1) &
            (agent_day_plan_df["is_resmi_tatil"] == False) &
            (agent_day_plan_df["is_arife"] == False) &
            (agent_day_plan_df["status"] == "WORK")
        ].copy()

        if worked_normal_days.empty:
            continue

        # Normal mesailer genelde hafta sonu olur. Öncelik hafta sonu.
        weekend_worked = worked_normal_days[
            worked_normal_days["weekday"].isin([5, 6])
        ].copy()

        if not weekend_worked.empty:
            selected_rows = weekend_worked.sort_values("date").tail(int(overtime_val))
        else:
            selected_rows = worked_normal_days.sort_values("date").tail(int(overtime_val))

        for _, r in selected_rows.iterrows():
            normal_mesai_day_set.add(
                (
                    r["agent_user_code"],
                    r["date"],
                    r["assigned_shift"],
                )
            )

agent_day_plan_df["is_normal_mesai"] = agent_day_plan_df.apply(
    lambda r: (
        r["agent_user_code"],
        r["date"],
        r["assigned_shift"],
    ) in normal_mesai_day_set,
    axis=1,
)

agent_day_plan_df.loc[
    (agent_day_plan_df["is_normal_mesai"] == True) &
    (agent_day_plan_df["status"] == "WORK"),
    "status"
] = "NORMAL_MESAI"


# =================================================
# 5) DF_OFF SHEET
# =================================================

df_off_export = agent_day_plan_df[
    agent_day_plan_df["status"] == "OFF"
][
    [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "date",
        "week",
        "gun",
        "is_weekend",
    ]
].copy()


# =================================================
# 6) VARDİYA TALEP SHEET
# =================================================

talep_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        if (ds, v) not in talep:
            continue

        shift_start, shift_end = get_shift_time(ds, v)

        talep_rows.append({
            "date": ds_key(ds),
            "week": day_week.get(ds) if "day_week" in globals() else None,
            "gun": safe_day_name(ds),
            "weekday": pd.to_datetime(ds).weekday(),
            "is_weekend": pd.to_datetime(ds).weekday() in [5, 6],
            "shift": v,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "required": int(talep[(ds, v)]),
            "is_arife": ds in arife_days_set,
            "is_resmi_tatil": ds in resmi_tatil_days_set,
            "is_ozel_gun": ds in ozel_tatil_days_set,
        })

vardiya_talep_df = pd.DataFrame(talep_rows)


# =================================================
# 7) AYLIK TAKVİM
# =================================================

calendar_value_df = agent_day_plan_df.copy()

calendar_value_df["calendar_value"] = np.where(
    calendar_value_df["assigned"] == 1,
    calendar_value_df["status"].fillna("") +
    " | " +
    calendar_value_df["assigned_shift"].fillna("") +
    " (" +
    calendar_value_df["shift_start"].fillna("") +
    "-" +
    calendar_value_df["shift_end"].fillna("") +
    ")",
    calendar_value_df["status"]
)

calendar_shift_df = calendar_value_df.pivot_table(
    index=["agent_user_code", "agent_name", "takim", "teamleader_name"],
    columns="date",
    values="calendar_value",
    aggfunc="first"
).reset_index()

calendar_shift_df.columns = [str(c) for c in calendar_shift_df.columns]


# =================================================
# 8) COVERAGE SADE TABLO
# =================================================

coverage_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        if (ds, v) not in talep:
            continue

        required = int(talep[(ds, v)])

        assigned = sum(
            safe_solver_value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        shift_start, shift_end = get_shift_time(ds, v)
        weekday = pd.to_datetime(ds).weekday()

        coverage_rows.append({
            "date": ds_key(ds),
            "week": day_week.get(ds) if "day_week" in globals() else None,
            "gun": safe_day_name(ds),
            "weekday": weekday,
            "is_weekend": weekday in [5, 6],
            "shift": v,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "required": required,
            "assigned": assigned,
            "gap": assigned - required,
            "is_arife": ds in arife_days_set,
            "is_resmi_tatil": ds in resmi_tatil_days_set,
            "is_ozel_gun": ds in ozel_tatil_days_set,
        })

coverage_simple_df = pd.DataFrame(coverage_rows)


# =================================================
# 9) VARDİYA ÖZET
# =================================================

vardiya_ozet_df = (
    coverage_simple_df
    .groupby(["shift", "shift_start", "shift_end"], as_index=False)
    .agg(
        toplam_required=("required", "sum"),
        toplam_assigned=("assigned", "sum"),
        toplam_gap=("gap", "sum"),
        min_gap=("gap", "min"),
        max_gap=("gap", "max"),
        ortalama_gap=("gap", "mean"),
        gun_sayisi=("date", "count"),
    )
    .sort_values(["shift_start", "shift_end", "shift"])
)


# =================================================
# 10) SADE AGENT AYLIK ÖZET
# =================================================

agent_monthly_base = agent_day_plan_df.copy()

def monthly_status_group(status):
    status = str(status).strip()

    if status == "WORK":
        return "normal_calisma_gun"

    if status == "NORMAL_MESAI":
        return "normal_mesai_gun"

    if status in ["ARIFE_09_13", "ARIFE_MESAI"]:
        return "arife_gun"

    if status in ["RESMI_TATIL_MESAI", "RESMI_TATIL_KISITLI_IHLAL"]:
        return "resmi_tatil_gun"

    if status == "OFF":
        return "off_gun"

    if status == "İZİN":
        return "izin_gun"

    return "diger_gun"


agent_monthly_base["aylik_kategori"] = agent_monthly_base["status"].apply(monthly_status_group)

agent_monthly_df = (
    agent_monthly_base
    .pivot_table(
        index=["agent_user_code", "agent_name", "takim", "teamleader_name"],
        columns="aylik_kategori",
        values="date",
        aggfunc="count",
        fill_value=0,
    )
    .reset_index()
)

agent_monthly_df.columns = [str(c) for c in agent_monthly_df.columns]

required_monthly_cols = [
    "normal_calisma_gun",
    "normal_mesai_gun",
    "arife_gun",
    "resmi_tatil_gun",
    "off_gun",
    "izin_gun",
    "diger_gun",
]

for col in required_monthly_cols:
    if col not in agent_monthly_df.columns:
        agent_monthly_df[col] = 0

agent_monthly_df["toplam_gun"] = (
    agent_monthly_df["normal_calisma_gun"]
    + agent_monthly_df["normal_mesai_gun"]
    + agent_monthly_df["arife_gun"]
    + agent_monthly_df["resmi_tatil_gun"]
    + agent_monthly_df["off_gun"]
    + agent_monthly_df["izin_gun"]
    + agent_monthly_df["diger_gun"]
)

agent_monthly_df["toplam_30_mu"] = agent_monthly_df["toplam_gun"] == len(PLAN_GUNLER)

agent_monthly_df = agent_monthly_df[
    [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "normal_calisma_gun",
        "normal_mesai_gun",
        "arife_gun",
        "resmi_tatil_gun",
        "off_gun",
        "izin_gun",
        "diger_gun",
        "toplam_gun",
        "toplam_30_mu",
    ]
].copy()


# =================================================
# 11) ÖZET SAYFASI
# =================================================

# Özel gün hariç hafta içi takım bölünme kontrolü
weekday_team_split_count = 0

if "weekday_team_viol_df" in globals() and isinstance(weekday_team_viol_df, pd.DataFrame):
    weekday_team_split_count = len(weekday_team_viol_df)

# Resmi tatil kısıtlı ihlal
resmi_tatil_kisitli_ihlal_toplam = len(resmi_tatil_ihlal_assignments)

# Haftalık hedef
weekly_under_toplam = 0
weekly_over_toplam = 0

if "weekly_under" in globals():
    weekly_under_toplam = sum(safe_solver_value(v) for v in weekly_under.values())

if "weekly_over" in globals():
    weekly_over_toplam = sum(safe_solver_value(v) for v in weekly_over.values())

summary_rows = [
    {"kontrol": "Agent sayısı", "deger": len(AGENTS), "beklenen": ""},
    {"kontrol": "Plan gün sayısı", "deger": len(PLAN_GUNLER), "beklenen": ""},
    {"kontrol": "Toplam required", "deger": coverage_simple_df["required"].sum(), "beklenen": ""},
    {"kontrol": "Toplam assigned", "deger": coverage_simple_df["assigned"].sum(), "beklenen": ""},
    {"kontrol": "Toplam gap", "deger": coverage_simple_df["gap"].sum(), "beklenen": "0'a yakın"},
    {"kontrol": "En düşük gap", "deger": coverage_simple_df["gap"].min(), "beklenen": "çok negatif olmamalı"},
    {"kontrol": "En yüksek gap", "deger": coverage_simple_df["gap"].max(), "beklenen": "çok yüksek olmamalı"},
    {
        "kontrol": "Required > 0 ama assigned = 0 vardiya sayısı",
        "deger": coverage_simple_df[
            (coverage_simple_df["required"] > 0) &
            (coverage_simple_df["assigned"] == 0)
        ].shape[0],
        "beklenen": "0",
    },
    {
        "kontrol": "Coverage gap negatif vardiya sayısı",
        "deger": (coverage_simple_df["gap"] < 0).sum(),
        "beklenen": "mümkün olduğunca düşük",
    },
    {
        "kontrol": "Resmi tatil kısıtlı ihlal toplam",
        "deger": resmi_tatil_kisitli_ihlal_toplam,
        "beklenen": "0",
    },
    {
        "kontrol": "Weekly under toplam",
        "deger": weekly_under_toplam,
        "beklenen": "mümkün olduğunca düşük",
    },
    {
        "kontrol": "Weekly over toplam",
        "deger": weekly_over_toplam,
        "beklenen": "mümkün olduğunca düşük",
    },
    {
        "kontrol": "Özel gün hariç hafta içi bölünen takım-gün",
        "deger": weekday_team_split_count,
        "beklenen": "0",
    },
    {
        "kontrol": "Aylık özette toplam günü 30 olmayan agent",
        "deger": (agent_monthly_df["toplam_30_mu"] == False).sum(),
        "beklenen": "0",
    },
    {
        "kontrol": "Aylık özette diger_gun toplam",
        "deger": agent_monthly_df["diger_gun"].sum(),
        "beklenen": "0",
    },
]

summary_df = pd.DataFrame(summary_rows)


# =================================================
# 12) EXCEL YAZIMI
# =================================================

output_file = f"vardiya_plani_sade_kapsamli_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

sheet_df_map = {
    "00_Ozet": summary_df,
    "01_df_tam": df_tam.copy(),
    "02_df_off": df_off_export,
    "03_Vardiya_Talep": vardiya_talep_df,
    "04_Aylik_Takvim": calendar_shift_df,
    "05_Coverage": coverage_simple_df,
    "06_Vardiya_Ozet": vardiya_ozet_df,
    "07_Agent_Aylik_Ozet": agent_monthly_df,
}

with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:

    for sheet_name, df_sheet in sheet_df_map.items():
        df_sheet.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    workbook = writer.book

    # Formatlar
    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#1F4E78",
        "font_color": "white",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })

    warning_format = workbook.add_format({
        "bg_color": "#FFC7CE",
        "font_color": "#9C0006",
    })

    good_format = workbook.add_format({
        "bg_color": "#C6EFCE",
        "font_color": "#006100",
    })

    special_format = workbook.add_format({
        "bg_color": "#FFEB9C",
        "font_color": "#9C6500",
    })

    izin_format = workbook.add_format({
        "bg_color": "#D9EAD3",
        "font_color": "#274E13",
    })

    off_format = workbook.add_format({
        "bg_color": "#E7E6E6",
        "font_color": "#666666",
    })

    normal_mesai_format = workbook.add_format({
        "bg_color": "#FCE4D6",
        "font_color": "#9C5700",
        "bold": True,
    })

    arife_0913_format = workbook.add_format({
        "bg_color": "#E2F0D9",
        "font_color": "#375623",
        "bold": True,
    })

    arife_mesai_format = workbook.add_format({
        "bg_color": "#FFF2CC",
        "font_color": "#7F6000",
        "bold": True,
    })

    resmi_tatil_mesai_format = workbook.add_format({
        "bg_color": "#BDD7EE",
        "font_color": "#1F4E78",
        "bold": True,
    })

    ihlal_format = workbook.add_format({
        "bg_color": "#FF0000",
        "font_color": "#FFFFFF",
        "bold": True,
    })

    # Header + filtre + genişlik
    for sheet_name, df_sheet in sheet_df_map.items():

        safe_sheet_name = sheet_name[:31]
        worksheet = writer.sheets[safe_sheet_name]

        worksheet.freeze_panes(1, 0)

        if len(df_sheet.columns) > 0:
            worksheet.autofilter(0, 0, max(len(df_sheet), 1), len(df_sheet.columns) - 1)

        for col_num, col_name in enumerate(df_sheet.columns):
            worksheet.write(0, col_num, str(col_name), header_format)

            col_name_str = str(col_name)

            if col_name_str == "agent_user_code":
                worksheet.set_column(col_num, col_num, 16)

            elif col_name_str == "agent_name":
                worksheet.set_column(col_num, col_num, 24)

            elif col_name_str == "takim":
                worksheet.set_column(col_num, col_num, 34)

            elif col_name_str == "teamleader_name":
                worksheet.set_column(col_num, col_num, 24)

            elif col_name_str in ["date", "saturday", "sunday"]:
                worksheet.set_column(col_num, col_num, 14)

            elif safe_sheet_name == "04_Aylik_Takvim" and col_num >= 4:
                worksheet.set_column(col_num, col_num, 24)

            elif col_name_str in ["kontrol", "beklenen"]:
                worksheet.set_column(col_num, col_num, 42)

            else:
                worksheet.set_column(col_num, col_num, 15)

    # =================================================
    # Conditional Formatting
    # =================================================

    # 00_Ozet
    ws_ozet = writer.sheets["00_Ozet"]

    if len(summary_df) > 0:
        deger_col = summary_df.columns.get_loc("deger")
        kontrol_col = summary_df.columns.get_loc("kontrol")

        ws_ozet.conditional_format(1, deger_col, len(summary_df), deger_col, {
            "type": "cell",
            "criteria": ">",
            "value": 0,
            "format": special_format,
        })

    # Coverage gap
    ws_cov = writer.sheets["05_Coverage"]

    if len(coverage_simple_df) > 0 and "gap" in coverage_simple_df.columns:
        gap_col = coverage_simple_df.columns.get_loc("gap")

        ws_cov.conditional_format(1, gap_col, len(coverage_simple_df), gap_col, {
            "type": "cell",
            "criteria": "<",
            "value": 0,
            "format": warning_format,
        })

        ws_cov.conditional_format(1, gap_col, len(coverage_simple_df), gap_col, {
            "type": "cell",
            "criteria": ">",
            "value": 0,
            "format": special_format,
        })

    # Aylık takvim renkleri
    ws_calendar = writer.sheets["04_Aylik_Takvim"]

    if len(calendar_shift_df.columns) > 4:
        max_rows = len(calendar_shift_df) + 1
        max_cols = len(calendar_shift_df.columns) - 1

        ws_calendar.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "OFF",
            "format": off_format,
        })

        ws_calendar.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "İZİN",
            "format": izin_format,
        })

        ws_calendar.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "RESMI_TATIL_KISITLI_IHLAL",
            "format": ihlal_format,
        })

        ws_calendar.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "RESMI_TATIL_MESAI",
            "format": resmi_tatil_mesai_format,
        })

        ws_calendar.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "ARIFE_MESAI",
            "format": arife_mesai_format,
        })

        ws_calendar.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "ARIFE_09_13",
            "format": arife_0913_format,
        })

        ws_calendar.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "NORMAL_MESAI",
            "format": normal_mesai_format,
        })

    # Agent aylık özet toplam kontrolü
    ws_month = writer.sheets["07_Agent_Aylik_Ozet"]

    if "toplam_30_mu" in agent_monthly_df.columns:
        toplam_ok_col = agent_monthly_df.columns.get_loc("toplam_30_mu")

        ws_month.conditional_format(1, toplam_ok_col, len(agent_monthly_df), toplam_ok_col, {
            "type": "text",
            "criteria": "containing",
            "value": "False",
            "format": warning_format,
        })

    if "diger_gun" in agent_monthly_df.columns:
        diger_col = agent_monthly_df.columns.get_loc("diger_gun")

        ws_month.conditional_format(1, diger_col, len(agent_monthly_df), diger_col, {
            "type": "cell",
            "criteria": ">",
            "value": 0,
            "format": warning_format,
        })

print("Excel oluşturuldu:", os.path.abspath(output_file))
print("Sheet sayısı:", len(sheet_df_map))
print("Dosya:", output_file)
