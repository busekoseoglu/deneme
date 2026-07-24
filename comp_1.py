# --------------------------------------------------
# ÇİFT OFF HESABI - MODELDEKİ pair_off ÜZERİNDEN
# --------------------------------------------------

cift_off_rows = []

for a in AGENTS:

    agent_code = str(a).strip()

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs):

        pair_key = (a, i)

        if pair_key not in pair_off:
            continue

        cift_off_rows.append({
            "agent_user_code": agent_code,
            "cift_off_sayisi": int(
                solver.Value(pair_off[pair_key])
            )
        })


aylik_cift_off_df = (
    pd.DataFrame(cift_off_rows)
    .groupby(
        "agent_user_code",
        as_index=False
    )
    .agg(
        cift_off_sayisi=(
            "cift_off_sayisi",
            "sum"
        )
    )
)




aylik_norm_mesai_df = (
    calendar_value_df
    .groupby(
        "agent_user_code",
        as_index=False
    )
    .agg(
        norm_calisma_sayisi=(
            "norm_calisma_mi",
            "sum"
        ),
        mesai_sayisi=(
            "mesai_mi",
            "sum"
        )
    )
)



aylik_calisma_ozet_df = (
    aylik_norm_mesai_df
    .merge(
        aylik_cift_off_df,
        on="agent_user_code",
        how="left"
    )
)

ozet_kolonlari = [
    "norm_calisma_sayisi",
    "mesai_sayisi",
    "cift_off_sayisi"
]

aylik_calisma_ozet_df[ozet_kolonlari] = (
    aylik_calisma_ozet_df[ozet_kolonlari]
    .fillna(0)
    .astype(int)
)



calendar_shift_df = calendar_shift_df.merge(
    aylik_calisma_ozet_df,
    on="agent_user_code",
    how="left"
)

calendar_shift_df[ozet_kolonlari] = (
    calendar_shift_df[ozet_kolonlari]
    .fillna(0)
    .astype(int)
)
