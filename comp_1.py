# %% [KISIT] - AKŞAM / GECE VARDİYALARINDA LOKASYON ORANLI DAĞILIM
# Amaç:
# 15:00 girişli vardiyadan 00:00 girişli vardiyaya kadar olan vardiyalarda
# izmir / gebze / samsun lokasyonlarının config'te verilen oranlara
# yakın dağıtılmasını sağlamak.
#
# Bu kural SOFT constraint'tir.
# Sapmalar objective içinde cezalandırılır.
#
# Notlar:
# - Oran model içinde hesaplanmaz.
# - Oranlar CONFIG içinden gelir.
# - Sadece LOKASYON_AKSAM_GECE_ORANLARI içinde verilen lokasyonlar için çalışır.
# - Ankara config'te yoksa oran hesabına girmez ama gece/akşam vardiyasına yazılabilir.
# - Hatay/Adıyaman/Maraş config'te yoksa oran hesabına girmez.
# - df_tam içindeki lokasyon kolonu kullanılır.

# --------------------------------------------------
# 0) DEFAULT / GÜVENLİ BAŞLANGIÇ
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
# 1) ÇIKTILAR / MODEL TERİMLERİ
# --------------------------------------------------

lokasyon_aksam_gece_sapma_terms = []

lokasyon_aksam_gece_count = {}
lokasyon_aksam_gece_target = {}
lokasyon_aksam_gece_diff = {}
lokasyon_aksam_gece_abs_diff = {}
lokasyon_aksam_gece_max_possible = {}

lokasyon_aksam_gece_debug_rows = []
lokasyon_aksam_gece_shift_rows = []

agent_location_map = {}
aksam_gece_shift_keys = []


# --------------------------------------------------
# 2) HELPERLAR
# --------------------------------------------------

def _clean_loc_for_aksam_gece(val):
    if pd.isna(val):
        return None
    return str(val).strip().lower()


def _time_to_min_for_aksam_gece(t):
    if t is None or pd.isna(t):
        return None

    t = str(t).strip()

    if len(t) == 5 and ":" in t:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)

    if len(t) == 8 and ":" in t:
        hh, mm, ss = t.split(":")
        return int(hh) * 60 + int(mm)

    return None


def _get_shift_time_for_aksam_gece(ds, v):
    """
    saat dict'inde ds bazen string, date veya Timestamp olabilir.
    Bu yüzden birkaç farklı key ile dener.
    """

    if "saat" not in globals() or not isinstance(saat, dict):
        return None, None

    ds_ts = pd.to_datetime(ds)
    ds_str = ds_ts.strftime("%Y-%m-%d")
    ds_date = ds_ts.date()

    v_str = str(v).strip()

    possible_keys = [
        (ds, v),
        (ds, v_str),
        (ds_str, v),
        (ds_str, v_str),
        (ds_date, v),
        (ds_date, v_str),
        (ds_ts, v),
        (ds_ts, v_str),
    ]

    for key in possible_keys:
        if key in saat:
            val = saat[key]

            if isinstance(val, (list, tuple)) and len(val) >= 2:
                return val[0], val[1]

    return None, None


def _is_aksam_gece_shift(ds, v):
    """
    Akşam/gece vardiyası:
    - 15:00 ve sonrası başlayan vardiyalar
    - 00:00 başlayan vardiya
    """

    shift_start, shift_end = _get_shift_time_for_aksam_gece(ds, v)

    start_min = _time_to_min_for_aksam_gece(shift_start)

    if start_min is None:
        return False

    limit_min = _time_to_min_for_aksam_gece(AKSAM_GECE_SHIFT_START_MIN)

    if limit_min is None:
        limit_min = 15 * 60

    if AKSAM_GECE_0000_DAHIL and start_min == 0:
        return True

    return start_min >= limit_min


# --------------------------------------------------
# 3) KURAL AKTİFSE KISITLARI KUR
# --------------------------------------------------

if ENABLE_LOKASYON_AKSAM_GECE_ORAN_KURALI:

    if "lokasyon" not in df_tam.columns:
        raise ValueError("df_tam içinde 'lokasyon' kolonu yok. Lokasyon oran kuralı çalışamaz.")

    # --------------------------------------------------
    # 3.1) Config oranlarını hazırla
    # --------------------------------------------------
    # Burada oran hesaplamıyoruz.
    # İş biriminin verdiği oranı direkt config'ten alıyoruz.

    lokasyon_oranlari = {
        _clean_loc_for_aksam_gece(loc): float(oran)
        for loc, oran in LOKASYON_AKSAM_GECE_ORANLARI.items()
    }

    oran_lokasyonlari = list(lokasyon_oranlari.keys())
    oran_toplami = sum(lokasyon_oranlari.values())

    print("Lokasyon akşam/gece oran kuralı aktif.")
    print("Config lokasyon oranları:", lokasyon_oranlari)
    print("Oran toplamı:", oran_toplami)

    if oran_toplami > 1.0001:
        print("UYARI: Lokasyon oran toplamı 1'den büyük. Hedef toplam required'ı aşabilir.")

    # --------------------------------------------------
    # 3.2) Agent lokasyon map'i
    # --------------------------------------------------

    for _, r in df_tam.iterrows():

        a = str(r["agent_user_code"]).strip()
        loc = _clean_loc_for_aksam_gece(r["lokasyon"])

        agent_location_map[a] = loc

    agent_location_debug_df = pd.DataFrame([
        {
            "agent_user_code": a,
            "lokasyon": loc
        }
        for a, loc in agent_location_map.items()
    ])

    print("Agent lokasyon dağılımı:")
    display(
        agent_location_debug_df
        .groupby("lokasyon", as_index=False)
        .agg(agent_sayisi=("agent_user_code", "nunique"))
        .sort_values("agent_sayisi", ascending=False)
    )

    # --------------------------------------------------
    # 3.3) Akşam/gece vardiyalarını bul
    # --------------------------------------------------

    for ds in PLAN_GUNLER:

        for v in gun_vardiyalari.get(ds, []):

            if (ds, v) not in talep:
                continue

            if not _is_aksam_gece_shift(ds, v):
                continue

            shift_start, shift_end = _get_shift_time_for_aksam_gece(ds, v)

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
    # 3.4) Lokasyon bazlı gerçek atama count değişkenleri
    # --------------------------------------------------
    # Sadece config içindeki lokasyonlar için count oluşturulur.
    # Örn: izmir, gebze, samsun.
    #
    # Ankara config'te yoksa burada sayılmaz.
    # Ama model Ankara'yı akşam/gece vardiyasına atayabilir.

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

        lokasyon_aksam_gece_max_possible[loc] = max_possible

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
    # 3.5) Config oranına göre hedef ve sapma değişkenleri
    # --------------------------------------------------
    # target = toplam akşam/gece required * config oran
    #
    # Örnek:
    # total required = 180
    # izmir oran = 0.30
    # izmir hedef = 54

    for loc in oran_lokasyonlari:

        oran = float(lokasyon_oranlari[loc])

        target = int(round(total_aksam_gece_required * oran))

        lokasyon_aksam_gece_target[loc] = target

        count_var = lokasyon_aksam_gece_count[loc]

        max_possible = lokasyon_aksam_gece_max_possible[loc]

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
            "sapma_weight": LOKASYON_AKSAM_GECE_ORAN_SAPMA_W,
            "kural_tipi": "soft_abs_diff_penalty",
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
