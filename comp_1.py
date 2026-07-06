# %% DEBUG - WEEKLY_UNDER MODEL EŞİTLİĞİ TUTUYOR MU?

weekly_equation_check_rows = []

for (a, wk), under_var in weekly_under.items():
    a = str(a).strip()

    if (a, wk) not in weekly_over:
        continue

    days_in_week = week_days[wk]

    # Model haftalık hücresindeki gibi resmi tatil günlerini çıkar
    resmi_tatil_days_this_week = set(
        ds for ds in days_in_week
        if "resmi_tatil_plan_gunleri" in globals()
        and ds in set(resmi_tatil_plan_gunleri)
    )

    izin_days_this_week = set(
        ds for ds in days_in_week
        if ds in izin_map.get(a, set())
        or pd.to_datetime(ds).date() in izin_map.get(a, set())
    )

    izin_normal_days_this_week = izin_days_this_week - resmi_tatil_days_this_week

    normal_work_vars_days = [
        ds for ds in days_in_week
        if (a, ds) in work
        and ds not in resmi_tatil_days_this_week
    ]

    normal_worked_days = sum(
        solver.Value(work[(a, ds)])
        for ds in normal_work_vars_days
    )

    normal_target_check = NORMAL_WORK_DAYS
    normal_target_check -= len(resmi_tatil_days_this_week)
    normal_target_check -= len(izin_normal_days_this_week)
    normal_target_check = max(0, normal_target_check)
    normal_target_check = min(normal_target_check, len(normal_work_vars_days))

    overtime_val = solver.Value(overtime_week[(a, wk)]) if (a, wk) in overtime_week else 0
    under_val = solver.Value(under_var)
    over_val = solver.Value(weekly_over[(a, wk)])

    lhs = normal_worked_days + under_val - over_val
    rhs = normal_target_check + overtime_val

    weekly_equation_check_rows.append({
        "agent_user_code": a,
        "week": wk,
        "normal_worked_days": normal_worked_days,
        "normal_target_check": normal_target_check,
        "overtime_week": overtime_val,
        "weekly_under": under_val,
        "weekly_over": over_val,
        "lhs": lhs,
        "rhs": rhs,
        "equation_ok": lhs == rhs,
        "worked_minus_target": normal_worked_days - normal_target_check,
        "resmi_tatil_count": len(resmi_tatil_days_this_week),
        "izin_normal_count": len(izin_normal_days_this_week),
    })

weekly_equation_check_df = pd.DataFrame(weekly_equation_check_rows)

print("Equation bozuk satır sayısı:", (~weekly_equation_check_df["equation_ok"]).sum())
print("Weekly under toplam:", weekly_equation_check_df["weekly_under"].sum())
print("Weekly over toplam:", weekly_equation_check_df["weekly_over"].sum())

display(
    weekly_equation_check_df
    .sort_values(["weekly_under", "weekly_over"], ascending=False)
    .head(100)
)