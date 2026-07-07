    # --------------------------------------------------
    # GÜNLÜK FAZLA ATAMA DENGE PARAMETRELERİ
    # --------------------------------------------------
    # Amaç:
    # Model fazla atamaları ayın sonundaki yarım haftaya veya tek bir güne yığmasın.
    #
    # Örn:
    # Bir gün toplam fazla atama 39 ise ve DAILY_EXCESS_SOFT_LIMIT = 10 ise
    # 29 kişilik kısım ekstra cezaya girer.
    #
    # Bu hard kural değildir. Gerekirse model yine fazla atama yapabilir,
    # ama bunu tek güne yığmak pahalı hale gelir.
    "DAILY_EXCESS_SOFT_LIMIT": 10,
    "DAILY_EXCESS_OVER_W": 20000,


DAILY_EXCESS_SOFT_LIMIT = CONFIG["DAILY_EXCESS_SOFT_LIMIT"]
DAILY_EXCESS_OVER_W = CONFIG["DAILY_EXCESS_OVER_W"]


# %% [HÜCRE] - GÜNLÜK FAZLA ATAMA DENGE DEĞİŞKENİ
# Amaç:
# Model fazla atamaları tek bir güne veya ay sonundaki yarım haftaya yığmasın.
#
# Mevcut durumda excess_to_required[(ds, v)] değişkeni:
# - Her gün-vardiya için talebin üstünde kalan kişi sayısını tutuyor.
#
# Bu hücrede:
# - Her gün için toplam fazla atama hesaplanır.
# - Belirlenen günlük soft limit aşılırsa daily_excess_over değişkeni pozitif olur.
# - Bu değişken objective içinde cezalandırılır.
#
# Örnek:
# Günlük limit = 10
# Bir gün toplam fazla atama = 39
# daily_excess_over = 29 olur.
#
# Not:
# Bu hard kural değildir. Model gerekirse yine fazla atama yapabilir.
# Ama fazla atamayı tek güne yığmak daha pahalı hale gelir.

daily_excess_over = {}
daily_excess_debug_rows = []

daily_excess_balance_constraints = 0

for ds in PLAN_GUNLER:
    
    # --------------------------------------------------
    # 1) O günün tüm vardiyalarındaki fazla atamaları topla
    # --------------------------------------------------
    # excess_to_required[(ds, v)]:
    # assigned > required ise aradaki farkı temsil eder.
    # assigned <= required ise 0 kalır.
    
    daily_excess_terms = [
        excess_to_required[(ds, v)]
        for v in gun_vardiyalari.get(ds, [])
        if (ds, v) in excess_to_required
    ]
    
    # Eğer o gün için hiç vardiya yoksa devam et
    if not daily_excess_terms:
        continue
    
    daily_excess_total = sum(daily_excess_terms)
    
    # --------------------------------------------------
    # 2) Günlük soft limit üstü fazla atama değişkeni
    # --------------------------------------------------
    # daily_excess_over[ds] şu anlama gelir:
    # O gün toplam fazla atama DAILY_EXCESS_SOFT_LIMIT değerini ne kadar aştı?
    
    daily_excess_over[ds] = model.NewIntVar(
        0,
        MAX_AGENT,
        f"daily_excess_over_{ds}"
    )
    
    model.Add(
        daily_excess_over[ds] >= daily_excess_total - DAILY_EXCESS_SOFT_LIMIT
    )
    
    daily_excess_balance_constraints += 1
    
    # Debug için satır tutuyoruz
    daily_excess_debug_rows.append({
        "date": ds,
        "daily_excess_soft_limit": DAILY_EXCESS_SOFT_LIMIT,
        "daily_excess_over_var": f"daily_excess_over_{ds}"
    })

daily_excess_balance_debug_df = pd.DataFrame(daily_excess_debug_rows)

print("Günlük fazla atama denge kısıtı:", daily_excess_balance_constraints)
print("Günlük fazla atama soft limit:", DAILY_EXCESS_SOFT_LIMIT)
print("Günlük fazla atama aşım cezası:", DAILY_EXCESS_OVER_W)

display(daily_excess_balance_debug_df.head(10))


# --------------------------------------------------
# GÜNLÜK FAZLA ATAMA YIĞILMA CEZASI
# --------------------------------------------------
# Amaç:
# Fazla atamalar tek bir güne, özellikle ay sonundaki yarım haftaya yığılmasın.
#
# daily_excess_over[ds]:
# O gün toplam fazla atamanın günlük soft limit üzerindeki kısmıdır.
#
# Örnek:
# Limit = 10
# Toplam fazla = 39
# Ceza değişkeni = 29
#
# Bu değişken objective'e eklenerek model fazla atamaları mümkün olduğunca
# ay içine daha dengeli dağıtmaya çalışır.

if "daily_excess_over" in globals():
    for ds, var in daily_excess_over.items():
        objective_terms.append(
            DAILY_EXCESS_OVER_W * var
        )

print("DAILY_EXCESS_SOFT_LIMIT:", DAILY_EXCESS_SOFT_LIMIT)
print("DAILY_EXCESS_OVER_W:", DAILY_EXCESS_OVER_W)
