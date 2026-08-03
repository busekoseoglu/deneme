# %% [HÜCRE] - TEMMUZ SON HAFTA GEÇMİŞİ (HISTORY / CONTEXT)
# Ağustos 1 Cumartesi -> W31 (27 Tem - 2 Ağu) devamlılığı Temmuz'dan gelir.
# Bu geçmiş SABİTTİR; karar değişkeni oluşturulmaz. Yalnızca:
#   - max 6 gün üst üste (HÜCRE 12)
#   - min 11 saat dinlenme (HÜCRE 15)
# kısıtlarına sabit olarak beslenir.

TEMMUZ_GECMIS_TABLE = "BNS_VP_TEMMUZ_SON_HAFTA_GECMIS"  # <-- KENDİ TABLO ADINLA DEĞİŞTİR

if "PLAN_START_DATE" not in globals():
    PLAN_START_DATE = min(pd.to_datetime(ds).date() for ds in PLAN_GUNLER)

query = f"SELECT * FROM {TEMMUZ_GECMIS_TABLE}"
chunks = pd.read_sql(query, sync_engine, chunksize=10000)
df_gecmis = pd.concat(chunks, ignore_index=True)
df_gecmis.columns = [str(c).strip().lower() for c in df_gecmis.columns]

def _pick_col(cands):
    for c in cands:
        if c in df_gecmis.columns:
            return c
    return None

col_agent = _pick_col(["agent_user_code"])
col_date  = _pick_col(["date", "tarih"])
col_start = _pick_col(["shift_start", "shift_start_hour", "baslangic"])

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

# df_talep'ten shift_start -> shift_end haritası (bitişi buradan mapliyoruz)
start_to_end = {}
for _, r in df_talep.iterrows():
    b = _norm_saat(r["baslangic"])
    e = str(r["bitis"]).strip()[:5]
    if b is None:
        continue
    start_to_end.setdefault(b, set()).add(e)

_cakisan = {b: v for b, v in start_to_end.items() if len(v) > 1}
if _cakisan:
    print("UYARI - aynı başlangıca birden çok bitiş eşleşiyor (ilki alınır):", _cakisan)
start_to_end = {b: sorted(v)[0] for b, v in start_to_end.items()}

gecmis_calisma = {}          # agent -> {date: (bas, bit)}
gecmis_calisma_gunleri = {}  # agent -> set(date)
_eslesmeyen_start = set()

for _, row in df_gecmis.iterrows():
    a = str(row[col_agent]).strip()
    d = pd.to_datetime(row[col_date], errors="coerce")
    if pd.isna(d):
        continue
    d = d.date()
    if d >= PLAN_START_DATE:   # Ağustos ve sonrası history değil
        continue
    bas = _norm_saat(row[col_start])
    if bas is None:
        continue
    bit = start_to_end.get(bas)
    if bit is None:
        _eslesmeyen_start.add(bas)
    gecmis_calisma.setdefault(a, {})[d] = (bas, bit)
    gecmis_calisma_gunleri.setdefault(a, set()).add(d)

print(f"Geçmiş verisi olan agent: {len(gecmis_calisma)}")
_tum = sorted({d for g in gecmis_calisma_gunleri.values() for d in g})
if _tum:
    print(f"Geçmiş gün aralığı: {_tum[0]} .. {_tum[-1]} ({len(_tum)} gün)")
print(f"Toplam geçmiş agent-gün: {sum(len(g) for g in gecmis_calisma_gunleri.values())}")
if _eslesmeyen_start:
    print("UYARI - df_talep'te bitişi bulunamayan başlangıçlar (rest'te atlanır):", sorted(_eslesmeyen_start))




# %% [HÜCRE 12] - MAKSİMUM 6 GÜN ÜST ÜSTE ÇALIŞMA (TEMMUZ GEÇMİŞİ DAHİL)
from datetime import timedelta

if "PLAN_START_DATE" not in globals():
    PLAN_START_DATE = min(pd.to_datetime(ds).date() for ds in PLAN_GUNLER)
if "PLAN_END_DATE" not in globals():
    PLAN_END_DATE = max(pd.to_datetime(ds).date() for ds in PLAN_GUNLER)

gecmis_calisma_gunleri = globals().get("gecmis_calisma_gunleri", {})

max_consecutive_constraints = 0
gecmis_pencere_katki = 0
plan_date_set_mc = {pd.to_datetime(ds).date() for ds in PLAN_GUNLER}
date_to_ds = {pd.to_datetime(ds).date(): ds for ds in PLAN_GUNLER}

# Pencere başlangıçları ilk plan gününden (WINDOW_DAYS-1) gün ÖNCE başlar
# -> Temmuz sonu / Ağustos başı geçişi kapsanır.
window_starts = []
d = PLAN_START_DATE - timedelta(days=WINDOW_DAYS - 1)
son_start = PLAN_END_DATE - timedelta(days=WINDOW_DAYS - 1)
while d <= son_start:
    window_starts.append(d)
    d += timedelta(days=1)

