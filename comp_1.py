# %% [FINAL OUTPUT] - AGENT GÜNLÜK SHIFT TABLOSU

final_roster = (
    roster
    .reset_index()
    .melt(
        id_vars="agent",
        var_name="tarih",
        value_name="vardiya"
    )
)

final_roster["agent"] = final_roster["agent"].astype(str).str.strip()
final_roster["tarih"] = final_roster["tarih"].astype(str)

# Çalışma / off / izin statüsü
final_roster["status"] = final_roster["vardiya"].apply(
    lambda x: "calisiyor" if x not in ["off", "izin"] else x
)

# Başlangıç / bitiş saatlerini ayır
final_roster["baslangic"] = None
final_roster["bitis"] = None

mask_work = final_roster["status"] == "calisiyor"

final_roster.loc[mask_work, ["baslangic", "bitis"]] = (
    final_roster.loc[mask_work, "vardiya"]
    .str.split("-", expand=True)
    .values
)

# Agent bilgilerini ekle
agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "working_main_group",
    "line_based_main_group",
    "sabah_calisir_flg",
    "hamile_flg",
    "sut_izni_flg",
    "pazartesi_izinli_flg",
    "cuma_izinli_flg",
    "idari_izinli_flg",
    "dogum_izni_flg",
    "mesaiye_kalamaz_flg"
]

existing_cols = [c for c in agent_info_cols if c in df_tam.columns]

agent_info = df_tam[existing_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

final_roster = final_roster.merge(
    agent_info,
    left_on="agent",
    right_on="agent_user_code",
    how="left"
)

# Eksik flag kolonları varsa 0 yap
flag_cols = [
    "sabah_calisir_flg",
    "hamile_flg",
    "sut_izni_flg",
    "pazartesi_izinli_flg",
    "cuma_izinli_flg",
    "idari_izinli_flg",
    "dogum_izni_flg",
    "mesaiye_kalamaz_flg"
]

for col in flag_cols:
    if col not in final_roster.columns:
        final_roster[col] = 0

    final_roster[col] = final_roster[col].fillna(0).astype(int)

# Özel durum özeti
final_roster["ozel_durum"] = ""

final_roster.loc[
    final_roster["sabah_calisir_flg"] == 1,
    "ozel_durum"
] += "sabah_calisir;"

final_roster.loc[
    final_roster["hamile_flg"] == 1,
    "ozel_durum"
] += "hamile;"

final_roster.loc[
    final_roster["sut_izni_flg"] == 1,
    "ozel_durum"
] += "sut_izni;"

final_roster.loc[
    final_roster["mesaiye_kalamaz_flg"] == 1,
    "ozel_durum"
] += "mesaiye_kalamaz;"

final_roster["ozel_durum"] = final_roster["ozel_durum"].replace("", "yok")

# Gün bilgileri
final_roster["tarih_dt"] = pd.to_datetime(final_roster["tarih"])
final_roster["gun_adi"] = final_roster["tarih_dt"].dt.day_name()
final_roster["hafta"] = final_roster["tarih_dt"].dt.isocalendar().week
final_roster["hafta_sonu_flg"] = final_roster["tarih_dt"].dt.weekday.isin([5, 6]).astype(int)

# Kolon sırası
final_cols = [
    "agent",
    "agent_name",
    "takim",
    "working_main_group",
    "line_based_main_group",
    "tarih",
    "gun_adi",
    "hafta",
    "hafta_sonu_flg",
    "vardiya",
    "baslangic",
    "bitis",
    "status",
    "ozel_durum",
    "sabah_calisir_flg",
    "hamile_flg",
    "sut_izni_flg",
    "mesaiye_kalamaz_flg",
    "pazartesi_izinli_flg",
    "cuma_izinli_flg",
    "idari_izinli_flg",
    "dogum_izni_flg"
]

final_cols = [c for c in final_cols if c in final_roster.columns]

final_roster = final_roster[final_cols].sort_values(
    ["takim", "agent_name", "tarih"]
).reset_index(drop=True)

display(final_roster.head(50))

print("Final roster satır sayısı:", len(final_roster))
