from ortools.sat.python import cp_model
import pandas as pd
import re


# ============================================================
# MODEL V5
#
# Hard constraints:
# 1. Shift + skill demand karşılanır
# 2. Agent sadece kendi skill_group’una atanır
# 3. Agent aynı gün max 1 vardiya alır
# 4. Pazartesi izinli pazartesi çalışmaz
# 5. Cuma izinli cuma çalışmaz
# 6. Sabah çalışan / hamile / süt izni 20:00 sonrası çalışmaz
# 7. Hamileler hafta sonu ve resmi tatilde çalışmaz
# 8. Günlük çalışma süresi max 9 saat
# 9. İki vardiya arası minimum 11 saat dinlenme
# 10. Max 6 gün üst üste çalışma
#
# Soft objective:
# 11. Her team + gün için bir ana vardiya seçilir.
# 12. Normal çalışan ana vardiyadan ayrılırsa yüksek ceza.
# 13. Özel durumlu çalışan ayrılırsa düşük ceza.
# 14. Team birden fazla vardiyaya bölünürse ayrıca ceza.
# ============================================================


# ============================================================
# 1. Parameters
# ============================================================

NORMAL_SPLIT_PENALTY = 100
SPECIAL_SPLIT_PENALTY = 20
EXTRA_TEAM_SHIFT_PENALTY = 30


# ============================================================
# 2. Display helper
# ============================================================

def safe_display(df, name=None, n=30):
    if name:
        print(f"\n{name}")

    try:
        display(df)
    except NameError:
        print(df.head(n))


def safe_var_name(value):
    value = str(value)
    value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    return value[:80]


# ============================================================
# 3. Helper functions
# ============================================================

def get_weekday(date_str):
    return pd.to_datetime(date_str).day_name().lower()


def is_special_employee(e, model_inputs):
    return (
        model_inputs["employee_hamile"].get(e, 0) == 1
        or model_inputs["employee_sut_izni"].get(e, 0) == 1
        or model_inputs["employee_sabah_calisir"].get(e, 0) == 1
    )


def get_employee_split_penalty(e, model_inputs):
    if is_special_employee(e, model_inputs):
        return SPECIAL_SPLIT_PENALTY
    return NORMAL_SPLIT_PENALTY


def is_employee_allowed_for_shift(e, sh, model_inputs, config):
    shift_date = model_inputs["shift_date"]
    shift_end_dt = model_inputs["shift_end_dt"]
    shift_duration = model_inputs["shift_duration"]

    employee_pazartesi_izinli = model_inputs["employee_pazartesi_izinli"]
    employee_cuma_izinli = model_inputs["employee_cuma_izinli"]
    employee_sabah_calisir = model_inputs["employee_sabah_calisir"]
    employee_sut_izni = model_inputs["employee_sut_izni"]
    employee_hamile = model_inputs["employee_hamile"]

    date_str = str(shift_date[sh])
    weekday = get_weekday(date_str)

    if employee_pazartesi_izinli.get(e, 0) == 1 and weekday == "monday":
        return False

    if employee_cuma_izinli.get(e, 0) == 1 and weekday == "friday":
        return False

    max_daily_minutes = config["shift_rules"]["max_daily_work_minutes"]

    if shift_duration[sh] > max_daily_minutes:
        return False

    day_only = (
        employee_sabah_calisir.get(e, 0) == 1
        or employee_hamile.get(e, 0) == 1
        or employee_sut_izni.get(e, 0) == 1
    )

    if day_only:
        latest_end_time = config["shift_rules"]["latest_end_time_for_day_only_agents"]
        latest_allowed_end_dt = pd.to_datetime(f"{date_str} {latest_end_time}")

        if shift_end_dt[sh] > latest_allowed_end_dt:
            return False

    if employee_hamile.get(e, 0) == 1:
        if weekday in ["saturday", "sunday"]:
            return False

        official_holidays = config.get("holiday_rules", {}).get("official_holidays", [])

        if date_str in official_holidays:
            return False

    return True


