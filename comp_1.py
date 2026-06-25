# %% [HÜCRE 17] - OBJECTIVE
# Öncelik:
# 1. Eksik kişi bırakma
# 2. Fazla kişi atama
# 3. Takımın haftalık base vardiyasından ayrılma
# 4. Özel durumlu kişilerin exception cezası daha düşük

objective_terms = []

SHORTAGE_W = 100000
EXCESS_W = 1000
EXCEPTION_NORMAL_W = 1000
EXCEPTION_SPECIAL_W = 100

# shortage / excess cezaları
for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        objective_terms.append(SHORTAGE_W * shortage[(ds, v)])
        objective_terms.append(EXCESS_W * excess[(ds, v)])


# özel durumlu agentlar
special_agents = set()

for _, row in df_tam.iterrows():
    a = str(row["agent_user_code"]).strip()

    is_special = (
        int(row.get("hamile_flg", 0) or 0) == 1
        or int(row.get("sut_izni_flg", 0) or 0) == 1
        or int(row.get("sabah_calisir_flg", 0) or 0) == 1
    )

    if is_special:
        special_agents.add(a)


# exception cezaları
for a in AGENTS:
    for ds in PLAN_GUNLER:
        if a in special_agents:
            objective_terms.append(EXCEPTION_SPECIAL_W * exception[(a, ds)])
        else:
            objective_terms.append(EXCEPTION_NORMAL_W * exception[(a, ds)])


model.Minimize(sum(objective_terms))

print(f"objective term sayısı: {len(objective_terms)}")
print(f"special agent sayısı: {len(special_agents)}")
