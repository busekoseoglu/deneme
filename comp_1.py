# %% [RAPOR] - MODEL SONUCUNDAN ÇOK SHEET'Lİ EXCEL RAPORU
#
# Bu hücre SOLVE hücresinden sonra çalıştırılır.
#
# Güncel model yapısı:
# - Tek izin/OFF kaynağı: tip_map
# - tip_map tipleri: izin, off_t, off_t2
# - x ve work solver kararlarından okunur
# - pair_off varsa doğrudan solver'dan okunur
# - aylik_mesai_gun varsa aylık mesai toplamı solver'dan okunur
#
# TELAFİ NOTU:
# Güncel modelde gün bazlı "telafi" karar değişkeni yoktur.
# Bu rapor telafi gününü şu şekilde sınıflandırır:
# 1) Bir haftadaki off_t + off_t2 talebi 2'yi aşarsa borç oluşur.
# 2) Başka bir haftada haftalık normal hedefin üzerindeki çalışma,
#    önce açık OFF borcuna atanır.
# 3) Kalan ekstra çalışma, aylik_mesai_gun toplamıyla uyumlu olacak
#    şekilde MESAİ olarak işaretlenir.
#
# Böylece raporda telafi borcu ve ödeme haftası görünür.
# Ancak gün bazlı telafinin solver tarafından kesin seçilmesini istiyorsan
# ileride modele ayrıca telafi_gun karar değişkeni eklenmelidir.

from collections import defaultdict, deque
from datetime import datetime, date, timedelta

import pandas as pd
from ortools.sat.python import cp_model
from artifact_tool import Workbook, SpreadsheetFile


# ------------------------------------------------------------
# 0) TEMEL KONTROLLER
# ------------------------------------------------------------

if "status" not in globals():
    raise NameError("Önce modeli solve et. 'status' bulunamadı.")

if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
    raise ValueError(
        f"Excel yalnızca FEASIBLE/OPTIMAL çözümden üretilebilir. "
        f"Mevcut status: {solver.StatusName(status)}"
    )

zorunlu_degiskenler = [
    "solver",
    "x",
    "work",
    "tip_map",
    "AGENTS",
    "PLAN_GUNLER",
    "gun_vardiyalari",
    "df_tam",
]

eksik_degiskenler = [
    isim for isim in zorunlu_degiskenler
    if isim not in globals()
]

if eksik_degiskenler:
    raise NameError(
        "Eksik değişkenler: " + ", ".join(eksik_degiskenler)
    )


# ------------------------------------------------------------
# 1) AYARLAR
# ------------------------------------------------------------

EXCEL_DOSYA_ADI = globals().get(
    "EXCEL_DOSYA_ADI",
    "vardiya_planlama_model_raporu.xlsx"
)

RAPOR_YOLU = f"/mnt/data/{EXCEL_DOSYA_ADI}"

RENKLER = {
    "BASLIK": "#1F4E78",
    "ALT_BASLIK": "#D9EAF7",
    "NORM": "#E2F0D9",
    "MESAI": "#F8CBAD",
    "TELAFI": "#FFD966",
    "IZIN": "#D9E1F2",
    "OFF_T": "#B4C6E7",
    "OFF_T2": "#8EA9DB",
    "NORMAL_OFF": "#E7E6E6",
    "RESMI_TATIL": "#F4B183",
    "ARIFE": "#FFE699",
    "CIFT_OFF": "#C6E0B4",
    "IHLAL": "#F4CCCC",
    "OK": "#D9EAD3",
    "BEYAZ": "#FFFFFF",
    "YAZI": "#1F1F1F",
}

PLAN_TARIHLER = sorted({
    pd.to_datetime(ds).date()
    for ds in PLAN_GUNLER
})

PLAN_TARIH_SET = set(PLAN_TARIHLER)

DATE_TO_DS = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

RESMI_TATIL_SET = set()

if "resmi_tatil_date_set" in globals():
    RESMI_TATIL_SET = {
        pd.to_datetime(d).date()
        for d in resmi_tatil_date_set
    }
elif "resmi_tatil_plan_gunleri" in globals():
    RESMI_TATIL_SET = {
        pd.to_datetime(d).date()
        for d in resmi_tatil_plan_gunleri
    }
elif "RESMI_TATIL_GUNLERI" in globals():
    RESMI_TATIL_SET = {
        pd.to_datetime(d).date()
        for d in RESMI_TATIL_GUNLERI
    }

ARIFE_SET = set()

if "arife_plan_gunleri" in globals():
    ARIFE_SET = {
        pd.to_datetime(d).date()
        for d in arife_plan_gunleri
    }
elif "ARIFE_GUNLERI" in globals():
    for d in ARIFE_GUNLERI:
        try:
            ARIFE_SET.add(pd.to_datetime(d).date())
        except Exception:
            pass


# ------------------------------------------------------------
# 2) YARDIMCI FONKSİYONLAR
# ------------------------------------------------------------

def norm_agent(value):
    return str(value).strip()


def tip_getir(agent, tarih):
    tip = tip_map.get(norm_agent(agent), {}).get(tarih)
    return str(tip).strip().lower() if tip is not None else ""


