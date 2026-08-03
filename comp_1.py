# %% [HÜCRE] - TEMMUZ SON HAFTA GEÇMİŞİ - İŞLEME (HISTORY / CONTEXT)
# Ağustos 1 Cumartesi -> W31 (27 Tem - 2 Ağu) devamlılığı Temmuz'dan gelir.
# df_gecmis yukarıda (SQL çekme bölümünde) yüklenmiş olmalı.
# Bu geçmiş SABİTTİR; karar değişkeni oluşturulmaz. Yalnızca:
#   - max 6 gün üst üste (HÜCRE 12)
#   - min 11 saat dinlenme (HÜCRE 15)
# kısıtlarına sabit olarak beslenir.

if "df_gecmis" not in globals():
    raise SystemExit("df_gecmis yok - önce 'TEMMUZ GEÇMİŞİ - VERİ ÇEKME' hücresini çalıştır.")

if "PLAN_START_DATE" not in globals():
    PLAN_START_DATE = min(pd.to_datetime(ds).date() for ds in PLAN_GUNLER)

def _pick_col(cands):
    for c in cands:
        if c in df_gecmis.columns:
            return c
    return None

col_agent = _pick_col(["agent_user_code"])
col_date  = _pick_col(["date", "tarih"])
col_start = _pick_col(["shift_start", "shift_start_hour", "baslangic"])

# Sadece modele giren agentlar (df_tam) tutulur; df_gecmis'te fazladan agent olabilir.
_model_agents = set(df_tam["agent_user_code"].astype(str).str.strip())

def _norm_saat(t):
    if pd.isna(t):
        return None
    s = str(t).strip()
    try:  # "8" / "8.0" gibi tam saat
        return f"{int(float(s)):02d}:00"
    except ValueError:
        pass
    s = s[:5]
    if len(s) == 4 and s[1] == ":":  # "8:00" -> "08:00"
        s = "0" + s
    return s

def _dk(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)

# BİTİŞ SAATİ KURALI:
#   - 17:00 ve sonrası başlayan vardiya -> 8 saat  (örn. 17:00 -> 01:00, 18:00 -> 02:00)
#   - 17:00 öncesi başlayan vardiya     -> 9 saat  (örn. 15:00 -> 00:00, 09:00 -> 18:00)
# İSTİSNA: config GECE_AKSAM_VARDIYA_SET'teki tanımlı çiftler aynen kullanılır (örn. 00:00 -> 08:00).
_gece_bitis_override = {b: e for (b, e) in GECE_AKSAM_VARDIYA_SET}

def bitis_saat_hesapla(bas):
    bas = _norm_saat(bas)
    if bas is None:
        return None
    if bas in _gece_bitis_override:
        return _gece_bitis_override[bas]
    bas_dk = _dk(bas)
    sure = 8 * 60 if bas_dk >= 17 * 60 else 9 * 60
    bit_dk = (bas_dk + sure) % (24 * 60)
    return f"{bit_dk // 60:02d}:{bit_dk % 60:02d}"

gecmis_calisma = {}          # agent -> {date: (bas, bit)}
gecmis_calisma_gunleri = {}  # agent -> set(date)

for _, row in df_gecmis.iterrows():
    a = str(row[col_agent]).strip()
    if a not in _model_agents:
        continue
    d = pd.to_datetime(row[col_date], errors="coerce")
    if pd.isna(d):
        continue
    d = d.date()
    if d >= PLAN_START_DATE:   # Ağustos ve sonrası history değil
        continue
    bas = _norm_saat(row[col_start])
    if bas is None:
        continue
    bit = bitis_saat_hesapla(bas)
    gecmis_calisma.setdefault(a, {})[d] = (bas, bit)
    gecmis_calisma_gunleri.setdefault(a, set()).add(d)

print(f"df_gecmis ham satır: {len(df_gecmis)} | modeldeki agent (df_tam): {len(_model_agents)}")
print(f"Geçmiş verisi olan agent: {len(gecmis_calisma)}")
_tum = sorted({d for g in gecmis_calisma_gunleri.values() for d in g})
if _tum:
    print(f"Geçmiş gün aralığı: {_tum[0]} .. {_tum[-1]} ({len(_tum)} gün)")
print(f"Toplam geçmiş agent-gün: {sum(len(g) for g in gecmis_calisma_gunleri.values())}")
_ornek = sorted({bas for g in gecmis_calisma.values() for (bas, _b) in g.values()})
print("Görülen başlangıç -> hesaplanan bitiş:")
for _b in _ornek:
    print(f"  {_b} -> {bitis_saat_hesapla(_b)}")
