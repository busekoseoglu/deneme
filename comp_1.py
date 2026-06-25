# Under / over en çok hangi vardiyalarda?

coverage_shift_summary = (
    coverage_for_excel
    .groupby(["vardiya", "baslangic", "bitis"], as_index=False)
    .agg(
        toplam_talep=("talep", "sum"),
        toplam_atanan=("atanan", "sum"),
        toplam_under=("under_buffer", "sum"),
        toplam_over=("over_buffer", "sum"),
        gun_sayisi=("tarih", "nunique")
    )
)

display(
    coverage_shift_summary
    .sort_values("toplam_under", ascending=False)
    .head(20)
)

display(
    coverage_shift_summary
    .sort_values("toplam_over", ascending=False)
    .head(20)
)

# Gün bazlı under / over

coverage_day_summary = (
    coverage_for_excel
    .groupby(["tarih", "gun"], as_index=False)
    .agg(
        toplam_talep=("talep", "sum"),
        toplam_atanan=("atanan", "sum"),
        toplam_under=("under_buffer", "sum"),
        toplam_over=("over_buffer", "sum")
    )
)

display(
    coverage_day_summary
    .sort_values("toplam_under", ascending=False)
    .head(20)
)

display(
    coverage_day_summary
    .sort_values("toplam_over", ascending=False)
    .head(20)
)


# Mesai değişkeni haftalık çalışma gününe doğru bağlanmış mı?

weekly_debug_rows = []

for a in AGENTS:
    izinli = izin_map.get(a, set())

    for wk, days_in_week in week_days.items():

        izin_count_this_week = sum(
            1
            for ds in days_in_week
            if pd.to_datetime(ds).date() in izinli
        )

        normal_target = max(0, 5 - izin_count_this_week)

        worked_days = sum(
            solver.Value(work[(a, ds)])
            for ds in days_in_week
        )

        overtime_val = solver.Value(overtime_week[(a, wk)])

        weekly_debug_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "izin_count_this_week": izin_count_this_week,
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
    .sort_values("worked_minus_target", ascending=False)
    .head(50)
)
