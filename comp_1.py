# Coverage sapma değişkenleri
under_buffer = {}
over_buffer = {}

# Talebe göre eksik/fazla değişkenleri
missing_to_required = {}
excess_to_required = {}

MAX_AGENT = len(AGENTS)

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        under_buffer[(ds, v)] = model.NewIntVar(
            0,
            MAX_AGENT,
            f"under_buffer_{ds}_{v}"
        )

        over_buffer[(ds, v)] = model.NewIntVar(
            0,
            MAX_AGENT,
            f"over_buffer_{ds}_{v}"
        )

        # Buffer içinde kalsa bile talebin altında kalan kişi sayısı
        missing_to_required[(ds, v)] = model.NewIntVar(
            0,
            MAX_AGENT,
            f"missing_to_required_{ds}_{v}"
        )

        # Buffer içinde kalsa bile talebin üstünde kalan kişi sayısı
        excess_to_required[(ds, v)] = model.NewIntVar(
            0,
            MAX_AGENT,
            f"excess_to_required_{ds}_{v}"
        )


# %% [HÜCRE] - BUFFERLI COVERAGE + TALEBE YAKLAŞMA
# Amaç:
# 1. %5 buffer altına düşerse under_buffer oluşur.
# 2. %5 buffer üstüne çıkarsa over_buffer oluşur.
# 3. Talebin altında kalırsa missing_to_required oluşur.
# 4. Talebin üstünde kalırsa excess_to_required oluşur.
#
# Böylece model sadece buffer içinde kalmaya değil,
# mümkün olduğunca talebe yaklaşmaya çalışır.

BUFFER_RATE = 0.05

coverage_lower = {}
coverage_upper = {}

coverage_constraints = 0
target_gap_constraints = 0

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        required = int(talep[(ds, v)])

        lower_req = math.floor(required * (1 - BUFFER_RATE))
        upper_req = math.ceil(required * (1 + BUFFER_RATE))

        coverage_lower[(ds, v)] = lower_req
        coverage_upper[(ds, v)] = upper_req

        assigned = sum(
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
        )

        # Buffer alt sınırı
        model.Add(
            assigned + under_buffer[(ds, v)] >= lower_req
        )
        coverage_constraints += 1

        # Buffer üst sınırı
        model.Add(
            assigned - over_buffer[(ds, v)] <= upper_req
        )
        coverage_constraints += 1

        # Talebe göre eksik kişi sayısı
        # assigned < required ise missing_to_required pozitif olur.
        model.Add(
            assigned + missing_to_required[(ds, v)] >= required
        )
        target_gap_constraints += 1

        # Talebe göre fazla kişi sayısı
        # assigned > required ise excess_to_required pozitif olur.
        model.Add(
            assigned - excess_to_required[(ds, v)] <= required
        )
        target_gap_constraints += 1

print("Coverage buffer kısıtı:", coverage_constraints)
print("Talebe göre gap kısıtı:", target_gap_constraints)


# %% [HÜCRE] - OBJECTIVE
# Öncelik:
# 1. Buffer altına düşme minimize edilir.
# 2. Talebe göre eksik kalma minimize edilir.
# 3. Talebe göre fazla kalma minimize edilir.
# 4. Mesai minimize edilir.
# 5. Buffer üstüne çıkma minimize edilir.

objective_terms = []

UNDER_BUFFER_W = 100000
MISSING_TO_REQUIRED_W = 20000
EXCESS_TO_REQUIRED_W = 3000
OVERTIME_W = 5000
OVER_BUFFER_W = 1000

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        # %5 buffer altına düşmek en kötü durum
        objective_terms.append(
            UNDER_BUFFER_W * under_buffer[(ds, v)]
        )

        # Buffer içinde kalsa bile talebin altında kalmak ciddi cezalı
        objective_terms.append(
            MISSING_TO_REQUIRED_W * missing_to_required[(ds, v)]
        )

        # Talebin üstünde fazla kişi yığmak da cezalı
        objective_terms.append(
            EXCESS_TO_REQUIRED_W * excess_to_required[(ds, v)]
        )

        # %5 üst sınırın da üstüne çıkmak ayrıca cezalı
        objective_terms.append(
            OVER_BUFFER_W * over_buffer[(ds, v)]
        )

# Mesai cezası
for a in AGENTS:
    for wk in WEEKS:
        objective_terms.append(
            OVERTIME_W * overtime_week[(a, wk)]
        )

model.Minimize(sum(objective_terms))

print("Objective term sayısı:", len(objective_terms))
print("UNDER_BUFFER_W:", UNDER_BUFFER_W)
print("MISSING_TO_REQUIRED_W:", MISSING_TO_REQUIRED_W)
print("EXCESS_TO_REQUIRED_W:", EXCESS_TO_REQUIRED_W)
print("OVERTIME_W:", OVERTIME_W)
print("OVER_BUFFER_W:", OVER_BUFFER_W)


# %% KONTROL - TALEBE GÖRE EKSİK / FAZLA GAP

target_gap_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        required = int(talep[(ds, v)])
        gap = assigned - required

        target_gap_rows.append({
            "tarih": str(ds),
            "gun": DAY_TR[pd.to_datetime(ds).weekday()],
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "talep": required,
            "atanan": assigned,
            "gap_to_required": gap,
            "lower_buffer": coverage_lower[(ds, v)],
            "upper_buffer": coverage_upper[(ds, v)],
            "buffer_ici": coverage_lower[(ds, v)] <= assigned <= coverage_upper[(ds, v)],
            "under_buffer": solver.Value(under_buffer[(ds, v)]),
            "over_buffer": solver.Value(over_buffer[(ds, v)]),
            "missing_to_required": solver.Value(missing_to_required[(ds, v)]),
            "excess_to_required": solver.Value(excess_to_required[(ds, v)])
        })

target_gap_check = pd.DataFrame(target_gap_rows)

print("Toplam missing_to_required:", target_gap_check["missing_to_required"].sum())
print("Toplam excess_to_required:", target_gap_check["excess_to_required"].sum())
print("Toplam under_buffer:", target_gap_check["under_buffer"].sum())
print("Toplam over_buffer:", target_gap_check["over_buffer"].sum())

print("\nTalebin altında kalan vardiya sayısı:")
print(len(target_gap_check[target_gap_check["gap_to_required"] < 0]))

print("\nTalebin üstünde kalan vardiya sayısı:")
print(len(target_gap_check[target_gap_check["gap_to_required"] > 0]))

display(
    target_gap_check
    .sort_values(["gap_to_required", "tarih", "baslangic"])
)
