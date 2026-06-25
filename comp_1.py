coverage_for_excel["weekday"] = pd.to_datetime(coverage_for_excel["tarih"]).dt.weekday
coverage_for_excel["hafta_ici"] = coverage_for_excel["weekday"].isin([0, 1, 2, 3, 4])

coverage_weektype = (
    coverage_for_excel
    .groupby("hafta_ici", as_index=False)
    .agg(
        toplam_talep=("talep", "sum"),
        toplam_atanan=("atanan", "sum"),
        toplam_under=("under_buffer", "sum"),
        toplam_over=("over_buffer", "sum")
    )
)

display(coverage_weektype)

weekly_debug_rows = []

for a in AGENTS:
    izinli = izin_map.get(a, set())

    for wk, days_in_week in week_days.items():

        izin_count_this_week = sum(
            1
            for ds in days_in_week
            if pd.to_datetime(ds).date() in izinli
        )

        raw_normal_target = max(0, 5 - izin_count_this_week)

        feasible_days = []

        for ds in days_in_week:
            d_date = pd.to_datetime(ds).date()

            if d_date in izinli:
                continue

            has_option = any(
                (a, ds, v) in x
                for v in gun_vardiyalari.get(ds, [])
            )

            if has_option:
                feasible_days.append(ds)

        normal_target = min(raw_normal_target, len(feasible_days))

        worked_days = sum(
            solver.Value(work[(a, ds)])
            for ds in days_in_week
        )

        overtime_val = solver.Value(overtime_week[(a, wk)])

        weekly_debug_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "haftadaki_gun": len(days_in_week),
            "izin_count_this_week": izin_count_this_week,
            "normal_target": normal_target,
            "worked_days": worked_days,
            "overtime_week": overtime_val,
            "worked_minus_target": worked_days - normal_target
        })

weekly_debug_df = pd.DataFrame(weekly_debug_rows)

print("normal_target dağılımı:")
display(
    weekly_debug_df["normal_target"]
    .value_counts()
    .sort_index()
)

print("izin_count_this_week dağılımı:")
display(
    weekly_debug_df["izin_count_this_week"]
    .value_counts()
    .sort_index()
)

print("worked_minus_target dağılımı:")
display(
    weekly_debug_df["worked_minus_target"]
    .value_counts()
    .sort_index()
)
