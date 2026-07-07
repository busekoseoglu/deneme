# Resmi tatil olan haftaları bul
resmi_tatil_set = set()

if "RESMI_TATIL_GUNLERI" in globals():
    for x in RESMI_TATIL_GUNLERI:
        try:
            resmi_tatil_set.add(pd.to_datetime(x).date())
        except Exception:
            pass

# Her plan gününün haftasında resmi tatil var mı?
haftada_resmi_tatil_var = {}

for d in GUN_SET:
    d_date = pd.to_datetime(d).date()
    iso = d_date.isocalendar()
    
    ayni_hafta_gunleri = {
        pd.to_datetime(g).date()
        for g in GUN_SET
        if pd.to_datetime(g).date().isocalendar().year == iso.year
        and pd.to_datetime(g).date().isocalendar().week == iso.week
    }
    
    haftada_resmi_tatil_var[d_date] = any(
        g in resmi_tatil_set for g in ayni_hafta_gunleri
    )




sut_izni_mi = _b(row, "sut_izni_flg")

if _b(row, "pazartesi_izinli_flg"):
    if sut_izni_mi:
        izin |= {
            d for d in mondays
            if not haftada_resmi_tatil_var.get(pd.to_datetime(d).date(), False)
        }
    else:
        izin |= mondays

if _b(row, "cuma_izinli_flg"):
    if sut_izni_mi:
        izin |= {
            d for d in fridays
            if not haftada_resmi_tatil_var.get(pd.to_datetime(d).date(), False)
        }
    else:
        izin |= fridays



sut_izni_resmi_tatil_debug = []

for _, row in df_tam.iterrows():
    a = str(row["agent_user_code"]).strip()
    sut_izni_mi = _b(row, "sut_izni_flg")
    
    if not sut_izni_mi:
        continue
    
    if _b(row, "pazartesi_izinli_flg"):
        for d in mondays:
            d_date = pd.to_datetime(d).date()
            if haftada_resmi_tatil_var.get(d_date, False):
                sut_izni_resmi_tatil_debug.append({
                    "agent_user_code": a,
                    "gun": d_date,
                    "normalde_izin_tipi": "pazartesi_izinli_flg",
                    "haftada_resmi_tatil_var": 1,
                    "aksiyon": "pazartesi_izni_uygulanmadi"
                })
    
    if _b(row, "cuma_izinli_flg"):
        for d in fridays:
            d_date = pd.to_datetime(d).date()
            if haftada_resmi_tatil_var.get(d_date, False):
                sut_izni_resmi_tatil_debug.append({
                    "agent_user_code": a,
                    "gun": d_date,
                    "normalde_izin_tipi": "cuma_izinli_flg",
                    "haftada_resmi_tatil_var": 1,
                    "aksiyon": "cuma_izni_uygulanmadi"
                })

df_sut_izni_resmi_tatil_debug = pd.DataFrame(sut_izni_resmi_tatil_debug)

print("Süt izni resmi tatil nedeniyle uygulanmayan Pzt/Cuma izin sayısı:", len(df_sut_izni_resmi_tatil_debug))

if len(df_sut_izni_resmi_tatil_debug) > 0:
    display(df_sut_izni_resmi_tatil_debug.head(20))
