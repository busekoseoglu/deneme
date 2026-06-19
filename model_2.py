from ortools.sat.python import cp_model
import pandas as pd


# ============================================================
# 1. Helper functions
# ============================================================

def get_weekday(date_str):
    return pd.to_datetime(date_str).day_name().lower()


def is_employee_allowed_for_shift(e, sh, model_inputs, config):
    """
    Employee e, shift sh'ye atanabilir mi?
    False dönerse o employee-shift için değişken oluşturulmaz.
    """

    shift_date = model_inputs["shift_date"]
    shift_end_dt = model_inputs["shift_end_dt"]
    shift_duration = model_inputs["shift_duration"]

    employee_pazartesi_izinli = model_inputs["employee_pazartesi_izinli"]
    employee_cuma_izinli = model_inputs["employee_cuma_izinli"]
    employee_sabah_calisir = model_inputs["employee_sabah_calisir"]
    employee_sut_izni = model_inputs["employee_sut_izni"]
    employee_hamile = model_inputs["employee_hamile"]

    date_str = shift_date[sh]
    weekday = get_weekday(date_str)

    # Pazartesi izinli olan pazartesi çalışamaz
    if employee_pazartesi_izinli.get(e, 0) == 1 and weekday == "monday":
        return False

    # Cuma izinli olan cuma çalışamaz
    if employee_cuma_izinli.get(e, 0) == 1 and weekday == "friday":
        return False

    # Günlük çalışma süresi max 9 saat
    max_daily_minutes = config["shift_rules"]["max_daily_work_minutes"]

    if shift_duration[sh] > max_daily_minutes:
        return False

    # Sabah çalışan / hamile / süt izni olanlar 20:00 sonrası biten shifte atanamaz
    day_only = (
        employee_sabah_calisir.get(e, 0) == 1
        or employee_hamile.get(e, 0) == 1
        or employee_sut_izni.get(e, 0) == 1
    )

    if day_only:
        latest_end_time = config["shift_rules"]["latest_end_time_for_day_only_agents"]

        latest_allowed_end_dt = pd.to_datetime(
            f"{date_str} {latest_end_time}"
        )

        if shift_end_dt[sh] > latest_allowed_end_dt:
            return False

    # Hamileler hafta sonu ve resmi tatilde çalışamaz
    if employee_hamile.get(e, 0) == 1:
        if weekday in ["saturday", "sunday"]:
            return False

        official_holidays = config.get("holiday_rules", {}).get("official_holidays", [])

        if date_str in official_holidays:
            return False

    return True


# ============================================================
# 2. OR-Tools model
# ============================================================

def build_assignment_model_v2(model_inputs, config):
    model = cp_model.CpModel()

    employees = model_inputs["employees"]
    shifts = model_inputs["shifts"]

    employee_skill = model_inputs["employee_skill"]
    shift_date = model_inputs["shift_date"]
    required_count = model_inputs["required_count"]

    assign = {}

    # ------------------------------------------------------------
    # Karar değişkenleri
    # assign[e, sh] = 1 ise employee e, shift sh'ye atanır
    # ------------------------------------------------------------

    for e in employees:
        emp_skill = employee_skill[e]

        for sh in shifts:
            required = required_count.get((sh, emp_skill), 0)

            if required <= 0:
                continue

            if not is_employee_allowed_for_shift(
                e=e,
                sh=sh,
                model_inputs=model_inputs,
                config=config
            ):
                continue

            assign[e, sh] = model.NewBoolVar(f"assign_{e}_{sh}")

    # ------------------------------------------------------------
    # Her shift + skill_group için required_count kadar agent atanmalı
    # ------------------------------------------------------------

    for (sh, skill), required in required_count.items():
        eligible_agents = [
            e for e in employees
            if employee_skill[e] == skill and (e, sh) in assign
        ]

        if len(eligible_agents) < required:
            raise ValueError(
                f"Yetersiz uygun agent var. "
                f"Shift: {sh}, Skill: {skill}, "
                f"Required: {required}, Eligible after constraints: {len(eligible_agents)}"
            )

        model.Add(
            sum(assign[e, sh] for e in eligible_agents) == required
        )

    # ------------------------------------------------------------
    # Bir agent aynı gün en fazla 1 vardiya alabilir
    # ------------------------------------------------------------

    dates = sorted(set(shift_date.values()))

    for e in employees:
        for d in dates:
            employee_shift_vars_on_day = [
                assign[e, sh]
                for sh in shifts
                if shift_date[sh] == d and (e, sh) in assign
            ]

            if employee_shift_vars_on_day:
                model.Add(sum(employee_shift_vars_on_day) <= 1)

    return model, assign