# ============================================================
# 4. Build OR-Tools model
# ============================================================

def build_assignment_model_v5(model_inputs, config):
    model = cp_model.CpModel()

    employees = model_inputs["employees"]
    shifts = model_inputs["shifts"]

    employee_skill = model_inputs["employee_skill"]
    employee_team = model_inputs["employee_team"]

    shift_date = model_inputs["shift_date"]
    shift_start_dt = model_inputs["shift_start_dt"]
    shift_end_dt = model_inputs["shift_end_dt"]

    required_count = model_inputs["required_count"]

    assign = {}

    # ------------------------------------------------------------
    # 4.1 Employee-shift assignment variables
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

            assign[e, sh] = model.NewBoolVar(
                f"assign_{safe_var_name(e)}_{safe_var_name(sh)}"
            )

    # ------------------------------------------------------------
    # 4.2 Demand coverage
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

        model.Add(sum(assign[e, sh] for e in eligible_agents) == required)

    # ------------------------------------------------------------
    # 4.3 One shift per employee per day
    # ------------------------------------------------------------

    dates = sorted(set(str(d) for d in shift_date.values()))

    for e in employees:
        for d in dates:
            employee_shift_vars_on_day = [
                assign[e, sh]
                for sh in shifts
                if str(shift_date[sh]) == d and (e, sh) in assign
            ]

            if employee_shift_vars_on_day:
                model.Add(sum(employee_shift_vars_on_day) <= 1)

    # ------------------------------------------------------------
    # 4.4 Minimum 11 hours rest between shifts
    # ------------------------------------------------------------

    min_rest_hours = config["constraints"]["min_rest_between_shifts"]["min_rest_hours"]
    min_rest_minutes = min_rest_hours * 60

    sorted_shifts = sorted(shifts, key=lambda sh: shift_start_dt[sh])

    for e in employees:
        for i in range(len(sorted_shifts)):
            sh1 = sorted_shifts[i]

            if (e, sh1) not in assign:
                continue

            end1 = shift_end_dt[sh1]

            for j in range(i + 1, len(sorted_shifts)):
                sh2 = sorted_shifts[j]

                if (e, sh2) not in assign:
                    continue

                start2 = shift_start_dt[sh2]
                rest_minutes = (start2 - end1).total_seconds() / 60

                if rest_minutes < min_rest_minutes:
                    model.Add(assign[e, sh1] + assign[e, sh2] <= 1)

                if rest_minutes >= min_rest_minutes:
                    break

    # ------------------------------------------------------------
    # 4.5 Max 6 consecutive working days
    # ------------------------------------------------------------

    max_days = config["constraints"]["max_consecutive_work_days"]["max_days"]
    window_days = config["constraints"]["max_consecutive_work_days"]["window_days"]

    min_date = pd.to_datetime(min(dates))
    max_date = pd.to_datetime(max(dates))

    all_calendar_dates = pd.date_range(min_date, max_date, freq="D")
    all_calendar_dates_str = [d.strftime("%Y-%m-%d") for d in all_calendar_dates]

    for e in employees:
        for start_idx in range(0, len(all_calendar_dates_str) - window_days + 1):
            window_dates = set(
                all_calendar_dates_str[start_idx:start_idx + window_days]
            )

            vars_in_window = [
                assign[e, sh]
                for sh in shifts
                if str(shift_date[sh]) in window_dates and (e, sh) in assign
            ]

            if vars_in_window:
                model.Add(sum(vars_in_window) <= max_days)

    # ------------------------------------------------------------
    # 4.6 Team main shift objective
    # ------------------------------------------------------------

    objective_terms = []

    team_members = {}

    for e in employees:
        team_id = employee_team[e]

        if team_id not in team_members:
            team_members[team_id] = []

        team_members[team_id].append(e)

    shifts_by_date = {}

    for sh in shifts:
        d = str(shift_date[sh])

        if d not in shifts_by_date:
            shifts_by_date[d] = []

        shifts_by_date[d].append(sh)

    team_work_day = {}
    team_shift_used = {}
    team_main_shift = {}
    employee_split = {}
    extra_team_shift = {}

    for team_id, members in team_members.items():
        team_name = safe_var_name(team_id)

        for d, day_shifts in shifts_by_date.items():
            date_name = safe_var_name(d)

            team_day_assignment_vars = [
                assign[e, sh]
                for e in members
                for sh in day_shifts
                if (e, sh) in assign
            ]

            if not team_day_assignment_vars:
                continue

            work_day_var = model.NewBoolVar(
                f"team_work_day_{team_name}_{date_name}"
            )

            team_work_day[team_id, d] = work_day_var

            for var in team_day_assignment_vars:
                model.Add(work_day_var >= var)

            model.Add(work_day_var <= sum(team_day_assignment_vars))

            main_shift_vars_for_day = []

            for sh in day_shifts:
                shift_name = safe_var_name(sh)

                member_shift_vars = [
                    assign[e, sh]
                    for e in members
                    if (e, sh) in assign
                ]

                used_var = model.NewBoolVar(
                    f"team_shift_used_{team_name}_{date_name}_{shift_name}"
                )

                main_var = model.NewBoolVar(
                    f"team_main_shift_{team_name}_{date_name}_{shift_name}"
                )

                team_shift_used[team_id, d, sh] = used_var
                team_main_shift[team_id, d, sh] = main_var

                if member_shift_vars:
                    for var in member_shift_vars:
                        model.Add(used_var >= var)

                    model.Add(used_var <= sum(member_shift_vars))
                else:
                    model.Add(used_var == 0)

                model.Add(main_var <= used_var)

                main_shift_vars_for_day.append(main_var)

            model.Add(sum(main_shift_vars_for_day) == work_day_var)

            for sh in day_shifts:
                used_var = team_shift_used[team_id, d, sh]
                main_var = team_main_shift[team_id, d, sh]

                extra_var = model.NewBoolVar(
                    f"extra_team_shift_{team_name}_{date_name}_{safe_var_name(sh)}"
                )

                extra_team_shift[team_id, d, sh] = extra_var

                model.Add(extra_var <= used_var)
                model.Add(extra_var <= 1 - main_var)
                model.Add(extra_var >= used_var - main_var)

                objective_terms.append(EXTRA_TEAM_SHIFT_PENALTY * extra_var)

            for e in members:
                employee_penalty = get_employee_split_penalty(e, model_inputs)

                for sh in day_shifts:
                    if (e, sh) not in assign:
                        continue

                    main_var = team_main_shift[team_id, d, sh]

                    split_var = model.NewBoolVar(
                        f"employee_split_{safe_var_name(e)}_{team_name}_{date_name}_{safe_var_name(sh)}"
                    )

                    employee_split[e, d, sh] = split_var

                    model.Add(split_var <= assign[e, sh])
                    model.Add(split_var <= 1 - main_var)
                    model.Add(split_var >= assign[e, sh] - main_var)

                    objective_terms.append(employee_penalty * split_var)

    print(f"Team work day var sayısı: {len(team_work_day)}")
    print(f"Team shift used var sayısı: {len(team_shift_used)}")
    print(f"Team main shift var sayısı: {len(team_main_shift)}")
    print(f"Employee split var sayısı: {len(employee_split)}")
    print(f"Extra team shift var sayısı: {len(extra_team_shift)}")

    if objective_terms:
        model.Minimize(sum(objective_terms))

    return model, assign


