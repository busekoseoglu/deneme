# %% KONTROL - BUFFER İÇİNDE AMA TALEBE GÖRE EKSİK KALAN VARDİYALAR

missing_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        required = int(talep[(ds, v)])

        missing_rows.append({
            "tarih": str(ds),
            "gun": DAY_TR[pd.to_datetime(ds).weekday()],
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "talep": required,
            "atanan": assigned,
            "gap_to_required": assigned - required,
            "lower_5pct": coverage_lower[(ds, v)],
            "upper_5pct": coverage_upper[(ds, v)],
            "buffer_ici": coverage_lower[(ds, v)] <= assigned <= coverage_upper[(ds, v)],
            "under_buffer": solver.Value(under_buffer[(ds, v)]),
            "over_buffer": solver.Value(over_buffer[(ds, v)]),
            "missing_to_required": solver.Value(missing_to_required[(ds, v)])
        })

missing_check = pd.DataFrame(missing_rows)

print("Toplam missing_to_required:", missing_check["missing_to_required"].sum())
print("Toplam under_buffer:", missing_check["under_buffer"].sum())
print("Toplam over_buffer:", missing_check["over_buffer"].sum())

print("\nBuffer içinde ama talebin altında kalan vardiya sayısı:")
print(len(missing_check[
    (missing_check["buffer_ici"] == True) &
    (missing_check["gap_to_required"] < 0)
]))

display(
    missing_check[
        (missing_check["missing_to_required"] > 0)
    ]
    .sort_values(
        ["missing_to_required", "tarih", "baslangic"],
        ascending=[False, True, True]
    )
)