def hafta_key(tarih):
    iso = tarih.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def gun_adi_tr(tarih):
    gunler = [
        "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"
    ]
    return gunler[tarih.weekday()]


def vardiya_str(v):
    if isinstance(v, tuple) and len(v) == 2:
        return f"{v[0]}-{v[1]}"
    return str(v)


def agent_meta_map_olustur():
    sonuc = {}

    df_local = df_tam.copy()
    df_local["agent_user_code"] = (
        df_local["agent_user_code"]
        .astype(str)
        .str.strip()
    )

    for _, row in df_local.iterrows():
        a = row["agent_user_code"]

        sonuc[a] = {
            "agent_name": row.get("agent_name", ""),
            "teamleader_name": row.get("teamleader_name", ""),
            "takim": (
                row.get("takim", "")
                or row.get("team", "")
                or row.get("team_name", "")
            ),
            "working_main_group": row.get("working_main_group", ""),
            "mesaiye_kalamaz_flg": row.get(
                "mesaiye_kalamaz_flg", 0
            ),
            "hamile_flg": row.get("hamile_flg", 0),
            "sut_izni_flg": row.get("sut_izni_flg", 0),
            "dogum_izni_flg": row.get("dogum_izni_flg", 0),
            "idari_izinli_flg": row.get("idari_izinli_flg", 0),
        }

    return sonuc


AGENT_META = agent_meta_map_olustur()


# ------------------------------------------------------------
# 3) SOLVER ATAMALARINI OKU
# ------------------------------------------------------------

atama_map = {}
work_map = {}

for a_raw in AGENTS:
    a = norm_agent(a_raw)

    for tarih in PLAN_TARIHLER:
        ds = DATE_TO_DS[tarih]

        work_value = 0
        if (a, ds) in work:
            work_value = int(solver.Value(work[(a, ds)]))

        work_map[(a, tarih)] = work_value

        secilen_vardiyalar = []

        for v in gun_vardiyalari.get(ds, []):
            if (
                (a, ds, v) in x
                and solver.Value(x[(a, ds, v)]) == 1
            ):
                secilen_vardiyalar.append(v)

        atama_map[(a, tarih)] = secilen_vardiyalar


# ------------------------------------------------------------
# 4) HAFTALIK BAZ NORMAL HEDEF
# ------------------------------------------------------------

hafta_tarihleri = defaultdict(list)

for tarih in PLAN_TARIHLER:
    hafta_tarihleri[hafta_key(tarih)].append(tarih)


def haftalik_baz_hedef(agent, wk):
    tarihler = hafta_tarihleri[wk]

    hafta_ici_is_gunleri = [
        t for t in tarihler
        if t.weekday() < 5 and t not in RESMI_TATIL_SET
    ]

    izin_is_gunu = sum(
        1 for t in hafta_ici_is_gunleri
        if tip_getir(agent, t) == "izin"
    )

    return max(
        len(hafta_ici_is_gunleri) - izin_is_gunu,
        0
    )


# ------------------------------------------------------------
# 5) OFF BORCU VE TELAFİ GÜNLERİNİ TÜRET
# ------------------------------------------------------------

off_borc_rows = []
telafi_gunleri = {}
telafi_detay_rows = []
acik_borc_agent = {}

