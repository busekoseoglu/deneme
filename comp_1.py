# %% [KONTROL] - MESAİ ÖZETİ

overtime_rows = []

agent_info_small = df_tam[
    [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "mesaiye_kalamaz_flg"
    ]
].copy()

agent_info_small["agent_user_code"] = agent_info_small["agent_user_code"].astype(str).str.strip()

for a in AGENTS:
    for wk in WEEKS:
        overtime_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "overtime_week": solver.Value(overtime_week[(a, wk)])
        })

overtime_df = pd.DataFrame(overtime_rows)

overtime_df = overtime_df.merge(
    agent_info_small,
    on="agent_user_code",
    how="left"
)

overtime_month_summary = (
    overtime_df
    .groupby(
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "teamleader_name",
            "mesaiye_kalamaz_flg"
        ],
        as_index=False
    )
    .agg(
        toplam_mesai=("overtime_week", "sum")
    )
)

print("toplam mesai günü:", overtime_df["overtime_week"].sum())
print("mesai yapan agent sayısı:", (overtime_month_summary["toplam_mesai"] > 0).sum())

display(
    overtime_month_summary
    .sort_values("toplam_mesai", ascending=False)
    .head(50)
)

print("mesaiye kalamaz olup mesai yazılan:")
display(
    overtime_month_summary[
        (pd.to_numeric(overtime_month_summary["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1)
        &
        (overtime_month_summary["toplam_mesai"] > 0)
    ]
)
