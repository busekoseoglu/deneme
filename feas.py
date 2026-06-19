import pandas as pd


# ============================================================
# TEAM FEASIBILITY CHECK
# Amaç:
# Takım kısıtına geçmeden önce şu soruları cevaplamak:
#
# 1. Aynı team içinde farklı skill_group var mı?
# 2. Aynı team içinde farklı location var mı?
# 3. Aynı team içinde farklı izin / uygunluk flagleri var mı?
# 4. Team block mantığında daily capacity yeterli mi?
# 5. Her shift + skill demand, team boyutlarıyla buffer dahil karşılanabilir mi?
# ============================================================


# ============================================================
# 1. Helper functions
# ============================================================

def get_weekday(date_str):
    return pd.to_datetime(date_str).day_name().lower()


def is_employee_allowed_for_shift(e, sh, model_inputs, config):
    """
    Employee e, shift sh'ye atanabilir mi?
    Modelde kullandığımız bireysel uygunluk kurallarıyla aynı mantık.
    """

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


def possible_counts_with_team_sizes(team_sizes, required, buffer):
    """
    Verilen team size listesiyle required ile required + buffer arasında
    bir toplam yapılabiliyor mu?
    """

    upper_bound = required + buffer

    possible = {0}

    for size in team_sizes:
        if size <= 0:
            continue

        new_values = set()

        for current in possible:
            new_sum = current + size

            if new_sum <= upper_bound:
                new_values.add(new_sum)

        possible = possible.union(new_values)

    feasible_counts = sorted([
        value for value in possible
        if required <= value <= upper_bound
    ])

    if feasible_counts:
        return True, feasible_counts[0], feasible_counts

    return False, None, []


# ============================================================
# 2. Employee-team dataframe oluştur
# ============================================================

def build_team_employee_df(model_inputs):
    employees = model_inputs["employees"]

    rows = []

    for e in employees:
        rows.append({
            "employee_id": e,
            "employee_name": model_inputs["employee_name"].get(e),
            "team_id": model_inputs["employee_team"].get(e),
            "location": model_inputs["employee_location"].get(e),
            "skill_group": model_inputs["employee_skill"].get(e),

            "pazartesi_izinli_flg": int(model_inputs["employee_pazartesi_izinli"].get(e, 0)),
            "cuma_izinli_flg": int(model_inputs["employee_cuma_izinli"].get(e, 0)),
            "sabah_calisir_flg": int(model_inputs["employee_sabah_calisir"].get(e, 0)),
            "mesaiye_kalamaz_flg": int(model_inputs["employee_mesaiye_kalamaz"].get(e, 0)),
            "sut_izni_flg": int(model_inputs["employee_sut_izni"].get(e, 0)),
            "hamile_flg": int(model_inputs["employee_hamile"].get(e, 0))
        })

    return pd.DataFrame(rows)


# ============================================================
# 3. Team structure check
# ============================================================

def analyze_team_structure(team_employee_df):
    flag_cols = [
        "pazartesi_izinli_flg",
        "cuma_izinli_flg",
        "sabah_calisir_flg",
        "mesaiye_kalamaz_flg",
        "sut_izni_flg",
        "hamile_flg"
    ]

    rows = []

    for team_id, team_df in team_employee_df.groupby("team_id"):
        skills = sorted(team_df["skill_group"].dropna().astype(str).unique().tolist())
        locations = sorted(team_df["location"].dropna().astype(str).unique().tolist())

        row = {
            "team_id": team_id,
            "member_count": len(team_df),
            "skill_count": len(skills),
            "skills": ", ".join(skills),
            "location_count": len(locations),
            "locations": ", ".join(locations)
        }

        for flag in flag_cols:
            row[f"{flag}_sum"] = int(team_df[flag].sum())
            row[f"{flag}_unique_count"] = int(team_df[flag].nunique())

        rows.append(row)

    team_summary_df = pd.DataFrame(rows)

    mixed_skill_teams_df = team_summary_df[
        team_summary_df["skill_count"] > 1
    ].copy()

    mixed_location_teams_df = team_summary_df[
        team_summary_df["location_count"] > 1
    ].copy()

    mixed_flag_rows = []

    for team_id, team_df in team_employee_df.groupby("team_id"):
        for flag in flag_cols:
            unique_values = sorted(team_df[flag].dropna().unique().tolist())

            if len(unique_values) > 1:
                mixed_flag_rows.append({
                    "team_id": team_id,
                    "flag": flag,
                    "values_in_team": unique_values,
                    "member_count": len(team_df),
                    "flag_1_count": int(team_df[flag].sum())
                })

    mixed_flag_teams_df = pd.DataFrame(mixed_flag_rows)

    return team_summary_df, mixed_skill_teams_df, mixed_location_teams_df, mixed_flag_teams_df