for a_raw in AGENTS:
    a = norm_agent(a_raw)

    hafta_bilgileri = []

    for wk in sorted(hafta_tarihleri):
        tarihler = sorted(hafta_tarihleri[wk])

        talep_tarihleri = [
            t for t in tarihler
            if tip_getir(a, t) in {"off_t", "off_t2"}
        ]

        talep_sayisi = len(talep_tarihleri)
        borc = max(talep_sayisi - 2, 0)

        calisma_tarihleri = [
            t for t in tarihler
            if work_map.get((a, t), 0) == 1
        ]

        baz_hedef = haftalik_baz_hedef(a, wk)
        fazla_calisma = max(
            len(calisma_tarihleri) - baz_hedef,
            0
        )

        # Fazladan çalışılmış günleri raporlama için seç.
        # Öncelik: hafta sonu, sonra en geç tarih.
        telafi_aday_gunleri = sorted(
            calisma_tarihleri,
            key=lambda t: (
                0 if t.weekday() >= 5 else 1,
                -t.toordinal()
            )
        )[:fazla_calisma]

        hafta_bilgileri.append({
            "week": wk,
            "dates": tarihler,
            "off_request_dates": talep_tarihleri,
            "off_request_count": talep_sayisi,
            "debt": borc,
            "work_dates": calisma_tarihleri,
            "base_target": baz_hedef,
            "extra_work": fazla_calisma,
            "extra_work_dates": telafi_aday_gunleri,
        })

        off_borc_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "off_talep_sayisi": talep_sayisi,
            "off_talep_tarihleri": ", ".join(
                t.isoformat() for t in talep_tarihleri
            ),
            "standart_off_hakki": 2,
            "telafi_borcu": borc,
            "haftalik_baz_hedef": baz_hedef,
            "gerceklesen_calisma": len(calisma_tarihleri),
            "fazla_calisma_kapasitesi": fazla_calisma,
        })

    borclar = []

    for info in hafta_bilgileri:
        for sira in range(info["debt"]):
            borclar.append({
                "source_week": info["week"],
                "source_dates": info["off_request_dates"],
                "paid": False,
                "payment_week": "",
                "payment_date": None,
                "payment_type": "",
            })

    kullanilan_odeme_gunleri = set()

    # Önce borç haftasından sonraki haftaları kullan.
    for borc in borclar:
        adaylar = []

        for info in hafta_bilgileri:
            if info["week"] <= borc["source_week"]:
                continue

            for t in info["extra_work_dates"]:
                if t not in kullanilan_odeme_gunleri:
                    adaylar.append((info["week"], t))

        if adaylar:
            odeme_week, odeme_tarih = sorted(
                adaylar,
                key=lambda x: (x[0], x[1])
            )[0]

            borc["paid"] = True
            borc["payment_week"] = odeme_week
            borc["payment_date"] = odeme_tarih
            borc["payment_type"] = "TELAFİ"
            kullanilan_odeme_gunleri.add(odeme_tarih)
            telafi_gunleri[(a, odeme_tarih)] = {
                "source_week": borc["source_week"],
                "payment_week": odeme_week,
                "payment_type": "TELAFİ",
            }

    # Sonraki haftalarda yer yoksa önceki haftadaki fazla
    # çalışma "ön ödeme" olarak kullanılır.
    for borc in borclar:
        if borc["paid"]:
            continue

        adaylar = []

        for info in hafta_bilgileri:
            if info["week"] >= borc["source_week"]:
                continue

            for t in info["extra_work_dates"]:
                if t not in kullanilan_odeme_gunleri:
                    adaylar.append((info["week"], t))

        if adaylar:
            odeme_week, odeme_tarih = sorted(
                adaylar,
                key=lambda x: (x[0], x[1]),
                reverse=True
            )[0]

            borc["paid"] = True
            borc["payment_week"] = odeme_week
            borc["payment_date"] = odeme_tarih
            borc["payment_type"] = "TELAFİ ÖN ÖDEME"
            kullanilan_odeme_gunleri.add(odeme_tarih)
            telafi_gunleri[(a, odeme_tarih)] = {
                "source_week": borc["source_week"],
                "payment_week": odeme_week,
                "payment_type": "TELAFİ ÖN ÖDEME",
            }

    acik_borc = 0

    for borc in borclar:
        if not borc["paid"]:
            acik_borc += 1

        telafi_detay_rows.append({
            "agent_user_code": a,
            "borc_haftasi": borc["source_week"],
            "borca_neden_olan_off_tarihleri": ", ".join(
                t.isoformat()
                for t in borc["source_dates"]
            ),
            "durum": (
                "ÖDENDİ"
                if borc["paid"]
                else "AÇIK BORÇ"
            ),
            "odeme_haftasi": borc["payment_week"],
            "odeme_tarihi": (
                borc["payment_date"].isoformat()
                if borc["payment_date"]
                else ""
            ),
            "odeme_tipi": borc["payment_type"],
        })

    acik_borc_agent[a] = acik_borc


# ------------------------------------------------------------
# 6) MESAİ GÜNLERİNİ RAPORLAMA İÇİN DAĞIT
# ------------------------------------------------------------
#
# aylik_mesai_gun yalnızca aylık toplamı veriyor.
# Bu nedenle gün bazlı MESAİ sınıflandırması rapor amacıyla
# deterministik şekilde yapılır:
# - TELAFİ olarak ayrılan günler dışarıda bırakılır.
# - Öncelik resmi tatil / arife / hafta sonu çalışmalarıdır.
# - Sonra en geç tarihler seçilir.

mesai_gunleri = {}

for a_raw in AGENTS:
    a = norm_agent(a_raw)

    mesai_sayisi = 0

    if (
        "aylik_mesai_gun" in globals()
        and a in aylik_mesai_gun
    ):
        mesai_sayisi = int(
            solver.Value(aylik_mesai_gun[a])
        )

    aday_gunler = [
        t for t in PLAN_TARIHLER
        if (
            work_map.get((a, t), 0) == 1
            and (a, t) not in telafi_gunleri
        )
    ]

    aday_gunler = sorted(
        aday_gunler,
        key=lambda t: (
            0 if t in RESMI_TATIL_SET else 1,
            0 if t in ARIFE_SET else 1,
            0 if t.weekday() >= 5 else 1,
            -t.toordinal(),
        )
    )

    for tarih in aday_gunler[:mesai_sayisi]:
        mesai_gunleri[(a, tarih)] = True


# ------------------------------------------------------------
# 7) GÜNLÜK DURUM SATIRLARI
# ------------------------------------------------------------

gunluk_rows = []
calendar_status = {}

