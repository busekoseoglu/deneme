# %% [HÜCRE] - AYDA EN AZ 1 CUMARTESİ-PAZAR PEŞ PEŞE OFF
# Her agent için ay içinde en az bir Cumartesi-Pazar çifti tamamen OFF olmalı.
# Yani o Cumartesi work=0 ve o Pazar work=0 olmalı.

weekend_pairs = []

plan_dates = sorted([pd.to_datetime(ds).date() for ds in PLAN_GUNLER])
date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

for d in plan_dates:
    # Cumartesi = 5
    if d.weekday() == 5:
        sunday = d + pd.Timedelta(days=1)

        if sunday in date_to_ds:
            sat_ds = date_to_ds[d]
            sun_ds = date_to_ds[sunday]

            weekend_pairs.append((sat_ds, sun_ds))

print("Cumartesi-Pazar çiftleri:")
for p in weekend_pairs:
    print(p)


# pair_off[(a, i)] = 1 ise agent a, i. hafta sonu çiftinde hem Cumartesi hem Pazar OFF
pair_off = {}

weekend_pair_constraints = 0

for a in AGENTS:
    pair_vars = []

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs):
        pair_off[(a, i)] = model.NewBoolVar(f"pair_off_{a}_{i}")

        # Eğer pair_off = 1 ise Cumartesi çalışamaz
        model.Add(work[(a, sat_ds)] == 0).OnlyEnforceIf(pair_off[(a, i)])

        # Eğer pair_off = 1 ise Pazar çalışamaz
        model.Add(work[(a, sun_ds)] == 0).OnlyEnforceIf(pair_off[(a, i)])

        # Eğer Cumartesi çalışıyorsa pair_off 1 olamaz
        model.Add(pair_off[(a, i)] <= 1 - work[(a, sat_ds)])

        # Eğer Pazar çalışıyorsa pair_off 1 olamaz
        model.Add(pair_off[(a, i)] <= 1 - work[(a, sun_ds)])

        pair_vars.append(pair_off[(a, i)])
        weekend_pair_constraints += 4

    # Her agent için ayda en az 1 Cumartesi-Pazar peş peşe OFF
    if pair_vars:
        model.Add(sum(pair_vars) >= 1)
        weekend_pair_constraints += 1

print("pair_off değişken sayısı:", len(pair_off))
print("Cumartesi-Pazar peş peşe OFF kısıtı:", weekend_pair_constraints)
