# %% [EXPORT] - FINAL EXCEL ÇIKTISI

import pandas as pd
import numpy as np

output_path = "vardiya_planlama_final_sonuc.xlsx"

# -------------------------------------------------
# 0) Agent info + PM info
# -------------------------------------------------

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "working_main_group",
    "line_based_main_group",
    "sabah_calisir_flg",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg",
    "pm_mesai_sayisi",
    "pm_gece_sayisi",
    "pm_hafta_sonu_calisma_sayisi"
]

existing_agent_info_cols = [
    c for c in agent_info_cols
    if c in df_tam.columns
]

agent_info = (
    df_tam[existing_agent_info_cols]
    .copy()
    .drop_duplicates("agent_user_code")
)

agent_info["agent_user_code"] = (
    agent_info["agent_user_code"]
    .astype(str)
    .str.strip()
)

# PM kolonları yoksa boş gelmesin
for col in [
    "pm_mesai_sayisi",
    "pm_gece_sayisi",
    "pm_hafta_sonu_calisma_sayisi"
]:
    if col not in agent_info.columns:
        agent_info[col] = 0

    agent_info[col] = (
        pd.to_numeric(agent_info[col], errors="coerce")
        .fillna(0)
        .astype(int)
    )


# -------------------------------------------------
# 1) Agent - Gün detay
# -------------------------------------------------

day_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in PLAN_GUNLER:

        assigned_shift = None
        shift_start = None
        shift_end = None

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                assigned_shift = v

                if (ds, v) in saat:
                    shift_start, shift_end = saat[(ds, v)]

                break

        is_work = solver.Value(work[(a, ds)]) if (a, ds) in work else 0
        is_leave = ds in izin_map.get(a, set())
        is_weekend = pd.to_datetime(ds).weekday() >= 5
        wk = day_week[ds]

        # Status önceliği:
        # 1. İzinliyse ve çalışmıyorsa: İZİN
        # 2. Çalışıyorsa: WORK
        # 3. Değilse: OFF
        if is_work == 1:
            status_day = "WORK"
        elif is_leave:
            status_day = "İZİN"
        else:
            status_day = "OFF"

        day_rows.append({
            "agent_user_code": a,
            "date": ds,
            "week": wk,
            "day_name": DAY_TR[pd.to_datetime(ds).weekday()] if "DAY_TR" in globals() else pd.to_datetime(ds).day_name(),
            "is_weekend": is_weekend,
            "is_leave": is_leave,
            "work": is_work,
            "assigned_shift": assigned_shift,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "status": status_day
        })

agent_day_df = pd.DataFrame(day_rows)

agent_day_df = agent_day_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)


# -------------------------------------------------
# 2) Mesai günü etiketi
# -------------------------------------------------
# overtime_week haftalık mesaiyi gösteriyor.
# Excel'de görünür olması için o hafta içindeki bir çalışma gününü WORK_MESAI yapıyoruz.
#
# Öncelik:
# 1. Cumartesi çalıştıysa Cumartesi
# 2. Pazar çalıştıysa Pazar
# 3. Hafta sonu yoksa haftadaki son çalışılan gün

agent_day_df["is_overtime_week"] = 0
agent_day_df["is_mesai_day"] = 0

for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:

        if (a, wk) not in overtime_week:
            continue

        overtime_val = solver.Value(overtime_week[(a, wk)])

        if overtime_val != 1:
            continue

        mask_week = (
            (agent_day_df["agent_user_code"] == a) &
            (agent_day_df["week"] == wk)
        )

        agent_day_df.loc[mask_week, "is_overtime_week"] = 1

        worked_days = agent_day_df[
            mask_week &
            (agent_day_df["work"] == 1)
        ].copy()

        if worked_days.empty:
            continue

        sat_days = worked_days[
            pd.to_datetime(worked_days["date"]).dt.weekday == 5
        ]

        sun_days = worked_days[
            pd.to_datetime(worked_days["date"]).dt.weekday == 6
        ]

        if len(sat_days) > 0:
            mesai_idx = sat_days.index[0]
        elif len(sun_days) > 0:
            mesai_idx = sun_days.index[0]
        else:
            mesai_idx = worked_days.sort_values("date").index[-1]

        agent_day_df.loc[mesai_idx, "is_mesai_day"] = 1

