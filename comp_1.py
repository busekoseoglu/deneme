# %% [KONTROL 2] - COVERAGE / TALEP KONTROLÜ

assigned_df = (
    work_roster
    .groupby(["tarih", "vardiya"])
    .size()
    .reset_index(name="assigned_count")
)

demand_df = df_talep[["tarih", "vardiya", "talep"]].copy()
demand_df["tarih"] = demand_df["tarih"].astype(str)

coverage_check = demand_df.merge(
    assigned_df,
    on=["tarih", "vardiya"],
    how="left"
)

coverage_check["assigned_count"] = coverage_check["assigned_count"].fillna(0).astype(int)
coverage_check["diff"] = coverage_check["assigned_count"] - coverage_check["talep"]

coverage_problem_df = coverage_check[coverage_check["diff"] != 0]

display(coverage_problem_df)
print("Coverage problem sayısı:", len(coverage_problem_df))
