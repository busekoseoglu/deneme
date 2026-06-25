# %% KONTROL - CUMARTESİ-PAZAR PEŞ PEŞE OFF

weekend_off_rows = []

for a in AGENTS:
    off_pair_count = 0

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs):
        sat_work = solver.Value(work[(a, sat_ds)])
        sun_work = solver.Value(work[(a, sun_ds)])

        both_off = int((sat_work == 0) and (sun_work == 0))

        if both_off == 1:
            off_pair_count += 1

        weekend_off_rows.append({
            "agent_user_code": a,
            "pair_no": i,
            "cumartesi": sat_ds,
            "pazar": sun_ds,
            "cumartesi_work": sat_work,
            "pazar_work": sun_work,
            "both_off": both_off
        })

weekend_off_check = pd.DataFrame(weekend_off_rows)

agent_weekend_off_summary = (
    weekend_off_check
    .groupby("agent_user_code", as_index=False)
    .agg(
        toplam_pes_pese_hafta_sonu_off=("both_off", "sum")
    )
)

viol_weekend_pair = agent_weekend_off_summary[
    agent_weekend_off_summary["toplam_pes_pese_hafta_sonu_off"] < 1
]

print("Peş peşe Cumartesi-Pazar OFF almayan agent sayısı:", len(viol_weekend_pair))
display(viol_weekend_pair.head(20))