for a in AGENTS:
    a = str(a).strip()
    gecmis_gunler_a = gecmis_calisma_gunleri.get(a, set())
    for ws in window_starts:
        window_dates = [ws + timedelta(days=k) for k in range(WINDOW_DAYS)]
        aug_vars = [
            work[(a, date_to_ds[dd])]
            for dd in window_dates
            if dd in plan_date_set_mc and (a, date_to_ds[dd]) in work
        ]
        if not aug_vars:
            continue  # tamamen geçmişte kalan pencere; Ağustos kararı yok
        gecmis_calismis = sum(1 for dd in window_dates if dd in gecmis_gunler_a)
        limit = max(0, MAX_CONSECUTIVE_WORK_DAYS - gecmis_calismis)
        model.Add(sum(aug_vars) <= limit)
        max_consecutive_constraints += 1
        if gecmis_calismis > 0:
            gecmis_pencere_katki += 1

print(f"max 6 gün üst üste çalışma kısıtı: {max_consecutive_constraints} adet")
print(f"  - Temmuz geçmişinden etkilenen pencere: {gecmis_pencere_katki} adet")



# %% [HÜCRE 15] - İKİ VARDİYA ARASI MİNİMUM 11 SAAT DİNLENME (TEMMUZ GEÇMİŞİ DAHİL)

def make_shift_datetime(ds, baslangic, bitis):
    start_dt = pd.to_datetime(f"{ds} {baslangic}")
    end_dt = pd.to_datetime(f"{ds} {bitis}")
    if end_dt <= start_dt:
        end_dt = end_dt + pd.Timedelta(days=1)
    return start_dt, end_dt

shift_dt_map = {}
for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        baslangic, bitis = saat[(ds, v)]
        start_dt, end_dt = make_shift_datetime(ds, baslangic, bitis)
        shift_dt_map[(ds, v)] = {"start_dt": start_dt, "end_dt": end_dt}

# --- Ağustos içi (mevcut mantık, değişmedi) ---
min_rest_constraints = 0
for a in AGENTS:
    agent_shift_options = []
    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue
            agent_shift_options.append({
                "ds": ds, "v": v,
                "start_dt": shift_dt_map[(ds, v)]["start_dt"],
                "end_dt": shift_dt_map[(ds, v)]["end_dt"],
            })
    agent_shift_options = sorted(agent_shift_options, key=lambda r: r["start_dt"])
    for i in range(len(agent_shift_options)):
        sh1 = agent_shift_options[i]
        for j in range(i + 1, len(agent_shift_options)):
            sh2 = agent_shift_options[j]
            if sh2["start_dt"] <= sh1["end_dt"]:
                rest_minutes = -1
            else:
                rest_minutes = int((sh2["start_dt"] - sh1["end_dt"]).total_seconds() / 60)
            if rest_minutes < MIN_REST_MINUTES:
                model.Add(x[(a, sh1["ds"], sh1["v"])] + x[(a, sh2["ds"], sh2["v"])] <= 1)
                min_rest_constraints += 1
            else:
                break

# --- YENİ: Temmuz geçmişi (SABİT önceki vardiya) ile 11 saat kontrolü ---
gecmis_calisma = globals().get("gecmis_calisma", {})
gecmis_min_rest_constraints = 0

for a in AGENTS:
    a = str(a).strip()
    gecmis_shiftler = gecmis_calisma.get(a, {})
    if not gecmis_shiftler:
        continue
    gecmis_dt = []
    for gtarih, (gbas, gbit) in gecmis_shiftler.items():
        if gbit is None:  # bitişi maplenememişse rest hesaplanamaz, atla
            continue
        gds = pd.to_datetime(gtarih).strftime("%Y-%m-%d")
        g_start, g_end = make_shift_datetime(gds, gbas, gbit)
        gecmis_dt.append(g_end)
    if not gecmis_dt:
        continue
    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue
            a_start = shift_dt_map[(ds, v)]["start_dt"]
            for g_end in gecmis_dt:
                if a_start <= g_end:
                    rest_minutes = -1
                else:
                    rest_minutes = int((a_start - g_end).total_seconds() / 60)
                if rest_minutes < MIN_REST_MINUTES:
                    model.Add(x[(a, ds, v)] == 0)  # geçmiş sabit=1, o yüzden hard yasak
                    gecmis_min_rest_constraints += 1

print(f"min 11 saat dinlenme kısıtı (Ağustos içi): {min_rest_constraints} adet")
print(f"min 11 saat dinlenme kısıtı (Temmuz geçmişi): {gecmis_min_rest_constraints} adet")

