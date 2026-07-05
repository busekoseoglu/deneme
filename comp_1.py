# -------------------------------------------------
# ARİFE / RESMİ TATİL PARAMETRELERİ
# -------------------------------------------------

# Arife kuralını aç/kapat.
# O ay arife yoksa False yap.
"ENABLE_ARIFE_KURALI": True,

# Arife günleri:
# - 13:00 öncesi başlayan vardiyalar normal sayılır.
# - 13:00 ve sonrası başlayan vardiyalar arife mesaisi sayılır.
# - Hamile / süt izni / mesaiye kalamaz agentlar 13:00 sonrasına sarkan vardiyalarda çalışamaz.
# - Bu agentlar için özel 09:00-13:00 vardiyası modele eklenir.
"ARIFE_GUNLERI": {
    "2026-06-16": {
        "mesai_baslangic": "13:00",
        "kisitli_agent_normal_vardiya": ("09:00", "13:00"),
        "ozel_vardiya_kodu": "ARIFE_09_13"
    }
},

# Arife mesaisi cezası.
# Şimdilik 0: sadece Excel'de etiketleme için kullanıyoruz, coverage'ı bozmasın.
"ARIFE_MESAI_W": 0,


# Resmi tatil kuralını aç/kapat.
# O ay resmi tatil yoksa False yap.
"ENABLE_RESMI_TATIL_KURALI": True,

# Tam gün resmi tatiller.
# Bu günlerde hamile / süt izni / mesaiye kalamaz çalışamaz.
# Diğerleri çalışırsa resmi tatil mesaisi sayılır.
"RESMI_TATIL_GUNLERI": [
    "2026-06-17"
],

# Resmi tatil mesaisi cezası.
# Şimdilik 0: sadece Excel'de etiketleme için kullanıyoruz.
"RESMI_TATIL_MESAI_W": 0,


ENABLE_ARIFE_KURALI = CONFIG["ENABLE_ARIFE_KURALI"]
ARIFE_GUNLERI = CONFIG["ARIFE_GUNLERI"] if ENABLE_ARIFE_KURALI else {}
ARIFE_MESAI_W = CONFIG["ARIFE_MESAI_W"]

ENABLE_RESMI_TATIL_KURALI = CONFIG["ENABLE_RESMI_TATIL_KURALI"]
RESMI_TATIL_GUNLERI = set(CONFIG["RESMI_TATIL_GUNLERI"]) if ENABLE_RESMI_TATIL_KURALI else set()
RESMI_TATIL_MESAI_W = CONFIG["RESMI_TATIL_MESAI_W"]



# %% [HÜCRE] - ARİFE ÖZEL 09:00-13:00 VARDİYASINI EKLE
# Bu hücre karar değişkenlerinden önce çalışmalı.

def tatil_ds_key_pre(ds):
    return pd.to_datetime(ds).strftime("%Y-%m-%d")


arife_ozel_vardiyalar = set()
arife_ozel_vardiya_kodlari = set()

if ENABLE_ARIFE_KURALI:

    for ds in PLAN_GUNLER:

        ds_key = tatil_ds_key_pre(ds)

        if ds_key not in ARIFE_GUNLERI:
            continue

        arife_cfg = ARIFE_GUNLERI[ds_key]

        ozel_v = arife_cfg["ozel_vardiya_kodu"]
        hedef_bas, hedef_bit = arife_cfg["kisitli_agent_normal_vardiya"]

        # gun_vardiyalari içine ekle
        if ds not in gun_vardiyalari:
            gun_vardiyalari[ds] = []

        if ozel_v not in gun_vardiyalari[ds]:
            gun_vardiyalari[ds].append(ozel_v)

        # saat sözlüğüne ekle
        saat[(ds, ozel_v)] = (hedef_bas, hedef_bit)

        # talep sözlüğüne ekle
        # Bu özel vardiya operasyonel demand için değil,
        # kısıtlı agentların arife günü 09-13 çalışabilmesi için.
        talep[(ds, ozel_v)] = 0

        arife_ozel_vardiyalar.add((ds, ozel_v))
        arife_ozel_vardiya_kodlari.add(ozel_v)

