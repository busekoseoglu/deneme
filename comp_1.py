# =================================================
# LOKASYON AKŞAM / GECE DAĞILIM KURALI
# =================================================

ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI = True

# Akşam/gece vardiya kapsamı:
# 15:00 girişli vardiyadan 00:00 girişli vardiyaya kadar.
AKSAM_GECE_SHIFT_START_MIN = "15:00"
AKSAM_GECE_0000_DAHIL = True

# Oranlar iş biriminin Excel'inden alınır.
# Model bu oranları hesaplamaz.
LOKASYON_AKSAM_GECE_ORANLARI = {
    "izmir": 0.30,
    "gebze": 0.35,
    "samsun": 0.35,
}

# Sapma cezası
LOKASYON_AKSAM_GECE_ORAN_SAPMA_W = 25000


# %% [KISIT] - AKŞAM / GECE VARDİYALARINDA LOKASYON ORANLI DAĞILIM
# Amaç:
# 15:00 girişli vardiyadan 00:00 girişli vardiyaya kadar olan vardiyalarda
# İzmir / Gebze / Samsun lokasyonlarının iş biriminin verdiği oranlara
# yakın çalışmasını sağlamak.
#
# Bu kural SOFT constraint'tir.
# Sapmalar objective içinde cezalandırılır.
#
# Ankara bu oran kuralına dahil değildir ama gece/akşam vardiyasına yazılabilir.
# Hatay/Adıyaman/Maraş zaten sabah_calisir_flg=1 kuralı ile geç vardiyalara yazılmamalıdır.

# --------------------------------------------------
# 0) DEFAULTLAR
# --------------------------------------------------

if "ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI" not in globals():
    ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI = False

if "LOKASYON_AKSAM_GECE_ORANLARI" not in globals():
    LOKASYON_AKSAM_GECE_ORANLARI = {}

if "LOKASYON_AKSAM_GECE_ORAN_SAPMA_W" not in globals():
    LOKASYON_AKSAM_GECE_ORAN_SAPMA_W = 25000

if "AKSAM_GECE_SHIFT_START_MIN" not in globals():
    AKSAM_GECE_SHIFT_START_MIN = "15:00"

if "AKSAM_GECE_0000_DAHIL" not in globals():
    AKSAM_GECE_0000_DAHIL = True


# --------------------------------------------------
# 1) ÇIKTI / DEĞİŞKEN SÖZLÜKLERİ
# --------------------------------------------------

lokasyon_aksam_gece_sapma_terms = []

lokasyon_aksam_gece_count = {}
lokasyon_aksam_gece_target = {}
lokasyon_aksam_gece_diff = {}
lokasyon_aksam_gece_abs_diff = {}

lokasyon_aksam_gece_debug_rows = []
lokasyon_aksam_gece_shift_rows = []

agent_location_map = {}
aksam_gece_shift_keys = []


# --------------------------------------------------
# 2) HELPERLAR
# --------------------------------------------------

def _time_to_min_for_loc_rule(t):
    if t is None:
        return None

    if pd.isna(t):
        return None

    t = str(t).strip()

    if len(t) == 5 and ":" in t:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)

    if len(t) == 8 and ":" in t:
        hh, mm, ss = t.split(":")
        return int(hh) * 60 + int(mm)

    return None


def _normalize_location_for_rule(val):
    if val is None:
        return None

    if pd.isna(val):
        return None

    val = str(val).strip().lower()

    tr_map = str.maketrans({
        "ı": "i",
        "İ": "i",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ş": "s",
        "Ş": "s",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    })

    val = val.translate(tr_map)

    if "izmir" in val:
        return "izmir"

    if "gebze" in val:
        return "gebze"

    if "samsun" in val:
        return "samsun"

    if "ankara" in val:
        return "ankara"

    if (
        "hatay" in val
        or "hata" in val
        or "adiyaman" in val
        or "maras" in val
        or "kahramanmaras" in val
    ):
        return "hatay_adiyaman_maras"

    return val


def _get_shift_time_for_loc_rule(ds, v):
    """
    saat dict'inde ds farklı formatlarda tutulmuş olabilir.
    Bu yüzden birkaç formatla dener.
    """

    if "saat" not in globals() or not isinstance(saat, dict):
        return None, None

    ds_ts = pd.to_datetime(ds)
    ds_str = ds_ts.strftime("%Y-%m-%d")
    ds_date = ds_ts.date()

    possible_ds_keys = [
        ds,
        ds_str,
        ds_date,
        ds_ts,
    ]

    possible_v_keys = [
        v,
        str(v).strip(),
    ]

    for d_key in possible_ds_keys:
        for v_key in possible_v_keys:
            key = (d_key, v_key)

            if key in saat:
                val = saat[key]

                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    return val[0], val[1]

    return None, None


