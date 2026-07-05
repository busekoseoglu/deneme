# %% [HÜCRE] - ARİFE VARDİYA SINIFLANDIRMA YARDIMCILARI

def arife_ds_key(ds):
    """
    PLAN_GUNLER içindeki tarih string de olsa Timestamp de olsa
    'YYYY-MM-DD' formatına çevirir.
    """
    return pd.to_datetime(ds).strftime("%Y-%m-%d")


def arife_dakika(s):
    """
    '09:00' veya '9:00' formatındaki saati dakikaya çevirir.
    """
    hh, mm = str(s).split(":")
    return int(hh) * 60 + int(mm)


def arife_vardiya_abs_aralik(ds, v):
    """
    Vardiyanın başlangıç/bitiş dakikasını döndürür.
    Geceye sarkan vardiyalarda bitişe +24 saat ekler.
    """
    bas, bit = saat[(ds, v)]

    bas_dk = arife_dakika(bas)
    bit_dk = arife_dakika(bit)

    # Örn: 17:00-01:00 gibi geceye sarkan vardiya
    if bit_dk <= bas_dk:
        bit_dk += 24 * 60

    return bas, bit, bas_dk, bit_dk


def arife_mesai_vardiyasi_mi_func(ds, v):
    """
    Arife günü hangi vardiyanın mesaili plan sayılacağını belirler.

    Kural:
    - 13:00 öncesinde başlayan vardiyalar normal sayılır.
      Örn: 09-13, 10-19, 12-21 normal.
    - 13:00 ve sonrası başlayan vardiyalar arife mesaisi sayılır.
      Örn: 13-22, 15-00 mesaili.
    """

    ds_key = arife_ds_key(ds)

    if ds_key not in ARIFE_GUNLERI:
        return False

    if (ds, v) not in saat:
        return False

    bas, bit, bas_dk, bit_dk = arife_vardiya_abs_aralik(ds, v)

    limit_dk = arife_dakika(ARIFE_GUNLERI[ds_key]["mesai_baslangic"])

    # 13:00 öncesi başlayan vardiyalar normal.
    if bas_dk < limit_dk:
        return False

    # 13:00 ve sonrası başlayan vardiyalar mesaili.
    return True


def arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v):
    """
    Hamile / süt izni / mesaiye kalamaz agentlar için yasak vardiyayı belirler.

    Bu kişiler arife günü 13:00 sonrasına sarkan hiçbir vardiyada çalışamaz.
    Bu nedenle 12-21 normal plan sayılsa bile bu kişiler için yasaktır.
    """

    ds_key = arife_ds_key(ds)

    if ds_key not in ARIFE_GUNLERI:
        return False

    if (ds, v) not in saat:
        return False

    bas, bit, bas_dk, bit_dk = arife_vardiya_abs_aralik(ds, v)

    limit_dk = arife_dakika(ARIFE_GUNLERI[ds_key]["mesai_baslangic"])

    # 09-13 gibi tam 13:00'te biten vardiya yasak değildir.
    # 13:00 sonrasına sarkıyorsa yasaktır.
    return bit_dk > limit_dk


arife_mesai_vardiyasi_mi = {}
arife_kisitli_yasak_vardiya_mi = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        arife_mesai_vardiyasi_mi[(ds, v)] = arife_mesai_vardiyasi_mi_func(ds, v)
        arife_kisitli_yasak_vardiya_mi[(ds, v)] = arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v)


# Arife günleri
arife_plan_gunleri = [
    ds for ds in PLAN_GUNLER
    if arife_ds_key(ds) in ARIFE_GUNLERI
]

# Arifede 13 sonrası çalışamayacak agentlar:
# - hamile
# - süt izni
# - mesaiye kalamaz
arife_kisitli_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

print("Arife günleri:", arife_plan_gunleri)
print("Arife kısıtlı agent sayısı:", len(arife_kisitli_agents))
print("Arife mesaili vardiya sayısı:", sum(arife_mesai_vardiyasi_mi.values()))
print("Arife kısıtlı agent için yasak vardiya sayısı:", sum(arife_kisitli_yasak_vardiya_mi.values()))



# %% [HÜCRE] - ARİFE ÇALIŞMA KURALLARI

arife_mesai = {}