print("Arife özel vardiyalar:", arife_ozel_vardiyalar)



# %% [HÜCRE] - ARİFE / RESMİ TATİL HELPER

def tatil_ds_key(ds):
    return pd.to_datetime(ds).strftime("%Y-%m-%d")


def tatil_dakika(s):
    hh, mm = str(s).split(":")
    return int(hh) * 60 + int(mm)


def tatil_vardiya_abs_aralik(ds, v):
    bas, bit = saat[(ds, v)]

    bas_dk = tatil_dakika(bas)
    bit_dk = tatil_dakika(bit)

    # Geceye sarkan vardiya: 17:00-01:00 gibi
    if bit_dk <= bas_dk:
        bit_dk += 24 * 60

    return bas, bit, bas_dk, bit_dk


def is_arife_gunu(ds):
    return ENABLE_ARIFE_KURALI and tatil_ds_key(ds) in ARIFE_GUNLERI


def is_resmi_tatil_gunu(ds):
    return ENABLE_RESMI_TATIL_KURALI and tatil_ds_key(ds) in RESMI_TATIL_GUNLERI


def arife_mesai_vardiyasi_mi_func(ds, v):
    """
    Arife mesaisi:
    - Arife günü değilse False.
    - Özel ARIFE_09_13 vardiyası mesai değildir.
    - 13:00 öncesi başlayan vardiyalar normal.
    - 13:00 ve sonrası başlayan vardiyalar arife mesaisi.
    """

    if not is_arife_gunu(ds):
        return False

    if (ds, v) not in saat:
        return False

    if (ds, v) in arife_ozel_vardiyalar:
        return False

    ds_key = tatil_ds_key(ds)

    bas, bit, bas_dk, bit_dk = tatil_vardiya_abs_aralik(ds, v)
    limit_dk = tatil_dakika(ARIFE_GUNLERI[ds_key]["mesai_baslangic"])

    return bas_dk >= limit_dk


def arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v):
    """
    Arife günü kısıtlı agent yasağı:
    - Hamile / süt izni / mesaiye kalamaz agentlar 13:00 sonrasına sarkan vardiyada çalışamaz.
    - Özel ARIFE_09_13 vardiyası yasak değildir.
    """

    if not is_arife_gunu(ds):
        return False

    if (ds, v) not in saat:
        return False

    if (ds, v) in arife_ozel_vardiyalar:
        return False

    ds_key = tatil_ds_key(ds)

    bas, bit, bas_dk, bit_dk = tatil_vardiya_abs_aralik(ds, v)
    limit_dk = tatil_dakika(ARIFE_GUNLERI[ds_key]["mesai_baslangic"])

    return bit_dk > limit_dk


def resmi_tatil_mesai_vardiyasi_mi_func(ds, v):
    """
    Resmi tatil günü tüm vardiyalar resmi tatil mesaisi sayılır.
    """

    if not is_resmi_tatil_gunu(ds):
        return False

    if (ds, v) not in saat:
        return False

    return True


# Tatil kısıtlı agentlar:
# - hamile
# - süt izni
# - mesaiye kalamaz
tatil_kisitli_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

# Geriye dönük isimler
arife_kisitli_agents = tatil_kisitli_agents
resmi_tatil_kisitli_agents = tatil_kisitli_agents


arife_mesai_vardiyasi_mi = {}
arife_kisitli_yasak_vardiya_mi = {}
resmi_tatil_mesai_vardiyasi_mi = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        arife_mesai_vardiyasi_mi[(ds, v)] = arife_mesai_vardiyasi_mi_func(ds, v)
        arife_kisitli_yasak_vardiya_mi[(ds, v)] = arife_kisitli_agent_icin_yasak_vardiya_mi_func(ds, v)
        resmi_tatil_mesai_vardiyasi_mi[(ds, v)] = resmi_tatil_mesai_vardiyasi_mi_func(ds, v)