agent_day_df.loc[
    (agent_day_df["work"] == 1) &
    (agent_day_df["is_mesai_day"] == 1),
    "status"
] = "WORK_MESAI"


# -------------------------------------------------
# 3) Takvim görünümü
# -------------------------------------------------

calendar_df = agent_day_df.copy()

calendar_df["calendar_value"] = np.where(
    calendar_df["status"] == "WORK_MESAI",
    "MESAİ | " + calendar_df["assigned_shift"].fillna(""),
    np.where(
        calendar_df["status"] == "WORK",
        calendar_df["assigned_shift"].fillna("WORK"),
        np.where(
            calendar_df["status"] == "İZİN",
            "İZİN",
            "OFF"
        )
    )
)

agent_calendar_df = calendar_df.pivot_table(
    index=[
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "pm_mesai_sayisi",
        "pm_gece_sayisi",
        "pm_hafta_sonu_calisma_sayisi"
    ],
    columns="date",
    values="calendar_value",
    aggfunc="first"
).reset_index()

agent_calendar_df.columns = [str(c) for c in agent_calendar_df.columns]


# -------------------------------------------------
# 4) Coverage
# -------------------------------------------------

coverage_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        required = int(talep[(ds, v)])

        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        start_time, end_time = saat[(ds, v)] if (ds, v) in saat else (None, None)

        coverage_rows.append({
            "date": ds,
            "week": day_week[ds],
            "day_name": DAY_TR[pd.to_datetime(ds).weekday()] if "DAY_TR" in globals() else pd.to_datetime(ds).day_name(),
            "is_weekend": pd.to_datetime(ds).weekday() >= 5,
            "shift": v,
            "shift_start": start_time,
            "shift_end": end_time,
            "required": required,
            "assigned": assigned,
            "gap_to_required": assigned - required,
            "coverage_lower": coverage_lower.get((ds, v), None),
            "coverage_upper": coverage_upper.get((ds, v), None),
            "under_buffer": solver.Value(under_buffer[(ds, v)]) if (ds, v) in under_buffer else None,
            "over_buffer": solver.Value(over_buffer[(ds, v)]) if (ds, v) in over_buffer else None,
            "missing_to_required": solver.Value(missing_to_required[(ds, v)]) if (ds, v) in missing_to_required else None,
            "excess_to_required": solver.Value(excess_to_required[(ds, v)]) if (ds, v) in excess_to_required else None,
            "gece_aksam_vardiyasi_mi": gece_aksam_vardiyasi_mi.get((ds, v), None) if "gece_aksam_vardiyasi_mi" in globals() else None,
            "mola_destek_vardiyasi_mi": mola_destek_vardiyasi_mi.get((ds, v), None) if "mola_destek_vardiyasi_mi" in globals() else None,
            "mola_destek_skoru": mola_destek_skoru.get((ds, v), None) if "mola_destek_skoru" in globals() else None,
            "fazla_atama_ust_limit": fazla_atama_ust_limit.get((ds, v), None) if "fazla_atama_ust_limit" in globals() else None,
        })

coverage_df = pd.DataFrame(coverage_rows)

gap_problem_df = coverage_df[
    coverage_df["gap_to_required"] < 0
].sort_values(
    ["gap_to_required", "date", "shift"]
)


# -------------------------------------------------
# 5) Agent aylık özet
# -------------------------------------------------