def _is_aksam_gece_shift_for_loc_rule(ds, v):
    """
    Akşam/gece vardiyası:
    - 15:00 ve sonrası başlayan vardiyalar
    - 00:00 başlayan vardiya
    """

    shift_start, shift_end = _get_shift_time_for_loc_rule(ds, v)

    start_min = _time_to_min_for_loc_rule(shift_start)

    if start_min is None:
        return False

    limit_min = _time_to_min_for_loc_rule(AKSAM_GECE_SHIFT_START_MIN)

    if limit_min is None:
        limit_min = 15 * 60

    if AKSAM_GECE_0000_DAHIL and start_min == 0:
        return True

    return start_min >= limit_min


# --------------------------------------------------
# 3) KURAL AKTİFSE MODEL KISITLARINI KUR
# --------------------------------------------------

if ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI:

    # --------------------------------------------------
    # 3.1) Config lokasyonlarını normalize et
    # --------------------------------------------------

    lokasyon_oranlari_normalized = {}

    for loc, oran in LOKASYON_AKSAM_GECE_ORANLARI.items():
        loc_norm = _normalize_location_for_rule(loc)
        lokasyon_oranlari_normalized[loc_norm] = float(oran)

    oran_lokasyonlari = list(lokasyon_oranlari_normalized.keys())

    oran_toplami = sum(lokasyon_oranlari_normalized.values())

    print("Lokasyon oran kuralı aktif.")
    print("Config lokasyon oranları:", lokasyon_oranlari_normalized)
    print("Oran toplamı:", oran_toplami)

    if oran_toplami > 1.0001:
        print("UYARI: Lokasyon oran toplamı 1'den büyük. Hedef toplam talebi aşabilir.")

    # --------------------------------------------------
    # 3.2) Agent lokasyon map'i
    # --------------------------------------------------
    # Öncelik df_tam["lokasyon"].
    # Eğer yoksa fallback olarak working_main_group kullanılır.

    for _, r in df_tam.iterrows():

        a = str(r["agent_user_code"]).strip()

        if "lokasyon" in df_tam.columns:
            raw_loc = r.get("lokasyon")

        elif "working_main_group" in df_tam.columns:
            raw_loc = r.get("working_main_group")

        else:
            raw_loc = None

        agent_location_map[a] = _normalize_location_for_rule(raw_loc)

    agent_location_debug_df = pd.DataFrame([
        {
            "agent_user_code": a,
            "lokasyon_normalized": loc
        }
        for a, loc in agent_location_map.items()
    ])

    print("Agent lokasyon dağılımı:")
    display(
        agent_location_debug_df
        .groupby("lokasyon_normalized", as_index=False)
        .agg(agent_sayisi=("agent_user_code", "nunique"))
        .sort_values("agent_sayisi", ascending=False)
    )

    # --------------------------------------------------
    # 3.3) Akşam/gece vardiya key'lerini bul
    # --------------------------------------------------

    for ds in PLAN_GUNLER:

        for v in gun_vardiyalari.get(ds, []):

            if (ds, v) not in talep:
                continue

            if not _is_aksam_gece_shift_for_loc_rule(ds, v):
                continue

            shift_start, shift_end = _get_shift_time_for_loc_rule(ds, v)

            aksam_gece_shift_keys.append((ds, v))

            lokasyon_aksam_gece_shift_rows.append({
                "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
                "week": day_week.get(ds) if "day_week" in globals() else None,
                "shift": v,
                "shift_start": shift_start,
                "shift_end": shift_end,
                "required": int(talep[(ds, v)]),
            })

    lokasyon_aksam_gece_shift_df = pd.DataFrame(
        lokasyon_aksam_gece_shift_rows
    )

    total_aksam_gece_required = sum(
        int(talep[(ds, v)])
        for ds, v in aksam_gece_shift_keys
        if (ds, v) in talep
    )

    print("Akşam/gece vardiya satır sayısı:", len(aksam_gece_shift_keys))
    print("Toplam akşam/gece required:", total_aksam_gece_required)

    display(lokasyon_aksam_gece_shift_df.head(20))

    # --------------------------------------------------
    # 3.4) Lokasyon bazlı gerçek atama değişkenlerini say
    # --------------------------------------------------
    # Sadece config içindeki lokasyonlar için count oluşturulur.
    # Ankara bu count'a dahil değildir.

    for loc in oran_lokasyonlari:

        loc_agents = [
            str(a).strip()
            for a in AGENTS
            if agent_location_map.get(str(a).strip()) == loc
        ]

        loc_assignment_vars = []

        for a in loc_agents:

            for ds, v in aksam_gece_shift_keys:

                if (a, ds, v) in x:
                    loc_assignment_vars.append(x[(a, ds, v)])

        max_possible = len(loc_assignment_vars)

        lokasyon_aksam_gece_count[loc] = model.NewIntVar(
            0,
            max_possible,
            f"lokasyon_aksam_gece_count_{loc}"
        )

        if loc_assignment_vars:
            model.Add(
                lokasyon_aksam_gece_count[loc]
                == sum(loc_assignment_vars)
            )
        else:
            model.Add(
                lokasyon_aksam_gece_count[loc] == 0
            )

    # --------------------------------------------------
    # 3.5) Config oranına göre hedefleri ve sapmaları oluştur
    # --------------------------------------------------
    # target = toplam akşam/gece required * config oran
    #
    # Oran burada hesaplanmaz.
    # İş birimi oranı config'ten gelir.

    for loc in oran_lokasyonlari:

        oran = float(lokasyon_oranlari_normalized[loc])

        target = int(round(total_aksam_gece_required * oran))

        lokasyon_aksam_gece_target[loc] = target

        count_var = lokasyon_aksam_gece_count[loc]

        max_possible = count_var.Proto().domain[-1]

        diff_lb = -target
        diff_ub = max_possible - target

        lokasyon_aksam_gece_diff[loc] = model.NewIntVar(
            diff_lb,
            diff_ub,
            f"lokasyon_aksam_gece_diff_{loc}"
        )

        max_abs_diff = max(abs(diff_lb), abs(diff_ub))

        lokasyon_aksam_gece_abs_diff[loc] = model.NewIntVar(
            0,
            max_abs_diff,
            f"lokasyon_aksam_gece_abs_diff_{loc}"
        )

        model.Add(
            lokasyon_aksam_gece_diff[loc]
            ==
            count_var - target
        )

        model.AddAbsEquality(
            lokasyon_aksam_gece_abs_diff[loc],
            lokasyon_aksam_gece_diff[loc]
        )

        lokasyon_aksam_gece_sapma_terms.append(
            LOKASYON_AKSAM_GECE_ORAN_SAPMA_W
            * lokasyon_aksam_gece_abs_diff[loc]
        )

        loc_agent_count = sum(
            1
            for a in AGENTS
            if agent_location_map.get(str(a).strip()) == loc
        )

        lokasyon_aksam_gece_debug_rows.append({
            "lokasyon": loc,
            "config_oran": oran,
            "agent_sayisi": loc_agent_count,
            "toplam_aksam_gece_required": total_aksam_gece_required,
            "hedef_atama": target,
            "max_possible_var_count": max_possible,
            "kural_tipi": "soft_abs_diff_penalty",
            "penalty_weight": LOKASYON_AKSAM_GECE_ORAN_SAPMA_W,
        })

    lokasyon_aksam_gece_debug_df = pd.DataFrame(
        lokasyon_aksam_gece_debug_rows
    )

    print("Lokasyon akşam/gece hedefleri:")
    display(lokasyon_aksam_gece_debug_df)