for a_raw in AGENTS:
    a = norm_agent(a_raw)
    meta = AGENT_META.get(a, {})

    for tarih in PLAN_TARIHLER:
        tip = tip_getir(a, tarih)
        calisti = work_map.get((a, tarih), 0) == 1
        vardiyalar = atama_map.get((a, tarih), [])
        vardiya_text = " / ".join(
            vardiya_str(v) for v in vardiyalar
        )

        if tip == "izin":
            durum = "İZİN"
            renk_kodu = "IZIN"

        elif tip == "off_t":
            durum = "OFF_T ✓"
            renk_kodu = "OFF_T"

        elif tip == "off_t2":
            durum = "OFF_T2 ✓"
            renk_kodu = "OFF_T2"

        elif calisti:
            if (a, tarih) in telafi_gunleri:
                durum = "TELAFİ"
                renk_kodu = "TELAFI"
            elif (a, tarih) in mesai_gunleri:
                if tarih in RESMI_TATIL_SET:
                    durum = "RESMİ TATİL MESAİ"
                    renk_kodu = "RESMI_TATIL"
                elif tarih in ARIFE_SET:
                    durum = "ARİFE MESAİ"
                    renk_kodu = "ARIFE"
                else:
                    durum = "MESAİ"
                    renk_kodu = "MESAI"
            else:
                durum = "NORM"
                renk_kodu = "NORM"

        else:
            if tarih in RESMI_TATIL_SET:
                durum = "RESMİ TATİL"
                renk_kodu = "RESMI_TATIL"
            else:
                durum = "OFF"
                renk_kodu = "NORMAL_OFF"

        calendar_status[(a, tarih)] = {
            "durum": durum,
            "renk_kodu": renk_kodu,
            "vardiya": vardiya_text,
        }

        gunluk_rows.append({
            "agent_user_code": a,
            "agent_name": meta.get("agent_name", ""),
            "takim": meta.get("takim", ""),
            "teamleader_name": meta.get(
                "teamleader_name", ""
            ),
            "tarih": tarih.isoformat(),
            "gun": gun_adi_tr(tarih),
            "hafta": hafta_key(tarih),
            "durum": durum,
            "vardiya": vardiya_text,
            "izin_off_tipi": tip,
            "calisti_mi": int(calisti),
            "resmi_tatil_mi": int(
                tarih in RESMI_TATIL_SET
            ),
            "arife_mi": int(tarih in ARIFE_SET),
            "telafi_borc_haftasi": (
                telafi_gunleri.get(
                    (a, tarih), {}
                ).get("source_week", "")
            ),
        })


# ------------------------------------------------------------
# 8) ÇİFT OFF SONUÇLARI
# ------------------------------------------------------------

cift_off_rows = []
cift_off_sayisi_agent = defaultdict(int)

if (
    "pair_off" in globals()
    and "weekend_pairs" in globals()
):
    for a_raw in AGENTS:
        a = norm_agent(a_raw)

        for pair_index, (
            sat_ds,
            sun_ds
        ) in enumerate(weekend_pairs):

            var = pair_off.get((a, pair_index))
            pair_value = (
                int(solver.Value(var))
                if var is not None
                else 0
            )

            sat_date = pd.to_datetime(sat_ds).date()
            sun_date = pd.to_datetime(sun_ds).date()

            if pair_value == 1:
                cift_off_sayisi_agent[a] += 1

            cift_off_rows.append({
                "agent_user_code": a,
                "pair_index": pair_index,
                "cumartesi": sat_date.isoformat(),
                "pazar": sun_date.isoformat(),
                "cumartesi_durum": calendar_status[
                    (a, sat_date)
                ]["durum"],
                "pazar_durum": calendar_status[
                    (a, sun_date)
                ]["durum"],
                "cift_off_mi": pair_value,
            })


# ------------------------------------------------------------
# 9) AGENT AYLIK ÖZET
# ------------------------------------------------------------

agent_ozet_rows = []

for a_raw in AGENTS:
    a = norm_agent(a_raw)
    meta = AGENT_META.get(a, {})

    durum_sayilari = defaultdict(int)

    for tarih in PLAN_TARIHLER:
        durum = calendar_status[(a, tarih)]["durum"]

        if durum.startswith("RESMİ TATİL MESAİ"):
            durum_sayilari["resmi_tatil_calisma"] += 1
            durum_sayilari["mesai"] += 1
        elif durum.startswith("ARİFE MESAİ"):
            durum_sayilari["arife_calisma"] += 1
            durum_sayilari["mesai"] += 1
        elif durum == "MESAİ":
            durum_sayilari["mesai"] += 1
        elif durum == "TELAFİ":
            durum_sayilari["telafi"] += 1
        elif durum == "NORM":
            durum_sayilari["norm"] += 1
        elif durum == "İZİN":
            durum_sayilari["izin"] += 1
        elif durum == "OFF_T ✓":
            durum_sayilari["off_t"] += 1
        elif durum == "OFF_T2 ✓":
            durum_sayilari["off_t2"] += 1
        elif durum == "OFF":
            durum_sayilari["normal_off"] += 1
        elif durum == "RESMİ TATİL":
            durum_sayilari["resmi_tatil_off"] += 1

    toplam_calisma = sum(
        work_map.get((a, t), 0)
        for t in PLAN_TARIHLER
    )

    agent_ozet_rows.append({
        "agent_user_code": a,
        "agent_name": meta.get("agent_name", ""),
        "takim": meta.get("takim", ""),
        "teamleader_name": meta.get(
            "teamleader_name", ""
        ),
        "working_main_group": meta.get(
            "working_main_group", ""
        ),
        "toplam_calisma_gunu": toplam_calisma,
        "norm_calisma": durum_sayilari["norm"],
        "telafi_calisma": durum_sayilari["telafi"],
        "mesai_calisma": durum_sayilari["mesai"],
        "izin_gunu": durum_sayilari["izin"],
        "off_t_karsilanan": durum_sayilari["off_t"],
        "off_t2_karsilanan": durum_sayilari["off_t2"],
        "normal_off": durum_sayilari["normal_off"],
        "resmi_tatil_calisma": durum_sayilari[
            "resmi_tatil_calisma"
        ],
        "arife_calisma": durum_sayilari[
            "arife_calisma"
        ],
        "cift_off_sayisi": cift_off_sayisi_agent[a],
        "acik_telafi_borcu": acik_borc_agent.get(a, 0),
        "mesaiye_kalamaz_flg": meta.get(
            "mesaiye_kalamaz_flg", 0
        ),
        "hamile_flg": meta.get("hamile_flg", 0),
        "sut_izni_flg": meta.get(
            "sut_izni_flg", 0
        ),
        "dogum_izni_flg": meta.get(
            "dogum_izni_flg", 0
        ),
        "idari_izinli_flg": meta.get(
            "idari_izinli_flg", 0
        ),
    })


