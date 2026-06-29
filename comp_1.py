# Coverage sapma değişkenleri
under_buffer = {}
over_buffer = {}
missing_to_required = {}

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

        # Buffer içinde kalsa bile talebin altında kalan eksik kişi sayısı
        missing_to_required[(ds, v)] = model.NewIntVar(
            0,
            MAX_AGENT,
            f"missing_to_required_{ds}_{v}"
        )


# %% [HÜCRE] - BUFFERLI COVERAGE + TALEBE YAKLAŞMA KISITI
# Amaç:
# 1. Atanan kişi sayısı buffer alt sınırının altına düşerse under_buffer oluşur.
# 2. Atanan kişi sayısı buffer üst sınırının üstüne çıkarsa over_buffer oluşur.
# 3. Atanan kişi talebin altında kalırsa, buffer içinde olsa bile missing_to_required oluşur.
#
# Örnek:
# Talep = 200
# BUFFER_RATE = 0.05
# Alt sınır = 190
# Üst sınır = 210
# Atanan = 190 ise:
# under_buffer = 0
# over_buffer = 0
# missing_to_required = 10

BUFFER_RATE = 0.05

coverage_lower = {}
coverage_upper = {}

coverage_constraints = 0
missing_constraints = 0

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

        # Talebe göre eksik kalan kişi sayısı
        # Buffer içinde olsa bile eksikliği ölçer
        model.Add(
            assigned + missing_to_required[(ds, v)] >= required
        )
        missing_constraints += 1

print("Coverage buffer kısıtı:", coverage_constraints)
print("Talebe göre eksik kişi kısıtı:", missing_constraints)



# %% [HÜCRE] - OBJECTIVE
# Öncelik sırası:
# 1. Buffer altına düşme minimize edilir.
# 2. Buffer içinde kalsa bile talebe göre eksik kalma minimize edilir.
# 3. Gereksiz mesai minimize edilir.
# 4. Buffer üstüne çıkma minimize edilir.

objective_terms = []

UNDER_BUFFER_W = 100000
MISSING_TO_REQUIRED_W = 10000
OVERTIME_W = 5000
OVER_BUFFER_W = 1000

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        # %5 buffer altına düşmek en kötü durum
        objective_terms.append(
            UNDER_BUFFER_W * under_buffer[(ds, v)]
        )

        # Buffer içinde kalsa bile talebin altında kalmak cezalı
        objective_terms.append(
            MISSING_TO_REQUIRED_W * missing_to_required[(ds, v)]
        )

        # Fazla atama daha düşük ceza
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
print("OVERTIME_W:", OVERTIME_W)
print("OVER_BUFFER_W:", OVER_BUFFER_W)
