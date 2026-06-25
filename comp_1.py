coverage_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        req = int(talep[(ds, v)])

        coverage_rows.append({
            "tarih": str(ds),
            "gun": DAY_TR[pd.to_datetime(ds).weekday()],
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "talep": req,
            "lower_10pct": coverage_lower[(ds, v)],
            "upper_10pct": coverage_upper[(ds, v)],
            "atanan": assigned,
            "gap": assigned - req,
            "under_buffer": solver.Value(under_buffer[(ds, v)]),
            "over_buffer": solver.Value(over_buffer[(ds, v)]),
            "buffer_ici": coverage_lower[(ds, v)] <= assigned <= coverage_upper[(ds, v)]
        })

coverage_for_excel = pd.DataFrame(coverage_rows).sort_values(["tarih", "baslangic"])

print("toplam under_buffer:", coverage_for_excel["under_buffer"].sum())
print("toplam over_buffer:", coverage_for_excel["over_buffer"].sum())

display(
    coverage_for_excel[
        (coverage_for_excel["under_buffer"] > 0) |
        (coverage_for_excel["over_buffer"] > 0)
    ]
)