# ============================================================
# 3. Solve
# ============================================================

def solve_model(model, time_limit_seconds=30):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        print("Optimal çözüm bulundu.")
    elif status == cp_model.FEASIBLE:
        print("Feasible çözüm bulundu.")
    elif status == cp_model.INFEASIBLE:
        print("Model infeasible. Yani bu kısıtlarla çözüm yok.")
    elif status == cp_model.MODEL_INVALID:
        print("Model invalid. Modelde teknik bir hata var.")
    else:
        print("Çözüm bulunamadı veya süre doldu.")

    return solver, status


# ============================================================
# 4. Extract roster
# ============================================================

def extract_roster(solver, status, assign, model_inputs):
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return pd.DataFrame()

    employee_name = model_inputs["employee_name"]
    employee_team = model_inputs["employee_team"]
    employee_location = model_inputs["employee_location"]
    employee_skill = model_inputs["employee_skill"]

    shift_date = model_inputs["shift_date"]
    shift_start = model_inputs["shift_start"]
    shift_end = model_inputs["shift_end"]
    shift_start_dt = model_inputs["shift_start_dt"]
    shift_end_dt = model_inputs["shift_end_dt"]
    shift_duration = model_inputs["shift_duration"]

    rows = []

    for (e, sh), var in assign.items():
        if solver.Value(var) == 1:
            rows.append({
                "employee_id": e,
                "employee_name": employee_name[e],
                "team_id": employee_team[e],
                "location": employee_location[e],
                "skill_group": employee_skill[e],
                "date": shift_date[sh],
                "shift_id": sh,
                "shift_start": shift_start[sh],
                "shift_end": shift_end[sh],
                "shift_start_dt": shift_start_dt[sh],
                "shift_end_dt": shift_end_dt[sh],
                "duration_minutes": shift_duration[sh]
            })

    roster_df = pd.DataFrame(rows)

    if not roster_df.empty:
        roster_df = roster_df.sort_values(
            ["date", "shift_start", "skill_group", "team_id", "employee_name"]
        ).reset_index(drop=True)

    return roster_df


# ============================================================
# 5. Demand check
# ============================================================

def check_demand_coverage(roster_df, shift_demand_long_df):
    assigned_count_df = (
        roster_df
        .groupby(["date", "shift_start", "shift_end", "skill_group"])
        .size()
        .reset_index(name="assigned_count")
    )

    demand_check_df = shift_demand_long_df[
        ["date", "shift_start", "shift_end", "skill_group", "required_count"]
    ].copy()

    demand_check_df["date"] = demand_check_df["date"].astype(str)
    assigned_count_df["date"] = assigned_count_df["date"].astype(str)

    comparison_df = demand_check_df.merge(
        assigned_count_df,
        on=["date", "shift_start", "shift_end", "skill_group"],
        how="left"
    )

    comparison_df["assigned_count"] = (
        comparison_df["assigned_count"]
        .fillna(0)
        .astype(int)
    )

    comparison_df["diff"] = (
        comparison_df["assigned_count"] - comparison_df["required_count"]
    )

    return comparison_df


# ============================================================
# 6. Daily assignment check
# ============================================================

def check_one_shift_per_day(roster_df):
    daily_assignment_check = (
        roster_df
        .groupby(["employee_id", "date"])
        .size()
        .reset_index(name="shift_count")
    )

    return daily_assignment_check[daily_assignment_check["shift_count"] > 1]


# ============================================================
# 7. Run model
# ============================================================

model, assign = build_assignment_model_v2(
    model_inputs=model_inputs,
    config=constraints_config
)

solver, status = solve_model(
    model=model,
    time_limit_seconds=30
)

roster_df = extract_roster(
    solver=solver,
    status=status,
    assign=assign,
    model_inputs=model_inputs
)

print("\nRoster sample:")
display(roster_df.head(20))


# ============================================================
# 8. Run checks
# ============================================================

comparison_df = check_demand_coverage(
    roster_df=roster_df,
    shift_demand_long_df=shift_demand_long_df
)

print("\nDemand coverage farkı olan satırlar:")
display(comparison_df[comparison_df["diff"] != 0])

daily_assignment_problem_df = check_one_shift_per_day(roster_df)

print("\nAynı gün birden fazla vardiya alan agentlar:")
display(daily_assignment_problem_df)

import pandas as pd