arife_constraints = 0
arife_09_13_zorunlu_constraints = 0
arife_skip_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in arife_plan_gunleri:

        ds_key = arife_ds_key(ds)

        # -------------------------------------------------
        # 1) Kısıtlı agentlar 13:00 sonrasına sarkan vardiyada çalışamaz
        # -------------------------------------------------
        if a in arife_kisitli_agents:

            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):
                    model.Add(x[(a, ds, v)] == 0)
                    arife_constraints += 1

            # -------------------------------------------------
            # 2) Kısıtlı agentlar arife günü 09:00-13:00 çalışır
            # -------------------------------------------------
            # Agent izinliyse zorlamıyoruz.
            if ds in izin_map.get(a, set()):
                arife_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "reason": "izinli"
                })
                continue

            hedef_bas, hedef_bit = ARIFE_GUNLERI[ds_key]["kisitli_agent_normal_vardiya"]

            hedef_vardiya_vars = []

            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if (ds, v) not in saat:
                    continue

                bas, bit = saat[(ds, v)]

                if bas == hedef_bas and bit == hedef_bit:
                    hedef_vardiya_vars.append(x[(a, ds, v)])

            # 09-13 vardiyası varsa hard çalıştırıyoruz.
            # Yoksa infeasible olmasın diye zorlamıyoruz; rapora yazıyoruz.
            if hedef_vardiya_vars:
                model.Add(sum(hedef_vardiya_vars) == 1)
                arife_09_13_zorunlu_constraints += 1
            else:
                arife_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "reason": "09-13_vardiyasi_yok"
                })

        # -------------------------------------------------
        # 3) Kısıtlı olmayan agentlar arife mesaili vardiyada çalışırsa işaretle
        # -------------------------------------------------
        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if arife_mesai_vardiyasi_mi.get((ds, v), False):

                if a not in arife_kisitli_agents:

                    arife_mesai[(a, ds, v)] = model.NewBoolVar(
                        f"arife_mesai_{a}_{ds}_{v}"
                    )

                    model.Add(arife_mesai[(a, ds, v)] == x[(a, ds, v)])
                    arife_constraints += 1


print("Arife günleri:", arife_plan_gunleri)
print("Arife kısıtlı agent sayısı:", len(arife_kisitli_agents))
print("Arife 13 sonrası yasak/mesai kısıt sayısı:", arife_constraints)
print("Arife 09-13 zorunlu çalışma kısıtı:", arife_09_13_zorunlu_constraints)
print("Arife mesai değişken sayısı:", len(arife_mesai))

if arife_skip_rows:
    arife_skip_df = pd.DataFrame(arife_skip_rows)
    print("Arife 09-13 zorunlu çalışma skip sayısı:", len(arife_skip_df))
    display(arife_skip_df.head(100))



# %% [HÜCRE] - TAKIM HAFTALIK BASE VARDİYA - HAFTA İÇİ HARD / HAFTA SONU SERBEST
# Yeni iş kuralı:
# Pazartesi-Cuma: Takım bütünlüğü korunur. Takımdaki herkes o hafta seçilen base vardiyada çalışır.
# Cumartesi-Pazar: Takım bütünlüğü zorunlu değildir. Agentlar ihtiyaca göre farklı vardiyalara dağılabilir.
# Arife günü: özel kural vardır, takım base hard kuralından hariç tutulur.

team_base_constraints = 0
team_weekday_link_constraints = 0
weekend_free_count = 0
arife_team_base_skip_count = 0

# 1. Her takım-her hafta için tek base vardiya seç
for t in TAKIMLAR:
    for wk in WEEKS:
        vars_base = [
            team_week_base[(t, wk, v)]
            for v in week_vardiyalari[wk]
            if (t, wk, v) in team_week_base
        ]

        if vars_base:
            model.Add(sum(vars_base) == 1)
            team_base_constraints += 1


# 2. Sadece hafta içi günlerde agent takımının base vardiyasında çalışabilir
for a in AGENTS:
    a = str(a).strip()

    t = agent_team.get(a)

    if t is None or pd.isna(t):
        continue

    t = str(t).strip()

    for ds in PLAN_GUNLER:

        # Arife günü özel planlandığı için takım base hard kuralından çıkarılır.
        if arife_ds_key(ds) in ARIFE_GUNLERI:
            arife_team_base_skip_count += 1
            continue

        weekday = pd.to_datetime(ds).weekday()
        wk = day_week[ds]

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            # Hafta içi: takım base vardiyası hard
            if weekday in [0, 1, 2, 3, 4]:

                if (t, wk, v) in team_week_base:
                    model.Add(
                        x[(a, ds, v)] <= team_week_base[(t, wk, v)]
                    )
                    team_weekday_link_constraints += 1

                else:
                    # Eğer bu vardiya takımın haftalık base seçeneklerinde yoksa,
                    # hafta içi bu vardiyaya atanamaz.
                    model.Add(x[(a, ds, v)] == 0)
                    team_weekday_link_constraints += 1

            # Hafta sonu: takım serbest, constraint eklemiyoruz
            else:
                weekend_free_count += 1


print("Takım-hafta tek base vardiya kısıtı:", team_base_constraints)
print("Hafta içi takım hard bağlantı kısıtı:", team_weekday_link_constraints)
print("Hafta sonu serbest bırakılan agent-gün-vardiya opsiyonu:", weekend_free_count)
print("Arife takım base skip sayısı:", arife_team_base_skip_count)


# %% [HÜCRE] - FAZLA ATAMA ÜST LİMİTİ
# Bu hücrede her vardiyada talebin üstüne çıkabilecek maksimum kişi sayısını sınırlıyoruz.
#
# Genel kural:
# assigned <= required + 15
#
# Gece/akşam vardiyası ise:
# assigned <= required + 3
#
# Arife 09-13 özel durumu:
# Hamile / süt izni / mesaiye kalamaz agentlar 09-13'e hard yazıldığı için
# bu vardiyada cap, zorunlu agent sayısını alabilecek kadar esnetilir.

