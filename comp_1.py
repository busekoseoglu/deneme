df_roster_long.groupby("agent_user_code")["durum"].value_counts().unstack(fill_value=0).head()


w27_roster = df_roster_long[
    df_roster_long["date"].astype(str).isin(["2026-06-29", "2026-06-30"])
]

w27_agent_summary = (
    w27_roster
    .assign(calisti=lambda d: (d["durum"] == "ÇALIŞTI").astype(int))
    .groupby("agent_user_code", as_index=False)
    .agg(
        w27_gorunen_gun_sayisi=("date", "nunique"),
        w27_calistigi_gun=("calisti", "sum")
    )
)

w27_double_off = w27_agent_summary[
    w27_agent_summary["w27_calistigi_gun"] == 0
]

print("29-30 Haziran ikisinde de çalışmayan agent sayısı:", len(w27_double_off))
display(w27_double_off.head(20))
