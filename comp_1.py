# %% [AŞAMA 1] - BASELINE METRİKLERİ KAYDET

base_under_buffer = sum(
    solver.Value(under_buffer[(ds, v)])
    for ds in PLAN_GUNLER
    for v in gun_vardiyalari.get(ds, [])
    if (ds, v) in under_buffer
)

base_missing_to_required = sum(
    solver.Value(missing_to_required[(ds, v)])
    for ds in PLAN_GUNLER
    for v in gun_vardiyalari.get(ds, [])
    if (ds, v) in missing_to_required
)

base_overtime = sum(
    solver.Value(overtime_week[(a, wk)])
    for a in AGENTS
    for wk in WEEKS
    if (a, wk) in overtime_week
)

base_ikinci_mesai = sum(
    solver.Value(ikinci_mesai_aylik[a])
    for a in AGENTS
    if "ikinci_mesai_aylik" in globals() and a in ikinci_mesai_aylik
)

print("BASE under_buffer:", base_under_buffer)
print("BASE missing_to_required:", base_missing_to_required)
print("BASE overtime:", base_overtime)
print("BASE ikinci mesai:", base_ikinci_mesai)


# %% [AŞAMA 2] - COVERAGE KALİTESİNİ KORU

# PM adilliği optimize edilirken coverage bozulmasın.
# Burada toleransları istersen 0 tutuyoruz.
# Yani 2. aşama, 1. aşamadan daha kötü coverage üretemez.

COVERAGE_UNDER_TOLERANS = 0
MISSING_TOLERANS = 0
OVERTIME_TOLERANS = 0
IKINCI_MESAI_TOLERANS = 0

total_under_buffer_expr = sum(
    under_buffer[(ds, v)]
    for ds in PLAN_GUNLER
    for v in gun_vardiyalari.get(ds, [])
    if (ds, v) in under_buffer
)

total_missing_expr = sum(
    missing_to_required[(ds, v)]
    for ds in PLAN_GUNLER
    for v in gun_vardiyalari.get(ds, [])
    if (ds, v) in missing_to_required
)

total_overtime_expr = sum(
    overtime_week[(a, wk)]
    for a in AGENTS
    for wk in WEEKS
    if (a, wk) in overtime_week
)

model.Add(total_under_buffer_expr <= base_under_buffer + COVERAGE_UNDER_TOLERANS)
model.Add(total_missing_expr <= base_missing_to_required + MISSING_TOLERANS)
model.Add(total_overtime_expr <= base_overtime + OVERTIME_TOLERANS)

if "ikinci_mesai_aylik" in globals():
    total_ikinci_mesai_expr = sum(
        ikinci_mesai_aylik[a]
        for a in AGENTS
        if a in ikinci_mesai_aylik
    )

    model.Add(total_ikinci_mesai_expr <= base_ikinci_mesai + IKINCI_MESAI_TOLERANS)

print("2. aşama coverage koruma kısıtları eklendi.")


# %% [AŞAMA 2] - PM ADİLLİK OBJECTIVE

pm_objective_terms = []

for a in AGENTS:
    a = str(a).strip()

    pm_mesai = pm_mesai_map.get(a, 0)
    pm_gece = pm_gece_map.get(a, 0)
    pm_hafta_sonu = pm_hafta_sonu_map.get(a, 0)

    # Bu ay mesai sayısı
    mevcut_ay_mesai_sayisi = sum(
        overtime_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in overtime_week
    )

    pm_objective_terms.append(
        PM_MESAI_EXTRA_W * pm_mesai * mevcut_ay_mesai_sayisi
    )

    # Bu ay gece sayısı
    if "bu_ay_gece_sayisi" in globals() and a in bu_ay_gece_sayisi:
        pm_objective_terms.append(
            PM_GECE_EXTRA_W * pm_gece * bu_ay_gece_sayisi[a]
        )

    # Bu ay hafta sonu çalışma sayısı
    if "bu_ay_hafta_sonu_calisma_sayisi" in globals() and a in bu_ay_hafta_sonu_calisma_sayisi:
        pm_objective_terms.append(
            PM_HAFTA_SONU_EXTRA_W * pm_hafta_sonu * bu_ay_hafta_sonu_calisma_sayisi[a]
        )

model.Minimize(sum(pm_objective_terms))

print("2. aşama PM objective kuruldu.")
print("PM objective term sayısı:", len(pm_objective_terms))


# %% [AŞAMA 2] - SOLVE

solver2 = cp_model.CpSolver()

solver2.parameters.max_time_in_seconds = 300
solver2.parameters.num_search_workers = 8

status2 = solver2.Solve(model)

print("Stage 2 Status:", solver2.StatusName(status2))
print("Stage 2 Objective:", solver2.ObjectiveValue())

solver = solver2
status = status2