month_summary = (
    agent_day_df
    .groupby("agent_user_code", as_index=False)
    .agg(
        agent_name=("agent_name", "first"),
        takim=("takim", "first"),
        teamleader_name=("teamleader_name", "first"),

        pm_mesai_sayisi=("pm_mesai_sayisi", "first"),
        pm_gece_sayisi=("pm_gece_sayisi", "first"),
        pm_hafta_sonu_calisma_sayisi=("pm_hafta_sonu_calisma_sayisi", "first"),

        total_work_days=("work", "sum"),
        total_leave_days=("is_leave", "sum"),
        total_mesai_days=("is_mesai_day", "sum"),
        total_overtime_weeks=("is_overtime_week", lambda s: int(s.sum()))
    )
)

# Gerçek OFF: çalışmadığı ve izinli olmadığı günler
real_off_summary = (
    agent_day_df
    .assign(real_off=lambda d: ((d["work"] == 0) & (d["is_leave"] == False)).astype(int))
    .groupby("agent_user_code", as_index=False)
    .agg(total_real_off_days=("real_off", "sum"))
)

month_summary = month_summary.merge(
    real_off_summary,
    on="agent_user_code",
    how="left"
)

# Hafta sonu özet
weekend_summary = (
    agent_day_df[agent_day_df["is_weekend"] == True]
    .groupby("agent_user_code", as_index=False)
    .agg(
        bu_ay_hafta_sonu_calisma_sayisi=("work", "sum"),
        bu_ay_hafta_sonu_izin_sayisi=("is_leave", "sum")
    )
)

month_summary = month_summary.merge(
    weekend_summary,
    on="agent_user_code",
    how="left"
)

month_summary[
    [
        "total_real_off_days",
        "bu_ay_hafta_sonu_calisma_sayisi",
        "bu_ay_hafta_sonu_izin_sayisi"
    ]
] = month_summary[
    [
        "total_real_off_days",
        "bu_ay_hafta_sonu_calisma_sayisi",
        "bu_ay_hafta_sonu_izin_sayisi"
    ]
].fillna(0).astype(int)


# Bu ay gece sayısı
gece_rows = []

for a in AGENTS:
    a = str(a).strip()

    bu_ay_gece = 0

    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                if "gece_aksam_vardiyasi_mi" in globals() and gece_aksam_vardiyasi_mi.get((ds, v), False):
                    bu_ay_gece += 1

    gece_rows.append({
        "agent_user_code": a,
        "bu_ay_gece_sayisi": bu_ay_gece
    })

bu_ay_gece_df = pd.DataFrame(gece_rows)

month_summary = month_summary.merge(
    bu_ay_gece_df,
    on="agent_user_code",
    how="left"
)

month_summary["bu_ay_gece_sayisi"] = month_summary["bu_ay_gece_sayisi"].fillna(0).astype(int)

# İki ay toplamları
month_summary["toplam_iki_ay_mesai"] = (
    month_summary["pm_mesai_sayisi"] + month_summary["total_mesai_days"]
)

month_summary["toplam_iki_ay_gece"] = (
    month_summary["pm_gece_sayisi"] + month_summary["bu_ay_gece_sayisi"]
)

month_summary["toplam_iki_ay_hafta_sonu"] = (
    month_summary["pm_hafta_sonu_calisma_sayisi"] + month_summary["bu_ay_hafta_sonu_calisma_sayisi"]
)

# İkinci mesai değişkeni varsa
if "ikinci_mesai_aylik" in globals():
    ikinci_mesai_rows = []

    for a in AGENTS:
        a = str(a).strip()
        ikinci_mesai_rows.append({
            "agent_user_code": a,
            "ikinci_mesai_aylik": solver.Value(ikinci_mesai_aylik[a]) if a in ikinci_mesai_aylik else None
        })

    ikinci_mesai_df = pd.DataFrame(ikinci_mesai_rows)

    month_summary = month_summary.merge(
        ikinci_mesai_df,
        on="agent_user_code",
        how="left"
    )


# -------------------------------------------------
# 6) Agent hafta özeti
# -------------------------------------------------

week_rows = []