# ------------------------------------------------------------
# 10) COVERAGE
# ------------------------------------------------------------

coverage_rows = []

for ds in PLAN_GUNLER:
    tarih = pd.to_datetime(ds).date()

    for v in gun_vardiyalari.get(ds, []):
        atanan = sum(
            int(solver.Value(x[(norm_agent(a), ds, v)]))
            for a in AGENTS
            if (norm_agent(a), ds, v) in x
        )

        required = int(talep.get((ds, v), 0)) \
            if "talep" in globals() else 0

        coverage_rows.append({
            "tarih": tarih.isoformat(),
            "gun": gun_adi_tr(tarih),
            "vardiya": vardiya_str(v),
            "required": required,
            "atanan": atanan,
            "gap": atanan - required,
            "eksik": max(required - atanan, 0),
            "fazla": max(atanan - required, 0),
        })


# ------------------------------------------------------------
# 11) KURAL KONTROLLERİ
# ------------------------------------------------------------

kural_rows = []

# 11.1 Günde en fazla bir vardiya
for a_raw in AGENTS:
    a = norm_agent(a_raw)

    for tarih in PLAN_TARIHLER:
        vardiya_sayisi = len(
            atama_map.get((a, tarih), [])
        )

        if vardiya_sayisi > 1:
            kural_rows.append({
                "kural": "Günde en fazla 1 vardiya",
                "agent_user_code": a,
                "tarih_hafta": tarih.isoformat(),
                "sonuc": "İHLAL",
                "detay": f"{vardiya_sayisi} vardiya",
            })

# 11.2 Maksimum 6 gün üst üste
for a_raw in AGENTS:
    a = norm_agent(a_raw)
    streak = 0
    streak_start = None

    for tarih in PLAN_TARIHLER:
        if work_map.get((a, tarih), 0) == 1:
            if streak == 0:
                streak_start = tarih
            streak += 1

            if streak > 6:
                kural_rows.append({
                    "kural": "Maksimum 6 gün üst üste",
                    "agent_user_code": a,
                    "tarih_hafta": (
                        f"{streak_start.isoformat()} - "
                        f"{tarih.isoformat()}"
                    ),
                    "sonuc": "İHLAL",
                    "detay": f"{streak} gün üst üste",
                })
        else:
            streak = 0
            streak_start = None

# 11.3 İzin/OFF tarihinde çalışma
for a_raw in AGENTS:
    a = norm_agent(a_raw)

    for tarih in PLAN_TARIHLER:
        tip = tip_getir(a, tarih)

        if (
            tip in {"izin", "off_t", "off_t2"}
            and work_map.get((a, tarih), 0) == 1
        ):
            kural_rows.append({
                "kural": "İzin/OFF tarihinde çalışmama",
                "agent_user_code": a,
                "tarih_hafta": tarih.isoformat(),
                "sonuc": "İHLAL",
                "detay": tip,
            })

# 11.4 OFF talebi karşılanma
for a_raw in AGENTS:
    a = norm_agent(a_raw)

    for tarih, tip in tip_map.get(a, {}).items():
        tip_str = str(tip).strip().lower()

        if (
            tarih in PLAN_TARIH_SET
            and tip_str in {"off_t", "off_t2"}
        ):
            karsilandi = (
                work_map.get((a, tarih), 0) == 0
            )

            kural_rows.append({
                "kural": "OFF talebi karşılanma",
                "agent_user_code": a,
                "tarih_hafta": tarih.isoformat(),
                "sonuc": (
                    "OK" if karsilandi else "İHLAL"
                ),
                "detay": tip_str,
            })

# 11.5 Çift OFF
for a_raw in AGENTS:
    a = norm_agent(a_raw)

    tum_plan_izinli = all(
        tip_getir(a, t) == "izin"
        for t in PLAN_TARIHLER
    )

    if not tum_plan_izinli:
        cift_sayi = cift_off_sayisi_agent.get(a, 0)

        kural_rows.append({
            "kural": "Ayda en az 1 çift OFF",
            "agent_user_code": a,
            "tarih_hafta": "",
            "sonuc": (
                "OK" if cift_sayi >= 1 else "İHLAL"
            ),
            "detay": f"çift OFF sayısı: {cift_sayi}",
        })

