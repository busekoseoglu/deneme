# %% EXCEL EXPORT - KAPSAMLI PLAN + KONTROLLER

import pandas as pd
import numpy as np
from datetime import datetime
import os

# -------------------------------------------------
# 0) Solve kontrolü
# -------------------------------------------------

try:
    feasible_statuses = [cp_model.OPTIMAL, cp_model.FEASIBLE]
    if status not in feasible_statuses:
        raise ValueError(f"Model çözümü feasible değil. Status: {status}")
except NameError:
    print("Uyarı: status veya cp_model bulunamadı. Yine de export deneniyor.")


# -------------------------------------------------
# 1) Genel helper fonksiyonlar
# -------------------------------------------------

def ds_key(ds):
    return pd.to_datetime(ds).strftime("%Y-%m-%d")

def safe_solver_value(var, default=0):
    try:
        return solver.Value(var)
    except Exception:
        return default

def get_shift_time(ds, v):
    if (ds, v) in saat:
        return saat[(ds, v)][0], saat[(ds, v)][1]
    return None, None

def normalize_agent(a):
    return str(a).strip()

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

    return (ds in izin_set) or (ds_str in izin_set) or (ds_date in izin_set)


# -------------------------------------------------
# 2) Agent info
# -------------------------------------------------

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
    "sabah_calisir_flg"
]

available_agent_info_cols = [c for c in agent_info_cols if c in df_tam.columns]

agent_info_df = df_tam[available_agent_info_cols].copy()
agent_info_df["agent_user_code"] = agent_info_df["agent_user_code"].astype(str).str.strip()

agent_info_map = (
    agent_info_df
    .drop_duplicates("agent_user_code")
    .set_index("agent_user_code")
    .to_dict("index")
)


# -------------------------------------------------
# 3) Özel gün setleri
# -------------------------------------------------

arife_days_set = set(arife_plan_gunleri) if "arife_plan_gunleri" in globals() else set()
resmi_tatil_days_set = set(resmi_tatil_plan_gunleri) if "resmi_tatil_plan_gunleri" in globals() else set()
ozel_tatil_days_set = set(ozel_tatil_plan_gunleri) if "ozel_tatil_plan_gunleri" in globals() else arife_days_set | resmi_tatil_days_set

arife_mesai_assignments = set()
if "arife_mesai" in globals():
    for (a, ds, v), var in arife_mesai.items():
        if safe_solver_value(var) == 1:
            arife_mesai_assignments.add((normalize_agent(a), ds, v))

resmi_tatil_mesai_assignments = set()
if "resmi_tatil_mesai" in globals():
    for (a, ds, v), var in resmi_tatil_mesai.items():
        if safe_solver_value(var) == 1:
            resmi_tatil_mesai_assignments.add((normalize_agent(a), ds, v))

resmi_tatil_ihlal_assignments = set()
if "resmi_tatil_kisitli_ihlal" in globals():
    for (a, ds, v), var in resmi_tatil_kisitli_ihlal.items():
        if safe_solver_value(var) == 1:
            resmi_tatil_ihlal_assignments.add((normalize_agent(a), ds, v))


# -------------------------------------------------
# 4) Agent günlük plan
# -------------------------------------------------

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

        is_leave = agent_izinli_mi_export(a, ds)
        is_arife = ds in arife_days_set
        is_resmi_tatil = ds in resmi_tatil_days_set
        is_ozel_gun = ds in ozel_tatil_days_set

        wk = day_week[ds] if "day_week" in globals() and ds in day_week else None
        weekday = pd.to_datetime(ds).weekday()

        overtime_week_val = None
        if wk is not None and (a, wk) in overtime_week:
            overtime_week_val = safe_solver_value(overtime_week[(a, wk)])

        status_label = "OFF"

        if is_leave:
            status_label = "İZİN"

        if assigned == 1:
            status_label = "WORK"

            if is_arife and assigned_shift in arife_ozel_vardiya_kodlari:
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
            "gun": pd.to_datetime(ds).day_name(),
            "assigned": assigned,
            "status": status_label,
            "assigned_shift": assigned_shift,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "is_leave": is_leave,
            "is_arife": is_arife,
            "is_resmi_tatil": is_resmi_tatil,
            "is_ozel_gun": is_ozel_gun,
            "overtime_week": overtime_week_val,
            "hamile_flg": info.get("hamile_flg"),
            "sut_izni_flg": info.get("sut_izni_flg"),
            "mesaiye_kalamaz_flg": info.get("mesaiye_kalamaz_flg"),
            "sabah_calisir_flg": info.get("sabah_calisir_flg"),
        })

