# ==================================================
# 7) AYLIK TAKVİM
# ==================================================

calendar_value_df = agent_day_plan_df.copy()

calendar_value_df["date"] = pd.to_datetime(
    calendar_value_df["date"]
).dt.normalize()

calendar_value_df["weekday"] = (
    calendar_value_df["date"].dt.weekday
)

# Mevcut day_week map'i varsa onu kullan
calendar_value_df["week"] = (
    calendar_value_df["date"]
    .map(day_week)
)

calendar_value_df["calendar_value"] = np.where(
    calendar_value_df["assigned"] == 1,
    calendar_value_df["status"].fillna("") +
    " | " +
    calendar_value_df["assigned_shift"].fillna("") +
    " (" +
    calendar_value_df["shift_start"].fillna("") +
    "-" +
    calendar_value_df["shift_end"].fillna("") +
    ")",
    calendar_value_df["status"].fillna("")
)


# ==================================================
# 7.1) HAFTALIK NORM / MESAİ / ÇİFT OFF HESABI
# ==================================================

haftalik_calisma_rows = []

for (agent_user_code, week), grp in calendar_value_df.groupby(
    ["agent_user_code", "week"],
    dropna=False
):

    # Pazartesi-Cuma arasında çalışılmayan gün sayısı
    hafta_ici_off_sayisi = int(
        (
            (grp["weekday"].isin([0, 1, 2, 3, 4]))
            &
            (grp["assigned"] == 0)
        ).sum()
    )

    # Cumartesi-Pazar çalışılan gün sayısı
    hafta_sonu_calisma_sayisi = int(
        (
            (grp["weekday"].isin([5, 6]))
            &
            (grp["assigned"] == 1)
        ).sum()
    )

    # Hafta içindeki OFF kadar hafta sonu çalışma normal sayılır
    norm_calisma_sayisi = min(
        hafta_ici_off_sayisi,
        hafta_sonu_calisma_sayisi
    )

    # Norm sınırını aşan hafta sonu çalışmaları mesai sayılır
    mesai_sayisi = max(
        0,
        hafta_sonu_calisma_sayisi - norm_calisma_sayisi
    )

    # Aynı haftada hem Cumartesi hem Pazar OFF mu?
    cumartesi_rows = grp[grp["weekday"] == 5]
    pazar_rows = grp[grp["weekday"] == 6]

    cumartesi_off = (
        len(cumartesi_rows) > 0
        and (cumartesi_rows["assigned"] == 0).all()
    )

    pazar_off = (
        len(pazar_rows) > 0
        and (pazar_rows["assigned"] == 0).all()
    )

    cift_off_sayisi = int(
        cumartesi_off and pazar_off
    )

    haftalik_calisma_rows.append({
        "agent_user_code": agent_user_code,
        "week": week,
        "hafta_ici_off_sayisi": hafta_ici_off_sayisi,
        "hafta_sonu_calisma_sayisi": hafta_sonu_calisma_sayisi,
        "norm_calisma_sayisi": norm_calisma_sayisi,
        "mesai_sayisi": mesai_sayisi,
        "cift_off_sayisi": cift_off_sayisi,
    })


haftalik_calisma_df = pd.DataFrame(
    haftalik_calisma_rows
)


# ==================================================
# 7.2) AYLIK AGENT TOPLAMLARI
# ==================================================

aylik_calisma_ozet_df = (
    haftalik_calisma_df
    .groupby(
        "agent_user_code",
        as_index=False
    )
    .agg(
        norm_calisma_sayisi=(
            "norm_calisma_sayisi",
            "sum"
        ),
        mesai_sayisi=(
            "mesai_sayisi",
            "sum"
        ),
        cift_off_sayisi=(
            "cift_off_sayisi",
            "sum"
        )
    )
)


# ==================================================
# 7.3) AYLIK TAKVİM PIVOT
# ==================================================

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


# ==================================================
# 7.4) ÖZET KOLONLARINI AYLIK TAKVİME EKLE
# ==================================================

calendar_shift_df = calendar_shift_df.merge(
    aylik_calisma_ozet_df,
    on="agent_user_code",
    how="left"
)

ozet_kolonlari = [
    "norm_calisma_sayisi",
    "mesai_sayisi",
    "cift_off_sayisi"
]

calendar_shift_df[ozet_kolonlari] = (
    calendar_shift_df[ozet_kolonlari]
    .fillna(0)
    .astype(int)
)

display(
    calendar_shift_df[
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "norm_calisma_sayisi",
            "mesai_sayisi",
            "cift_off_sayisi"
        ]
    ].head(20)
)
