from ortools.sat.python import cp_model
import pandas as pd


def build_basic_assignment_model(model_inputs):
    model = cp_model.CpModel()

    employees = model_inputs["employees"]
    shifts = model_inputs["shifts"]

    employee_skill = model_inputs["employee_skill"]
    shift_date = model_inputs["shift_date"]
    required_count = model_inputs["required_count"]

    # ------------------------------------------------
    # 1. Karar değişkeni
    # ------------------------------------------------
    # assign[e, sh] = 1 ise employee e, shift sh'ye atanmıştır.
    #
    # Sadece employee'nin skill_group'u o shiftte gerekiyorsa değişken oluşturuyoruz.
    # Örn: employee kitle ise, sadece kitle ihtiyacı olan shiftlerde değişken açılır.
    # ------------------------------------------------

    assign = {}

    for e in employees:
        emp_skill = employee_skill[e]

        for sh in shifts:
            required = required_count.get((sh, emp_skill), 0)

            if required > 0:
                assign[e, sh] = model.NewBoolVar(f"assign_{e}_{sh}")

    # ------------------------------------------------
    # 2. Shift + skill_group demand karşılansın
    # ------------------------------------------------
    # Örn:
    # 2026-06-01_08:00_17:00 shiftinde kitle için 56 kişi gerekiyorsa,
    # kitle skill_group'una sahip 56 agent atanmalı.
    # ------------------------------------------------

    for (sh, skill), required in required_count.items():
        eligible_agents = [
            e for e in employees
            if employee_skill[e] == skill and (e, sh) in assign
        ]

        if len(eligible_agents) < required:
            raise ValueError(
                f"Yetersiz agent var. Shift: {sh}, Skill: {skill}, "
                f"Required: {required}, Eligible: {len(eligible_agents)}"
            )

        model.Add(
            sum(assign[e, sh] for e in eligible_agents) == required
        )

    # ------------------------------------------------
    # 3. Bir agent aynı gün en fazla 1 vardiya alsın
    # ------------------------------------------------

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
def solve_basic_model(model, time_limit_seconds=60):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        print("Optimal çözüm bulundu.")
    elif status == cp_model.FEASIBLE:
        print("Feasible çözüm bulundu.")
    else:
        print("Çözüm bulunamadı.")

    return solver, status

def extract_basic_roster(solver, status, assign, model_inputs):
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
model, assign = build_basic_assignment_model(model_inputs)

solver, status = solve_basic_model(
    model=model,
    time_limit_seconds=60
)

roster_df = extract_basic_roster(
    solver=solver,
    status=status,
    assign=assign,
    model_inputs=model_inputs
)

roster_df.head(20)