agent_day_plan_df = pd.DataFrame(agent_day_rows)


# -------------------------------------------------
# 5) Takvim planı: agent satır, gün kolon
# -------------------------------------------------

calendar_df = agent_day_plan_df.pivot_table(
    index=["agent_user_code", "agent_name", "takim", "teamleader_name"],
    columns="date",
    values="status",
    aggfunc="first"
).reset_index()

# Vardiya saatli takvim
calendar_shift_df = agent_day_plan_df.copy()
calendar_shift_df["calendar_value"] = np.where(
    calendar_shift_df["assigned"] == 1,
    calendar_shift_df["assigned_shift"].fillna("") + " (" +
    calendar_shift_df["shift_start"].fillna("") + "-" +
    calendar_shift_df["shift_end"].fillna("") + ")",
    calendar_shift_df["status"]
)

calendar_shift_df = calendar_shift_df.pivot_table(
    index=["agent_user_code", "agent_name", "takim", "teamleader_name"],
    columns="date",
    values="calendar_value",
    aggfunc="first"
).reset_index()


# -------------------------------------------------
# 6) Coverage kontrol
# -------------------------------------------------

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

        under_buffer_val = safe_solver_value(under_buffer[(ds, v)]) if (ds, v) in under_buffer else None
        over_buffer_val = safe_solver_value(over_buffer[(ds, v)]) if (ds, v) in over_buffer else None
        missing_val = safe_solver_value(missing_to_required[(ds, v)]) if (ds, v) in missing_to_required else None
        excess_val = safe_solver_value(excess_to_required[(ds, v)]) if (ds, v) in excess_to_required else None

        coverage_rows.append({
            "date": ds_key(ds),
            "gun": pd.to_datetime(ds).day_name(),
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
            "buffer_ici": (
                assigned >= lower_req and assigned <= upper_req
                if lower_req is not None and upper_req is not None
                else None
            ),
            "under_buffer": under_buffer_val,
            "over_buffer": over_buffer_val,
            "missing_to_required": missing_val,
            "excess_to_required": excess_val,
            "is_arife": ds in arife_days_set,
            "is_resmi_tatil": ds in resmi_tatil_days_set,
            "is_ozel_gun": ds in ozel_tatil_days_set,
        })

coverage_gap_df = pd.DataFrame(coverage_rows)


# -------------------------------------------------
# 7) Haftalık hedef kontrol
# -------------------------------------------------

weekly_rows = []

for a in AGENTS:
    a = normalize_agent(a)
    info = agent_info_map.get(a, {})

    for wk, days_in_week in week_days.items():

        resmi_tatil_days_this_week = set(ds for ds in days_in_week if ds in resmi_tatil_days_set)
        izin_days_this_week = set(ds for ds in days_in_week if agent_izinli_mi_export(a, ds))
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

        overtime_val = safe_solver_value(overtime_week[(a, wk)]) if (a, wk) in overtime_week else 0
        weekly_under_val = safe_solver_value(weekly_under[(a, wk)]) if "weekly_under" in globals() and (a, wk) in weekly_under else 0
        weekly_over_val = safe_solver_value(weekly_over[(a, wk)]) if "weekly_over" in globals() and (a, wk) in weekly_over else 0

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


# -------------------------------------------------
# 8) Mesai özeti
# -------------------------------------------------

mesai_rows = []

