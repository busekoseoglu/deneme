# %% FINAL EXCEL EXPORT - KAPSAMLI VARDİYA PLANI + TÜM KONTROLLER

import pandas as pd
import numpy as np
import os
from datetime import datetime


# =================================================
# 0) GENEL KONTROLLER / HELPERLAR
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
    """
    izin_map içinde tarih string/date/timestamp gelebilir.
    Hepsini güvenli şekilde kontrol eder.
    """
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


def df_or_empty(df, columns=None):
    if df is None:
        return pd.DataFrame(columns=columns if columns else [])
    if isinstance(df, pd.DataFrame):
        return df
    return pd.DataFrame(df)


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
            "working_main_group": info.get("working_main_group"),
            "line_based_main_group": info.get("line_based_main_group"),
            "date": ds_key(ds),
            "week": wk,
            "weekday": weekday,
            "gun": safe_day_name(ds),
            "assigned": assigned,
            "status": status_label,
            "special_day_label": special_day_label,
            "assigned_shift": assigned_shift,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "is_leave": is_leave,
            "is_arife": is_arife,
            "is_resmi_tatil": is_resmi_tatil,
            "is_ozel_gun": is_ozel_gun,
            "normal_overtime_week": normal_overtime_week,
            "hamile_flg": info.get("hamile_flg"),
            "sut_izni_flg": info.get("sut_izni_flg"),
            "mesaiye_kalamaz_flg": info.get("mesaiye_kalamaz_flg"),
            "sabah_calisir_flg": info.get("sabah_calisir_flg"),
        })

agent_day_plan_df = pd.DataFrame(agent_day_rows)


# =================================================
# 4) TAKVİM SHEETLERİ
# =================================================

calendar_status_df = agent_day_plan_df.pivot_table(
    index=["agent_user_code", "agent_name", "takim", "teamleader_name"],
    columns="date",
    values="status",
    aggfunc="first"
).reset_index()

calendar_value_df = agent_day_plan_df.copy()

