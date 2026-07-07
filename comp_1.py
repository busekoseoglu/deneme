# Günlük fazla atama dağılımı
daily_excess_debug_df = (
    coverage_check_df
    .assign(
        gap=lambda d: d["assigned"] - d["required"],
        positive_gap=lambda d: (d["assigned"] - d["required"]).clip(lower=0)
    )
    .groupby(["date", "week", "gun", "weekday", "is_weekend"], as_index=False)
    .agg(
        toplam_required=("required", "sum"),
        toplam_assigned=("assigned", "sum"),
        toplam_gap=("gap", "sum"),
        toplam_fazla=("positive_gap", "sum"),
        fazla_olan_vardiya_sayisi=("positive_gap", lambda x: (x > 0).sum())
    )
    .sort_values(["date"])
)

display(daily_excess_debug_df)


# Haftalık fazla atama dağılımı
weekly_excess_debug_df = (
    daily_excess_debug_df
    .groupby("week", as_index=False)
    .agg(
        plan_gun_sayisi=("date", "nunique"),
        toplam_required=("toplam_required", "sum"),
        toplam_assigned=("toplam_assigned", "sum"),
        toplam_fazla=("toplam_fazla", "sum"),
        ortalama_gunluk_fazla=("toplam_fazla", "mean"),
        max_gunluk_fazla=("toplam_fazla", "max")
    )
    .sort_values("week")
)

display(weekly_excess_debug_df)


# Fazla atama olan gün-vardiya detayları
excess_shift_debug_df = (
    coverage_check_df
    .assign(
        gap=lambda d: d["assigned"] - d["required"],
        positive_gap=lambda d: (d["assigned"] - d["required"]).clip(lower=0)
    )
    .query("positive_gap > 0")
    .sort_values(["date", "positive_gap"], ascending=[True, False])
)

display(excess_shift_debug_df)