# ============================================================
# 5. Solve model
# ============================================================

def solve_model(model, time_limit_seconds=600):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    print("Status:", solver.StatusName(status))
    print(solver.ResponseStats())

    return solver, status


# ============================================================
# 6. Extract roster
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
                "date": str(shift_date[sh]),
                "shift_id": sh,
                "shift_start": shift_start[sh],
                "shift_end": shift_end[sh],
                "shift_start_dt": shift_start_dt[sh],
                "shift_end_dt": shift_end_dt[sh],
                "duration_minutes": shift_duration[sh],
                "special_employee_flg": int(is_special_employee(e, model_inputs))
            })

    roster_df = pd.DataFrame(rows)

    if not roster_df.empty:
        roster_df = roster_df.sort_values(
            ["date", "team_id", "shift_start", "employee_name"]
        ).reset_index(drop=True)

    return roster_df


# ============================================================
# 7. Hard constraint checks
# ============================================================

def check_demand_coverage(roster_df, shift_demand_long_df):
    if roster_df.empty:
        return pd.DataFrame()

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


def check_one_shift_per_day(roster_df):
    if roster_df.empty:
        return pd.DataFrame()

    daily_assignment_check = (
        roster_df
        .groupby(["employee_id", "date"])
        .size()
        .reset_index(name="shift_count")
    )

    return daily_assignment_check[daily_assignment_check["shift_count"] > 1]


