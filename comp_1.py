# %% [HÜCRE] - OBJECTIVE
# Mesaiyi daha aktif kullandıran versiyon
#
# Öncelik:
# 1. Buffer altına düşme çok pahalı
# 2. Talebe göre eksik kalma pahalı
# 3. Mesai daha ucuz
# 4. Talebe göre fazla kalma cezalı
# 5. Buffer üstüne çıkma cezalı

objective_terms = []

UNDER_BUFFER_W = 300000
MISSING_TO_REQUIRED_W = 50000
OVERTIME_W = 1000
EXCESS_TO_REQUIRED_W = 3000
OVER_BUFFER_W = 1000

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        objective_terms.append(
            UNDER_BUFFER_W * under_buffer[(ds, v)]
        )

        objective_terms.append(
            MISSING_TO_REQUIRED_W * missing_to_required[(ds, v)]
        )

        objective_terms.append(
            EXCESS_TO_REQUIRED_W * excess_to_required[(ds, v)]
        )

        objective_terms.append(
            OVER_BUFFER_W * over_buffer[(ds, v)]
        )

for a in AGENTS:
    for wk in WEEKS:
        objective_terms.append(
            OVERTIME_W * overtime_week[(a, wk)]
        )

model.Minimize(sum(objective_terms))

print("Objective term sayısı:", len(objective_terms))
print("UNDER_BUFFER_W:", UNDER_BUFFER_W)
print("MISSING_TO_REQUIRED_W:", MISSING_TO_REQUIRED_W)
print("OVERTIME_W:", OVERTIME_W)
print("EXCESS_TO_REQUIRED_W:", EXCESS_TO_REQUIRED_W)
print("OVER_BUFFER_W:", OVER_BUFFER_W)
