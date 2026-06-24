# %% [HÜCRE] - HER AGENT HAFTADA 5 GÜN ÇALIŞSIN
# Fiilen çalışabileceği gün sayısı 5'ten azsa, o kadar çalışır.

weekly_work_constraints = 0

WEEKLY_WORK_DAYS = 5

def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def time_to_minutes(t):
    h, m = map(int, str(t).split(":"))
    return h * 60 + m


def is_day_only_shift_allowed(baslangic, bitis):
    start_min = time_to_minutes(baslangic)
    end_min = time_to_minutes(bitis)

    # geceye dönen vardiya yasak
    if end_min <= start_min:
        return False

    # 07:00 öncesi başlangıç yasak
    if start_min < time_to_minutes("07:00"):
        return False

    # 20:00 sonrası bitiş yasak
    if end_min > time_to_minutes("20:00"):
        return False

    return True


week_days = {}

for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


agent_flags = {}

for _, row in df_tam.iterrows():
    a = str(row["agent_user_code"]).strip()

    agent_flags[a] = {
        "sabah": int(row.get("sabah_calisir_flg", 0)),
        "hamile": int(row.get("hamile_flg", 0)),
        "sut": int(row.get("sut_izni_flg", 0))
    }


for a in AGENTS:
    flags = agent_flags.get(str(a).strip(), {"sabah": 0, "hamile": 0, "sut": 0})

    is_day_only = (
        flags["sabah"] == 1
        or flags["hamile"] == 1
        or flags["sut"] == 1
    )

    weekend_off = (
        flags["hamile"] == 1
        or flags["sut"] == 1
    )

    for wk, days in week_days.items():

        work_day_vars = []

        for ds in days:
            d = pd.to_datetime(ds).date()

            # Hamile / süt izni hafta sonu çalışamaz
            if weekend_off and d.weekday() in [5, 6]:
                continue

            day_shift_vars = []

            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) not in x:
                    continue

                bas, bit = saat[(ds, v)]

                # Sabah/hamile/süt izni gece veya 20 sonrası çalışamaz
                if is_day_only and not is_day_only_shift_allowed(bas, bit):
                    continue

                day_shift_vars.append(x[(a, ds, v)])

            if day_shift_vars:
                # günde max 1 vardiya olduğu için bu toplam 0/1 gibi davranır
                work_day_vars.append(sum(day_shift_vars))

        if not work_day_vars:
            continue

        required_work_days = min(WEEKLY_WORK_DAYS, len(work_day_vars))

        model.Add(sum(work_day_vars) == required_work_days)
        weekly_work_constraints += 1

print("haftalık çalışma günü kısıtı:", weekly_work_constraints)