def check_current_employee_constraints(roster_df, model_inputs, config):
    check_df = roster_df.copy()

    if check_df.empty:
        return pd.DataFrame(), {}

    check_df["date"] = check_df["date"].astype(str)
    check_df["shift_end_dt"] = pd.to_datetime(check_df["shift_end_dt"])
    check_df["weekday"] = pd.to_datetime(check_df["date"]).dt.day_name().str.lower()

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

    pazartesi_violation = check_df[
        (check_df["pazartesi_izinli_flg"] == 1) &
        (check_df["weekday"] == "monday")
    ].copy()

    cuma_violation = check_df[
        (check_df["cuma_izinli_flg"] == 1) &
        (check_df["weekday"] == "friday")
    ].copy()

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

    official_holidays = config.get("holiday_rules", {}).get("official_holidays", [])

    pregnant_weekend_holiday_violation = check_df[
        (check_df["hamile_flg"] == 1) &
        (
            check_df["weekday"].isin(["saturday", "sunday"]) |
            check_df["date"].isin(official_holidays)
        )
    ].copy()

    max_daily_minutes = config["shift_rules"]["max_daily_work_minutes"]

    max_daily_work_violation = check_df[
        check_df["duration_minutes"] > max_daily_minutes
    ].copy()

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


def check_min_rest_between_shifts(roster_df, min_rest_hours=11):
    df = roster_df.copy()

    if df.empty:
        return pd.DataFrame()

    df["shift_start_dt"] = pd.to_datetime(df["shift_start_dt"])
    df["shift_end_dt"] = pd.to_datetime(df["shift_end_dt"])

    df = df.sort_values(["employee_id", "shift_start_dt"])

    rows = []

    for employee_id, emp_df in df.groupby("employee_id"):
        emp_df = emp_df.sort_values("shift_start_dt").reset_index(drop=True)

        for i in range(len(emp_df) - 1):
            current_row = emp_df.loc[i]
            next_row = emp_df.loc[i + 1]

            rest_hours = (
                next_row["shift_start_dt"] - current_row["shift_end_dt"]
            ).total_seconds() / 3600

            if rest_hours < min_rest_hours:
                rows.append({
                    "employee_id": employee_id,
                    "employee_name": current_row["employee_name"],
                    "current_date": current_row["date"],
                    "current_shift_start": current_row["shift_start"],
                    "current_shift_end": current_row["shift_end"],
                    "next_date": next_row["date"],
                    "next_shift_start": next_row["shift_start"],
                    "next_shift_end": next_row["shift_end"],
                    "rest_hours": rest_hours
                })

    return pd.DataFrame(rows)


