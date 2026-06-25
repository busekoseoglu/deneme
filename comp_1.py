# %% [KONTROL] - BASE DIŞI ÇALIŞANLARA AGENT ÖZELLİKLERİNİ EKLE

agent_cols = [
    "agent_user_code",
    "agent_name",
    "teamleader_name",
    "working_main_group",
    "line_based_main_group",
    "sabah_calisir_flg",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg",
    "idari_izinli_flg",
    "dogum_izni_flg"
]

agent_info = df_tam[agent_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

roster_base_detail = roster_base_check.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

# Özel durum flag'i
flag_cols = [
    "sabah_calisir_flg",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg",
    "idari_izinli_flg",
    "dogum_izni_flg"
]

for c in flag_cols:
    roster_base_detail[c] = pd.to_numeric(
        roster_base_detail[c], errors="coerce"
    ).fillna(0).astype(int)

roster_base_detail["ozel_durumlu"] = (
    (roster_base_detail["sabah_calisir_flg"] == 1) |
    (roster_base_detail["mesaiye_kalamaz_flg"] == 1) |
    (roster_base_detail["hamile_flg"] == 1) |
    (roster_base_detail["sut_izni_flg"] == 1) |
    (roster_base_detail["idari_izinli_flg"] == 1) |
    (roster_base_detail["dogum_izni_flg"] == 1)
).astype(int)

base_disi_df = roster_base_detail[
    roster_base_detail["base_disi"] == 1
].copy()

print("base dışı çalışan satır:", len(base_disi_df))
print("base dışı özel durumlu satır:", base_disi_df["ozel_durumlu"].sum())
print("base dışı normal satır:", len(base_disi_df) - base_disi_df["ozel_durumlu"].sum())

display(
    base_disi_df[
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "tarih",
            "gun",
            "hafta",
            "vardiya",
            "base_vardiya",
            "is_exception",
            "ozel_durumlu",
            "sabah_calisir_flg",
            "mesaiye_kalamaz_flg",
            "hamile_flg",
            "sut_izni_flg"
        ]
    ].sort_values(["hafta", "takim", "tarih"]).head(100)
)