arife_plan_gunleri = [
    ds for ds in PLAN_GUNLER
    if is_arife_gunu(ds)
]

resmi_tatil_plan_gunleri = [
    ds for ds in PLAN_GUNLER
    if is_resmi_tatil_gunu(ds)
]

ozel_tatil_plan_gunleri = sorted(
    set(arife_plan_gunleri + resmi_tatil_plan_gunleri),
    key=lambda x: pd.to_datetime(x)
)

print("Arife kuralı aktif mi:", ENABLE_ARIFE_KURALI)
print("Arife günleri:", arife_plan_gunleri)
print("Arife özel vardiyalar:", arife_ozel_vardiyalar)
print("Arife mesaili vardiya sayısı:", sum(arife_mesai_vardiyasi_mi.values()))
print("Arife kısıtlı agent için yasak vardiya sayısı:", sum(arife_kisitli_yasak_vardiya_mi.values()))

print("Resmi tatil kuralı aktif mi:", ENABLE_RESMI_TATIL_KURALI)
print("Resmi tatil günleri:", resmi_tatil_plan_gunleri)
print("Resmi tatil mesaili vardiya sayısı:", sum(resmi_tatil_mesai_vardiyasi_mi.values()))

print("Tatil kısıtlı agent sayısı:", len(tatil_kisitli_agents))


# %% [HÜCRE] - ARİFE / RESMİ TATİL ÇALIŞMA KURALLARI

arife_mesai = {}
resmi_tatil_mesai = {}

tatil_constraints = 0
arife_09_13_zorunlu_constraints = 0
arife_non_kisitli_ozel_vardiya_yasak_constraints = 0
resmi_tatil_kisitli_yasak_constraints = 0
tatil_skip_rows = []


for a in AGENTS:
    a = str(a).strip()

    # -------------------------------------------------
    # 1) ARİFE KURALLARI
    # -------------------------------------------------
    for ds in arife_plan_gunleri:

        ds_key = tatil_ds_key(ds)
        ozel_v = ARIFE_GUNLERI[ds_key]["ozel_vardiya_kodu"]

        if a in tatil_kisitli_agents:

            # Kısıtlı agent izinliyse arife 09-13'e zorlamıyoruz.
            if ds in izin_map.get(a, set()):
                tatil_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "rule": "arife_09_13",
                    "reason": "izinli"
                })
            else:
                # Kısıtlı agent arife özel 09-13 vardiyasına atanır.
                if (a, ds, ozel_v) in x:
                    model.Add(x[(a, ds, ozel_v)] == 1)
                    arife_09_13_zorunlu_constraints += 1
                else:
                    tatil_skip_rows.append({
                        "agent_user_code": a,
                        "date": ds,
                        "rule": "arife_09_13",
                        "reason": "ozel_09_13_x_yok"
                    })

            # Kısıtlı agentlar 13 sonrasına sarkan vardiyalarda çalışamaz.
            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):
                    model.Add(x[(a, ds, v)] == 0)
                    tatil_constraints += 1

        else:
            # Kısıtlı olmayan agentlar özel ARIFE_09_13 vardiyasına atanamaz.
            if (a, ds, ozel_v) in x:
                model.Add(x[(a, ds, ozel_v)] == 0)
                arife_non_kisitli_ozel_vardiya_yasak_constraints += 1

        # Arife mesai etiketi
        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if arife_mesai_vardiyasi_mi.get((ds, v), False):

                arife_mesai[(a, ds, v)] = model.NewBoolVar(
                    f"arife_mesai_{a}_{ds}_{v}"
                )

                model.Add(arife_mesai[(a, ds, v)] == x[(a, ds, v)])
                tatil_constraints += 1


    # -------------------------------------------------
    # 2) RESMİ TATİL KURALLARI
    # -------------------------------------------------
    for ds in resmi_tatil_plan_gunleri:

        if a in tatil_kisitli_agents:

            # Hamile / süt izni / mesaiye kalamaz resmi tatilde çalışamaz.
            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                model.Add(x[(a, ds, v)] == 0)
                resmi_tatil_kisitli_yasak_constraints += 1

        else:
            # Diğer agentlar çalışırsa resmi tatil mesaisi olarak işaretlenir.
            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False):

                    resmi_tatil_mesai[(a, ds, v)] = model.NewBoolVar(
                        f"resmi_tatil_mesai_{a}_{ds}_{v}"
                    )

                    model.Add(resmi_tatil_mesai[(a, ds, v)] == x[(a, ds, v)])
                    tatil_constraints += 1