else:

    total_aksam_gece_required = 0
    lokasyon_aksam_gece_shift_df = pd.DataFrame()
    lokasyon_aksam_gece_debug_df = pd.DataFrame()
    agent_location_debug_df = pd.DataFrame()

    print("Lokasyon akşam/gece oran kuralı kapalı.")



# Lokasyon akşam/gece oran sapma cezası
if (
    "ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI" in globals()
    and ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI
    and "lokasyon_aksam_gece_sapma_terms" in globals()
):
    obj_terms.extend(lokasyon_aksam_gece_sapma_terms)


# %% [KONTROL] - AKŞAM / GECE LOKASYON ORAN SONUÇ KONTROLÜ
# Amaç:
# İzmir / Gebze / Samsun için akşam/gece atama sayıları
# config hedeflerine yakın mı görmek.

lokasyon_aksam_gece_result_rows = []

if (
    "ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI" in globals()
    and ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI
):

    for loc in LOKASYON_AKSAM_GECE_ORANLARI.keys():

        actual = int(
            solver.Value(lokasyon_aksam_gece_count[loc])
        )

        target = int(lokasyon_aksam_gece_target[loc])

        diff = actual - target

        abs_diff = abs(diff)

        lokasyon_aksam_gece_result_rows.append({
            "lokasyon": loc,
            "config_oran": float(LOKASYON_AKSAM_GECE_ORANLARI[loc]),
            "toplam_aksam_gece_required": sum(
                int(talep[(ds, v)])
                for ds, v in aksam_gece_shift_keys
                if (ds, v) in talep
            ),
            "hedef_atama": target,
            "gercek_atama": actual,
            "fark": diff,
            "mutlak_fark": abs_diff,
            "gercek_oran": (
                actual
                /
                sum(
                    int(talep[(ds, v)])
                    for ds, v in aksam_gece_shift_keys
                    if (ds, v) in talep
                )
                if len(aksam_gece_shift_keys) > 0
                else 0
            ),
        })

lokasyon_aksam_gece_result_df = pd.DataFrame(
    lokasyon_aksam_gece_result_rows
)

display(lokasyon_aksam_gece_result_df)


