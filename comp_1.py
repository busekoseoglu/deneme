# %% [HÜCRE] - ARİFE ÖĞLEDEN ÖNCE HAMİLE / SÜT İZNİ SOFT ÖNCELİK

# Amaç:
# 16 Haziran arife günü, hamile / süt izni olan agentlar mümkünse
# resmi tatil mesaisi başlamadan önceki vardiyalara atansın.
#
# Ancak bunu hard yapmıyoruz.
# Çünkü sabah vardiyalarında yeterli ihtiyaç yoksa veya diğer hard kurallarla çakışırsa
# model infeasible olabilir.
#
# Soft mantık:
# Uygun sabah vardiyası varsa ve agent çalıştırılamazsa ceza alır.

arife_hamile_sut_calisamadi = {}
arife_soft_constraints = 0
arife_soft_skip_rows = []

for ds, limit_saat in RESMI_TATIL_YARIM_GUNLER.items():

    if ds not in PLAN_GUNLER:
        continue

    for a in arife_oncesi_calisacak_agents:
        a = str(a).strip()

        # Eğer agent o gün izinliyse zorlamıyoruz, ceza da vermiyoruz.
        if ds in izin_map.get(a, set()):
            arife_soft_skip_rows.append({
                "agent_user_code": a,
                "date": ds,
                "reason": "izinli"
            })
            continue

        uygun_mesai_olmayan_vardiyalar = [
            x[(a, ds, v)]
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
            and resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False) == False
        ]

        # Eğer uygun sabah / mesai olmayan vardiya yoksa ceza da vermiyoruz.
        if not uygun_mesai_olmayan_vardiyalar:
            arife_soft_skip_rows.append({
                "agent_user_code": a,
                "date": ds,
                "reason": "uygun_mesai_olmayan_vardiya_yok"
            })
            continue

        arife_hamile_sut_calisamadi[(a, ds)] = model.NewBoolVar(
            f"arife_hamile_sut_calisamadi_{a}_{ds}"
        )

        # Eğer uygun sabah vardiyalarından birine atanmazsa,
        # arife_hamile_sut_calisamadi = 1 olabilir ve objective'te ceza alır.
        model.Add(
            sum(uygun_mesai_olmayan_vardiyalar) + arife_hamile_sut_calisamadi[(a, ds)] >= 1
        )

        arife_soft_constraints += 1

print("Arife hamile/süt izni soft öncelik kısıtı:", arife_soft_constraints)
print("Arife hamile/süt izni soft değişken sayısı:", len(arife_hamile_sut_calisamadi))

if arife_soft_skip_rows:
    arife_soft_skip_df = pd.DataFrame(arife_soft_skip_rows)
    print("Arife soft öncelik dışında kalan kayıt sayısı:", len(arife_soft_skip_df))
    display(arife_soft_skip_df.head(50))
    
    
# -------------------------------------------------
# ARİFE HAMİLE / SÜT İZNİ SABAH ÇALIŞMADI CEZASI
# -------------------------------------------------
# 16 Haziran arife günü hamile/süt izni olanlar mümkünse
# mesai başlamadan önce çalışsın.
# Çalışamazsa ceza alır ama model infeasible olmaz.

if "arife_hamile_sut_calisamadi" in globals():
    for (a, ds), var in arife_hamile_sut_calisamadi.items():
        objective_terms.append(
            ARIFE_HAMILE_SUT_CALISMADI_W * var
        )

print("ARIFE_HAMILE_SUT_CALISMADI_W:", ARIFE_HAMILE_SUT_CALISMADI_W)


# %% KONTROL - 16 HAZİRAN VARDİYA SINIFLANDIRMASI

arife_vardiya_rows = []

for ds in RESMI_TATIL_YARIM_GUNLER.keys():
    if ds not in PLAN_GUNLER:
        continue

    for v in gun_vardiyalari.get(ds, []):

        bas, bit = saat[(ds, v)]

        arife_vardiya_rows.append({
            "date": ds,
            "shift": v,
            "start": bas,
            "end": bit,
            "resmi_tatil_mesai_vardiyasi_mi": resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False),
            "required": int(talep[(ds, v)])
        })

arife_vardiya_df = pd.DataFrame(arife_vardiya_rows)

display(
    arife_vardiya_df
    .sort_values(["resmi_tatil_mesai_vardiyasi_mi", "start", "end"])
)