for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:

        week_days_list = week_days[wk]

        work_days = sum(
            solver.Value(work[(a, ds)])
            for ds in week_days_list
            if (a, ds) in work
        )

        izin_days = sum(
            1
            for ds in week_days_list
            if ds in izin_map.get(a, set())
        )

        real_off_days = sum(
            1
            for ds in week_days_list
            if (a, ds) in work
            and solver.Value(work[(a, ds)]) == 0
            and ds not in izin_map.get(a, set())
        )

        weekend_work = sum(
            solver.Value(work[(a, ds)])
            for ds in week_days_list
            if (a, ds) in work
            and pd.to_datetime(ds).weekday() >= 5
        )

        weekend_leave = sum(
            1
            for ds in week_days_list
            if ds in izin_map.get(a, set())
            and pd.to_datetime(ds).weekday() >= 5
        )

        overtime_val = solver.Value(overtime_week[(a, wk)]) if (a, wk) in overtime_week else None

        week_rows.append({
            "agent_user_code": a,
            "week": wk,
            "work_days": work_days,
            "izin_days": izin_days,
            "real_off_days": real_off_days,
            "weekend_work_days": weekend_work,
            "weekend_leave_days": weekend_leave,
            "overtime_week": overtime_val
        })

agent_week_df = pd.DataFrame(week_rows)

agent_week_df = agent_week_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)


# -------------------------------------------------
# 7) Hafta sonu fairness / kontrol
# -------------------------------------------------

weekend_fairness_rows = []

for a in AGENTS:
    a = str(a).strip()

    toplam_hafta_sonu_calisma = 0
    toplam_hafta_sonu_izin = 0
    cumartesi_calisma = 0
    pazar_calisma = 0
    cift_off_sayisi = 0
    cift_izin_sayisi = 0

    for sat_ds, sun_ds in weekend_pairs:

        sat_work = solver.Value(work[(a, sat_ds)]) if (a, sat_ds) in work else 0
        sun_work = solver.Value(work[(a, sun_ds)]) if (a, sun_ds) in work else 0

        sat_leave = sat_ds in izin_map.get(a, set())
        sun_leave = sun_ds in izin_map.get(a, set())

        cumartesi_calisma += sat_work
        pazar_calisma += sun_work
        toplam_hafta_sonu_calisma += sat_work + sun_work
        toplam_hafta_sonu_izin += int(sat_leave) + int(sun_leave)

        # Gerçek Cmt-Paz çift OFF:
        # iki gün de çalışmıyor ve iki gün de izin değilse.
        if (
            sat_work == 0 and sun_work == 0
            and not sat_leave and not sun_leave
        ):
            cift_off_sayisi += 1

        # İki gün de izinliyse ayrıca takip
        if sat_leave and sun_leave:
            cift_izin_sayisi += 1

    weekend_fairness_rows.append({
        "agent_user_code": a,

        "pm_hafta_sonu_calisma_sayisi": pm_hafta_sonu_map.get(a, 0) if "pm_hafta_sonu_map" in globals() else None,

        "bu_ay_hafta_sonu_calisma_sayisi": toplam_hafta_sonu_calisma,
        "toplam_iki_ay_hafta_sonu": (
            pm_hafta_sonu_map.get(a, 0) + toplam_hafta_sonu_calisma
            if "pm_hafta_sonu_map" in globals()
            else None
        ),

        "cumartesi_calisma_gunu": cumartesi_calisma,
        "pazar_calisma_gunu": pazar_calisma,
        "hafta_sonu_izin_gunu": toplam_hafta_sonu_izin,

        "gercek_cmt_paz_cift_off": cift_off_sayisi,
        "cmt_paz_cift_izin": cift_izin_sayisi,

        # Eski hard kural pair_off izinleri de OFF kabul ediyorsa burada farklı görünebilir.
        # Bu kolon insan kontrolü için gerçek OFF'u gösterir.
        "min_1_gercek_cift_off_ok": cift_off_sayisi >= 1,

        "5_ve_uzeri_hafta_sonu_calisma": toplam_hafta_sonu_calisma >= 5
    })

weekend_fairness_df = pd.DataFrame(weekend_fairness_rows)