def check_max_consecutive_work_days(roster_df, max_days=6, window_days=7):
    df = roster_df.copy()

    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])

    rows = []

    min_date = df["date"].min()
    max_date = df["date"].max()
    all_dates = pd.date_range(min_date, max_date, freq="D")

    for employee_id, emp_df in df.groupby("employee_id"):
        employee_name = emp_df["employee_name"].iloc[0]
        worked_dates = set(emp_df["date"].dt.strftime("%Y-%m-%d"))

        for start_date in all_dates:
            window = pd.date_range(start_date, periods=window_days, freq="D")
            window_str = [d.strftime("%Y-%m-%d") for d in window]

            worked_in_window = [
                d for d in window_str
                if d in worked_dates
            ]

            if len(worked_in_window) > max_days:
                rows.append({
                    "employee_id": employee_id,
                    "employee_name": employee_name,
                    "window_start": window_str[0],
                    "window_end": window_str[-1],
                    "worked_days_count": len(worked_in_window),
                    "worked_days": worked_in_window
                })

    return pd.DataFrame(rows)


# ============================================================
# 8. Team consistency analysis
# ============================================================

def analyze_team_consistency(roster_df):
    df = roster_df.copy()

    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    rows = []

    for (date, team_id), group_df in df.groupby(["date", "team_id"]):
        working_count = len(group_df)

        shift_counts = (
            group_df
            .groupby(["shift_id", "shift_start", "shift_end"])
            .size()
            .reset_index(name="assigned_count")
            .sort_values("assigned_count", ascending=False)
        )

        shift_count = len(shift_counts)

        majority_shift_id = shift_counts.iloc[0]["shift_id"]
        majority_shift_start = shift_counts.iloc[0]["shift_start"]
        majority_shift_end = shift_counts.iloc[0]["shift_end"]
        majority_count = int(shift_counts.iloc[0]["assigned_count"])

        split_count = working_count - majority_count

        split_members_df = group_df[
            group_df["shift_id"] != majority_shift_id
        ].copy()

        normal_split_count = int(
            (split_members_df["special_employee_flg"] == 0).sum()
        )

        special_split_count = int(
            (split_members_df["special_employee_flg"] == 1).sum()
        )

        rows.append({
            "date": date,
            "team_id": team_id,
            "working_count": working_count,
            "shift_count": shift_count,
            "majority_shift_id": majority_shift_id,
            "majority_shift_start": majority_shift_start,
            "majority_shift_end": majority_shift_end,
            "majority_count": majority_count,
            "split_count": split_count,
            "normal_split_count": normal_split_count,
            "special_split_count": special_split_count,
            "is_split": int(shift_count > 1)
        })

    team_consistency_df = pd.DataFrame(rows)

    split_team_days_df = team_consistency_df[
        team_consistency_df["is_split"] == 1
    ].sort_values(
        ["normal_split_count", "split_count"],
        ascending=False
    ).reset_index(drop=True)

    summary_df = pd.DataFrame({
        "metric": [
            "team_day_count",
            "split_team_day_count",
            "total_split_members",
            "normal_split_members",
            "special_split_members"
        ],
        "value": [
            len(team_consistency_df),
            len(split_team_days_df),
            int(team_consistency_df["split_count"].sum()),
            int(team_consistency_df["normal_split_count"].sum()),
            int(team_consistency_df["special_split_count"].sum())
        ]
    })

    return team_consistency_df, split_team_days_df, summary_df


def get_split_team_members(roster_df, team_id, date):
    df = roster_df.copy()

    target_df = df[
        (df["team_id"] == team_id) &
        (df["date"] == date)
    ].copy()

    if target_df.empty:
        return pd.DataFrame()

    shift_counts = (
        target_df
        .groupby("shift_id")
        .size()
        .reset_index(name="assigned_count")
        .sort_values("assigned_count", ascending=False)
    )

    majority_shift_id = shift_counts.iloc[0]["shift_id"]

    target_df["is_majority_shift"] = (
        target_df["shift_id"] == majority_shift_id
    ).astype(int)

    return target_df.sort_values(
        ["is_majority_shift", "special_employee_flg", "shift_start", "employee_name"],
        ascending=[True, False, True, True]
    )


# ============================================================
# 9. Run everything
# ============================================================

