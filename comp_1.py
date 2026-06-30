# Aylık ikinci mesai değişkeni
# ikinci_mesai_aylik[a] = 1 ise agent ay içinde 2 mesai almış demektir.
# Amaç: 2. mesaiyi tamamen yasaklamak değil, daha pahalı hale getirmek.
ikinci_mesai_aylik = {}

for a in AGENTS:
    ikinci_mesai_aylik[a] = model.NewBoolVar(f"ikinci_mesai_aylik_{a}")


# %% [HÜCRE] - ADİL MESAİ DAĞITIMI / İKİNCİ MESAİ TAKİBİ
# Amaç:
# Agentlara mesai mümkün olduğunca 1'er gün dağıtılsın.
# 2. mesai tamamen yasak değil, ama objective'te ekstra cezalandırılacak.
#
# Mevcut hard kural:
# Bir agent ayda maksimum 2 mesai alabilir.
#
# Yeni soft kural:
# Eğer agent 2 mesai alıyorsa ikinci_mesai_aylik = 1 olur.
# Objective'te bu değişkene ekstra ceza verilecek.

ikinci_mesai_constraints = 0

for a in AGENTS:
    toplam_mesai_agent = sum(
        overtime_week[(a, wk)]
        for wk in WEEKS
    )

    # Bu kısıt şunu sağlar:
    # toplam_mesai = 0 veya 1 ise ikinci_mesai_aylik 0 kalabilir.
    # toplam_mesai = 2 ise ikinci_mesai_aylik 1 olmak zorunda kalır.
    model.Add(
        toplam_mesai_agent <= 1 + ikinci_mesai_aylik[a]
    )
    ikinci_mesai_constraints += 1

print("İkinci mesai takip kısıtı:", ikinci_mesai_constraints)


# Mesai cezası
for a in AGENTS:
    for wk in WEEKS:
        objective_terms.append(
            OVERTIME_W * overtime_week[(a, wk)]
        )

# İkinci mesai ekstra cezası
# Amaç:
# Model önce mesaiyi farklı agentlara dağıtsın.
# Aynı agenta 2. mesaiyi ancak gerekiyorsa versin.
IKINCI_MESAI_W = 50000

for a in AGENTS:
    objective_terms.append(
        IKINCI_MESAI_W * ikinci_mesai_aylik[a]
    )

print("IKINCI_MESAI_W:", IKINCI_MESAI_W)