calendar_value_df["calendar_value"] = np.where(
    calendar_value_df["assigned"] == 1,
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

# Excel başlıkları tarih/numara diye bozmasın
calendar_status_df.columns = [str(c) for c in calendar_status_df.columns]
calendar_shift_df.columns = [str(c) for c in calendar_shift_df.columns]


# =================================================
# 5) COVERAGE KONTROL
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

        lower_req = coverage_lower.get((ds, v), None) if "coverage_lower" in globals() else None
        upper_req = coverage_upper.get((ds, v), None) if "coverage_upper" in globals() else None

        under_buffer_val = (
            safe_solver_value(under_buffer[(ds, v)])
            if "under_buffer" in globals() and (ds, v) in under_buffer
            else None
        )

        over_buffer_val = (
            safe_solver_value(over_buffer[(ds, v)])
            if "over_buffer" in globals() and (ds, v) in over_buffer
            else None
        )

        missing_val = (
            safe_solver_value(missing_to_required[(ds, v)])
            if "missing_to_required" in globals() and (ds, v) in missing_to_required
            else None
        )

        excess_val = (
            safe_solver_value(excess_to_required[(ds, v)])
            if "excess_to_required" in globals() and (ds, v) in excess_to_required
            else None
        )

        buffer_ici = None
        if lower_req is not None and upper_req is not None:
            buffer_ici = assigned >= lower_req and assigned <= upper_req

        coverage_rows.append({
            "date": ds_key(ds),
            "gun": safe_day_name(ds),
            "weekday": pd.to_datetime(ds).weekday(),
            "hafta_ici": pd.to_datetime(ds).weekday() in [0, 1, 2, 3, 4],
            "week": day_week.get(ds) if "day_week" in globals() else None,
            "shift": v,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "required": required,
            "assigned": assigned,
            "gap_to_required": assigned - required,
            "lower_buffer": lower_req,
            "upper_buffer": upper_req,
            "gap_to_lower": assigned - lower_req if lower_req is not None else None,
            "gap_to_upper": assigned - upper_req if upper_req is not None else None,
            "buffer_ici": buffer_ici,
            "under_buffer": under_buffer_val,
            "over_buffer": over_buffer_val,
            "missing_to_required": missing_val,
            "excess_to_required": excess_val,
            "is_arife": ds in arife_days_set,
            "is_resmi_tatil": ds in resmi_tatil_days_set,
            "is_ozel_gun": ds in ozel_tatil_days_set,
        })

coverage_gap_df = pd.DataFrame(coverage_rows)

coverage_zero_assigned_df = coverage_gap_df[
    (coverage_gap_df["required"] > 0) &
    (coverage_gap_df["assigned"] == 0)
].copy()

coverage_worst_df = coverage_gap_df.sort_values(
    ["gap_to_lower", "gap_to_required"],
    ascending=[True, True]
).head(100).copy()


# =================================================
# 6) HAFTALIK HEDEF KONTROL
# =================================================

weekly_rows = []

for a in AGENTS:
    a = normalize_agent(a)
    info = agent_info_map.get(a, {})

    for wk, days_in_week in week_days.items():

        resmi_tatil_days_this_week = set(
            ds for ds in days_in_week
            if ds in resmi_tatil_days_set
        )

        izin_days_this_week = set(
            ds for ds in days_in_week
            if agent_izinli_mi_export(a, ds)
        )

        izin_normal_days_this_week = izin_days_this_week - resmi_tatil_days_this_week

        normal_work_days = [
            ds for ds in days_in_week
            if (a, ds) in work
            and ds not in resmi_tatil_days_this_week
        ]

        normal_target = NORMAL_WORK_DAYS
        normal_target -= len(resmi_tatil_days_this_week)
        normal_target -= len(izin_normal_days_this_week)
        normal_target = max(0, normal_target)
        normal_target = min(normal_target, len(normal_work_days))

        normal_worked_days = sum(
            safe_solver_value(work[(a, ds)])
            for ds in normal_work_days
        )

        resmi_tatil_worked_days = sum(
            safe_solver_value(work[(a, ds)])
            for ds in days_in_week
            if (a, ds) in work and ds in resmi_tatil_days_this_week
        )

        overtime_val = (
            safe_solver_value(overtime_week[(a, wk)])
            if "overtime_week" in globals() and (a, wk) in overtime_week
            else 0
        )

        weekly_under_val = (
            safe_solver_value(weekly_under[(a, wk)])
            if "weekly_under" in globals() and (a, wk) in weekly_under
            else 0
        )

        weekly_over_val = (
            safe_solver_value(weekly_over[(a, wk)])
            if "weekly_over" in globals() and (a, wk) in weekly_over
            else 0
        )

        weekly_rows.append({
            "agent_user_code": a,
            "agent_name": info.get("agent_name"),
            "takim": info.get("takim"),
            "teamleader_name": info.get("teamleader_name"),
            "week": wk,
            "week_day_count": len(days_in_week),
            "normal_target": normal_target,
            "normal_worked_days": normal_worked_days,
            "resmi_tatil_worked_days": resmi_tatil_worked_days,
            "total_worked_days": normal_worked_days + resmi_tatil_worked_days,
            "overtime_week": overtime_val,
            "weekly_under": weekly_under_val,
            "weekly_over": weekly_over_val,
            "worked_minus_target": normal_worked_days - normal_target,
            "target_plus_overtime_ok": normal_worked_days == normal_target + overtime_val,
            "izin_count": len(izin_days_this_week),
            "izin_normal_count": len(izin_normal_days_this_week),
            "resmi_tatil_count": len(resmi_tatil_days_this_week),
            "mesaiye_kalamaz_flg": info.get("mesaiye_kalamaz_flg"),
            "hamile_flg": info.get("hamile_flg"),
            "sut_izni_flg": info.get("sut_izni_flg"),
        })

weekly_target_check_df = pd.DataFrame(weekly_rows)

weekly_under_detail_df = weekly_target_check_df[
    weekly_target_check_df["weekly_under"] > 0
].sort_values(["week", "weekly_under", "agent_user_code"], ascending=[True, False, True]).copy()

weekly_over_detail_df = weekly_target_check_df[
    weekly_target_check_df["weekly_over"] > 0
].sort_values(["week", "weekly_over", "agent_user_code"], ascending=[True, False, True]).copy()


# =================================================
# 7) MESAİ ÖZET
# =================================================

mesai_rows = []

for a in AGENTS:
    a = normalize_agent(a)
    info = agent_info_map.get(a, {})

    normal_mesai_count = sum(
        safe_solver_value(overtime_week[(a, wk)])
        for wk in WEEKS
        if "overtime_week" in globals() and (a, wk) in overtime_week
    )

    arife_mesai_count = sum(
        1 for (aa, ds, v) in arife_mesai_assignments
        if aa == a
    )

    resmi_tatil_mesai_count = sum(
        1 for (aa, ds, v) in resmi_tatil_mesai_assignments
        if aa == a
    )

    resmi_tatil_ihlal_count = sum(
        1 for (aa, ds, v) in resmi_tatil_ihlal_assignments
        if aa == a
    )

    total_work_days = agent_day_plan_df[
        (agent_day_plan_df["agent_user_code"] == a) &
        (agent_day_plan_df["assigned"] == 1)
    ].shape[0]

    izin_count = agent_day_plan_df[
        (agent_day_plan_df["agent_user_code"] == a) &
        (agent_day_plan_df["is_leave"] == True)
    ].shape[0]

    mesai_rows.append({
        "agent_user_code": a,
        "agent_name": info.get("agent_name"),
        "takim": info.get("takim"),
        "teamleader_name": info.get("teamleader_name"),
        "normal_mesai_count": normal_mesai_count,
        "arife_mesai_count": arife_mesai_count,
        "resmi_tatil_mesai_count": resmi_tatil_mesai_count,
        "resmi_tatil_kisitli_ihlal_count": resmi_tatil_ihlal_count,
        "total_work_days": total_work_days,
        "izin_count": izin_count,
        "hamile_flg": info.get("hamile_flg"),
        "sut_izni_flg": info.get("sut_izni_flg"),
        "mesaiye_kalamaz_flg": info.get("mesaiye_kalamaz_flg"),
    })

mesai_summary_df = pd.DataFrame(mesai_rows)


# =================================================
# 8) ÖZEL GÜN ÇALIŞANLARI
# =================================================

special_day_df = agent_day_plan_df[
    agent_day_plan_df["is_ozel_gun"] == True
].copy()

special_day_df = special_day_df[
    (special_day_df["assigned"] == 1) |
    (special_day_df["is_leave"] == True)
].sort_values(["date", "status", "takim", "agent_user_code"])


# =================================================
# 9) RESMİ TATİL İHLAL
# =================================================

resmi_tatil_ihlal_rows = []

for (a, ds, v) in resmi_tatil_ihlal_assignments:
    info = agent_info_map.get(a, {})
    shift_start, shift_end = get_shift_time(ds, v)

    resmi_tatil_ihlal_rows.append({
        "agent_user_code": a,
        "agent_name": info.get("agent_name"),
        "takim": info.get("takim"),
        "teamleader_name": info.get("teamleader_name"),
        "date": ds_key(ds),
        "shift": v,
        "shift_start": shift_start,
        "shift_end": shift_end,
        "hamile_flg": info.get("hamile_flg"),
        "sut_izni_flg": info.get("sut_izni_flg"),
        "mesaiye_kalamaz_flg": info.get("mesaiye_kalamaz_flg"),
        "ihlal": 1,
    })

resmi_tatil_ihlal_df = pd.DataFrame(resmi_tatil_ihlal_rows)


# =================================================
# 10) TAKIM BÖLÜNME KONTROL
# =================================================

weekday_team_rows = []
weekend_team_rows = []
special_team_rows = []

for ds in PLAN_GUNLER:
    weekday = pd.to_datetime(ds).weekday()
    is_special = ds in ozel_tatil_days_set

    for t in TAKIMLAR:
        t = str(t).strip()

        team_agents = [
            normalize_agent(a)
            for a in AGENTS
            if str(agent_team.get(normalize_agent(a), "")).strip() == t
        ]

        assigned_shifts = []

        for a in team_agents:
            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                    assigned_shifts.append(v)

        if not assigned_shifts:
            continue

        row = {
            "week": day_week.get(ds) if "day_week" in globals() else None,
            "date": ds_key(ds),
            "gun": safe_day_name(ds),
            "weekday": weekday,
            "hafta_ici": weekday in [0, 1, 2, 3, 4],
            "is_ozel_gun": is_special,
            "takim": t,
            "calisan_agent": len(assigned_shifts),
            "vardiya_sayisi": len(set(assigned_shifts)),
            "vardiyalar": ", ".join(sorted(set(assigned_shifts))),
        }

        if is_special:
            if len(set(assigned_shifts)) > 1:
                special_team_rows.append(row)

        elif weekday in [0, 1, 2, 3, 4]:
            if len(set(assigned_shifts)) > 1:
                weekday_team_rows.append(row)

        else:
            if len(set(assigned_shifts)) > 1:
                weekend_team_rows.append(row)

weekday_team_viol_df = pd.DataFrame(weekday_team_rows)
weekend_team_split_df = pd.DataFrame(weekend_team_rows)
special_team_split_df = pd.DataFrame(special_team_rows)


# =================================================
# 11) TAKIM BASE SEÇİMİ KONTROL
# =================================================

team_base_rows = []

if "team_week_base" in globals():
    for t in TAKIMLAR:
        t = str(t).strip()

        for wk in WEEKS:
            for v in week_vardiyalari.get(wk, []):

                if (t, wk, v) not in team_week_base:
                    continue

                if safe_solver_value(team_week_base[(t, wk, v)]) != 1:
                    continue

                start, end = None, None

                for ds in week_days[wk]:
                    if (ds, v) in saat:
                        start, end = saat[(ds, v)]
                        break

                team_size = sum(
                    1
                    for a in AGENTS
                    if str(agent_team.get(normalize_agent(a), "")).strip() == t
                )

                team_base_rows.append({
                    "week": wk,
                    "takim": t,
                    "base_shift": v,
                    "shift_start": start,
                    "shift_end": end,
                    "team_size": team_size,
                })

team_base_selection_df = pd.DataFrame(team_base_rows)


# =================================================
# 12) HAFTA SONU OFF KONTROL
# =================================================

weekend_pairs_final = []
plan_dates = sorted([pd.to_datetime(ds).date() for ds in PLAN_GUNLER])
date_to_ds = {pd.to_datetime(ds).date(): ds for ds in PLAN_GUNLER}

for d in plan_dates:
    if d.weekday() == 5:
        sunday = d + pd.Timedelta(days=1)
        if sunday in date_to_ds:
            weekend_pairs_final.append((date_to_ds[d], date_to_ds[sunday]))

weekend_off_rows = []

for a in AGENTS:
    a = normalize_agent(a)
    info = agent_info_map.get(a, {})

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs_final):

        sat_work = (
            safe_solver_value(work[(a, sat_ds)])
            if (a, sat_ds) in work
            else 0
        )

        sun_work = (
            safe_solver_value(work[(a, sun_ds)])
            if (a, sun_ds) in work
            else 0
        )

        pair_off = 1 if sat_work == 0 and sun_work == 0 else 0

        weekend_off_rows.append({
            "agent_user_code": a,
            "agent_name": info.get("agent_name"),
            "takim": info.get("takim"),
            "teamleader_name": info.get("teamleader_name"),
            "pair_no": i + 1,
            "saturday": ds_key(sat_ds),
            "sunday": ds_key(sun_ds),
            "saturday_work": sat_work,
            "sunday_work": sun_work,
            "pair_off": pair_off,
            "hamile_flg": info.get("hamile_flg"),
            "sut_izni_flg": info.get("sut_izni_flg"),
        })