print("Arife 09-13 zorunlu atama kısıtı:", arife_09_13_zorunlu_constraints)
print("Arife non-kısıtlı özel vardiya yasak kısıtı:", arife_non_kisitli_ozel_vardiya_yasak_constraints)
print("Arife mesai değişken sayısı:", len(arife_mesai))

print("Resmi tatil kısıtlı agent yasak kısıtı:", resmi_tatil_kisitli_yasak_constraints)
print("Resmi tatil mesai değişken sayısı:", len(resmi_tatil_mesai))

print("Toplam tatil kısıtı:", tatil_constraints)

if tatil_skip_rows:
    tatil_skip_df = pd.DataFrame(tatil_skip_rows)
    print("Tatil skip sayısı:", len(tatil_skip_df))
    display(tatil_skip_df.head(100))



# %% [HÜCRE] - TAKIM HAFTALIK BASE VARDİYA - HAFTA İÇİ HARD / HAFTA SONU SERBEST
# Pazartesi-Cuma: Takım bütünlüğü korunur.
# Cumartesi-Pazar: Serbest.
# Arife / resmi tatil: özel gün olduğu için takım base hard kuralından hariç tutulur.

team_base_constraints = 0
team_weekday_link_constraints = 0
weekend_free_count = 0
tatil_team_base_skip_count = 0

# 1. Her takım-her hafta için tek base vardiya seç
for t in TAKIMLAR:
    for wk in WEEKS:

        vars_base = [
            team_week_base[(t, wk, v)]
            for v in week_vardiyalari[wk]
            if (t, wk, v) in team_week_base
            and v not in arife_ozel_vardiya_kodlari
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

        # Arife / resmi tatil özel planlanır.
        # Bu günlerde takım base hard kuralı uygulanmaz.
        if ds in ozel_tatil_plan_gunleri:
            tatil_team_base_skip_count += 1
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
                    model.Add(x[(a, ds, v)] == 0)
                    team_weekday_link_constraints += 1

            # Hafta sonu: takım serbest
            else:
                weekend_free_count += 1


print("Takım-hafta tek base vardiya kısıtı:", team_base_constraints)
print("Hafta içi takım hard bağlantı kısıtı:", team_weekday_link_constraints)
print("Hafta sonu serbest bırakılan agent-gün-vardiya opsiyonu:", weekend_free_count)
print("Arife/resmi tatil takım base skip sayısı:", tatil_team_base_skip_count)



# %% [HÜCRE] - FAZLA ATAMA ÜST LİMİTİ

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

        max_fazla = fazla_atama_ust_limit.get((ds, v), GENEL_MAX_FAZLA_ATAMA)

        # -------------------------------------------------
        # ARİFE ÖZEL 09-13 VARDİYASI
        # -------------------------------------------------
        if (ds, v) in arife_ozel_vardiyalar:

            forced_count = 0

            for a in tatil_kisitli_agents:
                a = str(a).strip()

                if ds in izin_map.get(a, set()):
                    continue

                if (a, ds, v) in x:
                    forced_count += 1

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
    print("Arife özel 09-13 cap esnetilen satır sayısı:", len(arife_cap_relax_df))
    display(arife_cap_relax_df)



# -------------------------------------------------
# ARİFE / RESMİ TATİL MESAİ CEZASI
# -------------------------------------------------
# Şimdilik ikisi de 0.
# Bu nedenle model tatil mesaisinden kaçmak için coverage bozmaz.
# Sadece Excel/kontrol tarafında mesai etiketi üretir.

if "arife_mesai" in globals() and ARIFE_MESAI_W > 0:
    for (a, ds, v), var in arife_mesai.items():
        objective_terms.append(
            ARIFE_MESAI_W * var
        )

if "resmi_tatil_mesai" in globals() and RESMI_TATIL_MESAI_W > 0:
    for (a, ds, v), var in resmi_tatil_mesai.items():
        objective_terms.append(
            RESMI_TATIL_MESAI_W * var
        )

print("ARIFE_MESAI_W:", ARIFE_MESAI_W)
print("RESMI_TATIL_MESAI_W:", RESMI_TATIL_MESAI_W)



# %% KONTROL - ARİFE / RESMİ TATİL

tatil_kontrol_rows = []

for a in AGENTS:
    a = str(a).strip()

    for ds in ozel_tatil_plan_gunleri:

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            assigned = solver.Value(x[(a, ds, v)])

            if assigned == 0:
                continue

            bas, bit = saat[(ds, v)] if (ds, v) in saat else (None, None)

            tatil_kontrol_rows.append({
                "agent_user_code": a,
                "date": ds,
                "shift": v,
                "shift_start": bas,
                "shift_end": bit,

                "is_arife": is_arife_gunu(ds),
                "is_resmi_tatil": is_resmi_tatil_gunu(ds),

                "is_arife_ozel_09_13": (ds, v) in arife_ozel_vardiyalar,
                "arife_mesai_vardiyasi_mi": arife_mesai_vardiyasi_mi.get((ds, v), False),
                "resmi_tatil_mesai_vardiyasi_mi": resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False),

                "tatil_kisitli_agent": a in tatil_kisitli_agents,
                "arife_kisitli_icin_yasak_mi": arife_kisitli_yasak_vardiya_mi.get((ds, v), False),

                "arife_mesai": (
                    solver.Value(arife_mesai[(a, ds, v)])
                    if "arife_mesai" in globals() and (a, ds, v) in arife_mesai
                    else 0
                ),

                "resmi_tatil_mesai": (
                    solver.Value(resmi_tatil_mesai[(a, ds, v)])
                    if "resmi_tatil_mesai" in globals() and (a, ds, v) in resmi_tatil_mesai
                    else 0
                ),
            })