def run_model_v5(model_inputs, constraints_config, shift_demand_long_df, time_limit_seconds=600):
    model, assign = build_assignment_model_v5(
        model_inputs=model_inputs,
        config=constraints_config
    )

    solver, status = solve_model(
        model=model,
        time_limit_seconds=time_limit_seconds
    )

    roster_df = extract_roster(
        solver=solver,
        status=status,
        assign=assign,
        model_inputs=model_inputs
    )

    comparison_df = check_demand_coverage(
        roster_df=roster_df,
        shift_demand_long_df=shift_demand_long_df
    )

    daily_assignment_problem_df = check_one_shift_per_day(roster_df)

    employee_constraint_summary_df, employee_constraint_violations = check_current_employee_constraints(
        roster_df=roster_df,
        model_inputs=model_inputs,
        config=constraints_config
    )

    min_rest_violation_df = check_min_rest_between_shifts(
        roster_df=roster_df,
        min_rest_hours=constraints_config["constraints"]["min_rest_between_shifts"]["min_rest_hours"]
    )

    consecutive_violation_df = check_max_consecutive_work_days(
        roster_df=roster_df,
        max_days=constraints_config["constraints"]["max_consecutive_work_days"]["max_days"],
        window_days=constraints_config["constraints"]["max_consecutive_work_days"]["window_days"]
    )

    team_consistency_df, split_team_days_df, team_consistency_summary_df = analyze_team_consistency(
        roster_df=roster_df
    )

    objective_value = None

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        objective_value = solver.ObjectiveValue()

    print("\nÖzet:")
    print(f"Status: {solver.StatusName(status)}")
    print(f"Objective value: {objective_value}")
    print(f"Roster satır sayısı: {len(roster_df)}")
    print(f"Demand diff problemi sayısı: {len(comparison_df[comparison_df['diff'] != 0]) if not comparison_df.empty else 0}")
    print(f"Aynı gün çoklu vardiya problemi sayısı: {len(daily_assignment_problem_df)}")
    print(f"Employee kısıt violation toplamı: {employee_constraint_summary_df['violation_count'].sum() if not employee_constraint_summary_df.empty else 0}")
    print(f"11 saat dinlenme violation sayısı: {len(min_rest_violation_df)}")
    print(f"Max 6 gün üst üste violation sayısı: {len(consecutive_violation_df)}")
    print(f"Bölünen team-day sayısı: {len(split_team_days_df)}")

    print("\nTeam consistency summary:")
    safe_display(team_consistency_summary_df)

    team_check_simple_df = split_team_days_df[
        [
            "date",
            "team_id",
            "working_count",
            "shift_count",
            "majority_shift_start",
            "majority_shift_end",
            "majority_count",
            "split_count",
            "normal_split_count",
            "special_split_count"
        ]
    ].copy()

    team_check_simple_df = team_check_simple_df.sort_values(
        ["normal_split_count", "split_count"],
        ascending=False
    ).reset_index(drop=True)

    print("\nEn problemli bölünen team-day örnekleri:")
    safe_display(team_check_simple_df.head(50))

    return {
        "model": model,
        "assign": assign,
        "solver": solver,
        "status": status,
        "roster_df": roster_df,
        "comparison_df": comparison_df,
        "daily_assignment_problem_df": daily_assignment_problem_df,
        "employee_constraint_summary_df": employee_constraint_summary_df,
        "employee_constraint_violations": employee_constraint_violations,
        "min_rest_violation_df": min_rest_violation_df,
        "consecutive_violation_df": consecutive_violation_df,
        "team_consistency_df": team_consistency_df,
        "split_team_days_df": split_team_days_df,
        "team_consistency_summary_df": team_consistency_summary_df,
        "team_check_simple_df": team_check_simple_df
    }


# ============================================================
# 10. Execute
# ============================================================

results_v5 = run_model_v5(
    model_inputs=model_inputs,
    constraints_config=constraints_config,
    shift_demand_long_df=shift_demand_long_df,
    time_limit_seconds=600
)

roster_df = results_v5["roster_df"]
split_team_days_df = results_v5["split_team_days_df"]
team_check_simple_df = results_v5["team_check_simple_df"]
team_consistency_summary_df = results_v5["team_consistency_summary_df"]