weekend_off_df = pd.DataFrame(weekend_off_rows)

if len(weekend_off_df) > 0:
    weekend_off_summary_df = (
        weekend_off_df
        .groupby(["agent_user_code", "agent_name", "takim", "teamleader_name"], as_index=False)
        .agg(pair_off_count=("pair_off", "sum"))
    )
    weekend_off_summary_df["en_az_1_pair_off_ok"] = weekend_off_summary_df["pair_off_count"] >= 1
else:
    weekend_off_summary_df = pd.DataFrame(columns=[
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "pair_off_count",
        "en_az_1_pair_off_ok",
    ])


# =================================================
# 13) AGENT AYLIK ÖZET
# =================================================

agent_monthly_df = (
    agent_day_plan_df
    .groupby(["agent_user_code", "agent_name", "takim", "teamleader_name"], as_index=False)
    .agg(
        total_assigned_days=("assigned", "sum"),
        izin_days=("is_leave", "sum"),
        arife_flag_days=("is_arife", "sum"),
        resmi_tatil_flag_days=("is_resmi_tatil", "sum"),
    )
)

status_counts_df = (
    agent_day_plan_df
    .pivot_table(
        index="agent_user_code",
        columns="status",
        values="date",
        aggfunc="count",
        fill_value=0,
    )
    .reset_index()
)

