import json
import pandas as pd


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_model_inputs(planning_employee_df, shift_demand_long_df, config):
    employee_df = planning_employee_df.copy()
    shift_df = shift_demand_long_df.copy()

    # ------------------------------------------------
    # 1. Temel kolon kontrolleri
    # ------------------------------------------------
    required_employee_cols = [
        "employee_id",
        "employee_name",
        "team_id",
        "location",
        "skill_group",
        "pazartesi_izinli_flg",
        "cuma_izinli_flg",
        "sabah_calisir_flg",
        "mesaiye_kalamaz_flg",
        "sut_izni_flg",
        "hamile_flg"
    ]

    required_shift_cols = [
        "date",
        "shift_id",
        "shift_start",
        "shift_end",
        "shift_start_dt",
        "shift_end_dt",
        "duration_minutes",
        "skill_group",
        "required_count"
    ]

    missing_employee_cols = [
        col for col in required_employee_cols
        if col not in employee_df.columns
    ]

    missing_shift_cols = [
        col for col in required_shift_cols
        if col not in shift_df.columns
    ]

    if missing_employee_cols:
        raise ValueError(f"Employee datasında eksik kolonlar var: {missing_employee_cols}")

    if missing_shift_cols:
        raise ValueError(f"Shift datasında eksik kolonlar var: {missing_shift_cols}")

    # ------------------------------------------------
    # 2. Format düzeltmeleri
    # ------------------------------------------------
    employee_df["employee_id"] = employee_df["employee_id"].astype(str)
    employee_df["skill_group"] = employee_df["skill_group"].astype(str).str.lower().str.strip()
    employee_df["team_id"] = employee_df["team_id"].astype(str).str.lower().str.strip()
    employee_df["location"] = employee_df["location"].astype(str).str.lower().str.strip()

    shift_df["date"] = shift_df["date"].astype(str)
    shift_df["shift_id"] = shift_df["shift_id"].astype(str)
    shift_df["skill_group"] = shift_df["skill_group"].astype(str).str.lower().str.strip()
    shift_df["required_count"] = shift_df["required_count"].astype(int)

    shift_df["shift_start_dt"] = pd.to_datetime(shift_df["shift_start_dt"])
    shift_df["shift_end_dt"] = pd.to_datetime(shift_df["shift_end_dt"])

    # ------------------------------------------------
    # 3. Ana listeler
    # ------------------------------------------------
    employees = employee_df["employee_id"].unique().tolist()
    shifts = shift_df["shift_id"].unique().tolist()
    dates = sorted(shift_df["date"].unique().tolist())
    skill_groups = config["planning_settings"]["skill_groups"]

    # ------------------------------------------------
    # 4. Employee dictionary'leri
    # ------------------------------------------------
    employee_name = dict(zip(employee_df["employee_id"], employee_df["employee_name"]))
    employee_team = dict(zip(employee_df["employee_id"], employee_df["team_id"]))
    employee_location = dict(zip(employee_df["employee_id"], employee_df["location"]))
    employee_skill = dict(zip(employee_df["employee_id"], employee_df["skill_group"]))

    employee_pazartesi_izinli = dict(
        zip(employee_df["employee_id"], employee_df["pazartesi_izinli_flg"])
    )

    employee_cuma_izinli = dict(
        zip(employee_df["employee_id"], employee_df["cuma_izinli_flg"])
    )

    employee_sabah_calisir = dict(
        zip(employee_df["employee_id"], employee_df["sabah_calisir_flg"])
    )

    employee_mesaiye_kalamaz = dict(
        zip(employee_df["employee_id"], employee_df["mesaiye_kalamaz_flg"])
    )

    employee_sut_izni = dict(
        zip(employee_df["employee_id"], employee_df["sut_izni_flg"])
    )

    employee_hamile = dict(
        zip(employee_df["employee_id"], employee_df["hamile_flg"])
    )

    # ------------------------------------------------
    # 5. Team dictionary
    # ------------------------------------------------
    team_members = (
        employee_df
        .groupby("team_id")["employee_id"]
        .apply(list)
        .to_dict()
    )

    # ------------------------------------------------
    # 6. Shift dictionary'leri
    # ------------------------------------------------
    shift_info_df = (
        shift_df[
            [
                "shift_id",
                "date",
                "shift_start",
                "shift_end",
                "shift_start_dt",
                "shift_end_dt",
                "duration_minutes"
            ]
        ]
        .drop_duplicates("shift_id")
        .copy()
    )

    shift_date = dict(zip(shift_info_df["shift_id"], shift_info_df["date"]))
    shift_start = dict(zip(shift_info_df["shift_id"], shift_info_df["shift_start"]))
    shift_end = dict(zip(shift_info_df["shift_id"], shift_info_df["shift_end"]))
    shift_start_dt = dict(zip(shift_info_df["shift_id"], shift_info_df["shift_start_dt"]))
    shift_end_dt = dict(zip(shift_info_df["shift_id"], shift_info_df["shift_end_dt"]))
    shift_duration = dict(zip(shift_info_df["shift_id"], shift_info_df["duration_minutes"]))

    # ------------------------------------------------
    # 7. Demand dictionary
    # ------------------------------------------------
    # Key: (shift_id, skill_group)
    # Value: required_count
    required_count = {
        (row["shift_id"], row["skill_group"]): int(row["required_count"])
        for _, row in shift_df.iterrows()
    }

    # ------------------------------------------------
    # 8. Skill bazlı uygun employee listesi
    # ------------------------------------------------
    employees_by_skill = {
        skill: employee_df.loc[
            employee_df["skill_group"] == skill,
            "employee_id"
        ].tolist()
        for skill in skill_groups
    }

    # ------------------------------------------------
    # 9. Basit validation
    # ------------------------------------------------
    shift_skills = set(shift_df["skill_group"].unique())
    employee_skills = set(employee_df["skill_group"].unique())

    missing_skills_in_employee = shift_skills - employee_skills

    if missing_skills_in_employee:
        raise ValueError(
            f"Shift demand içinde olup employee datasında olmayan skill_group var: "
            f"{missing_skills_in_employee}"
        )

    for skill in shift_skills:
        total_required = shift_df.loc[
            shift_df["skill_group"] == skill,
            "required_count"
        ].max()

        available_agents = len(employees_by_skill.get(skill, []))

        if available_agents == 0:
            raise ValueError(f"{skill} için hiç uygun employee yok.")

    # ------------------------------------------------
    # 10. Tüm inputları tek yerde topla
    # ------------------------------------------------
    model_inputs = {
        "employees": employees,
        "shifts": shifts,
        "dates": dates,
        "skill_groups": skill_groups,

        "employee_name": employee_name,
        "employee_team": employee_team,
        "employee_location": employee_location,
        "employee_skill": employee_skill,
        "employee_pazartesi_izinli": employee_pazartesi_izinli,
        "employee_cuma_izinli": employee_cuma_izinli,
        "employee_sabah_calisir": employee_sabah_calisir,
        "employee_mesaiye_kalamaz": employee_mesaiye_kalamaz,
        "employee_sut_izni": employee_sut_izni,
        "employee_hamile": employee_hamile,

        "team_members": team_members,

        "shift_date": shift_date,
        "shift_start": shift_start,
        "shift_end": shift_end,
        "shift_start_dt": shift_start_dt,
        "shift_end_dt": shift_end_dt,
        "shift_duration": shift_duration,

        "required_count": required_count,
        "employees_by_skill": employees_by_skill
    }

    return model_inputs
