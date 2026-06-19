# 1. Model sonucundan gerçekleşen kişi sayısını hesapla
assigned_count_df = (
    roster_df
    .groupby(["date", "shift_start", "shift_end", "skill_group"])
    .size()
    .reset_index(name="assigned_count")
)

# 2. Demand tarafındaki beklenen kişi sayısını al
demand_check_df = (
    shift_demand_long_df[
        ["date", "shift_start", "shift_end", "skill_group", "required_count"]
    ]
    .copy()
)

# 3. Karşılaştır
comparison_df = demand_check_df.merge(
    assigned_count_df,
    on=["date", "shift_start", "shift_end", "skill_group"],
    how="left"
)

# Eğer hiç atama yoksa NaN gelir, 0 yapalım
comparison_df["assigned_count"] = comparison_df["assigned_count"].fillna(0).astype(int)

# 4. Fark hesapla
comparison_df["diff"] = (
    comparison_df["assigned_count"] - comparison_df["required_count"]
)

comparison_df.head(20)
