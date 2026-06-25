team_day_split = (
    roster_df
    .groupby(["hafta", "tarih", "gun", "weekday", "takim"], as_index=False)
    .agg(
        calisan_sayi=("agent_user_code", "nunique"),
        vardiya_sayisi=("vardiya", "nunique")
    )
)

team_day_split["hafta_ici"] = team_day_split["weekday"].isin([0, 1, 2, 3, 4])

weekday_team_viol = team_day_split[
    (team_day_split["hafta_ici"]) &
    (team_day_split["vardiya_sayisi"] > 1)
]

print("Hafta içi bölünen takım-gün sayısı:", len(weekday_team_viol))
display(weekday_team_viol.head(20))



team_day_split = (
    roster_df
    .groupby(["hafta", "tarih", "gun", "weekday", "takim"], as_index=False)
    .agg(
        calisan_sayi=("agent_user_code", "nunique"),
        vardiya_sayisi=("vardiya", "nunique")
    )
)

team_day_split["hafta_ici"] = team_day_split["weekday"].isin([0, 1, 2, 3, 4])

weekday_team_viol = team_day_split[
    (team_day_split["hafta_ici"]) &
    (team_day_split["vardiya_sayisi"] > 1)
]

print("Hafta içi bölünen takım-gün sayısı:", len(weekday_team_viol))
display(weekday_team_viol.head(20))