def check_current_constraints(roster_df, model_inputs, config):
    check_df = roster_df.copy()

    # Tarih / datetime formatları
    check_df["date"] = check_df["date"].astype(str)
    check_df["shift_end_dt"] = pd.to_datetime(check_df["shift_end_dt"])
    check_df["weekday"] = pd.to_datetime(check_df["date"]).dt.day_name().str.lower()

    # Employee flaglerini roster'a ekle
    check_df["pazartesi_izinli_flg"] = check_df["employee_id"].map(
        model_inputs["employee_pazartesi_izinli"]
    )

    check_df["cuma_izinli_flg"] = check_df["employee_id"].map(
        model_inputs["employee_cuma_izinli"]
    )

    check_df["sabah_calisir_flg"] = check_df["employee_id"].map(
        model_inputs["employee_sabah_calisir"]
    )

    check_df["sut_izni_flg"] = check_df["employee_id"].map(
        model_inputs["employee_sut_izni"]
    )

    check_df["hamile_flg"] = check_df["employee_id"].map(
        model_inputs["employee_hamile"]
    )

    # ------------------------------------------------------------
    # 1. Pazartesi izinli kontrolü
    # ------------------------------------------------------------
    pazartesi_violation = check_df[
        (check_df["pazartesi_izinli_flg"] == 1) &
        (check_df["weekday"] == "monday")
    ].copy()

    # ------------------------------------------------------------
    # 2. Cuma izinli kontrolü
    # ------------------------------------------------------------
    cuma_violation = check_df[
        (check_df["cuma_izinli_flg"] == 1) &
        (check_df["weekday"] == "friday")
    ].copy()

    # ------------------------------------------------------------
    # 3. Sabah çalışan / hamile / süt izni 20:00 sonrası çalışmış mı?
    # ------------------------------------------------------------
    latest_end_time = config["shift_rules"]["latest_end_time_for_day_only_agents"]

    check_df["latest_allowed_end_dt"] = pd.to_datetime(
        check_df["date"] + " " + latest_end_time
    )

    check_df["day_only_flg"] = (
        (check_df["sabah_calisir_flg"] == 1) |
        (check_df["hamile_flg"] == 1) |
        (check_df["sut_izni_flg"] == 1)
    ).astype(int)

    day_only_violation = check_df[
        (check_df["day_only_flg"] == 1) &
        (check_df["shift_end_dt"] > check_df["latest_allowed_end_dt"])
    ].copy()

    # ------------------------------------------------------------
    # 4. Hamile hafta sonu / resmi tatil çalışmış mı?
    # ------------------------------------------------------------
    official_holidays = config.get("holiday_rules", {}).get("official_holidays", [])

    pregnant_weekend_holiday_violation = check_df[
        (check_df["hamile_flg"] == 1) &
        (
            check_df["weekday"].isin(["saturday", "sunday"]) |
            check_df["date"].isin(official_holidays)
        )
    ].copy()

    # ------------------------------------------------------------
    # 5. Günlük max çalışma süresi kontrolü
    # ------------------------------------------------------------
    max_daily_minutes = config["shift_rules"]["max_daily_work_minutes"]

    max_daily_work_violation = check_df[
        check_df["duration_minutes"] > max_daily_minutes
    ].copy()

    # ------------------------------------------------------------
    # Özet
    # ------------------------------------------------------------
    summary = pd.DataFrame({
        "constraint": [
            "pazartesi_izinli",
            "cuma_izinli",
            "day_only_20_sonrasi",
            "hamile_weekend_holiday",
            "max_daily_work_minutes"
        ],
        "violation_count": [
            len(pazartesi_violation),
            len(cuma_violation),
            len(day_only_violation),
            len(pregnant_weekend_holiday_violation),
            len(max_daily_work_violation)
        ]
    })

    violations = {
        "pazartesi_izinli": pazartesi_violation,
        "cuma_izinli": cuma_violation,
        "day_only_20_sonrasi": day_only_violation,
        "hamile_weekend_holiday": pregnant_weekend_holiday_violation,
        "max_daily_work_minutes": max_daily_work_violation
    }

    return summary, violations


constraint_summary_df, constraint_violations = check_current_constraints(
    roster_df=roster_df,
    model_inputs=model_inputs,
    config=constraints_config
)

display(constraint_summary_df)

print("\nÖzet:")
print(f"Roster satır sayısı: {len(roster_df)}")
print(f"Demand diff problemi sayısı: {len(comparison_df[comparison_df['diff'] != 0])}")
print(f"Aynı gün çoklu vardiya problemi sayısı: {len(daily_assignment_problem_df)}")