for a in AGENTS:
    a = normalize_agent(a)
    info = agent_info_map.get(a, {})

    normal_mesai_count = sum(
        safe_solver_value(overtime_week[(a, wk)])
        for wk in WEEKS
        if (a, wk) in overtime_week
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


# -------------------------------------------------
# 9) Özel gün çalışanları
# -------------------------------------------------

special_day_df = agent_day_plan_df[
    agent_day_plan_df["is_ozel_gun"] == True
].copy()

special_day_df = special_day_df[
    (special_day_df["assigned"] == 1) |
    (special_day_df["is_leave"] == True)
].sort_values(["date", "status", "takim", "agent_user_code"])


# -------------------------------------------------
# 10) Resmi tatil ihlal sheet
# -------------------------------------------------

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


# -------------------------------------------------
# 11) Takım bölünme kontrol
# Özel günleri hafta içi takım kontrolünden hariç tutuyoruz.
# -------------------------------------------------

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
            "gun": pd.to_datetime(ds).day_name(),
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


# -------------------------------------------------
# 12) Hafta sonu OFF kontrol
# -------------------------------------------------

weekend_off_rows = []

weekend_pairs_final = []
plan_dates = sorted([pd.to_datetime(ds).date() for ds in PLAN_GUNLER])
date_to_ds = {pd.to_datetime(ds).date(): ds for ds in PLAN_GUNLER}

for d in plan_dates:
    if d.weekday() == 5:
        sunday = d + pd.Timedelta(days=1)
        if sunday in date_to_ds:
            weekend_pairs_final.append((date_to_ds[d], date_to_ds[sunday]))

for a in AGENTS:
    a = normalize_agent(a)
    info = agent_info_map.get(a, {})

    pair_off_count = 0

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs_final):
        sat_work = safe_solver_value(work[(a, sat_ds)]) if (a, sat_ds) in work else 0
        sun_work = safe_solver_value(work[(a, sun_ds)]) if (a, sun_ds) in work else 0

        pair_off = 1 if sat_work == 0 and sun_work == 0 else 0
        pair_off_count += pair_off

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

weekend_off_summary_df = (
    weekend_off_df
    .groupby(["agent_user_code", "agent_name", "takim", "teamleader_name"], as_index=False)
    .agg(pair_off_count=("pair_off", "sum"))
)

weekend_off_summary_df["en_az_1_pair_off_ok"] = weekend_off_summary_df["pair_off_count"] >= 1


# -------------------------------------------------
# 13) Agent aylık özet
# -------------------------------------------------

agent_monthly_df = (
    agent_day_plan_df
    .groupby(["agent_user_code", "agent_name", "takim", "teamleader_name"], as_index=False)
    .agg(
        total_assigned_days=("assigned", "sum"),
        izin_days=("is_leave", "sum"),
        arife_days=("is_arife", "sum"),
        resmi_tatil_days=("is_resmi_tatil", "sum"),
    )
)

status_counts = (
    agent_day_plan_df
    .pivot_table(
        index=["agent_user_code"],
        columns="status",
        values="date",
        aggfunc="count",
        fill_value=0
    )
    .reset_index()
)

agent_monthly_df = agent_monthly_df.merge(status_counts, on="agent_user_code", how="left")
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
    how="left"
)


# -------------------------------------------------
# 14) Vardiya bazlı özet
# -------------------------------------------------

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
        satir_sayisi=("date", "count")
    )
    .sort_values(["shift_start", "shift_end", "shift"])
)


# -------------------------------------------------
# 15) Özet sheet
# -------------------------------------------------