status_counts_df.columns = [str(c) for c in status_counts_df.columns]

agent_monthly_df = agent_monthly_df.merge(
    status_counts_df,
    on="agent_user_code",
    how="left"
)

agent_monthly_df = agent_monthly_df.merge(
    mesai_summary_df[
        [
            "agent_user_code",
            "normal_mesai_count",
            "arife_mesai_count",
            "resmi_tatil_mesai_count",
            "resmi_tatil_kisitli_ihlal_count",
        ]
    ],
    on="agent_user_code",
    how="left",
)


# =================================================
# 14) VARDİYA ÖZET
# =================================================

shift_summary_df = (
    coverage_gap_df
    .groupby(["shift", "shift_start", "shift_end"], as_index=False)
    .agg(
        toplam_talep=("required", "sum"),
        toplam_atanan=("assigned", "sum"),
        toplam_gap=("gap_to_required", "sum"),
        toplam_under_buffer=("under_buffer", "sum"),
        toplam_missing=("missing_to_required", "sum"),
        toplam_excess=("excess_to_required", "sum"),
        satir_sayisi=("date", "count"),
    )
    .sort_values(["shift_start", "shift_end", "shift"])
)


# =================================================
# 15) ÖZET SHEET
# =================================================

summary_rows = [
    {"metric": "Agent sayısı", "value": len(AGENTS)},
    {"metric": "Plan gün sayısı", "value": len(PLAN_GUNLER)},
    {"metric": "Vardiya coverage satır sayısı", "value": len(coverage_gap_df)},
    {"metric": "Toplam talep", "value": coverage_gap_df["required"].sum()},
    {"metric": "Toplam atanan", "value": coverage_gap_df["assigned"].sum()},
    {"metric": "Toplam gap_to_required", "value": coverage_gap_df["gap_to_required"].sum()},
    {"metric": "Toplam under_buffer", "value": coverage_gap_df["under_buffer"].sum()},
    {"metric": "Toplam missing_to_required", "value": coverage_gap_df["missing_to_required"].sum()},
    {"metric": "Toplam over_buffer", "value": coverage_gap_df["over_buffer"].sum()},
    {"metric": "Toplam excess_to_required", "value": coverage_gap_df["excess_to_required"].sum()},
    {"metric": "Hiç atanmayan talep vardiyası", "value": len(coverage_zero_assigned_df)},
    {"metric": "Weekly under toplam", "value": weekly_target_check_df["weekly_under"].sum()},
    {"metric": "Weekly over toplam", "value": weekly_target_check_df["weekly_over"].sum()},
    {"metric": "Weekly under agent-week sayısı", "value": (weekly_target_check_df["weekly_under"] > 0).sum()},
    {"metric": "Weekly over agent-week sayısı", "value": (weekly_target_check_df["weekly_over"] > 0).sum()},
    {"metric": "Normal mesai toplam", "value": mesai_summary_df["normal_mesai_count"].sum()},
    {"metric": "Arife mesai toplam", "value": mesai_summary_df["arife_mesai_count"].sum()},
    {"metric": "Resmi tatil mesai toplam", "value": mesai_summary_df["resmi_tatil_mesai_count"].sum()},
    {"metric": "Resmi tatil kısıtlı ihlal toplam", "value": mesai_summary_df["resmi_tatil_kisitli_ihlal_count"].sum()},
    {"metric": "Özel gün hariç hafta içi bölünen takım-gün", "value": len(weekday_team_viol_df)},
    {"metric": "Hafta sonu bölünen takım-gün", "value": len(weekend_team_split_df)},
    {"metric": "Özel gün bölünen takım-gün", "value": len(special_team_split_df)},
]

