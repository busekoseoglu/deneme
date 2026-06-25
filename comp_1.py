# %% [HÜCRE 10] - COVERAGE KISITI
# Eski mantık:
# assigned >= required
#
# Yeni mantık:
# assigned + shortage - excess == required
#
# Böylece model infeasible olmaz.
# Eksik kalan yerleri shortage olarak raporlarız.

coverage_constraints = 0

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        vars_shift = [
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
        ]

        required = int(talep[(ds, v)])

        model.Add(
            sum(vars_shift) + shortage[(ds, v)] - excess[(ds, v)] == required
        )

        coverage_constraints += 1

print(f"coverage kısıtı: {coverage_constraints} gün-vardiya")
