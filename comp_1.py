# %% DOĞRU HAFTALIK ÇALIŞMA / MESAİ DEBUG

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
            "raw_normal_target": raw_normal_target,
            "feasible_day_count": len(feasible_days),
            "normal_target": normal_target,
            "worked_days": worked_days,
            "overtime_week": overtime_val,
            "worked_minus_target": worked_days - normal_target
        })

weekly_debug_df = pd.DataFrame(weekly_debug_rows)

print("worked_minus_target dağılımı:")
display(
    weekly_debug_df["worked_minus_target"]
    .value_counts()
    .sort_index()
)

display(
    weekly_debug_df
    .sort_values(["worked_minus_target", "hafta"], ascending=[True, True])
    .head(50)
)