summary_df = pd.DataFrame(summary_rows)


# =================================================
# 16) PARAMETRELER
# =================================================

debug_params = {
    "BUFFER_RATE": BUFFER_RATE if "BUFFER_RATE" in globals() else None,
    "NORMAL_WORK_DAYS": NORMAL_WORK_DAYS if "NORMAL_WORK_DAYS" in globals() else None,
    "MAX_OVERTIME_PER_MONTH": MAX_OVERTIME_PER_MONTH if "MAX_OVERTIME_PER_MONTH" in globals() else None,
    "IKINCI_MESAI_W": IKINCI_MESAI_W if "IKINCI_MESAI_W" in globals() else None,
    "OVERTIME_W": OVERTIME_W if "OVERTIME_W" in globals() else None,
    "ARIFE_MESAI_W": ARIFE_MESAI_W if "ARIFE_MESAI_W" in globals() else None,
    "RESMI_TATIL_MESAI_W": RESMI_TATIL_MESAI_W if "RESMI_TATIL_MESAI_W" in globals() else None,
    "RESMI_TATIL_KISITLI_IHLAL_W": RESMI_TATIL_KISITLI_IHLAL_W if "RESMI_TATIL_KISITLI_IHLAL_W" in globals() else None,
    "GENEL_MAX_FAZLA_ATAMA": GENEL_MAX_FAZLA_ATAMA if "GENEL_MAX_FAZLA_ATAMA" in globals() else None,
    "GECE_MAX_FAZLA_ATAMA": GECE_MAX_FAZLA_ATAMA if "GECE_MAX_FAZLA_ATAMA" in globals() else None,
    "MAX_CONSECUTIVE_WORK_DAYS": MAX_CONSECUTIVE_WORK_DAYS if "MAX_CONSECUTIVE_WORK_DAYS" in globals() else None,
    "MIN_REST_HOURS": MIN_REST_HOURS if "MIN_REST_HOURS" in globals() else None,
    "Arife günleri": ", ".join(sorted([ds_key(d) for d in arife_days_set])),
    "Resmi tatil günleri": ", ".join(sorted([ds_key(d) for d in resmi_tatil_days_set])),
}

