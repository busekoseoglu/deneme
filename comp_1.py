# %% [KONTROL 1] - ROSTER LONG FORMAT + AGENT BİLGİLERİ

roster_long = (
    roster
    .reset_index()
    .melt(
        id_vars="agent",
        var_name="tarih",
        value_name="vardiya"
    )
)

roster_long["agent"] = roster_long["agent"].astype(str).str.strip()
roster_long["tarih"] = roster_long["tarih"].astype(str)

# Sadece çalışan satırlar
work_roster = roster_long[
    ~roster_long["vardiya"].isin(["off", "izin"])
].copy()

# Vardiya saatlerini ayır: 09:00-18:00
work_roster[["baslangic", "bitis"]] = work_roster["vardiya"].str.split("-", expand=True)

# Önce df_tam kolonlarını görelim
print("df_tam kolonları:")
print(df_tam.columns.tolist())

# Kontrollerde ihtiyaç duyacağımız kolonlar
needed_cols = [
    "agent_user_code",
    "agent_name",
    "team",
    "sabah_calisir_flg",
    "hamile_flg",
    "sut_izni_flg",
    "pazartesi_izinli_flg",
    "cuma_izinli_flg"
]

# df_tam içinde gerçekten olan kolonları al
existing_cols = [c for c in needed_cols if c in df_tam.columns]

agent_info = df_tam[existing_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

work_roster = work_roster.merge(
    agent_info,
    left_on="agent",
    right_on="agent_user_code",
    how="left"
)

# Eksik flag kolonları varsa 0 olarak ekle
flag_cols = [
    "sabah_calisir_flg",
    "hamile_flg",
    "sut_izni_flg",
    "pazartesi_izinli_flg",
    "cuma_izinli_flg"
]

for col in flag_cols:
    if col not in work_roster.columns:
        work_roster[col] = 0

# Eğer agent_name veya team yoksa boş geç
if "agent_name" not in work_roster.columns:
    work_roster["agent_name"] = None

if "team" not in work_roster.columns:
    work_roster["team"] = None

# Flagleri int'e çevir
for col in flag_cols:
    work_roster[col] = work_roster[col].fillna(0).astype(int)

display(work_roster.head())

print("work_roster kolonları:")
print(work_roster.columns.tolist())

print("Toplam çalışma satırı:", len(work_roster))