# ============================================================
# 4. Team shift availability
# ============================================================

def get_team_shift_counts(team_id, sh, skill, team_employee_df, model_inputs, config):
    """
    İki farklı bakış döndürüyoruz:

    1. strict_team_block_count:
       Team ancak tüm üyeleri aynı skill'deyse ve tüm üyeler bu shifte uygunsa kullanılabilir.

    2. available_skill_members_count:
       Team içindeki ilgili skill'e sahip ve bu shifte uygun üyeler sayılır.
       Bu daha esnek bir yorumdur.
    """

    team_df = team_employee_df[
        team_employee_df["team_id"] == team_id
    ].copy()

    # -------------------------------
    # Strict team block
    # -------------------------------

    team_skills = set(team_df["skill_group"].astype(str).tolist())

    strict_team_block_count = 0

    if team_skills == {skill}:
        all_members_allowed = True

        for e in team_df["employee_id"]:
            if not is_employee_allowed_for_shift(
                e=e,
                sh=sh,
                model_inputs=model_inputs,
                config=config
            ):
                all_members_allowed = False
                break

        if all_members_allowed:
            strict_team_block_count = len(team_df)

    # -------------------------------
    # Available skill members
    # -------------------------------

    skill_members_df = team_df[
        team_df["skill_group"] == skill
    ].copy()

    available_members = []

    for e in skill_members_df["employee_id"]:
        if is_employee_allowed_for_shift(
            e=e,
            sh=sh,
            model_inputs=model_inputs,
            config=config
        ):
            available_members.append(e)

    available_skill_members_count = len(available_members)

    return strict_team_block_count, available_skill_members_count


# ============================================================
# 5. Shift + skill feasibility check
# ============================================================

