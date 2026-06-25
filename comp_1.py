# %% [HÜCRE 17] - OBJECTIVE

objective_terms = []

UNDER_BUFFER_W = 100000
OVER_BUFFER_W = 1000

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        objective_terms.append(
            UNDER_BUFFER_W * under_buffer[(ds, v)]
        )
        objective_terms.append(
            OVER_BUFFER_W * over_buffer[(ds, v)]
        )

# Buradan sonra eski exception / takım bölünme / istenmeyen vardiya cezaların neyse aynen devam edecek.