# 11.6 Telafi borcu
for a_raw in AGENTS:
    a = norm_agent(a_raw)
    acik = acik_borc_agent.get(a, 0)

    kural_rows.append({
        "kural": "OFF telafi borcu",
        "agent_user_code": a,
        "tarih_hafta": "",
        "sonuc": "OK" if acik == 0 else "İHLAL",
        "detay": f"açık borç: {acik}",
    })

# 11.7 Aylık çalışma hedefi
if "aylik_calisma_debug_df" in globals():
    debug_map = {}

    for _, row in aylik_calisma_debug_df.iterrows():
        debug_map[norm_agent(
            row["agent_user_code"]
        )] = row.to_dict()

    for a_raw in AGENTS:
        a = norm_agent(a_raw)

        toplam_calisma = sum(
            work_map.get((a, t), 0)
            for t in PLAN_TARIHLER
            if t not in RESMI_TATIL_SET
        )

        info = debug_map.get(a, {})
        min_calisma = int(
            info.get("min_calisma", 0)
        )
        max_calisma = int(
            info.get(
                "max_calisma",
                min_calisma
            )
        )

        uygun = (
            min_calisma
            <= toplam_calisma
            <= max_calisma
        )

        kural_rows.append({
            "kural": "Aylık çalışma hedefi",
            "agent_user_code": a,
            "tarih_hafta": "",
            "sonuc": "OK" if uygun else "İHLAL",
            "detay": (
                f"gerçekleşen={toplam_calisma}, "
                f"min={min_calisma}, max={max_calisma}"
            ),
        })

# Hiç ihlal oluşmayan bazı kontrollerin de görünmesi için
# özet satırları
kural_ozet_rows = []

for kural in sorted({
    row["kural"] for row in kural_rows
}):
    satirlar = [
        row for row in kural_rows
        if row["kural"] == kural
    ]
    ihlal = sum(
        1 for row in satirlar
        if row["sonuc"] == "İHLAL"
    )

    kural_ozet_rows.append({
        "kural": kural,
        "kontrol_kaydi": len(satirlar),
        "ihlal_sayisi": ihlal,
        "genel_sonuc": "OK" if ihlal == 0 else "İHLAL",
    })


# ------------------------------------------------------------
# 12) WORKBOOK YARDIMCILARI
# ------------------------------------------------------------

def excel_col_name(n):
    sonuc = ""
    while n:
        n, kalan = divmod(n - 1, 26)
        sonuc = chr(65 + kalan) + sonuc
    return sonuc


def sheet_yaz(sheet, headers, rows):
    matrix = [headers]

    for row in rows:
        matrix.append([
            row.get(header, "")
            for header in headers
        ])

    end_col = excel_col_name(len(headers))
    end_row = max(len(matrix), 1)

    sheet.get_range(
        f"A1:{end_col}{end_row}"
    ).values = matrix

    header_range = sheet.get_range(
        f"A1:{end_col}1"
    )

    header_range.format = {
        "fill": RENKLER["BASLIK"],
        "font": {
            "bold": True,
            "color": RENKLER["BEYAZ"],
        },
        "horizontal_alignment": "center",
        "vertical_alignment": "center",
        "wrap_text": True,
    }

    sheet.freeze_panes.freeze_rows(1)

    data_range = sheet.get_range(
        f"A1:{end_col}{end_row}"
    )
    data_range.format.wrap_text = True
    data_range.format.autofit_columns()

    return end_row, end_col


def kolon_genisligi_ayarla(
    sheet,
    kolon,
    genislik
):
    sheet.get_range(
        f"{kolon}:{kolon}"
    ).format.column_width = genislik


# ------------------------------------------------------------
# 13) WORKBOOK OLUŞTUR
# ------------------------------------------------------------

wb = Workbook.create()


# 13.1 Renk Açıklamaları
sheet = wb.worksheets.add("Renk Açıklamaları")

legend_rows = [
    ["Durum", "Anlam"],
    ["NORM", "Normal çalışma"],
    ["MESAİ", "Aylık hedef üzerindeki çalışma"],
    ["TELAFİ", "2'yi aşan haftalık OFF talebinin başka haftada ödenmesi"],
    ["İZİN", "Gerçek izin"],
    ["OFF_T ✓", "Agent OFF_T talebi karşılandı"],
    ["OFF_T2 ✓", "Agent OFF_T2 talebi karşılandı"],
    ["OFF", "Modelin verdiği normal OFF"],
    ["RESMİ TATİL", "Resmî tatilde çalışmadı"],
    ["RESMİ TATİL MESAİ", "Resmî tatil çalışması"],
    ["ARİFE MESAİ", "Arife çalışması"],
]

sheet.get_range(
    f"A1:B{len(legend_rows)}"
).values = legend_rows

sheet.get_range("A1:B1").format = {
    "fill": RENKLER["BASLIK"],
    "font": {
        "bold": True,
        "color": RENKLER["BEYAZ"],
    },
}

legend_renk_map = {
    "NORM": "NORM",
    "MESAİ": "MESAI",
    "TELAFİ": "TELAFI",
    "İZİN": "IZIN",
    "OFF_T ✓": "OFF_T",
    "OFF_T2 ✓": "OFF_T2",
    "OFF": "NORMAL_OFF",
    "RESMİ TATİL": "RESMI_TATIL",
    "RESMİ TATİL MESAİ": "RESMI_TATIL",
    "ARİFE MESAİ": "ARIFE",
}

