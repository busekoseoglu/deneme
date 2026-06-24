# %% [HÜCRE] - TAKIM GÜNLÜK BÖLÜNMESİN
# Normal ekip aynı gün kesinlikle aynı vardiyada olacak.
# Özel durumlu kişiler ayrılabilir ama ceza alır.

import re

objective_terms = []

team_col = "takim"

DAY_SPECIAL_SPLIT_PENALTY = 500


def safe_name(x):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(x))


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

team_members = (
    df_team
    .groupby(team_col)["agent_user_code"]
    .apply(list)
    .to_dict()
)

all_patterns = sorted({
    get_shift_pattern(ds, v)
    for ds in PLAN_GUNLER
    for v in gun_vardiyalari.get(ds, [])
})

team_day_main = {}

normal_hard_split_constraints = 0
special_split_penalties = 0
team_day_count = 0

for team, members in team_members.items():
    team_name = safe_name(team)

    for ds in PLAN_GUNLER:
        ds_name = safe_name(ds)

        day_work_vars = [
            x[(a, ds, v)]
            for a in members
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if not day_work_vars:
            continue

        team_works_day = model.NewBoolVar(
            f"team_works_day_{team_name}_{ds_name}"
        )

        for var in day_work_vars:
            model.Add(team_works_day >= var)

        model.Add(team_works_day <= sum(day_work_vars))

        main_vars = []

        for p in all_patterns:
            p_name = safe_name(p)

            main = model.NewBoolVar(
                f"team_day_main_{team_name}_{ds_name}_{p_name}"
            )

            team_day_main[(team, ds, p)] = main
            main_vars.append(main)

        # Takım o gün çalışıyorsa 1 ana vardiya seçsin
        model.Add(sum(main_vars) == team_works_day)
        team_day_count += 1

        for a in members:
            is_special = agent_special.get(a, False)

            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) not in x:
                    continue

                p = get_shift_pattern(ds, v)
                p_name = safe_name(p)

                split = model.NewBoolVar(
                    f"team_day_split_{a}_{team_name}_{ds_name}_{p_name}"
                )

                model.Add(split >= x[(a, ds, v)] - team_day_main[(team, ds, p)])
                model.Add(split <= x[(a, ds, v)])
                model.Add(split <= 1 - team_day_main[(team, ds, p)])

                if is_special:
                    # özel durumlu kişi ayrılabilir ama ceza alır
                    objective_terms.append(DAY_SPECIAL_SPLIT_PENALTY * split)
                    special_split_penalties += 1
                else:
                    # normal ekip ana vardiya dışına çıkamaz
                    model.Add(split == 0)
                    normal_hard_split_constraints += 1


print("team-day sayısı:", team_day_count)
print("normal ekip günlük bölünemez hard kısıt:", normal_hard_split_constraints)
print("özel durum split penalty:", special_split_penalties)
print("objective term:", len(objective_terms))