fazla_atama_cap_constraints = 0
arife_cap_relax_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        required = int(talep[(ds, v)])

        assigned = sum(
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
        )

        max_fazla = fazla_atama_ust_limit[(ds, v)]

        # -------------------------------------------------
        # ARİFE 09-13 ÖZEL DURUMU
        # -------------------------------------------------
        if arife_ds_key(ds) in ARIFE_GUNLERI and (ds, v) in saat:

            hedef_bas, hedef_bit = ARIFE_GUNLERI[arife_ds_key(ds)]["kisitli_agent_normal_vardiya"]

            bas, bit = saat[(ds, v)]

            if bas == hedef_bas and bit == hedef_bit:

                forced_count = 0

                for a in arife_kisitli_agents:
                    a = str(a).strip()

                    # İzinliyse 09-13'e zorlanmıyor.
                    if ds in izin_map.get(a, set()):
                        continue

                    if (a, ds, v) in x:
                        forced_count += 1

                # Bu vardiyada en az forced_count kişilik alan olmalı.
                min_needed_extra = max(0, forced_count - required)

                if min_needed_extra > max_fazla:
                    arife_cap_relax_rows.append({
                        "date": ds,
                        "shift": v,
                        "required": required,
                        "old_max_fazla": max_fazla,
                        "forced_count": forced_count,
                        "new_max_fazla": min_needed_extra
                    })

                    max_fazla = min_needed_extra

        model.Add(
            assigned <= required + max_fazla
        )

        fazla_atama_cap_constraints += 1


print("Fazla atama üst limit kısıtı:", fazla_atama_cap_constraints)
print("Genel max fazla atama:", GENEL_MAX_FAZLA_ATAMA)
print("Gece/akşam max fazla atama:", GECE_MAX_FAZLA_ATAMA)

if arife_cap_relax_rows:
    arife_cap_relax_df = pd.DataFrame(arife_cap_relax_rows)
    print("Arife 09-13 cap esnetilen satır sayısı:", len(arife_cap_relax_df))
    display(arife_cap_relax_df)



# -------------------------------------------------
# ARİFE MESAİ CEZASI
# -------------------------------------------------
# ARIFE_MESAI_W şu an 0.
# Bu nedenle model arife mesaisinden kaçmak için coverage bozmaz.
# Sadece arife mesaisi Excel/kontrol tarafında etiketlenir.

if "arife_mesai" in globals() and ARIFE_MESAI_W > 0:
    for (a, ds, v), var in arife_mesai.items():
        objective_terms.append(
            ARIFE_MESAI_W * var
        )

print("ARIFE_MESAI_W:", ARIFE_MESAI_W)


# %% KONTROL - ARİFE KURALLARI

arife_kontrol_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in arife_plan_gunleri:

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            assigned = solver.Value(x[(a, ds, v)])

            if assigned == 0:
                continue

            bas, bit = saat[(ds, v)] if (ds, v) in saat else (None, None)

            arife_kontrol_rows.append({
                "agent_user_code": a,
                "date": ds,
                "shift": v,
                "shift_start": bas,
                "shift_end": bit,
                "arife_mesai_vardiyasi_mi": arife_mesai_vardiyasi_mi.get((ds, v), False),
                "arife_kisitli_agent": a in arife_kisitli_agents,
                "arife_kisitli_icin_yasak_vardiya_mi": arife_kisitli_yasak_vardiya_mi.get((ds, v), False),
                "arife_mesai": (
                    solver.Value(arife_mesai[(a, ds, v)])
                    if "arife_mesai" in globals() and (a, ds, v) in arife_mesai
                    else 0
                )
            })

arife_kontrol_df = pd.DataFrame(arife_kontrol_rows)

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "hamile_flg",
    "sut_izni_flg",
    "mesaiye_kalamaz_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

arife_kontrol_df = arife_kontrol_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("Arife çalışan özet:")
display(
    arife_kontrol_df
    .groupby(["date", "shift_start", "shift_end", "arife_mesai_vardiyasi_mi"], as_index=False)
    .agg(
        calisan_agent_sayisi=("agent_user_code", "nunique"),
        arife_mesai_sayisi=("arife_mesai", "sum")
    )
    .sort_values(["date", "shift_start", "shift_end"])
)

ihlal_df = arife_kontrol_df[
    (arife_kontrol_df["arife_kisitli_agent"] == True) &
    (arife_kontrol_df["arife_kisitli_icin_yasak_vardiya_mi"] == True)
]

print("Kısıtlı agent 13 sonrası ihlal sayısı:", len(ihlal_df))
display(ihlal_df)

print("Kısıtlı agentların arife vardiyaları:")
display(
    arife_kontrol_df[
        arife_kontrol_df["arife_kisitli_agent"] == True
    ]
    .sort_values(["takim", "agent_user_code"])
)