weekend_fairness_df = weekend_fairness_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

weekend_work_distribution = (
    weekend_fairness_df
    .groupby("bu_ay_hafta_sonu_calisma_sayisi", as_index=False)
    .agg(agent_sayisi=("agent_user_code", "nunique"))
    .sort_values("bu_ay_hafta_sonu_calisma_sayisi")
)

weekend_real_pair_off_distribution = (
    weekend_fairness_df
    .groupby("gercek_cmt_paz_cift_off", as_index=False)
    .agg(agent_sayisi=("agent_user_code", "nunique"))
    .sort_values("gercek_cmt_paz_cift_off")
)


# -------------------------------------------------
# 8) PM / Bu ay adillik karşılaştırma
# -------------------------------------------------

pm_adillik_df = month_summary[
    [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",

        "pm_mesai_sayisi",
        "total_mesai_days",
        "toplam_iki_ay_mesai",

        "pm_gece_sayisi",
        "bu_ay_gece_sayisi",
        "toplam_iki_ay_gece",

        "pm_hafta_sonu_calisma_sayisi",
        "bu_ay_hafta_sonu_calisma_sayisi",
        "toplam_iki_ay_hafta_sonu",

        "total_leave_days",
        "total_real_off_days",
        "total_work_days"
    ]
].copy()

pm_adillik_df = pm_adillik_df.rename(columns={
    "total_mesai_days": "bu_ay_mesai_sayisi"
})


# -------------------------------------------------
# 9) Team base
# -------------------------------------------------

team_base_rows = []

if "team_week_base" in globals():
    all_shifts = sorted(set(
        v
        for ds in PLAN_GUNLER
        for v in gun_vardiyalari.get(ds, [])
    ))

    for t in TAKIMLAR:
        for wk in WEEKS:
            selected_base = None

            for v in all_shifts:
                if (t, wk, v) in team_week_base:
                    if solver.Value(team_week_base[(t, wk, v)]) == 1:
                        selected_base = v
                        break

            team_base_rows.append({
                "takim": t,
                "week": wk,
                "selected_base_shift": selected_base
            })

team_base_df = pd.DataFrame(team_base_rows)


# -------------------------------------------------
# 10) Team day check
# -------------------------------------------------

team_day_rows = []

for t in TAKIMLAR:
    team_agents = [
        a for a in AGENTS
        if agent_team.get(a) == t
    ]

    for ds in PLAN_GUNLER:
        shift_counts = {}

        for a in team_agents:
            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                    shift_counts[v] = shift_counts.get(v, 0) + 1

        active_shifts = [k for k, val in shift_counts.items() if val > 0]

        team_day_rows.append({
            "takim": t,
            "date": ds,
            "week": day_week[ds],
            "day_name": DAY_TR[pd.to_datetime(ds).weekday()] if "DAY_TR" in globals() else pd.to_datetime(ds).day_name(),
            "is_weekend": pd.to_datetime(ds).weekday() >= 5,
            "team_agent_count": len(team_agents),
            "working_agent_count": sum(shift_counts.values()),
            "active_shift_count": len(active_shifts),
            "active_shifts": " | ".join(active_shifts),
            "is_split": len(active_shifts) > 1
        })

team_day_df = pd.DataFrame(team_day_rows)


# -------------------------------------------------
# 11) Summary
# -------------------------------------------------

summary_rows = []

summary_rows.append({"metric": "solver_status", "value": solver.StatusName(status)})
summary_rows.append({"metric": "objective_value", "value": solver.ObjectiveValue() if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None})
summary_rows.append({"metric": "agent_count", "value": len(AGENTS)})
summary_rows.append({"metric": "plan_day_count", "value": len(PLAN_GUNLER)})
summary_rows.append({"metric": "week_count", "value": len(WEEKS)})

