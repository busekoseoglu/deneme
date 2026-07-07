# %% [KONTROL 0] ORTAK HELPERLAR

import pandas as pd
import numpy as np

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

def agent_izinli_mi_kontrol(a, ds):
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

def print_check(name, df):
    print("=" * 80)
    print(name)
    print("İhlal sayısı:", len(df))
    print("=" * 80)
    if len(df) > 0:
        display(df)


# %% [KONTROL 1] COVERAGE - REQUIRED / ASSIGNED / GAP

coverage_check_rows = []

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

        start, end = get_shift_time(ds, v)
        weekday = pd.to_datetime(ds).weekday()

        coverage_check_rows.append({
            "date": ds_key(ds),
            "week": day_week.get(ds) if "day_week" in globals() else None,
            "gun": safe_day_name(ds),
            "weekday": weekday,
            "is_weekend": weekday in [5, 6],
            "shift": v,
            "shift_start": start,
            "shift_end": end,
            "required": required,
            "assigned": assigned,
            "gap": assigned - required,
            "is_arife": ds in arife_plan_gunleri if "arife_plan_gunleri" in globals() else False,
            "is_resmi_tatil": ds in resmi_tatil_plan_gunleri if "resmi_tatil_plan_gunleri" in globals() else False,
            "is_ozel_gun": ds in ozel_tatil_plan_gunleri if "ozel_tatil_plan_gunleri" in globals() else False,
        })

coverage_check_df = pd.DataFrame(coverage_check_rows)

coverage_gap_negative_df = coverage_check_df[coverage_check_df["gap"] < 0].copy()
coverage_zero_assigned_df = coverage_check_df[
    (coverage_check_df["required"] > 0) &
    (coverage_check_df["assigned"] == 0)
].copy()

print("Toplam required:", coverage_check_df["required"].sum())
print("Toplam assigned:", coverage_check_df["assigned"].sum())
print("Toplam gap:", coverage_check_df["gap"].sum())
print("Negatif gap satır sayısı:", len(coverage_gap_negative_df))
print("Required > 0 ama assigned = 0 satır sayısı:", len(coverage_zero_assigned_df))

display(
    coverage_check_df
    .sort_values("gap")
    .head(50)
)


# %% [KONTROL 2] AGENT GÜNDE MAKSIMUM 1 VARDİYA

one_shift_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    for ds in PLAN_GUNLER:
        assigned_shifts = []

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                assigned_shifts.append(v)

        if len(assigned_shifts) > 1:
            one_shift_rows.append({
                "agent_user_code": a,
                "date": ds_key(ds),
                "assigned_shift_count": len(assigned_shifts),
                "assigned_shifts": ", ".join(assigned_shifts),
            })

one_shift_violation_df = pd.DataFrame(one_shift_rows)

print_check(
    "Günde maksimum 1 vardiya ihlali",
    one_shift_violation_df
)


# %% [KONTROL 3] İZİNLİ GÜNDE ÇALIŞMA VAR MI?

izin_work_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    for ds in PLAN_GUNLER:
        if not agent_izinli_mi_kontrol(a, ds):
            continue

        assigned_shifts = []

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                assigned_shifts.append(v)

        if len(assigned_shifts) > 0:
            izin_work_rows.append({
                "agent_user_code": a,
                "date": ds_key(ds),
                "assigned_shift_count": len(assigned_shifts),
                "assigned_shifts": ", ".join(assigned_shifts),
            })

izin_work_violation_df = pd.DataFrame(izin_work_rows)

print_check(
    "İzinli günde çalışma ihlali",
    izin_work_violation_df
)


# %% [KONTROL 4] HAFTALIK ÇALIŞMA DENKLEMİ

resmi_tatil_days_set = set(resmi_tatil_plan_gunleri) if "resmi_tatil_plan_gunleri" in globals() else set()

