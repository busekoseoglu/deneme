# %% [KONTROL] - ÖZEL DURUM FLAGLERİ DOĞRU GELMİŞ Mİ?

special_cols = ["sabah_calisir_flg", "hamile_flg", "sut_izni_flg"]

print("work_roster satır sayısı:", len(work_roster))

for col in special_cols:
    print(col, "kolon var mı:", col in work_roster.columns)
    if col in work_roster.columns:
        print(col, "toplam:", work_roster[col].fillna(0).astype(int).sum())

display(
    work_roster[
        (work_roster["sabah_calisir_flg"].fillna(0).astype(int) == 1) |
        (work_roster["hamile_flg"].fillna(0).astype(int) == 1) |
        (work_roster["sut_izni_flg"].fillna(0).astype(int) == 1)
    ][
        ["agent", "agent_name", "takim", "tarih", "vardiya",
         "sabah_calisir_flg", "hamile_flg", "sut_izni_flg"]
    ].head(50)
)