summary_rows.append({"metric": "total_required", "value": coverage_df["required"].sum()})
summary_rows.append({"metric": "total_assigned", "value": coverage_df["assigned"].sum()})
summary_rows.append({"metric": "min_gap_to_required", "value": coverage_df["gap_to_required"].min()})
summary_rows.append({"metric": "max_gap_to_required", "value": coverage_df["gap_to_required"].max()})
summary_rows.append({"metric": "negative_gap_row_count", "value": len(coverage_df[coverage_df["gap_to_required"] < 0])})

summary_rows.append({"metric": "total_under_buffer", "value": coverage_df["under_buffer"].sum()})
summary_rows.append({"metric": "total_over_buffer", "value": coverage_df["over_buffer"].sum()})
summary_rows.append({"metric": "total_missing_to_required", "value": coverage_df["missing_to_required"].sum()})
summary_rows.append({"metric": "total_excess_to_required", "value": coverage_df["excess_to_required"].sum()})

summary_rows.append({"metric": "total_mesai_days", "value": month_summary["total_mesai_days"].sum()})
summary_rows.append({"metric": "mesai_alan_agent_count", "value": month_summary[month_summary["total_mesai_days"] > 0]["agent_user_code"].nunique()})

summary_rows.append({"metric": "5_ve_uzeri_hafta_sonu_calisan_agent_count", "value": len(weekend_fairness_df[weekend_fairness_df["5_ve_uzeri_hafta_sonu_calisma"] == True])})
summary_rows.append({"metric": "gercek_min_1_cmt_paz_off_ihlal_count", "value": len(weekend_fairness_df[weekend_fairness_df["min_1_gercek_cift_off_ok"] == False])})

summary_df = pd.DataFrame(summary_rows)


# -------------------------------------------------
# 12) Excel'e yaz
# -------------------------------------------------

