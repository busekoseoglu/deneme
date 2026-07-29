# %% [HAZIRLIK] - GERÇEK İZİN MAP
def _b(row, col):
    return (
        pd.to_numeric(
            row.get(col, 0),
            errors="coerce"
        ) == 1
    )
# df_izin_off_model içindeki yalnızca "izin" kayıtları
izin_map = {}

izin_df = df_izin_off_model[
    df_izin_off_model["izin_tipi"] == "izin"
].copy()

for _, row in izin_df.iterrows():

    code = str(row["agent_user_code"]).strip()
    tarih = pd.to_datetime(row["tarih"]).date()

    izin_map.setdefault(code, set()).add(tarih)


# df_tam içindeki tam ay ve tekrarlı izinleri ekle
for _, row in df_tam.iterrows():

    code = str(row["agent_user_code"]).strip()

    # Agentın mevcut izinlerini al
    izin = set(izin_map.get(code, set()))

    # İdari izin veya doğum izni: tüm ay izinli
    if _b(row, "idari_izinli_flg") or _b(row, "dogum_izni_flg"):
        izin = set(GUN_SET)

    else:

        sut_izinli_mi = _b(row, "sut_izni_flg")

        tekrarli_izinler = [
            ("pazartesi_izinli_flg", 0),
            ("sali_izinli_flg", 1),
            ("carsamba_izinli_flg", 2),
            ("persembe_izinli_flg", 3),
            ("cuma_izinli_flg", 4),
        ]

        for flag_kolonu, weekday_no in tekrarli_izinler:

            if not _b(row, flag_kolonu):
                continue

            gunler = {
                d
                for d in GUN_SET
                if d.weekday() == weekday_no
            }

            # Süt izinliyse resmi tatil gününü tekrarlı izne ekleme
            if sut_izinli_mi:
                gunler = {
                    d
                    for d in gunler
                    if not haftada_resmi_tatil_var.get(
                        pd.to_datetime(d).date(),
                        False
                    )
                }

            izin |= gunler

    izin_map[code] = izin


# Kontrol kolonu
df_tam["izin_gun_sayisi"] = (
    df_tam["agent_user_code"]
    .astype(str)
    .str.strip()
    .map(lambda code: len(izin_map.get(code, set())))
)

print("İzinli agent sayısı:", len(izin_map))

display(
    df_tam[
        ["agent_user_code", "izin_gun_sayisi"]
    ]
    .sort_values(
        "izin_gun_sayisi",
        ascending=False
    )
    .head(10)
)
