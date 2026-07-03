# %% [AŞAMA 2] - STAGE 1 ÇÖZÜMÜNÜ HINT OLARAK VER

hint_count = 0

def add_hint_dict(var_dict):
    global hint_count

    for key, var in var_dict.items():
        try:
            model.AddHint(var, solver.Value(var))
            hint_count += 1
        except Exception:
            pass


# Ana değişkenler
add_hint_dict(x)
add_hint_dict(work)

# Mesai değişkenleri
if "overtime_week" in globals():
    add_hint_dict(overtime_week)

if "ikinci_mesai_aylik" in globals():
    add_hint_dict(ikinci_mesai_aylik)

# Coverage sapma değişkenleri
if "under_buffer" in globals():
    add_hint_dict(under_buffer)

if "over_buffer" in globals():
    add_hint_dict(over_buffer)

if "missing_to_required" in globals():
    add_hint_dict(missing_to_required)

if "excess_to_required" in globals():
    add_hint_dict(excess_to_required)

# Gece / hafta sonu sayım değişkenleri
if "bu_ay_gece_sayisi" in globals():
    add_hint_dict(bu_ay_gece_sayisi)

if "bu_ay_hafta_sonu_calisma_sayisi" in globals():
    add_hint_dict(bu_ay_hafta_sonu_calisma_sayisi)

# Hafta sonu fazla çalışma değişkenleri varsa
if "hafta_sonu_calisma_sayisi" in globals():
    add_hint_dict(hafta_sonu_calisma_sayisi)

if "fazla_hafta_sonu_calisma" in globals():
    add_hint_dict(fazla_hafta_sonu_calisma)

# Gece hafta değişkeni varsa
if "night_week" in globals():
    add_hint_dict(night_week)

print("Hint verilen değişken sayısı:", hint_count)


# %% [AŞAMA 2] - SOLVE

solver2 = cp_model.CpSolver()

solver2.parameters.max_time_in_seconds = 600
solver2.parameters.num_search_workers = 8

status2 = solver2.Solve(model)

print("Stage 2 Status:", solver2.StatusName(status2))

if status2 in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    print("Stage 2 Objective:", solver2.ObjectiveValue())

    # Bundan sonra export ve kontroller solver2 ile çalışsın
    solver = solver2
    status = status2

    print("Stage 2 çözümü kullanılacak.")
else:
    print("Stage 2 çözüm bulunamadı. Stage 1 çözümü kullanılacak.")
    print("Export için solver değiştirilmeyecek.")