for row_no in range(2, len(legend_rows) + 1):
    durum = legend_rows[row_no - 1][0]
    renk_anahtari = legend_renk_map.get(durum)

    if renk_anahtari:
        sheet.get_range(
            f"A{row_no}:B{row_no}"
        ).format.fill = RENKLER[renk_anahtari]

sheet.get_range(
    f"A1:B{len(legend_rows)}"
).format.autofit_columns()


# 13.2 Agent Takvimi
sheet = wb.worksheets.add("Agent Takvimi")

sabit_headers = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
]

tarih_headers = [
    f"{t.day:02d} {gun_adi_tr(t)}"
    for t in PLAN_TARIHLER
]

takvim_headers = sabit_headers + tarih_headers

takvim_matrix = [takvim_headers]

for a_raw in AGENTS:
    a = norm_agent(a_raw)
    meta = AGENT_META.get(a, {})

    row = [
        a,
        meta.get("agent_name", ""),
        meta.get("takim", ""),
        meta.get("teamleader_name", ""),
    ]

    for tarih in PLAN_TARIHLER:
        info = calendar_status[(a, tarih)]

        cell_text = info["durum"]

        if info["vardiya"]:
            cell_text += f"\n{info['vardiya']}"

        if (a, tarih) in telafi_gunleri:
            cell_text += (
                "\nBorç: "
                + telafi_gunleri[
                    (a, tarih)
                ]["source_week"]
            )

        row.append(cell_text)

    takvim_matrix.append(row)

takvim_end_col = excel_col_name(
    len(takvim_headers)
)

takvim_end_row = len(takvim_matrix)

sheet.get_range(
    f"A1:{takvim_end_col}{takvim_end_row}"
).values = takvim_matrix

sheet.get_range(
    f"A1:{takvim_end_col}1"
).format = {
    "fill": RENKLER["BASLIK"],
    "font": {
        "bold": True,
        "color": RENKLER["BEYAZ"],
    },
    "horizontal_alignment": "center",
    "vertical_alignment": "center",
    "wrap_text": True,
}

sheet.freeze_panes.freeze_rows(1)
sheet.freeze_panes.freeze_columns(4)

sheet.get_range(
    f"A1:{takvim_end_col}{takvim_end_row}"
).format.wrap_text = True

kolon_genisligi_ayarla(sheet, "A", 17)
kolon_genisligi_ayarla(sheet, "B", 22)
kolon_genisligi_ayarla(sheet, "C", 18)
kolon_genisligi_ayarla(sheet, "D", 22)

for tarih_index, tarih in enumerate(
    PLAN_TARIHLER,
    start=5
):
    col = excel_col_name(tarih_index)
    kolon_genisligi_ayarla(sheet, col, 16)

for row_index, a_raw in enumerate(
    AGENTS,
    start=2
):
    a = norm_agent(a_raw)

    for tarih_index, tarih in enumerate(
        PLAN_TARIHLER,
        start=5
    ):
        col = excel_col_name(tarih_index)
        info = calendar_status[(a, tarih)]

        cell = sheet.get_range(
            f"{col}{row_index}"
        )

        cell.format.fill = RENKLER[
            info["renk_kodu"]
        ]
        cell.format.horizontal_alignment = "center"
        cell.format.vertical_alignment = "center"


# 13.3 Agent Özet
sheet = wb.worksheets.add("Agent Özet")

agent_ozet_headers = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "working_main_group",
    "toplam_calisma_gunu",
    "norm_calisma",
    "telafi_calisma",
    "mesai_calisma",
    "izin_gunu",
    "off_t_karsilanan",
    "off_t2_karsilanan",
    "normal_off",
    "resmi_tatil_calisma",
    "arife_calisma",
    "cift_off_sayisi",
    "acik_telafi_borcu",
    "mesaiye_kalamaz_flg",
    "hamile_flg",
    "sut_izni_flg",
    "dogum_izni_flg",
    "idari_izinli_flg",
]

agent_end_row, agent_end_col = sheet_yaz(
    sheet,
    agent_ozet_headers,
    agent_ozet_rows
)

sheet.get_range(
    f"Q2:Q{agent_end_row}"
).conditional_formats.add_cell_is({
    "operator": "greaterThan",
    "formula": 0,
    "format": {
        "fill": RENKLER["IHLAL"]
    },
})


# 13.4 Günlük Atamalar
sheet = wb.worksheets.add("Günlük Atamalar")

gunluk_headers = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "tarih",
    "gun",
    "hafta",
    "durum",
    "vardiya",
    "izin_off_tipi",
    "calisti_mi",
    "resmi_tatil_mi",
    "arife_mi",
    "telafi_borc_haftasi",
]

sheet_yaz(
    sheet,
    gunluk_headers,
    gunluk_rows
)


# 13.5 OFF Talepleri
sheet = wb.worksheets.add("OFF Talepleri")

off_talep_rows = []

