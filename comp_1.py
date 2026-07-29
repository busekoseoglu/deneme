# Aynı agent aynı tarihte birden fazla kayıt var mı?

df_cakisma = (
    pd.concat([
        df_off[["agent_user_code", "tarih", "izin_tipi"]].assign(kaynak="df_off"),
        df_izin[["agent_user_code", "tarih", "izin_tipi"]].assign(kaynak="df_izin")
    ])
    .assign(
        agent_user_code=lambda x: x["agent_user_code"].astype(str).str.strip(),
        tarih=lambda x: pd.to_datetime(x["tarih"]).dt.normalize(),
        izin_tipi=lambda x: x["izin_tipi"].astype(str).str.strip().str.lower()
    )
)

df_cakisma = (
    df_cakisma
    .groupby(["agent_user_code", "tarih"], as_index=False)
    .agg(
        kayit_sayisi=("izin_tipi", "size"),
        izin_tipleri=("izin_tipi", lambda x: " | ".join(sorted(set(x)))),
        kaynaklar=("kaynak", lambda x: " | ".join(sorted(set(x))))
    )
)

df_cakisma = df_cakisma[
    df_cakisma["kayit_sayisi"] > 1
]

display(df_cakisma)
