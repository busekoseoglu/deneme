# %% [HÜCRE] - OBJECTIVE
# Amaç:
# 1. %10 buffer altına düşme olmasın / minimum olsun
# 2. %10 buffer üstüne çıkma mümkünse az olsun
#
# Takım bölünmesin kuralı objective'te değil,
# "Takım haftalık base vardiya - HARD" hücresinde constraint olarak sağlanıyor.

objective_terms = []

UNDER_BUFFER_W = 100000   # Eksik kalmak çok pahalı
OVER_BUFFER_W = 1000      # Fazla yazmak daha az pahalı

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        objective_terms.append(
            UNDER_BUFFER_W * under_buffer[(ds, v)]
        )
        objective_terms.append(
            OVER_BUFFER_W * over_buffer[(ds, v)]
        )

model.Minimize(sum(objective_terms))

print("objective term sayısı:", len(objective_terms))
print("under buffer weight:", UNDER_BUFFER_W)
print("over buffer weight:", OVER_BUFFER_W)