debug_params_df = pd.DataFrame(
    [{"parameter": k, "value": v} for k, v in debug_params.items()]
)


# =================================================
# 17) OPSİYONEL DEBUG SHEETLER
# =================================================

optional_sheets = {}

if "team_base_capacity_debug_df" in globals():
    optional_sheets["17_Base_Kapasite_Guard"] = df_or_empty(team_base_capacity_debug_df)

if "weekly_equation_check_df" in globals():
    optional_sheets["18_Weekly_Equation"] = df_or_empty(weekly_equation_check_df)

if "fazla_atama_kontrol" in globals():
    optional_sheets["19_Fazla_Atama_Kontrol"] = df_or_empty(fazla_atama_kontrol)

if "arife_cap_relax_df" in globals():
    optional_sheets["20_Arife_Cap_Relax"] = df_or_empty(arife_cap_relax_df)


# =================================================
# 18) EXCEL YAZIMI
# =================================================

output_file = f"vardiya_plani_kapsamli_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

sheet_df_map = {
    "00_Ozet": summary_df,
    "01_Agent_Gunluk_Plan": agent_day_plan_df,
    "02_Takvim_Vardiya": calendar_shift_df,
    "03_Takvim_Status": calendar_status_df,
    "04_Coverage_Kontrol": coverage_gap_df,
    "05_Haftalik_Hedef": weekly_target_check_df,
    "06_Mesai_Ozet": mesai_summary_df,
    "07_Ozel_Gun_Calisan": special_day_df,
    "08_Resmi_Tatil_Ihlal": resmi_tatil_ihlal_df,
    "09_Takim_Bolunme_HI": weekday_team_viol_df,
    "10_Takim_Bolunme_HS": weekend_team_split_df,
    "11_Takim_Bolunme_Ozel": special_team_split_df,
    "12_Team_Base_Secim": team_base_selection_df,
    "13_Weekend_OFF_Ozet": weekend_off_summary_df,
    "14_Weekend_OFF_Detay": weekend_off_df,
    "15_Agent_Aylik_Ozet": agent_monthly_df,
    "16_Vardiya_Ozet": shift_summary_df,
    "17_Coverage_En_Kotu": coverage_worst_df,
    "18_Atanmayan_Talep": coverage_zero_assigned_df,
    "19_Weekly_Under_Detay": weekly_under_detail_df,
    "20_Weekly_Over_Detay": weekly_over_detail_df,
    "21_Parametreler": debug_params_df,
}

