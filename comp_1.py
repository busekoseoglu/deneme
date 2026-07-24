# ==================================================
# 7.1) AYLIK NORM / MESAİ / ÇİFT OFF HESABI
# ==================================================

calendar_value_df["status_kontrol"] = (
    calendar_value_df["status"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
)

calendar_value_df["weekday"] = (
    pd.to_datetime(calendar_value_df["date"]).dt.weekday
)

calendar_value_df["week"] = (
    calendar_value_df["date"].map(day_week)
)


# --------------------------------------------------
# HAFTA SONU ÇALIŞMA TİPİ
# --------------------------------------------------

calendar_value_df["hafta_sonu_calisma"] = (
    calendar_value_df["weekday"].isin([5, 6])
    &
    (calendar_value_df["assigned"] == 1)
)

# Model tarafından NORMAL_MESAI yazılmış hafta sonu çalışmaları
calendar_value_df["mesai_mi"] = (
    calendar_value_df["hafta_sonu_calisma"]
    &
    calendar_value_df["status_kontrol"].str.contains(
        "NORMAL_MESAI",
        na=False
    )
)

# Hafta sonu çalışıyor ama NORMAL_MESAI değilse norm çalışma
calendar_value_df["norm_calisma_mi"] = (
    calendar_value_df["hafta_sonu_calisma"]
    &
    ~calendar_value_df["mesai_mi"]
)


# --------------------------------------------------
# ÇİFT OFF HESABI
# --------------------------------------------------
# Yalnızca Cumartesi ve Pazarın ikisi de gerçek OFF ise 1.
# İZİN, RESMİ TATİL veya başka bir çalışmama durumu OFF değildir.

cift_off_rows = []

for (agent_user_code, week), grp in calendar_value_df.groupby(
    ["agent_user_code", "week"],
    dropna=False
):

    cumartesi = grp[grp["weekday"] == 5]
    pazar = grp[grp["weekday"] == 6]

    # Parça haftada Cumartesi veya Pazar yoksa çift OFF sayma
    if cumartesi.empty or pazar.empty:
        cift_off = 0

    else:
        cumartesi_gercek_off = (
            cumartesi["status_kontrol"] == "OFF"
        ).all()

        pazar_gercek_off = (
            pazar["status_kontrol"] == "OFF"
        ).all()

        cift_off = int(
            cumartesi_gercek_off
            and pazar_gercek_off
        )

    cift_off_rows.append({
        "agent_user_code": agent_user_code,
        "week": week,
        "cift_off_sayisi": cift_off
    })


haftalik_cift_off_df = pd.DataFrame(cift_off_rows)


# --------------------------------------------------
# AYLIK AGENT ÖZETİ
# --------------------------------------------------

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

aylik_cift_off_df = (
    haftalik_cift_off_df
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

display(
    aylik_calisma_ozet_df
    .sort_values("agent_user_code")
    .reset_index(drop=True)
)


calendar_shift_df = calendar_value_df.pivot_table(
    index=[
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name"
    ],
    columns="date",
    values="calendar_value",
    aggfunc="first"
).reset_index()

calendar_shift_df.columns = [
    str(c)
    for c in calendar_shift_df.columns
]


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
