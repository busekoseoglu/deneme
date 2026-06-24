# %% [KONTROL] - COVERAGE / TALEP KONTROLÜ
# roster vardiya değeri saat aralığı olduğu için
# kontrolü tarih + başlangıç + bitiş üzerinden yapıyoruz.

roster_long = (
    roster
    .reset_index()
    .melt(
        id_vars="agent",
        var_name="tarih",
        value_name="vardiya_saat"
    )
)

roster_long["tarih"] = roster_long["tarih"].astype(str)

# sadece çalışan satırlar
work_roster = roster_long[
    ~roster_long["vardiya_saat"].isin(["off", "izin"])
].copy()

# vardiya_saat: 09:00-18:00 gibi
work_roster[["baslangic", "bitis"]] = work_roster["vardiya_saat"].str.split("-", expand=True)

assigned_df = (
    work_roster
    .groupby(["tarih", "baslangic", "bitis"])
    .size()
    .reset_index(name="assigned_count")
)

demand_df = df_talep[
    ["tarih", "vardiya", "baslangic", "bitis", "talep"]
].copy()

demand_df["tarih"] = demand_df["tarih"].astype(str)
demand_df["baslangic"] = demand_df["baslangic"].astype(str)
demand_df["bitis"] = demand_df["bitis"].astype(str)

coverage_check = demand_df.merge(
    assigned_df,
    on=["tarih", "baslangic", "bitis"],
    how="left"
)

coverage_check["assigned_count"] = coverage_check["assigned_count"].fillna(0).astype(int)
coverage_check["diff"] = coverage_check["assigned_count"] - coverage_check["talep"]

coverage_problem_df = coverage_check[coverage_check["diff"] != 0]

display(coverage_problem_df)

print("Coverage problem sayısı:", len(coverage_problem_df))