# Optional sheetleri sonlara ekle
sheet_df_map.update(optional_sheets)

with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:

    for sheet_name, df_sheet in sheet_df_map.items():
        df_sheet = df_or_empty(df_sheet)
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

    mesai_format = workbook.add_format({
        "bg_color": "#F4CCCC",
        "font_color": "#990000",
    })

    arife_format = workbook.add_format({
        "bg_color": "#D9EAD3",
        "font_color": "#274E13",
    })

    resmi_tatil_format = workbook.add_format({
        "bg_color": "#CFE2F3",
        "font_color": "#073763",
    })

    # Header + genişlik + filtre
    for sheet_name, df_sheet in sheet_df_map.items():

        safe_sheet_name = sheet_name[:31]
        worksheet = writer.sheets[safe_sheet_name]
        df_sheet = df_or_empty(df_sheet)

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

            elif col_name_str in ["vardiyalar", "calendar_value"]:
                worksheet.set_column(col_num, col_num, 28)

            elif safe_sheet_name in ["02_Takvim_Vardiya", "03_Takvim_Status"] and col_num >= 4:
                worksheet.set_column(col_num, col_num, 16)

            elif col_name_str in ["metric", "parameter"]:
                worksheet.set_column(col_num, col_num, 42)

            else:
                worksheet.set_column(col_num, col_num, 15)

    # =================================================
    # Conditional formatting
    # =================================================

    # Coverage
    ws_cov = writer.sheets["04_Coverage_Kontrol"]
    cov_rows = len(coverage_gap_df) + 1

    if len(coverage_gap_df) > 0:

        if "gap_to_lower" in coverage_gap_df.columns:
            col_idx = coverage_gap_df.columns.get_loc("gap_to_lower")
            ws_cov.conditional_format(1, col_idx, cov_rows, col_idx, {
                "type": "cell",
                "criteria": "<",
                "value": 0,
                "format": warning_format,
            })

        if "buffer_ici" in coverage_gap_df.columns:
            col_idx = coverage_gap_df.columns.get_loc("buffer_ici")
            ws_cov.conditional_format(1, col_idx, cov_rows, col_idx, {
                "type": "text",
                "criteria": "containing",
                "value": "False",
                "format": warning_format,
            })

        if "gap_to_required" in coverage_gap_df.columns:
            col_idx = coverage_gap_df.columns.get_loc("gap_to_required")
            ws_cov.conditional_format(1, col_idx, cov_rows, col_idx, {
                "type": "cell",
                "criteria": "<",
                "value": 0,
                "format": special_format,
            })

    # Haftalık hedef
    ws_week = writer.sheets["05_Haftalik_Hedef"]
    week_rows = len(weekly_target_check_df) + 1

    if len(weekly_target_check_df) > 0:

        if "weekly_under" in weekly_target_check_df.columns:
            col_idx = weekly_target_check_df.columns.get_loc("weekly_under")
            ws_week.conditional_format(1, col_idx, week_rows, col_idx, {
                "type": "cell",
                "criteria": ">",
                "value": 0,
                "format": warning_format,
            })

        if "weekly_over" in weekly_target_check_df.columns:
            col_idx = weekly_target_check_df.columns.get_loc("weekly_over")
            ws_week.conditional_format(1, col_idx, week_rows, col_idx, {
                "type": "cell",
                "criteria": ">",
                "value": 0,
                "format": special_format,
            })

        if "target_plus_overtime_ok" in weekly_target_check_df.columns:
            col_idx = weekly_target_check_df.columns.get_loc("target_plus_overtime_ok")
            ws_week.conditional_format(1, col_idx, week_rows, col_idx, {
                "type": "text",
                "criteria": "containing",
                "value": "False",
                "format": warning_format,
            })

    # Takvim renklendirme
    for safe_sheet_name, df_calendar in [
        ("02_Takvim_Vardiya", calendar_shift_df),
        ("03_Takvim_Status", calendar_status_df),
    ]:
        ws = writer.sheets[safe_sheet_name]

        if len(df_calendar.columns) > 4:
            max_rows = len(df_calendar) + 1
            max_cols = len(df_calendar.columns) - 1

            ws.conditional_format(1, 4, max_rows, max_cols, {
                "type": "text",
                "criteria": "containing",
                "value": "İZİN",
                "format": izin_format,
            })

            ws.conditional_format(1, 4, max_rows, max_cols, {
                "type": "text",
                "criteria": "containing",
                "value": "OFF",
                "format": off_format,
            })

            ws.conditional_format(1, 4, max_rows, max_cols, {
                "type": "text",
                "criteria": "containing",
                "value": "MESAI",
                "format": mesai_format,
            })

            ws.conditional_format(1, 4, max_rows, max_cols, {
                "type": "text",
                "criteria": "containing",
                "value": "ARIFE_09_13",
                "format": arife_format,
            })

            ws.conditional_format(1, 4, max_rows, max_cols, {
                "type": "text",
                "criteria": "containing",
                "value": "RESMI_TATIL",
                "format": resmi_tatil_format,
            })

    # Özel gün
    ws_special = writer.sheets["07_Ozel_Gun_Calisan"]

    if len(special_day_df) > 0 and "status" in special_day_df.columns:
        special_rows = len(special_day_df) + 1
        col_idx = special_day_df.columns.get_loc("status")

        ws_special.conditional_format(1, col_idx, special_rows, col_idx, {
            "type": "text",
            "criteria": "containing",
            "value": "MESAI",
            "format": mesai_format,
        })

        ws_special.conditional_format(1, col_idx, special_rows, col_idx, {
            "type": "text",
            "criteria": "containing",
            "value": "IHLAL",
            "format": warning_format,
        })

    # Özet sheet genişlik
    ws_summary = writer.sheets["00_Ozet"]
    ws_summary.set_column(0, 0, 46)
    ws_summary.set_column(1, 1, 18)

print("Excel oluşturuldu:", os.path.abspath(output_file))
print("Sheet sayısı:", len(sheet_df_map))
print("Dosya:", output_file)