tatil_kontrol_df = pd.DataFrame(tatil_kontrol_rows)

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "hamile_flg",
    "sut_izni_flg",
    "mesaiye_kalamaz_flg",
    "sabah_calisir_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

tatil_kontrol_df = tatil_kontrol_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("Tatil çalışan özet:")
display(
    tatil_kontrol_df
    .groupby(
        [
            "date",
            "is_arife",
            "is_resmi_tatil",
            "shift_start",
            "shift_end",
            "is_arife_ozel_09_13",
            "arife_mesai_vardiyasi_mi",
            "resmi_tatil_mesai_vardiyasi_mi"
        ],
        as_index=False
    )
    .agg(
        calisan_agent_sayisi=("agent_user_code", "nunique"),
        kisitli_agent_sayisi=("tatil_kisitli_agent", "sum"),
        arife_mesai_sayisi=("arife_mesai", "sum"),
        resmi_tatil_mesai_sayisi=("resmi_tatil_mesai", "sum"),
    )
    .sort_values(["date", "shift_start", "shift_end"])
)

print("Arife kısıtlı agent 13 sonrası ihlal sayısı:")
arife_ihlal_df = tatil_kontrol_df[
    (tatil_kontrol_df["is_arife"] == True) &
    (tatil_kontrol_df["tatil_kisitli_agent"] == True) &
    (tatil_kontrol_df["arife_kisitli_icin_yasak_mi"] == True)
]
print(len(arife_ihlal_df))
display(arife_ihlal_df)

print("Resmi tatilde kısıtlı agent çalışma ihlali:")
resmi_ihlal_df = tatil_kontrol_df[
    (tatil_kontrol_df["is_resmi_tatil"] == True) &
    (tatil_kontrol_df["tatil_kisitli_agent"] == True)
]
print(len(resmi_ihlal_df))
display(resmi_ihlal_df)
