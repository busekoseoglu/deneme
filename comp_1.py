# %% [HÜCRE] - TALEP KARŞILAMA KISITI
# Talep minimum karşılanır. Fazla atama olabilir.

coverage_constraints = 0

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        vars_shift = [
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
        ]

        required = int(talep[(ds, v)])

        model.Add(sum(vars_shift) >= required)
        coverage_constraints += 1

print(f"coverage kısıtı: {coverage_constraints} gün-vardiya")


# %% [HÜCRE] - HER AGENT HAFTADA 5 GÜN ÇALIŞSIN

weekly_work_constraints = 0

WEEKLY_WORK_DAYS = 5

def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


# haftalara göre günleri grupla
week_days = {}

for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


for a in AGENTS:
    for wk, days in week_days.items():

        # Bu agent için o hafta çalışabileceği x değişkenleri
        vars_week = [
            x[(a, ds, v)]
            for ds in days
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if not vars_week:
            continue

        # O hafta agent'ın kaç farklı günü çalışabileceğini bul
        available_days = []

        for ds in days:
            day_vars = [
                x[(a, ds, v)]
                for v in gun_vardiyalari.get(ds, [])
                if (a, ds, v) in x
            ]

            if day_vars:
                available_days.append(ds)

        available_day_count = len(available_days)

        # Normalde 5 gün çalışsın.
        # Ama izinlerden dolayı o hafta 5 günden az müsaitse,
        # maksimum müsait olduğu kadar çalışsın.
        required_work_days = min(WEEKLY_WORK_DAYS, available_day_count)

        if required_work_days == 0:
            continue

        model.Add(sum(vars_week) == required_work_days)
        weekly_work_constraints += 1

print("haftalık 5 gün çalışma kısıtı:", weekly_work_constraints)
