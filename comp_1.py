# df_izin'i ortak yapıya getir
df_izin_birlesim = df_izin[
    ["agent_user_code", "tarih", "izin_tipi"]
].copy()

df_izin_birlesim["tarih"] = pd.to_datetime(
    df_izin_birlesim["tarih"]
).dt.normalize()

df_izin_birlesim["kaynak"] = "df_izin"


# df_off_long zaten tarihli ve long formatta olmalı
df_off_birlesim = df_off_long[
    ["agent_user_code", "tarih", "izin_tipi"]
].copy()

df_off_birlesim["tarih"] = pd.to_datetime(
    df_off_birlesim["tarih"]
).dt.normalize()

df_off_birlesim["kaynak"] = "df_off"


# İki veriyi birleştir
df_izin_off = pd.concat(
    [
        df_izin_birlesim,
        df_off_birlesim
    ],
    ignore_index=True
)

# Temizlik
df_izin_off["agent_user_code"] = (
    df_izin_off["agent_user_code"]
    .astype(str)
    .str.strip()
)

df_izin_off["izin_tipi"] = (
    df_izin_off["izin_tipi"]
    .astype(str)
    .str.strip()
    .str.lower()
)

# Öncelik
oncelik_map = {
    "izin": 3,
    "off_t2": 2,
    "off_t": 1
}

df_izin_off["oncelik"] = (
    df_izin_off["izin_tipi"]
    .map(oncelik_map)
    .fillna(0)
    .astype(int)
)

# Aynı agent + aynı tarihte en yüksek öncelikli kayıt kalsın
df_izin_off_model = (
    df_izin_off
    .sort_values(
        [
            "agent_user_code",
            "tarih",
            "oncelik"
        ],
        ascending=[
            True,
            True,
            False
        ]
    )
    .drop_duplicates(
        subset=[
            "agent_user_code",
            "tarih"
        ],
        keep="first"
    )
    .drop(columns="oncelik")
    .sort_values(
        [
            "agent_user_code",
            "tarih"
        ]
    )
    .reset_index(drop=True)
)

display(df_izin_off_model)