with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:

    summary_df.to_excel(writer, sheet_name="00_summary", index=False)
    agent_calendar_df.to_excel(writer, sheet_name="01_agent_calendar", index=False)
    agent_day_df.to_excel(writer, sheet_name="02_agent_day_detail", index=False)
    month_summary.to_excel(writer, sheet_name="03_agent_month_summary", index=False)
    agent_week_df.to_excel(writer, sheet_name="04_agent_week_summary", index=False)
    coverage_df.to_excel(writer, sheet_name="05_coverage", index=False)
    gap_problem_df.to_excel(writer, sheet_name="06_gap_problem_rows", index=False)
    weekend_fairness_df.to_excel(writer, sheet_name="07_weekend_fairness", index=False)

    weekend_work_distribution.to_excel(
        writer,
        sheet_name="07_weekend_fairness",
        index=False,
        startrow=len(weekend_fairness_df) + 4
    )

    weekend_real_pair_off_distribution.to_excel(
        writer,
        sheet_name="07_weekend_fairness",
        index=False,
        startrow=len(weekend_fairness_df) + len(weekend_work_distribution) + 8
    )

    pm_adillik_df.to_excel(writer, sheet_name="08_pm_fairness", index=False)
    team_base_df.to_excel(writer, sheet_name="09_team_base", index=False)
    team_day_df.to_excel(writer, sheet_name="10_team_day_check", index=False)

    workbook = writer.book

    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#D9EAF7",
        "border": 1
    })

    problem_format = workbook.add_format({
        "bg_color": "#F4CCCC"
    })

    ok_format = workbook.add_format({
        "bg_color": "#D9EAD3"
    })

    mesai_format = workbook.add_format({
        "bg_color": "#FFF2CC"
    })

    izin_format = workbook.add_format({
        "bg_color": "#D9D2E9"
    })

    # Genel format
    sheets = {
        "00_summary": summary_df,
        "01_agent_calendar": agent_calendar_df,
        "02_agent_day_detail": agent_day_df,
        "03_agent_month_summary": month_summary,
        "04_agent_week_summary": agent_week_df,
        "05_coverage": coverage_df,
        "06_gap_problem_rows": gap_problem_df,
        "07_weekend_fairness": weekend_fairness_df,
        "08_pm_fairness": pm_adillik_df,
        "09_team_base": team_base_df,
        "10_team_day_check": team_day_df,
    }

    for sheet_name, df in sheets.items():
        ws = writer.sheets[sheet_name]

        if len(df.columns) > 0:
            for col_num, col_name in enumerate(df.columns):
                ws.write(0, col_num, col_name, header_format)

            ws.autofilter(0, 0, max(len(df), 1), len(df.columns) - 1)
            ws.freeze_panes(1, 0)

            for i, col in enumerate(df.columns):
                width = min(max(len(str(col)) + 2, 12), 40)
                ws.set_column(i, i, width)

    # Calendar özel
    ws_cal = writer.sheets["01_agent_calendar"]
    ws_cal.freeze_panes(1, 7)
    ws_cal.set_column(0, 6, 22)
    ws_cal.set_column(7, len(agent_calendar_df.columns), 18)

    # Calendar içinde MESAİ / İZİN renklendir
    for col_idx in range(7, len(agent_calendar_df.columns)):
        ws_cal.conditional_format(
            1,
            col_idx,
            len(agent_calendar_df),
            col_idx,
            {
                "type": "text",
                "criteria": "containing",
                "value": "MESAİ",
                "format": mesai_format
            }
        )

        ws_cal.conditional_format(
            1,
            col_idx,
            len(agent_calendar_df),
            col_idx,
            {
                "type": "text",
                "criteria": "containing",
                "value": "İZİN",
                "format": izin_format
            }
        )

    # Coverage negatif gap renklendir
    ws_cov = writer.sheets["05_coverage"]

    if "gap_to_required" in coverage_df.columns:
        gap_col_idx = coverage_df.columns.get_loc("gap_to_required")
        ws_cov.conditional_format(
            1,
            gap_col_idx,
            len(coverage_df),
            gap_col_idx,
            {
                "type": "cell",
                "criteria": "<",
                "value": 0,
                "format": problem_format
            }
        )

    if "under_buffer" in coverage_df.columns:
        under_col_idx = coverage_df.columns.get_loc("under_buffer")
        ws_cov.conditional_format(
            1,
            under_col_idx,
            len(coverage_df),
            under_col_idx,
            {
                "type": "cell",
                "criteria": ">",
                "value": 0,
                "format": problem_format
            }
        )

    # Weekend fairness 5+ çalışanları renklendir
    ws_weekend = writer.sheets["07_weekend_fairness"]

    if "bu_ay_hafta_sonu_calisma_sayisi" in weekend_fairness_df.columns:
        col_idx = weekend_fairness_df.columns.get_loc("bu_ay_hafta_sonu_calisma_sayisi")
        ws_weekend.conditional_format(
            1,
            col_idx,
            len(weekend_fairness_df),
            col_idx,
            {
                "type": "cell",
                "criteria": ">=",
                "value": 5,
                "format": problem_format
            }
        )

    if "min_1_gercek_cift_off_ok" in weekend_fairness_df.columns:
        col_idx = weekend_fairness_df.columns.get_loc("min_1_gercek_cift_off_ok")
        ws_weekend.conditional_format(
            1,
            col_idx,
            len(weekend_fairness_df),
            col_idx,
            {
                "type": "cell",
                "criteria": "==",
                "value": False,
                "format": problem_format
            }
        )

    # Agent detail status renklendir
    ws_day = writer.sheets["02_agent_day_detail"]

    if "status" in agent_day_df.columns:
        status_col_idx = agent_day_df.columns.get_loc("status")

        ws_day.conditional_format(
            1,
            status_col_idx,
            len(agent_day_df),
            status_col_idx,
            {
                "type": "text",
                "criteria": "containing",
                "value": "MESAİ",
                "format": mesai_format
            }
        )

        ws_day.conditional_format(
            1,
            status_col_idx,
            len(agent_day_df),
            status_col_idx,
            {
                "type": "text",
                "criteria": "containing",
                "value": "İZİN",
                "format": izin_format
            }
        )

print("Excel oluşturuldu:", output_path)