def check_shift_skill_team_feasibility(model_inputs, config, team_employee_df):
    required_count = model_inputs["required_count"]
    shift_date = model_inputs["shift_date"]
    shift_start = model_inputs["shift_start"]
    shift_end = model_inputs["shift_end"]

    team_ids = sorted(team_employee_df["team_id"].dropna().unique().tolist())

    team_rule_config = config.get("team_rules", {}).get("team_same_shift", {})
    allow_buffer = team_rule_config.get("allow_demand_buffer", True)
    max_buffer = int(team_rule_config.get("max_extra_agents_per_shift_skill", 0))

    if not allow_buffer:
        max_buffer = 0

    rows = []

    for (sh, skill), required in required_count.items():
        required = int(required)

        strict_team_sizes = []
        flexible_team_sizes = []

        strict_team_examples = []
        flexible_team_examples = []

        for team_id in team_ids:
            strict_count, flexible_count = get_team_shift_counts(
                team_id=team_id,
                sh=sh,
                skill=skill,
                team_employee_df=team_employee_df,
                model_inputs=model_inputs,
                config=config
            )

            if strict_count > 0:
                strict_team_sizes.append(strict_count)
                strict_team_examples.append(f"{team_id}({strict_count})")

            if flexible_count > 0:
                flexible_team_sizes.append(flexible_count)
                flexible_team_examples.append(f"{team_id}({flexible_count})")

        strict_feasible, strict_best_count, strict_possible_counts = possible_counts_with_team_sizes(
            team_sizes=strict_team_sizes,
            required=required,
            buffer=max_buffer
        )

        flexible_feasible, flexible_best_count, flexible_possible_counts = possible_counts_with_team_sizes(
            team_sizes=flexible_team_sizes,
            required=required,
            buffer=max_buffer
        )

        rows.append({
            "date": str(shift_date[sh]),
            "shift_id": sh,
            "shift_start": shift_start[sh],
            "shift_end": shift_end[sh],
            "skill_group": skill,
            "required_count": required,
            "buffer": max_buffer,
            "allowed_min": required,
            "allowed_max": required + max_buffer,

            "strict_eligible_team_count": len(strict_team_sizes),
            "strict_total_available": sum(strict_team_sizes),
            "strict_feasible": strict_feasible,
            "strict_best_assigned_count": strict_best_count,

            "flexible_eligible_team_count": len(flexible_team_sizes),
            "flexible_total_available": sum(flexible_team_sizes),
            "flexible_feasible": flexible_feasible,
            "flexible_best_assigned_count": flexible_best_count,

            "strict_team_examples": "; ".join(strict_team_examples[:10]),
            "flexible_team_examples": "; ".join(flexible_team_examples[:10])
        })

    return pd.DataFrame(rows)


# ============================================================
# 6. Daily capacity check
# ============================================================

def check_daily_team_capacity(model_inputs, config, team_employee_df):
    required_count = model_inputs["required_count"]
    shift_date = model_inputs["shift_date"]

    shifts = model_inputs["shifts"]
    skills = sorted(set(skill for _, skill in required_count.keys()))
    dates = sorted(set(str(d) for d in shift_date.values()))

    team_ids = sorted(team_employee_df["team_id"].dropna().unique().tolist())

    rows = []

    for d in dates:
        shifts_on_day = [
            sh for sh in shifts
            if str(shift_date[sh]) == d
        ]

        for skill in skills:
            total_required = sum(
                int(required)
                for (sh, sk), required in required_count.items()
                if sk == skill and str(shift_date[sh]) == d
            )

            strict_daily_capacity = 0
            flexible_daily_capacity = 0

            for team_id in team_ids:
                strict_counts_for_day = []
                flexible_counts_for_day = []

                for sh in shifts_on_day:
                    if required_count.get((sh, skill), 0) <= 0:
                        continue

                    strict_count, flexible_count = get_team_shift_counts(
                        team_id=team_id,
                        sh=sh,
                        skill=skill,
                        team_employee_df=team_employee_df,
                        model_inputs=model_inputs,
                        config=config
                    )

                    strict_counts_for_day.append(strict_count)
                    flexible_counts_for_day.append(flexible_count)

                # Bir team bir günde en fazla 1 shift alacağı için max kapasiteyi alıyoruz
                strict_daily_capacity += max(strict_counts_for_day) if strict_counts_for_day else 0
                flexible_daily_capacity += max(flexible_counts_for_day) if flexible_counts_for_day else 0

            rows.append({
                "date": d,
                "skill_group": skill,
                "total_required": total_required,

                "strict_daily_capacity": strict_daily_capacity,
                "strict_gap": strict_daily_capacity - total_required,

                "flexible_daily_capacity": flexible_daily_capacity,
                "flexible_gap": flexible_daily_capacity - total_required
            })

    return pd.DataFrame(rows)


# ============================================================
# 7. Run all checks
# ============================================================

