# %% [HÜCRE 9B] - MESAİ DEĞİŞKENLERİ
# overtime_week[a, wk] = agent a, hafta wk içinde mesai yaptı mı?
# 0/1 olacak. Yani haftada max 1 mesai günü gibi düşünüyoruz.
# Ay toplamında max 2 mesai olacak.

overtime_week = {}

for a in AGENTS:
    for wk in WEEKS:
        overtime_week[(a, wk)] = model.NewBoolVar(f"overtime_week_{a}_{wk}")

print("overtime_week değişken sayısı:", len(overtime_week))


# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ KISITI
# Normal kural:
# Agent haftada 5 gün çalışır.
#
# Yeni bilgi:
# Eğer o hafta 1 gün izinliyse 4 gün çalışır.
# Eğer 2 gün izinliyse 3 gün çalışır.
#
# Mesai:
# Agent normal hedefinin 1 gün üstüne çıkabilir.
# Bu 6. gün mesai sayılır.
# Haftada max 1 mesai.
# Ayda max 2 mesai.
# mesaiye_kalamaz_flg = 1 ise mesai yapamaz.

weekly_work_constraints = 0
monthly_overtime_constraints = 0
no_overtime_constraints = 0

NORMAL_WORK_DAYS = 5
MAX_OVERTIME_PER_MONTH = 2

# hafta -> günler
week_days = defaultdict(list)

for ds in PLAN_GUNLER:
    week_days[day_week[ds]].append(ds)

for wk in week_days:
    week_days[wk] = sorted(week_days[wk])


# mesaiye kalamaz agentlar
mesaiye_kalamaz_agents = set(
    df_tam[
        pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce")
        .fillna(0)
        .astype(int)
        == 1
    ]["agent_user_code"].astype(str).str.strip()
)


# hamile / süt izni agentlar
hamile_sut_agents = set(
    df_tam[
        (
            pd.to_numeric(df_tam["hamile_flg"], errors="coerce")
            .fillna(0)
            .astype(int)
            == 1
        )
        |
        (
            pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce")
            .fillna(0)
            .astype(int)
            == 1
        )
    ]["agent_user_code"].astype(str).str.strip()
)


def is_weekend(ds):
    return pd.to_datetime(ds).weekday() in [5, 6]


for a in AGENTS:
    izinli = izin_map.get(a, set())

    for wk, days_in_week in week_days.items():

        # Bu hafta hard/yıllık izin sayısı
        izin_count_this_week = sum(
            1
            for ds in days_in_week
            if pd.to_datetime(ds).date() in izinli
        )

        # Normal hedef: 5 - izin sayısı
        normal_target = max(0, NORMAL_WORK_DAYS - izin_count_this_week)

        # Agent'ın bu hafta teorik çalışabileceği gün sayısı
        feasible_days = []

        for ds in days_in_week:
            d_date = pd.to_datetime(ds).date()

            # hard izinliyse çalışamaz
            if d_date in izinli:
                continue

            # hamile/süt izni hafta sonu çalışamaz
            if a in hamile_sut_agents and is_weekend(ds):
                continue

            # o gün en az bir vardiya opsiyonu var mı?
            has_option = any(
                (a, ds, v) in x
                for v in gun_vardiyalari.get(ds, [])
            )

            if has_option:
                feasible_days.append(ds)

        # Ay başı/sonu gibi eksik haftalarda hedefi feasible günle sınırla
        normal_target = min(normal_target, len(feasible_days))

        # Toplam çalışılan gün = normal hedef + mesai
        # overtime_week 0/1 olduğu için max 1 ekstra gün verir.
        model.Add(
            sum(work[(a, ds)] for ds in days_in_week)
            == normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # Mesaiye kalamazsa overtime = 0
        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            no_overtime_constraints += 1


# Ayda max 2 mesai
for a in AGENTS:
    model.Add(
        sum(overtime_week[(a, wk)] for wk in WEEKS)
        <= MAX_OVERTIME_PER_MONTH
    )
    monthly_overtime_constraints += 1


print("haftalık çalışma + mesai kısıtı:", weekly_work_constraints)
print("aylık max mesai kısıtı:", monthly_overtime_constraints)
print("mesaiye kalamaz overtime=0 kısıtı:", no_overtime_constraints)
print("mesaiye kalamaz agent sayısı:", len(mesaiye_kalamaz_agents))


# %% [HÜCRE] - OBJECTIVE
# Öncelik:
# 1. %10 buffer altına düşme minimum olsun
# 2. %10 buffer üstüne çıkma minimum olsun
# 3. Gereksiz mesai minimum olsun

objective_terms = []

UNDER_BUFFER_W = 100000
OVER_BUFFER_W = 1000
OVERTIME_W = 5000

# Coverage buffer cezası
for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        objective_terms.append(
            UNDER_BUFFER_W * under_buffer[(ds, v)]
        )
        objective_terms.append(
            OVER_BUFFER_W * over_buffer[(ds, v)]
        )

# Mesai cezası
for a in AGENTS:
    for wk in WEEKS:
        objective_terms.append(
            OVERTIME_W * overtime_week[(a, wk)]
        )

model.Minimize(sum(objective_terms))

print("objective term sayısı:", len(objective_terms))
print("under buffer weight:", UNDER_BUFFER_W)
print("over buffer weight:", OVER_BUFFER_W)
print("overtime weight:", OVERTIME_W)