weekly_equation_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    for wk, days_in_week in week_days.items():

        resmi_tatil_days_this_week = set(
            ds for ds in days_in_week
            if ds in resmi_tatil_days_set
        )

        izin_days_this_week = set(
            ds for ds in days_in_week
            if agent_izinli_mi_kontrol(a, ds)
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

        overtime_val = (
            safe_solver_value(overtime_week[(a, wk)])
            if "overtime_week" in globals() and (a, wk) in overtime_week
            else 0
        )

        under_val = (
            safe_solver_value(weekly_under[(a, wk)])
            if "weekly_under" in globals() and (a, wk) in weekly_under
            else 0
        )

        over_val = (
            safe_solver_value(weekly_over[(a, wk)])
            if "weekly_over" in globals() and (a, wk) in weekly_over
            else 0
        )

        lhs = normal_worked_days + under_val - over_val
        rhs = normal_target + overtime_val

        weekly_equation_rows.append({
            "agent_user_code": a,
            "week": wk,
            "week_day_count": len(days_in_week),
            "normal_target": normal_target,
            "normal_worked_days": normal_worked_days,
            "overtime_week": overtime_val,
            "weekly_under": under_val,
            "weekly_over": over_val,
            "lhs": lhs,
            "rhs": rhs,
            "equation_ok": lhs == rhs,
            "izin_count": len(izin_days_this_week),
            "izin_normal_count": len(izin_normal_days_this_week),
            "resmi_tatil_count": len(resmi_tatil_days_this_week),
        })

weekly_equation_check_df = pd.DataFrame(weekly_equation_rows)

weekly_equation_violation_df = weekly_equation_check_df[
    weekly_equation_check_df["equation_ok"] == False
].copy()

print_check(
    "Haftalık çalışma denklem ihlali",
    weekly_equation_violation_df
)

print("Weekly under toplam:", weekly_equation_check_df["weekly_under"].sum())
print("Weekly over toplam:", weekly_equation_check_df["weekly_over"].sum())

display(
    weekly_equation_check_df[
        (weekly_equation_check_df["weekly_under"] > 0) |
        (weekly_equation_check_df["weekly_over"] > 0)
    ].sort_values(["week", "weekly_under"], ascending=[True, False]).head(100)
)


# %% [KONTROL 5] AYLIK NORMAL MESAİ MAX 2

monthly_overtime_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    normal_overtime_count = sum(
        safe_solver_value(overtime_week[(a, wk)])
        for wk in WEEKS
        if (a, wk) in overtime_week
    )

    if normal_overtime_count > MAX_OVERTIME_PER_MONTH:
        monthly_overtime_rows.append({
            "agent_user_code": a,
            "normal_overtime_count": normal_overtime_count,
            "max_allowed": MAX_OVERTIME_PER_MONTH,
        })

monthly_overtime_violation_df = pd.DataFrame(monthly_overtime_rows)

print_check(
    "Aylık normal mesai max limit ihlali",
    monthly_overtime_violation_df
)


# %% [KONTROL 6] HAFTADA MAKSIMUM 1 NORMAL MESAİ

weekly_overtime_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    for wk in WEEKS:
        if (a, wk) not in overtime_week:
            continue

        overtime_val = safe_solver_value(overtime_week[(a, wk)])

        if overtime_val > 1:
            weekly_overtime_rows.append({
                "agent_user_code": a,
                "week": wk,
                "overtime_week": overtime_val,
            })

weekly_overtime_violation_df = pd.DataFrame(weekly_overtime_rows)

print_check(
    "Haftada maksimum 1 normal mesai ihlali",
    weekly_overtime_violation_df
)


# %% [KONTROL 7] RESMİ TATİL MESAİSİ NORMAL MESAİDEN AYRI MI?

resmi_tatil_days_set = set(resmi_tatil_plan_gunleri) if "resmi_tatil_plan_gunleri" in globals() else set()

resmi_tatil_work_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    for ds in resmi_tatil_days_set:
        if (a, ds) in work and safe_solver_value(work[(a, ds)]) == 1:
            wk = day_week.get(ds)

            overtime_val = (
                safe_solver_value(overtime_week[(a, wk)])
                if wk is not None and (a, wk) in overtime_week
                else 0
            )

            assigned_shift = None
            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                    assigned_shift = v
                    break

            resmi_tatil_work_rows.append({
                "agent_user_code": a,
                "date": ds_key(ds),
                "week": wk,
                "assigned_shift": assigned_shift,
                "resmi_tatil_work": 1,
                "normal_overtime_week_value": overtime_val,
                "not": "Resmi tatil mesaisi ayrı sayılır. overtime_week aynı hafta başka normal mesai varsa 1 olabilir.",
            })

resmi_tatil_work_check_df = pd.DataFrame(resmi_tatil_work_rows)

print("Resmi tatilde çalışan kişi-gün sayısı:", len(resmi_tatil_work_check_df))
display(resmi_tatil_work_check_df.head(100))


# %% [KONTROL 8] MAX 6 GÜN ÜST ÜSTE ÇALIŞMA

max_consecutive_rows = []

plan_days_sorted = sorted(PLAN_GUNLER, key=lambda d: pd.to_datetime(d))

for a in AGENTS:
    a = normalize_agent(a)

    for i in range(len(plan_days_sorted) - 6):
        window_days = plan_days_sorted[i:i+7]

        worked_count = sum(
            safe_solver_value(work[(a, ds)])
            for ds in window_days
            if (a, ds) in work
        )

        if worked_count > 6:
            max_consecutive_rows.append({
                "agent_user_code": a,
                "window_start": ds_key(window_days[0]),
                "window_end": ds_key(window_days[-1]),
                "worked_count_in_7_days": worked_count,
                "window_days": ", ".join(ds_key(d) for d in window_days),
            })

max_consecutive_violation_df = pd.DataFrame(max_consecutive_rows)

print_check(
    "7 günlük pencerede 6 günden fazla çalışma ihlali",
    max_consecutive_violation_df
)


# %% [KONTROL 9] 11 SAAT DİNLENME KONTROLÜ

from datetime import datetime, timedelta

def shift_datetime_start_end(ds, v):
    start_str, end_str = get_shift_time(ds, v)

    if start_str is None or end_str is None:
        return None, None

    base_date = pd.to_datetime(ds).date()

    start_dt = pd.to_datetime(str(base_date) + " " + str(start_str))
    end_dt = pd.to_datetime(str(base_date) + " " + str(end_str))

    # gece devreden vardiya
    if end_dt <= start_dt:
        end_dt = end_dt + pd.Timedelta(days=1)

    return start_dt, end_dt

rest_rows = []

plan_days_sorted = sorted(PLAN_GUNLER, key=lambda d: pd.to_datetime(d))

for a in AGENTS:
    a = normalize_agent(a)

    assigned_list = []

    for ds in plan_days_sorted:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                start_dt, end_dt = shift_datetime_start_end(ds, v)
                if start_dt is not None:
                    assigned_list.append({
                        "date": ds,
                        "shift": v,
                        "start_dt": start_dt,
                        "end_dt": end_dt,
                    })

    assigned_list = sorted(assigned_list, key=lambda r: r["start_dt"])

    for i in range(len(assigned_list) - 1):
        current_shift = assigned_list[i]
        next_shift = assigned_list[i + 1]

        rest_hours = (
            next_shift["start_dt"] - current_shift["end_dt"]
        ).total_seconds() / 3600

        if rest_hours < MIN_REST_HOURS:
            rest_rows.append({
                "agent_user_code": a,
                "first_date": ds_key(current_shift["date"]),
                "first_shift": current_shift["shift"],
                "first_end": current_shift["end_dt"],
                "second_date": ds_key(next_shift["date"]),
                "second_shift": next_shift["shift"],
                "second_start": next_shift["start_dt"],
                "rest_hours": rest_hours,
                "min_required": MIN_REST_HOURS,
            })

rest_violation_df = pd.DataFrame(rest_rows)

print_check(
    "11 saat dinlenme ihlali",
    rest_violation_df
)



# %% [KONTROL 10] AYDA EN AZ 1 CUMARTESİ-PAZAR PEŞ PEŞE OFF

weekend_pairs = []

plan_dates = sorted([pd.to_datetime(ds).date() for ds in PLAN_GUNLER])
date_to_ds = {pd.to_datetime(ds).date(): ds for ds in PLAN_GUNLER}

for d in plan_dates:
    if d.weekday() == 5:
        sunday = d + pd.Timedelta(days=1)
        if sunday in date_to_ds:
            weekend_pairs.append((date_to_ds[d], date_to_ds[sunday]))

weekend_off_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    pair_off_count = 0
    pair_details = []

    for sat_ds, sun_ds in weekend_pairs:
        sat_work = safe_solver_value(work[(a, sat_ds)]) if (a, sat_ds) in work else 0
        sun_work = safe_solver_value(work[(a, sun_ds)]) if (a, sun_ds) in work else 0

        pair_off = sat_work == 0 and sun_work == 0

        if pair_off:
            pair_off_count += 1

        pair_details.append(
            f"{ds_key(sat_ds)}-{ds_key(sun_ds)} off={pair_off}"
        )

    if pair_off_count < 1:
        weekend_off_rows.append({
            "agent_user_code": a,
            "pair_off_count": pair_off_count,
            "weekend_pair_details": " | ".join(pair_details),
        })

weekend_off_violation_df = pd.DataFrame(weekend_off_rows)

print_check(
    "Ayda en az 1 Cumartesi-Pazar peş peşe OFF ihlali",
    weekend_off_violation_df
)



# %% [KONTROL 11] HAMİLE / SÜT İZNİ HAFTA SONU ÇALIŞAMAZ

agent_flags = df_tam.copy()
agent_flags["agent_user_code"] = agent_flags["agent_user_code"].astype(str).str.strip()
agent_flags = agent_flags.drop_duplicates("agent_user_code").set_index("agent_user_code")

weekend_restricted_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    hamile = int(agent_flags.loc[a, "hamile_flg"]) if a in agent_flags.index and "hamile_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "hamile_flg"]) else 0
    sut = int(agent_flags.loc[a, "sut_izni_flg"]) if a in agent_flags.index and "sut_izni_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "sut_izni_flg"]) else 0

    if hamile != 1 and sut != 1:
        continue

    for ds in PLAN_GUNLER:
        weekday = pd.to_datetime(ds).weekday()

        if weekday not in [5, 6]:
            continue

        worked_val = safe_solver_value(work[(a, ds)]) if (a, ds) in work else 0

        if worked_val == 1:
            weekend_restricted_rows.append({
                "agent_user_code": a,
                "date": ds_key(ds),
                "gun": safe_day_name(ds),
                "hamile_flg": hamile,
                "sut_izni_flg": sut,
                "worked": worked_val,
            })

weekend_restricted_violation_df = pd.DataFrame(weekend_restricted_rows)

print_check(
    "Hamile / süt izni hafta sonu çalışma ihlali",
    weekend_restricted_violation_df
)



# %% [KONTROL 12] SABAH ÇALIŞIR AGENT 20:00 SONRASI ÇALIŞAMAZ

sabah_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    sabah_flag = int(agent_flags.loc[a, "sabah_calisir_flg"]) if a in agent_flags.index and "sabah_calisir_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "sabah_calisir_flg"]) else 0

    if sabah_flag != 1:
        continue

    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            if safe_solver_value(x[(a, ds, v)]) != 1:
                continue

            start_str, end_str = get_shift_time(ds, v)

            if end_str is None:
                continue

            end_hour = int(str(end_str).split(":")[0])
            end_minute = int(str(end_str).split(":")[1])

            # 00:00, 01:00, 02:00 gibi bitenler gece devri olduğu için 20 sonrası sayılır
            ends_after_20 = (
                end_hour > 20
                or (end_hour == 20 and end_minute > 0)
                or end_hour in [0, 1, 2, 3, 4, 5, 6]
            )

            if ends_after_20:
                sabah_rows.append({
                    "agent_user_code": a,
                    "date": ds_key(ds),
                    "shift": v,
                    "shift_start": start_str,
                    "shift_end": end_str,
                    "sabah_calisir_flg": sabah_flag,
                })

sabah_violation_df = pd.DataFrame(sabah_rows)

print_check(
    "Sabah çalışır flag'i olan agent 20:00 sonrası çalışma ihlali",
    sabah_violation_df
)



# %% [KONTROL 13] GECE / AKŞAM VARDİYASI AYDA MAX 2 HAFTA

gece_aksam_shift_times = {
    ("17:00", "01:00"),
    ("18:00", "02:00"),
    ("00:00", "08:00"),
}

gece_aksam_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    weeks_with_gece_aksam = set()
    detail_list = []

    for ds in PLAN_GUNLER:
        wk = day_week.get(ds) if "day_week" in globals() else None

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            if safe_solver_value(x[(a, ds, v)]) != 1:
                continue

            start_str, end_str = get_shift_time(ds, v)

            if (start_str, end_str) in gece_aksam_shift_times:
                weeks_with_gece_aksam.add(wk)
                detail_list.append(f"{ds_key(ds)} {v} {start_str}-{end_str}")

    if len(weeks_with_gece_aksam) > 2:
        gece_aksam_rows.append({
            "agent_user_code": a,
            "gece_aksam_week_count": len(weeks_with_gece_aksam),
            "weeks": ", ".join(sorted([str(w) for w in weeks_with_gece_aksam])),
            "details": " | ".join(detail_list),
        })

gece_aksam_violation_df = pd.DataFrame(gece_aksam_rows)

print_check(
    "Gece / akşam vardiyası ayda max 2 hafta ihlali",
    gece_aksam_violation_df
)



# %% [KONTROL 13] GECE / AKŞAM VARDİYASI AYDA MAX 2 HAFTA

gece_aksam_shift_times = {
    ("17:00", "01:00"),
    ("18:00", "02:00"),
    ("00:00", "08:00"),
}

gece_aksam_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    weeks_with_gece_aksam = set()
    detail_list = []

    for ds in PLAN_GUNLER:
        wk = day_week.get(ds) if "day_week" in globals() else None

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            if safe_solver_value(x[(a, ds, v)]) != 1:
                continue

            start_str, end_str = get_shift_time(ds, v)

            if (start_str, end_str) in gece_aksam_shift_times:
                weeks_with_gece_aksam.add(wk)
                detail_list.append(f"{ds_key(ds)} {v} {start_str}-{end_str}")

    if len(weeks_with_gece_aksam) > 2:
        gece_aksam_rows.append({
            "agent_user_code": a,
            "gece_aksam_week_count": len(weeks_with_gece_aksam),
            "weeks": ", ".join(sorted([str(w) for w in weeks_with_gece_aksam])),
            "details": " | ".join(detail_list),
        })

gece_aksam_violation_df = pd.DataFrame(gece_aksam_rows)

print_check(
    "Gece / akşam vardiyası ayda max 2 hafta ihlali",
    gece_aksam_violation_df
)



# %% [KONTROL 14] TAKIM HAFTA İÇİ AYNI VARDİYADA MI?

ozel_tatil_days_set = set(ozel_tatil_plan_gunleri) if "ozel_tatil_plan_gunleri" in globals() else set()

team_weekday_rows = []

for ds in PLAN_GUNLER:

    weekday = pd.to_datetime(ds).weekday()

    # sadece normal hafta içi
    if weekday not in [0, 1, 2, 3, 4]:
        continue

    # arife/resmi tatil gibi özel günleri hariç tutuyoruz
    if ds in ozel_tatil_days_set:
        continue

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

        if len(set(assigned_shifts)) > 1:
            team_weekday_rows.append({
                "date": ds_key(ds),
                "week": day_week.get(ds) if "day_week" in globals() else None,
                "gun": safe_day_name(ds),
                "takim": t,
                "calisan_agent": len(assigned_shifts),
                "vardiya_sayisi": len(set(assigned_shifts)),
                "vardiyalar": ", ".join(sorted(set(assigned_shifts))),
            })

team_weekday_violation_df = pd.DataFrame(team_weekday_rows)

print_check(
    "Özel gün hariç hafta içi takım bölünme ihlali",
    team_weekday_violation_df
)



# %% [KONTROL 15] TAKIM BASE VARDİYA UYUM KONTROLÜ

team_base_assignment_rows = []

for ds in PLAN_GUNLER:

    weekday = pd.to_datetime(ds).weekday()

    if weekday not in [0, 1, 2, 3, 4]:
        continue

    if ds in ozel_tatil_days_set:
        continue

    wk = day_week.get(ds)

    for a in AGENTS:
        a = normalize_agent(a)
        t = str(agent_team.get(a, "")).strip()

        if not t:
            continue

        selected_team_base = []

        if "team_week_base" in globals():
            for v in gun_vardiyalari.get(ds, []):
                if (t, wk, v) in team_week_base and safe_solver_value(team_week_base[(t, wk, v)]) == 1:
                    selected_team_base.append(v)

        assigned_shift = None

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                assigned_shift = v
                break

        if assigned_shift is None:
            continue

        if assigned_shift not in selected_team_base:
            team_base_assignment_rows.append({
                "agent_user_code": a,
                "takim": t,
                "date": ds_key(ds),
                "week": wk,
                "assigned_shift": assigned_shift,
                "team_base_shift": ", ".join(selected_team_base),
            })

team_base_assignment_violation_df = pd.DataFrame(team_base_assignment_rows)

print_check(
    "Agent ataması takım base vardiyası dışında mı?",
    team_base_assignment_violation_df
)



# %% [KONTROL 16] TAKIM BASE KAPASİTE GUARD KONTROLÜ

team_size_map = (
    df_tam
    .assign(takim=df_tam["takim"].astype(str).str.strip())
    .groupby("takim")["agent_user_code"]
    .nunique()
    .to_dict()
)

team_base_capacity_check_rows = []

for wk in WEEKS:

    normal_weekdays = []

    for ds in week_days[wk]:
        if ds in ozel_tatil_days_set:
            continue

        if pd.to_datetime(ds).weekday() in [0, 1, 2, 3, 4]:
            normal_weekdays.append(ds)

    if not normal_weekdays:
        continue

    vardiyalar_this_week = sorted(
        set(
            v
            for ds in normal_weekdays
            for v in gun_vardiyalari.get(ds, [])
            if (ds, v) in talep
        )
    )

    for v in vardiyalar_this_week:

        max_required = max(
            int(talep[(ds, v)])
            for ds in normal_weekdays
            if (ds, v) in talep
        )

        selected_capacity = 0
        selected_teams = []

        for t in TAKIMLAR:
            t = str(t).strip()

            if "team_week_base" in globals() and (t, wk, v) in team_week_base:
                if safe_solver_value(team_week_base[(t, wk, v)]) == 1:
                    selected_capacity += int(team_size_map.get(t, 0))
                    selected_teams.append(t)

        if selected_capacity < max_required:
            team_base_capacity_check_rows.append({
                "week": wk,
                "shift": v,
                "max_required_in_week": max_required,
                "selected_team_capacity": selected_capacity,
                "selected_teams": ", ".join(selected_teams),
                "gap": selected_capacity - max_required,
            })

team_base_capacity_violation_df = pd.DataFrame(team_base_capacity_check_rows)

print_check(
    "Takım base kapasite guard ihlali",
    team_base_capacity_violation_df
)



# %% [KONTROL 17] ARİFE ÖZEL VARDİYA KONTROLÜ

arife_days_set = set(arife_plan_gunleri) if "arife_plan_gunleri" in globals() else set()
arife_special_set = set(arife_ozel_vardiya_kodlari) if "arife_ozel_vardiya_kodlari" in globals() else {"ARIFE_09_13"}

arife_rows = []

for ds in arife_days_set:

    for a in AGENTS:
        a = normalize_agent(a)

        if agent_izinli_mi_kontrol(a, ds):
            continue

        hamile = int(agent_flags.loc[a, "hamile_flg"]) if a in agent_flags.index and "hamile_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "hamile_flg"]) else 0
        sut = int(agent_flags.loc[a, "sut_izni_flg"]) if a in agent_flags.index and "sut_izni_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "sut_izni_flg"]) else 0
        mesaiye_kalamaz = int(agent_flags.loc[a, "mesaiye_kalamaz_flg"]) if a in agent_flags.index and "mesaiye_kalamaz_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "mesaiye_kalamaz_flg"]) else 0

        kisitli = hamile == 1 or sut == 1 or mesaiye_kalamaz == 1

        assigned_shift = None

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                assigned_shift = v
                break

        # kısıtlı agent arife özel vardiyaya gitmeli
        if kisitli and assigned_shift not in arife_special_set:
            arife_rows.append({
                "agent_user_code": a,
                "date": ds_key(ds),
                "issue": "Kısıtlı agent arife özel vardiyada değil",
                "assigned_shift": assigned_shift,
                "hamile_flg": hamile,
                "sut_izni_flg": sut,
                "mesaiye_kalamaz_flg": mesaiye_kalamaz,
            })

        # kısıtlı olmayan agent arife özel vardiya almamalı
        if (not kisitli) and assigned_shift in arife_special_set:
            arife_rows.append({
                "agent_user_code": a,
                "date": ds_key(ds),
                "issue": "Kısıtlı olmayan agent ARIFE_09_13 almış",
                "assigned_shift": assigned_shift,
                "hamile_flg": hamile,
                "sut_izni_flg": sut,
                "mesaiye_kalamaz_flg": mesaiye_kalamaz,
            })

arife_special_violation_df = pd.DataFrame(arife_rows)

print_check(
    "Arife özel vardiya kural ihlali",
    arife_special_violation_df
)



# %% [KONTROL 18] ARİFE KISITLI AGENT 13:00 SONRASI ÇALIŞAMAZ

arife_after_13_rows = []

for ds in arife_days_set:

    for a in AGENTS:
        a = normalize_agent(a)

        hamile = int(agent_flags.loc[a, "hamile_flg"]) if a in agent_flags.index and "hamile_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "hamile_flg"]) else 0
        sut = int(agent_flags.loc[a, "sut_izni_flg"]) if a in agent_flags.index and "sut_izni_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "sut_izni_flg"]) else 0
        mesaiye_kalamaz = int(agent_flags.loc[a, "mesaiye_kalamaz_flg"]) if a in agent_flags.index and "mesaiye_kalamaz_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "mesaiye_kalamaz_flg"]) else 0

        kisitli = hamile == 1 or sut == 1 or mesaiye_kalamaz == 1

        if not kisitli:
            continue

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            if safe_solver_value(x[(a, ds, v)]) != 1:
                continue

            start_str, end_str = get_shift_time(ds, v)

            if end_str is None:
                continue

            end_hour = int(str(end_str).split(":")[0])
            end_min = int(str(end_str).split(":")[1])

            ends_after_13 = end_hour > 13 or (end_hour == 13 and end_min > 0)

            if ends_after_13:
                arife_after_13_rows.append({
                    "agent_user_code": a,
                    "date": ds_key(ds),
                    "shift": v,
                    "shift_start": start_str,
                    "shift_end": end_str,
                    "hamile_flg": hamile,
                    "sut_izni_flg": sut,
                    "mesaiye_kalamaz_flg": mesaiye_kalamaz,
                })

arife_after_13_violation_df = pd.DataFrame(arife_after_13_rows)

print_check(
    "Arife kısıtlı agent 13:00 sonrası çalışma ihlali",
    arife_after_13_violation_df
)



# %% [KONTROL 19] RESMİ TATİLDE KISITLI AGENT ÇALIŞAMAZ

resmi_tatil_kisitli_rows = []

for ds in resmi_tatil_days_set:

    for a in AGENTS:
        a = normalize_agent(a)

        hamile = int(agent_flags.loc[a, "hamile_flg"]) if a in agent_flags.index and "hamile_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "hamile_flg"]) else 0
        sut = int(agent_flags.loc[a, "sut_izni_flg"]) if a in agent_flags.index and "sut_izni_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "sut_izni_flg"]) else 0
        mesaiye_kalamaz = int(agent_flags.loc[a, "mesaiye_kalamaz_flg"]) if a in agent_flags.index and "mesaiye_kalamaz_flg" in agent_flags.columns and pd.notna(agent_flags.loc[a, "mesaiye_kalamaz_flg"]) else 0

        kisitli = hamile == 1 or sut == 1 or mesaiye_kalamaz == 1

        if not kisitli:
            continue

        worked_val = safe_solver_value(work[(a, ds)]) if (a, ds) in work else 0

        if worked_val == 1:
            assigned_shift = None

            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                    assigned_shift = v
                    break

            resmi_tatil_kisitli_rows.append({
                "agent_user_code": a,
                "date": ds_key(ds),
                "assigned_shift": assigned_shift,
                "hamile_flg": hamile,
                "sut_izni_flg": sut,
                "mesaiye_kalamaz_flg": mesaiye_kalamaz,
            })

resmi_tatil_kisitli_violation_df = pd.DataFrame(resmi_tatil_kisitli_rows)

print_check(
    "Resmi tatilde kısıtlı agent çalışma ihlali",
    resmi_tatil_kisitli_violation_df
)



# %% [KONTROL 20] FAZLA ATAMA LİMİT KONTROLÜ

fazla_atama_rows = []

for _, r in coverage_check_df.iterrows():

    ds = r["date"]
    v = r["shift"]
    required = int(r["required"])
    assigned = int(r["assigned"])
    fazla = max(0, assigned - required)

    shift_start = r["shift_start"]
    shift_end = r["shift_end"]

    is_gece_aksam = (
        (shift_start, shift_end) in {
            ("17:00", "01:00"),
            ("18:00", "02:00"),
            ("00:00", "08:00"),
        }
    )

    allowed_extra = GECE_MAX_FAZLA_ATAMA if is_gece_aksam else GENEL_MAX_FAZLA_ATAMA

    if fazla > allowed_extra:
        fazla_atama_rows.append({
            "date": ds,
            "shift": v,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "required": required,
            "assigned": assigned,
            "fazla": fazla,
            "allowed_extra": allowed_extra,
            "is_gece_aksam": is_gece_aksam,
        })

fazla_atama_violation_df = pd.DataFrame(fazla_atama_rows)

print_check(
    "Fazla atama limit ihlali",
    fazla_atama_violation_df
)



# %% [KONTROL 21] GÜN BAZLI ÇALIŞMAZ FLAG KONTROLÜ

weekday_flag_map = {
    0: ["pazartesi_calismaz_flg", "pzt_calismaz_flg", "monday_calismaz_flg"],
    1: ["sali_calismaz_flg", "salı_calismaz_flg", "tuesday_calismaz_flg"],
    2: ["carsamba_calismaz_flg", "çarşamba_calismaz_flg", "wednesday_calismaz_flg"],
    3: ["persembe_calismaz_flg", "perşembe_calismaz_flg", "thursday_calismaz_flg"],
    4: ["cuma_calismaz_flg", "friday_calismaz_flg"],
    5: ["cumartesi_calismaz_flg", "saturday_calismaz_flg"],
    6: ["pazar_calismaz_flg", "sunday_calismaz_flg"],
}

available_flag_cols = set(df_tam.columns)

gun_calismaz_rows = []

for a in AGENTS:
    a = normalize_agent(a)

    if a not in agent_flags.index:
        continue

    for ds in PLAN_GUNLER:
        weekday = pd.to_datetime(ds).weekday()

        flag_cols = [
            c for c in weekday_flag_map.get(weekday, [])
            if c in available_flag_cols
        ]

        if not flag_cols:
            continue

        flag_active = False
        active_col = None

        for col in flag_cols:
            val = agent_flags.loc[a, col]

            if pd.notna(val) and int(val) == 1:
                flag_active = True
                active_col = col
                break

        if not flag_active:
            continue

        worked_val = safe_solver_value(work[(a, ds)]) if (a, ds) in work else 0

        if worked_val == 1:
            assigned_shift = None

            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) in x and safe_solver_value(x[(a, ds, v)]) == 1:
                    assigned_shift = v
                    break

            gun_calismaz_rows.append({
                "agent_user_code": a,
                "date": ds_key(ds),
                "gun": safe_day_name(ds),
                "active_flag_col": active_col,
                "assigned_shift": assigned_shift,
            })

