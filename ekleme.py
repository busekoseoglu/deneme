    # ------------------------------------------------------------
    # 3.7 Daily team shift pattern penalty
    #
    # Mantık:
    # Aynı ekip aynı gün çok fazla farklı vardiyaya bölünmesin.
    #
    # Örnek:
    # Team A bir günde 6 farklı shift pattern kullanırsa:
    # allowed = 2
    # extra = 6 - 2 = 4
    # ceza = 4 * EXTRA_DAILY_TEAM_SHIFT_PATTERN_PENALTY
    #
    # Bu hard constraint değil, ağır soft penalty.
    # ------------------------------------------------------------

    daily_team_pattern_used = {}
    daily_extra_pattern_count = {}

    for team_id, members in team_members.items():
        team_name = safe_var_name(team_id)

        for d, day_shifts in shifts_by_date.items():
            date_name = safe_var_name(d)

            day_patterns = sorted({
                get_shift_pattern(sh, model_inputs)
                for sh in day_shifts
            })

            pattern_used_vars_for_day = []

            for pattern in day_patterns:
                pattern_name = safe_var_name(pattern)

                pattern_shifts = [
                    sh for sh in day_shifts
                    if get_shift_pattern(sh, model_inputs) == pattern
                ]

                member_pattern_vars = [
                    assign[e, sh]
                    for e in members
                    for sh in pattern_shifts
                    if (e, sh) in assign
                ]

                pattern_used_var = model.NewBoolVar(
                    f"daily_team_pattern_used_{team_name}_{date_name}_{pattern_name}"
                )

                daily_team_pattern_used[team_id, d, pattern] = pattern_used_var

                if member_pattern_vars:
                    for var in member_pattern_vars:
                        model.Add(pattern_used_var >= var)

                    model.Add(pattern_used_var <= sum(member_pattern_vars))
                else:
                    model.Add(pattern_used_var == 0)

                pattern_used_vars_for_day.append(pattern_used_var)

            if pattern_used_vars_for_day:
                pattern_count = sum(pattern_used_vars_for_day)

                max_extra_possible = max(
                    0,
                    len(pattern_used_vars_for_day) - MAX_TEAM_SHIFT_PATTERNS_PER_DAY
                )

                extra_count_var = model.NewIntVar(
                    0,
                    max_extra_possible,
                    f"daily_extra_pattern_count_{team_name}_{date_name}"
                )

                daily_extra_pattern_count[team_id, d] = extra_count_var

                model.Add(
                    extra_count_var >= pattern_count - MAX_TEAM_SHIFT_PATTERNS_PER_DAY
                )

                objective_terms.append(
                    EXTRA_DAILY_TEAM_SHIFT_PATTERN_PENALTY * extra_count_var
                )

    print(f"Daily team pattern used var sayısı: {len(daily_team_pattern_used)}")
    print(f"Daily extra pattern count var sayısı: {len(daily_extra_pattern_count)}")