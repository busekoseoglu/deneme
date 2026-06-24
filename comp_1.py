# %% [HÜCRE] - TAKIM HAFTA BOYUNCA AYNI VARDİYADA KALSIN
# HARD CONSTRAINT
# Her takım + hafta için 1 ana vardiya seçilir.
# Normal agentlar o hafta sadece takımın seçilen vardiyasında çalışır.
# Özel durumlu agentlar ayrılabilir ama ceza alır.

import re

objective_terms = []

team_col = "takim"

SPECIAL_TEAM_SHIFT_SPLIT_PENALTY = 500

def safe_name(x):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(x))


def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


def is_special_agent(row):
    return (
        int(row.get("sabah_calisir_flg", 0)) == 1
        or int(row.get("hamile_flg", 0)) == 1
        or int(row.get("sut_izni_flg", 0)) == 1
    )


df_team = df_tam.copy()
df_team["agent_user_code"] = df_team["agent_user_code"].astype(str).str.strip()

agent_special = {
    row["agent_user_code"]: is_special_agent(row)
    for _, row in df_team.iterrows()
}

agent_team = {
    row["agent_user_code"]: row[team_col]
    for _, row in df_team.iterrows()
}

team_members = (
    df_team
    .groupby(team_col)["agent_user_code"]
    .apply(list)
    .to_dict()
)

# Haftaları oluştur
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

team_week_pattern = {}

team_week_pattern_constraints = 0
normal_agent_restrict_constraints = 0
special_agent_penalty_terms = 0

for team, members in team_members.items():
    team_name = safe_name(team)

    for wk, days in week_days.items():
        wk_name = safe_name(wk)

        # Bu takım-hafta için 1 vardiya pattern'i seç
        pattern_vars = {}

        for p in all_patterns:
            p_name = safe_name(p)

            pattern_vars[p] = model.NewBoolVar(
                f"team_week_pattern_{team_name}_{wk_name}_{p_name}"
            )

            team_week_pattern[(team, wk, p)] = pattern_vars[p]

        model.Add(sum(pattern_vars.values()) == 1)
        team_week_pattern_constraints += 1

        # Bu takımın agentları için kısıt
        for a in members:
            is_special = agent_special.get(a, False)

            for ds in days:
                for v in gun_vardiyalari.get(ds, []):
                    if (a, ds, v) not in x:
                        continue

                    p = get_shift_pattern(ds, v)

                    if not is_special:
                        # Normal agent, takımın haftalık seçilen vardiyası dışında çalışamaz
                        model.Add(x[(a, ds, v)] <= pattern_vars[p])
                        normal_agent_restrict_constraints += 1

                    else:
                        # Özel durumlu kişi ayrılabilir ama ceza alır
                        split = model.NewBoolVar(
                            f"special_week_split_{a}_{team_name}_{wk_name}_{safe_name(ds)}_{safe_name(p)}"
                        )

                        model.Add(split >= x[(a, ds, v)] - pattern_vars[p])
                        model.Add(split <= x[(a, ds, v)])
                        model.Add(split <= 1 - pattern_vars[p])

                        objective_terms.append(SPECIAL_TEAM_SHIFT_SPLIT_PENALTY * split)
                        special_agent_penalty_terms += 1


print("team-week pattern seçim kısıtı:", team_week_pattern_constraints)
print("normal agent haftalık vardiya hard kısıtı:", normal_agent_restrict_constraints)
print("özel durum split penalty term:", special_agent_penalty_terms)
print("objective term:", len(objective_terms))