def run_team_feasibility_check(model_inputs, constraints_config, shift_demand_long_df):
    team_employee_df = build_team_employee_df(model_inputs)

    team_summary_df, mixed_skill_teams_df, mixed_location_teams_df, mixed_flag_teams_df = analyze_team_structure(
        team_employee_df=team_employee_df
    )

    shift_skill_team_feasibility_df = check_shift_skill_team_feasibility(
        model_inputs=model_inputs,
        config=constraints_config,
        team_employee_df=team_employee_df
    )

    daily_team_capacity_df = check_daily_team_capacity(
        model_inputs=model_inputs,
        config=constraints_config,
        team_employee_df=team_employee_df
    )

    strict_shift_problems_df = shift_skill_team_feasibility_df[
        shift_skill_team_feasibility_df["strict_feasible"] == False
    ].copy()

    flexible_shift_problems_df = shift_skill_team_feasibility_df[
        shift_skill_team_feasibility_df["flexible_feasible"] == False
    ].copy()

    strict_daily_capacity_problems_df = daily_team_capacity_df[
        daily_team_capacity_df["strict_gap"] < 0
    ].copy()

    flexible_daily_capacity_problems_df = daily_team_capacity_df[
        daily_team_capacity_df["flexible_gap"] < 0
    ].copy()

    print("\n1. Team summary:")
    display(team_summary_df.head(30))

    print("\n2. Aynı team içinde birden fazla skill_group olan ekipler:")
    display(mixed_skill_teams_df)

    print("\n3. Aynı team içinde birden fazla location olan ekipler:")
    display(mixed_location_teams_df)

    print("\n4. Aynı team içinde farklı izin / uygunluk flagleri olan ekipler:")
    display(mixed_flag_teams_df)

    print("\n5. Strict team block yorumunda daily capacity problemi olan satırlar:")
    display(strict_daily_capacity_problems_df)

    print("\n6. Flexible available-member yorumunda daily capacity problemi olan satırlar:")
    display(flexible_daily_capacity_problems_df)

    print("\n7. Strict team block yorumunda shift + skill bazında karşılanamayan satırlar:")
    display(strict_shift_problems_df.head(100))

    print("\n8. Flexible available-member yorumunda shift + skill bazında karşılanamayan satırlar:")
    display(flexible_shift_problems_df.head(100))

    print("\nÖzet:")
    print(f"Toplam team sayısı: {team_summary_df['team_id'].nunique()}")
    print(f"Mixed skill team sayısı: {len(mixed_skill_teams_df)}")
    print(f"Mixed location team sayısı: {len(mixed_location_teams_df)}")
    print(f"Mixed flag satır sayısı: {len(mixed_flag_teams_df)}")
    print(f"Strict daily capacity problem sayısı: {len(strict_daily_capacity_problems_df)}")
    print(f"Flexible daily capacity problem sayısı: {len(flexible_daily_capacity_problems_df)}")
    print(f"Strict shift-skill problem sayısı: {len(strict_shift_problems_df)}")
    print(f"Flexible shift-skill problem sayısı: {len(flexible_shift_problems_df)}")

    return {
        "team_employee_df": team_employee_df,
        "team_summary_df": team_summary_df,
        "mixed_skill_teams_df": mixed_skill_teams_df,
        "mixed_location_teams_df": mixed_location_teams_df,
        "mixed_flag_teams_df": mixed_flag_teams_df,
        "daily_team_capacity_df": daily_team_capacity_df,
        "strict_daily_capacity_problems_df": strict_daily_capacity_problems_df,
        "flexible_daily_capacity_problems_df": flexible_daily_capacity_problems_df,
        "shift_skill_team_feasibility_df": shift_skill_team_feasibility_df,
        "strict_shift_problems_df": strict_shift_problems_df,
        "flexible_shift_problems_df": flexible_shift_problems_df
    }


# ============================================================
# 8. Execute
# ============================================================

team_feasibility_results = run_team_feasibility_check(
    model_inputs=model_inputs,
    constraints_config=constraints_config,
    shift_demand_long_df=shift_demand_long_df
)
