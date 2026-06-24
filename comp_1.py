# %% [HÜCRE] - AGENT HAFTADA 5 GÜN AYNI VARDİYADA ÇALIŞSIN
# Bu hücre eski "haftada 5 gün" ve eski "hafta boyunca aynı vardiya" hücrelerinin yerine geçer.

from collections import defaultdict

WEEKLY_WORK_DAYS = 5

weekly_same_shift_constraints = 0
weekly_pattern_choice_constraints = 0
no_candidate_rows = []


def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


def time_to_minutes(t):
    h, m = map(int, str(t).split(":"))
    return h * 60 + m


def is_day_only_shift_allowed(baslangic, bitis):
    start_min = time_to_minutes(baslangic)
    end_min = time_to_minutes(bitis)

    if end_min <= start_min:
        return False

    if start_min < time_to_minutes("07:00"):
        return False

    if end_min > time_to_minutes("20:00"):
        return False

    return True


# Haftaları oluştur
week_days = {}

for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


# Agent flag map
agent_flags = {}

for _, row in df_tam.iterrows():
    a = str(row["agent_user_code"]).strip()

    agent_flags[a] = {
        "sabah": int(row.get("sabah_calisir_flg", 0)),
        "hamile": int(row.get("hamile_flg", 0)),
        "sut": int(row.get("sut_izni_flg", 0))
    }


def is_shift_feasible_for_agent(a, ds, v):
    if (a, ds, v) not in x:
        return False

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

    d = pd.to_datetime(ds).date()

    # Hamile / süt izni hafta sonu çalışamaz
    if weekend_off and d.weekday() in [5, 6]:
        return False

    bas, bit = saat[(ds, v)]

    # Sabah/hamile/süt izni gece veya 20 sonrası çalışamaz
    if is_day_only and not is_day_only_shift_allowed(bas, bit):
        return False

    return True


for a in AGENTS:
    a = str(a).strip()

    for wk, days in week_days.items():

        pattern_to_vars = defaultdict(list)
        pattern_to_days = defaultdict(set)
        available_days = set()

        for ds in days:
            for v in gun_vardiyalari.get(ds, []):

                if not is_shift_feasible_for_agent(a, ds, v):
                    continue

                p = get_shift_pattern(ds, v)

                pattern_to_vars[p].append(x[(a, ds, v)])
                pattern_to_days[p].add(ds)
                available_days.add(ds)

        if not available_days:
            continue

        # O hafta kaç gün çalışması gerekiyorsa
        required_work_days = min(WEEKLY_WORK_DAYS, len(available_days))

        # Bu agent-week için aynı vardiyada required_work_days kadar gün sağlayabilen pattern'ler
        candidate_patterns = [
            p
            for p, p_days in pattern_to_days.items()
            if len(p_days) >= required_work_days
        ]

        if not candidate_patterns:
            no_candidate_rows.append({
                "agent": a,
                "week_key": wk,
                "available_day_count": len(available_days),
                "required_work_days": required_work_days,
                "best_pattern_day_count": max([len(v) for v in pattern_to_days.values()]) if pattern_to_days else 0
            })
            continue

        pattern_vars = {}

        for p in candidate_patterns:
            p_name = p.replace(":", "").replace("-", "_")
            wk_name = wk.replace("-", "_")

            pattern_vars[p] = model.NewBoolVar(
                f"weekly_pattern_{a}_{wk_name}_{p_name}"
            )

        # Agent-week için tek pattern seç
        model.Add(sum(pattern_vars.values()) == 1)
        weekly_pattern_choice_constraints += 1

        # Seçilen pattern'de tam required_work_days çalışsın,
        # seçilmeyen pattern'lerde hiç çalışmasın.
        for p, vars_p in pattern_to_vars.items():

            if p in candidate_patterns:
                model.Add(sum(vars_p) == required_work_days).OnlyEnforceIf(pattern_vars[p])
                model.Add(sum(vars_p) == 0).OnlyEnforceIf(pattern_vars[p].Not())
            else:
                model.Add(sum(vars_p) == 0)

            weekly_same_shift_constraints += 1


no_candidate_df = pd.DataFrame(no_candidate_rows)

display(no_candidate_df)

print("agent-week pattern seçim kısıtı:", weekly_pattern_choice_constraints)
print("haftalık aynı vardiya kısıtı:", weekly_same_shift_constraints)
print("candidate pattern bulunamayan agent-week:", len(no_candidate_df))
