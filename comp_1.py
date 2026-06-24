# %% [HÜCRE] - AGENT HAFTA BOYUNCA AYNI VARDİYADA KALSIN
# HARD CONSTRAINT
# Bir agent aynı hafta içinde çalıştığı tüm günlerde aynı vardiya pattern'inde kalır.
# Off / izin günleri bu kısıta dahil değildir.

agent_week_same_shift_constraints = 0

def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


# PLAN_GUNLER'i haftalara ayır
week_days = {}

for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


# Tüm vardiya pattern'leri
all_patterns = sorted({
    get_shift_pattern(ds, v)
    for ds in PLAN_GUNLER
    for v in gun_vardiyalari.get(ds, [])
})


for a in AGENTS:
    for wk, days in week_days.items():

        # Bu agent'ın o hafta çalışabileceği tüm x değişkenleri
        week_vars = [
            (ds, v)
            for ds in days
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if not week_vars:
            continue

        # Agent-week için 1 tane haftalık vardiya pattern'i seç
        pattern_vars = {}

        for p in all_patterns:
            pattern_vars[p] = model.NewBoolVar(
                f"agent_week_pattern_{a}_{wk}_{p.replace(':', '').replace('-', '_')}"
            )

        model.Add(sum(pattern_vars.values()) == 1)

        # Agent o hafta hangi gün çalışırsa, sadece seçilen pattern'de çalışabilir
        for ds, v in week_vars:
            p = get_shift_pattern(ds, v)

            model.Add(
                x[(a, ds, v)] <= pattern_vars[p]
            )

            agent_week_same_shift_constraints += 1


print("agent hafta boyunca aynı vardiya hard kısıtı:", agent_week_same_shift_constraints)
