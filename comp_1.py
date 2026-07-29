# df_off wide -> long

gun_kolonlari = [
    c for c in df_off.columns
    if str(c).startswith("gun_")
]

df_off_long = df_off.melt(
    id_vars=["agent_user_code", "izin_tipi"],
    value_vars=gun_kolonlari,
    var_name="gun_kolonu",
    value_name="deger"
)

df_off_long = df_off_long[
    pd.to_numeric(df_off_long["deger"], errors="coerce").fillna(0) == 1
].copy()

df_off_long["gun"] = (
    df_off_long["gun_kolonu"]
    .str.extract(r"(\d+)")
    .astype(int)
)

df_off_long["tarih"] = pd.to_datetime(
    "2026-08-" + df_off_long["gun"].astype(str).str.zfill(2)
)

df_off_long = df_off_long[
    ["agent_user_code", "tarih", "izin_tipi"]
].assign(kaynak="df_off")


# df_izin zaten long formatta

df_izin_long = df_izin[
    ["agent_user_code", "tarih", "izin_tipi"]
].copy()

df_izin_long["tarih"] = pd.to_datetime(
    df_izin_long["tarih"]
).dt.normalize()

df_izin_long["kaynak"] = "df_izin"


# Aynı agent + aynı tarih çakışmaları

df_cakisma = pd.concat(
    [df_off_long, df_izin_long],
    ignore_index=True
)

df_cakisma["agent_user_code"] = (
    df_cakisma["agent_user_code"]
    .astype(str)
    .str.strip()
)

df_cakisma["izin_tipi"] = (
    df_cakisma["izin_tipi"]
    .astype(str)
    .str.strip()
    .str.lower()
)

df_cakisma = (
    df_cakisma
    .groupby(
        ["agent_user_code", "tarih"],
        as_index=False
    )
    .agg(
        kayit_sayisi=("izin_tipi", "size"),
        izin_tipleri=(
            "izin_tipi",
            lambda x: " | ".join(sorted(set(x)))
        ),
        kaynaklar=(
            "kaynak",
            lambda x: " | ".join(sorted(set(x)))
        )
    )
)

df_cakisma = df_cakisma[
    df_cakisma["kayit_sayisi"] > 1
].copy()

display(df_cakisma)