summary_rows = [
    {"metric": "Agent sayısı", "value": len(AGENTS)},
    {"metric": "Plan gün sayısı", "value": len(PLAN_GUNLER)},
    {"metric": "Vardiya satır sayısı", "value": len(coverage_gap_df)},
    {"metric": "Toplam talep", "value": coverage_gap_df["required"].sum()},
    {"metric": "Toplam atanan", "value": coverage_gap_df["assigned"].sum()},
    {"metric": "Toplam gap_to_required", "value": coverage_gap_df["gap_to_required"].sum()},
    {"metric": "Toplam under_buffer", "value": coverage_gap_df["under_buffer"].sum()},
    {"metric": "Toplam missing_to_required", "value": coverage_gap_df["missing_to_required"].sum()},
    {"metric": "Toplam over_buffer", "value": coverage_gap_df["over_buffer"].sum()},
    {"metric": "Toplam excess_to_required", "value": coverage_gap_df["excess_to_required"].sum()},
    {"metric": "Hiç atanmayan talep vardiyası", "value": coverage_gap_df[(coverage_gap_df["required"] > 0) & (coverage_gap_df["assigned"] == 0)].shape[0]},
    {"metric": "Weekly under toplam", "value": weekly_target_check_df["weekly_under"].sum()},
    {"metric": "Weekly over toplam", "value": weekly_target_check_df["weekly_over"].sum()},
    {"metric": "Normal mesai toplam", "value": mesai_summary_df["normal_mesai_count"].sum()},
    {"metric": "Arife mesai toplam", "value": mesai_summary_df["arife_mesai_count"].sum()},
    {"metric": "Resmi tatil mesai toplam", "value": mesai_summary_df["resmi_tatil_mesai_count"].sum()},
    {"metric": "Resmi tatil kısıtlı ihlal toplam", "value": mesai_summary_df["resmi_tatil_kisitli_ihlal_count"].sum()},
    {"metric": "Özel gün hariç hafta içi bölünen takım-gün", "value": len(weekday_team_viol_df)},
    {"metric": "Hafta sonu bölünen takım-gün", "value": len(weekend_team_split_df)},
    {"metric": "Özel gün bölünen takım-gün", "value": len(special_team_split_df)},
]

summary_df = pd.DataFrame(summary_rows)


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


# -------------------------------------------------
# 16) Excel yazımı
# -------------------------------------------------

