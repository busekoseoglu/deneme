# %% [HÜCRE 13] - MAKSİMUM 6 GÜN ÜST ÜSTE ÇALIŞMA KISITI
# Herhangi ardışık 7 gün içinde en fazla 6 çalışma günü olabilir.
# Yani 7 gün üst üste çalışma yasak.

max_consecutive_constraints = 0

MAX_CONSECUTIVE_WORK_DAYS = 6
WINDOW_DAYS = 7

plan_dates = sorted([pd.to_datetime(ds).date() for ds in PLAN_GUNLER])

date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

for a in AGENTS:
    for i in range(0, len(plan_dates) - WINDOW_DAYS + 1):
        window_dates = plan_dates[i:i + WINDOW_DAYS]

        window_ds = [
            date_to_ds[d]
            for d in window_dates
            if d in date_to_ds
        ]

        model.Add(
            sum(work[(a, ds)] for ds in window_ds) <= MAX_CONSECUTIVE_WORK_DAYS
        )

        max_consecutive_constraints += 1

print(f"max 6 gün üst üste çalışma kısıtı: {max_consecutive_constraints} adet")
