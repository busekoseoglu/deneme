# %% [HÜCRE 12] - HAFTADA 5 GÜN ÇALIŞMA KISITI - GÜVENLİ VERSİYON
# Amaç:
# Normalde agent haftada 5 gün çalışır.
# Ama izin/off/full izin/hafta sonu çalışamaz gibi durumlar yüzünden
# gerçekten çalışabileceği gün sayısı 5'ten azsa, o kadar çalışır.

weekly_work_constraints = 0
TARGET_WORK_DAYS_PER_WEEK = 5

week_days = defaultdict(list)

for ds in PLAN_GUNLER:
    week_days[day_week[ds]].append(ds)

for wk in week_days:
    week_days[wk] = sorted(week_days[wk])


def is_weekend(ds):
    d = pd.to_datetime(ds).date()
    return d.weekday() in [5, 6]


# Agent özel durum map'leri
hamile_agents = set()
sut_agents = set()

for _, row in df_tam.iterrows():
    a = str(row["agent_user_code"]).strip()

    if int(row.get("hamile_flg", 0) or 0) == 1:
        hamile_agents.add(a)

    if int(row.get("sut_izni_flg", 0) or 0) == 1:
        sut_agents.add(a)


for a in AGENTS:
    izinli = izin_map.get(a, set())

    for wk, days_in_week in week_days.items():

        feasible_days = []

        for ds in days_in_week:
            d_date = pd.to_datetime(ds).date()

            # izinliyse çalışamaz
            if d_date in izinli:
                continue

            # hamile / süt izni hafta sonu çalışamaz
            if a in hamile_agents or a in sut_agents:
                if is_weekend(ds):
                    continue

            # o gün en az bir x değişkeni var mı?
            has_option = any(
                (a, ds, v) in x
                for v in gun_vardiyalari.get(ds, [])
            )

            if has_option:
                feasible_days.append(ds)

        # çalışabileceği gün sayısı
        target_days = min(TARGET_WORK_DAYS_PER_WEEK, len(feasible_days))

        # bütün hafta work toplamı target kadar olsun
        model.Add(
            sum(work[(a, ds)] for ds in days_in_week) == target_days
        )

        weekly_work_constraints += 1

print(f"haftada 5 gün çalışma kısıtı: {weekly_work_constraints} agent-hafta")