output_file = f"vardiya_plani_kapsamli_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:

    summary_df.to_excel(writer, sheet_name="00_Ozet", index=False)
    agent_day_plan_df.to_excel(writer, sheet_name="01_Agent_Gunluk_Plan", index=False)
    calendar_shift_df.to_excel(writer, sheet_name="02_Takvim_Vardiya", index=False)
    calendar_df.to_excel(writer, sheet_name="03_Takvim_Status", index=False)
    coverage_gap_df.to_excel(writer, sheet_name="04_Coverage_Kontrol", index=False)
    weekly_target_check_df.to_excel(writer, sheet_name="05_Haftalik_Hedef", index=False)
    mesai_summary_df.to_excel(writer, sheet_name="06_Mesai_Ozet", index=False)
    special_day_df.to_excel(writer, sheet_name="07_Ozel_Gun_Calisan", index=False)
    resmi_tatil_ihlal_df.to_excel(writer, sheet_name="08_Resmi_Tatil_Ihlal", index=False)
    weekday_team_viol_df.to_excel(writer, sheet_name="09_Takim_Bolunme_HI", index=False)
    weekend_team_split_df.to_excel(writer, sheet_name="10_Takim_Bolunme_HS", index=False)
    special_team_split_df.to_excel(writer, sheet_name="11_Takim_Bolunme_Ozel", index=False)
    weekend_off_summary_df.to_excel(writer, sheet_name="12_Weekend_OFF_Ozet", index=False)
    weekend_off_df.to_excel(writer, sheet_name="13_Weekend_OFF_Detay", index=False)
    agent_monthly_df.to_excel(writer, sheet_name="14_Agent_Aylik_Ozet", index=False)
    shift_summary_df.to_excel(writer, sheet_name="15_Vardiya_Ozet", index=False)
    debug_params_df.to_excel(writer, sheet_name="16_Parametreler", index=False)

    workbook = writer.book

    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#1F4E78",
        "font_color": "white",
        "border": 1,
        "align": "center",
        "valign": "vcenter"
    })

    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
    warning_format = workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
    good_format = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
    special_format = workbook.add_format({"bg_color": "#FFEB9C", "font_color": "#9C6500"})
    izin_format = workbook.add_format({"bg_color": "#D9EAD3", "font_color": "#274E13"})
    off_format = workbook.add_format({"bg_color": "#E7E6E6", "font_color": "#666666"})
    mesai_format = workbook.add_format({"bg_color": "#F4CCCC", "font_color": "#990000"})
    arife_format = workbook.add_format({"bg_color": "#D9EAD3", "font_color": "#274E13"})
    resmi_tatil_format = workbook.add_format({"bg_color": "#CFE2F3", "font_color": "#073763"})

    for sheet_name, worksheet in writer.sheets.items():
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, 0, 50)

        # Header format
        try:
            max_col = worksheet.dim_colmax
            for col_num in range(max_col + 1):
                worksheet.write(0, col_num, worksheet.table[0][col_num].string if hasattr(worksheet, "table") else None, header_format)
        except Exception:
            pass

        # Kolon genişlikleri
        worksheet.set_column(0, 0, 16)
        worksheet.set_column(1, 5, 18)
        worksheet.set_column(6, 20, 14)
        worksheet.set_column(21, 60, 16)

    # Sheet özel conditional formatting
    ws_cov = writer.sheets["04_Coverage_Kontrol"]
    cov_rows = len(coverage_gap_df) + 1
    cov_cols = len(coverage_gap_df.columns)

    if "gap_to_lower" in coverage_gap_df.columns:
        col_idx = coverage_gap_df.columns.get_loc("gap_to_lower")
        ws_cov.conditional_format(1, col_idx, cov_rows, col_idx, {
            "type": "cell",
            "criteria": "<",
            "value": 0,
            "format": warning_format
        })

    if "buffer_ici" in coverage_gap_df.columns:
        col_idx = coverage_gap_df.columns.get_loc("buffer_ici")
        ws_cov.conditional_format(1, col_idx, cov_rows, col_idx, {
            "type": "text",
            "criteria": "containing",
            "value": "False",
            "format": warning_format
        })

    ws_week = writer.sheets["05_Haftalik_Hedef"]
    week_rows = len(weekly_target_check_df) + 1

    if "weekly_under" in weekly_target_check_df.columns:
        col_idx = weekly_target_check_df.columns.get_loc("weekly_under")
        ws_week.conditional_format(1, col_idx, week_rows, col_idx, {
            "type": "cell",
            "criteria": ">",
            "value": 0,
            "format": warning_format
        })

    if "weekly_over" in weekly_target_check_df.columns:
        col_idx = weekly_target_check_df.columns.get_loc("weekly_over")
        ws_week.conditional_format(1, col_idx, week_rows, col_idx, {
            "type": "cell",
            "criteria": ">",
            "value": 0,
            "format": special_format
        })

    # Takvim status renklendirme
    for sheet_name in ["02_Takvim_Vardiya", "03_Takvim_Status"]:
        ws = writer.sheets[sheet_name]
        max_rows = len(calendar_shift_df) + 1 if sheet_name == "02_Takvim_Vardiya" else len(calendar_df) + 1
        max_cols = len(calendar_shift_df.columns) if sheet_name == "02_Takvim_Vardiya" else len(calendar_df.columns)

        ws.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "İZİN",
            "format": izin_format
        })

        ws.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "OFF",
            "format": off_format
        })

        ws.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "MESAI",
            "format": mesai_format
        })

        ws.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "ARIFE_09_13",
            "format": arife_format
        })

        ws.conditional_format(1, 4, max_rows, max_cols, {
            "type": "text",
            "criteria": "containing",
            "value": "RESMI_TATIL",
            "format": resmi_tatil_format
        })

    # Özel gün sheet format
    ws_special = writer.sheets["07_Ozel_Gun_Calisan"]
    special_rows = len(special_day_df) + 1

    if "status" in special_day_df.columns:
        col_idx = special_day_df.columns.get_loc("status")
        ws_special.conditional_format(1, col_idx, special_rows, col_idx, {
            "type": "text",
            "criteria": "containing",
            "value": "MESAI",
            "format": mesai_format
        })
        ws_special.conditional_format(1, col_idx, special_rows, col_idx, {
            "type": "text",
            "criteria": "containing",
            "value": "IHLAL",
            "format": warning_format
        })

    # Özet sheet biraz daha okunaklı olsun
    ws_summary = writer.sheets["00_Ozet"]
    ws_summary.set_column(0, 0, 42)
    ws_summary.set_column(1, 1, 20)

print("Excel oluşturuldu:", os.path.abspath(output_file))