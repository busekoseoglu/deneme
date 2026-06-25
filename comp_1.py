# %% [HÜCRE 12] - HAFTADA 5 GÜN ÇALIŞMA KISITI
# Her agent haftada 5 gün çalışır.
# Ama ayın son haftası gibi plan datasında eksik gün varsa, o hafta mevcut gün kadar çalışabilir.
# İzinli olduğu için x değişkeni hiç açılmayan günler zaten çalışılabilir gün sayısına dahil edilmez.

weekly_work_constraints = 0
TARGET_WORK_DAYS_PER_WEEK = 5

week_days = defaultdict(list)

for ds in PLAN_GUNLER:
    week_days[day_week[ds]].append(ds)

for wk in week_days:
    week_days[wk] = sorted(week_days[wk])

for a in AGENTS:
    for wk, days_in_week in week_days.items():

        # Agent'ın o hafta gerçekten çalışabileceği günler
        # Yani o gün için en az bir x değişkeni varsa available kabul ediyoruz.
        available_days = []

        for ds in days_in_week:
            has_option = any(
                (a, ds, v) in x
                for v in gun_vardiyalari.get(ds, [])
            )

            if has_option:
                available_days.append(ds)

        # Eğer agent o hafta hiç çalışabilir değilse 0'a sabitle
        if len(available_days) == 0:
            for ds in days_in_week:
                model.Add(work[(a, ds)] == 0)
            continue

        # Tam hafta ise 5 gün.
        # Eksik hafta ise örn. ay sonunda 2 gün varsa 2 gün.
        # Çok fazla izin varsa available gün sayısı 5'ten az olabilir; o zaman available kadar.
        target_days = min(TARGET_WORK_DAYS_PER_WEEK, len(available_days))

        model.Add(
            sum(work[(a, ds)] for ds in days_in_week) == target_days
        )

        weekly_work_constraints += 1

print(f"haftada 5 gün çalışma kısıtı: {weekly_work_constraints} agent-hafta")
