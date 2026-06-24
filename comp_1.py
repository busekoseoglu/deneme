# %% [KONTROL 1] - ROSTER LONG FORMAT

roster_long = (
    roster
    .reset_index()
    .melt(
        id_vars="agent",
        var_name="tarih",
        value_name="vardiya"
    )
)

roster_long["tarih"] = roster_long["tarih"].astype(str)

# sadece gerçek vardiya alanlar
work_roster = roster_long[
    ~roster_long["vardiya"].isin(["off", "izin"])
].copy()

# vardiya saatlerini ayır
work_roster[["baslangic", "bitis"]] = work_roster["vardiya"].str.split("-", expand=True)

# agent bilgilerini ekle
agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "team",
    "sabah_calisir_flg",
    "hamile_flg",
    "sut_izni_flg",
    "pazartesi_izinli_flg",
    "cuma_izinli_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

work_roster = work_roster.merge(
    agent_info,
    left_on="agent",
    right_on="agent_user_code",
    how="left"
)

display(work_roster.head())
print("Toplam çalışma satırı:", len(work_roster))