for a_raw in AGENTS:
    a = norm_agent(a_raw)

    for tarih, tip in sorted(
        tip_map.get(a, {}).items()
    ):
        tip_str = str(tip).strip().lower()

        if (
            tarih not in PLAN_TARIH_SET
            or tip_str not in {"off_t", "off_t2"}
        ):
            continue

        karsilandi = (
            work_map.get((a, tarih), 0) == 0
        )

        off_talep_rows.append({
            "agent_user_code": a,
            "agent_name": AGENT_META.get(
                a, {}
            ).get("agent_name", ""),
            "tarih": tarih.isoformat(),
            "hafta": hafta_key(tarih),
            "talep_tipi": tip_str,
            "karsilandi_mi": (
                "EVET" if karsilandi else "HAYIR"
            ),
            "takvim_durumu": calendar_status[
                (a, tarih)
            ]["durum"],
        })

off_end_row, _ = sheet_yaz(
    sheet,
    [
        "agent_user_code",
        "agent_name",
        "tarih",
        "hafta",
        "talep_tipi",
        "karsilandi_mi",
        "takvim_durumu",
    ],
    off_talep_rows
)

if off_end_row >= 2:
    sheet.get_range(
        f"F2:F{off_end_row}"
    ).conditional_formats.add_custom(
        '=F2="HAYIR"',
        {
            "fill": RENKLER["IHLAL"]
        }
    )

    sheet.get_range(
        f"F2:F{off_end_row}"
    ).conditional_formats.add_custom(
        '=F2="EVET"',
        {
            "fill": RENKLER["OK"]
        }
    )


# 13.6 Telafi Takibi
sheet = wb.worksheets.add("Telafi Takibi")

sheet_yaz(
    sheet,
    [
        "agent_user_code",
        "borc_haftasi",
        "borca_neden_olan_off_tarihleri",
        "durum",
        "odeme_haftasi",
        "odeme_tarihi",
        "odeme_tipi",
    ],
    telafi_detay_rows
)


# 13.7 Haftalık OFF Borcu
sheet = wb.worksheets.add("Haftalık OFF Borcu")

sheet_yaz(
    sheet,
    [
        "agent_user_code",
        "hafta",
        "off_talep_sayisi",
        "off_talep_tarihleri",
        "standart_off_hakki",
        "telafi_borcu",
        "haftalik_baz_hedef",
        "gerceklesen_calisma",
        "fazla_calisma_kapasitesi",
    ],
    off_borc_rows
)


# 13.8 Çift OFF
sheet = wb.worksheets.add("Çift OFF")

cift_end_row, _ = sheet_yaz(
    sheet,
    [
        "agent_user_code",
        "pair_index",
        "cumartesi",
        "pazar",
        "cumartesi_durum",
        "pazar_durum",
        "cift_off_mi",
    ],
    cift_off_rows
)

if cift_end_row >= 2:
    sheet.get_range(
        f"G2:G{cift_end_row}"
    ).conditional_formats.add_cell_is({
        "operator": "equalTo",
        "formula": 1,
        "format": {
            "fill": RENKLER["CIFT_OFF"]
        },
    })


# 13.9 Coverage
sheet = wb.worksheets.add("Coverage")

coverage_end_row, _ = sheet_yaz(
    sheet,
    [
        "tarih",
        "gun",
        "vardiya",
        "required",
        "atanan",
        "gap",
        "eksik",
        "fazla",
    ],
    coverage_rows
)

if coverage_end_row >= 2:
    sheet.get_range(
        f"G2:G{coverage_end_row}"
    ).conditional_formats.add_cell_is({
        "operator": "greaterThan",
        "formula": 0,
        "format": {
            "fill": RENKLER["IHLAL"]
        },
    })


# 13.10 Kural Kontrol Özeti
sheet = wb.worksheets.add("Kural Kontrol Özeti")

kural_ozet_end_row, _ = sheet_yaz(
    sheet,
    [
        "kural",
        "kontrol_kaydi",
        "ihlal_sayisi",
        "genel_sonuc",
    ],
    kural_ozet_rows
)

if kural_ozet_end_row >= 2:
    sheet.get_range(
        f"D2:D{kural_ozet_end_row}"
    ).conditional_formats.add_custom(
        '=D2="İHLAL"',
        {
            "fill": RENKLER["IHLAL"]
        }
    )

    sheet.get_range(
        f"D2:D{kural_ozet_end_row}"
    ).conditional_formats.add_custom(
        '=D2="OK"',
        {
            "fill": RENKLER["OK"]
        }
    )


# 13.11 Kural Kontrol Detay
sheet = wb.worksheets.add("Kural Kontrol Detay")

kural_end_row, _ = sheet_yaz(
    sheet,
    [
        "kural",
        "agent_user_code",
        "tarih_hafta",
        "sonuc",
        "detay",
    ],
    kural_rows
)

if kural_end_row >= 2:
    sheet.get_range(
        f"D2:D{kural_end_row}"
    ).conditional_formats.add_custom(
        '=D2="İHLAL"',
        {
            "fill": RENKLER["IHLAL"]
        }
    )


# ------------------------------------------------------------
# 14) EXPORT
# ------------------------------------------------------------

SpreadsheetFile.export_xlsx(wb).save(RAPOR_YOLU)

print("Excel raporu oluşturuldu:")
print(RAPOR_YOLU)