gun_calismaz_violation_df = pd.DataFrame(gun_calismaz_rows)

print("Kontrol edilen gün çalışmaz flag kolonları:", sorted(list(available_flag_cols.intersection(set(sum(weekday_flag_map.values(), []))))))
print_check(
    "Gün bazlı çalışmaz flag ihlali",
    gun_calismaz_violation_df
)



# %% [KONTROL 22] FINAL KURAL KONTROL ÖZETİ

control_summary_rows = [
    {
        "kural": "Coverage required > 0 ama assigned = 0",
        "ihlal_sayisi": len(coverage_zero_assigned_df),
        "beklenen": 0,
    },
    {
        "kural": "Coverage negatif gap",
        "ihlal_sayisi": len(coverage_gap_negative_df),
        "beklenen": "mümkün olduğunca düşük",
    },
    {
        "kural": "Günde max 1 vardiya",
        "ihlal_sayisi": len(one_shift_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "İzinli günde çalışma",
        "ihlal_sayisi": len(izin_work_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Haftalık çalışma denklemi",
        "ihlal_sayisi": len(weekly_equation_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Aylık normal mesai max 2",
        "ihlal_sayisi": len(monthly_overtime_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Haftada max 1 normal mesai",
        "ihlal_sayisi": len(weekly_overtime_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Max 6 gün üst üste çalışma",
        "ihlal_sayisi": len(max_consecutive_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "11 saat dinlenme",
        "ihlal_sayisi": len(rest_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Ayda en az 1 Cmt-Paz OFF",
        "ihlal_sayisi": len(weekend_off_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Hamile/süt izni hafta sonu çalışamaz",
        "ihlal_sayisi": len(weekend_restricted_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Sabah çalışır 20:00 sonrası çalışamaz",
        "ihlal_sayisi": len(sabah_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Gece/akşam ayda max 2 hafta",
        "ihlal_sayisi": len(gece_aksam_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Özel gün hariç hafta içi takım bölünmez",
        "ihlal_sayisi": len(team_weekday_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Agent takım base vardiyası dışında çalışmaz",
        "ihlal_sayisi": len(team_base_assignment_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Takım base kapasite guard",
        "ihlal_sayisi": len(team_base_capacity_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Arife özel vardiya",
        "ihlal_sayisi": len(arife_special_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Arife kısıtlı 13:00 sonrası çalışamaz",
        "ihlal_sayisi": len(arife_after_13_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Resmi tatilde kısıtlı çalışamaz",
        "ihlal_sayisi": len(resmi_tatil_kisitli_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Fazla atama limit",
        "ihlal_sayisi": len(fazla_atama_violation_df),
        "beklenen": 0,
    },
    {
        "kural": "Gün bazlı çalışmaz flag",
        "ihlal_sayisi": len(gun_calismaz_violation_df),
        "beklenen": 0,
    },
]

control_summary_df = pd.DataFrame(control_summary_rows)

display(control_summary_df)



