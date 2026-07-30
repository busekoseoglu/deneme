# %% [HAZIRLIK] - AGENT BAZLI İZİN / OFF MAP'LERİ

izin_map = {}
off_t2_map = {}
off_t_map = {}

for _, row in df_tam.iterrows():

    code = str(
        row["agent_user_code"]
    ).strip()

    izin = set()
    off_t2 = set()
    off_t = set()

    # df_izin + df_off birleşiminden gelen tarihler
    for tarih, tipi in tip_map.get(code, {}).items():

        tarih = pd.to_datetime(tarih).date()
        tipi = str(tipi).strip().lower()

        if tipi == "izin":
            izin.add(tarih)

        elif tipi == "off_t2":
            off_t2.add(tarih)

        elif tipi == "off_t":
            off_t.add(tarih)

    # Tam ay idari izin / doğum izni
    if (
        _b(row, "idari_izinli_flg")
        or _b(row, "dogum_izni_flg")
    ):
        izin |= set(GUN_SET)

    # Haftanın belirli günlerinde tekrarlanan izinler
    sut_izni_var = _b(
        row,
        "sut_izni_flg"
    )

    for flag, weekday_no in HAFTALIK_IZIN_FLG.items():

        if not _b(row, flag):
            continue

        gunler = set(
            gunluk_izin.get(
                weekday_no,
                set()
            )
        )

        if sut_izni_var:

            gunler = {
                d
                for d in gunler
                if d.isocalendar()[:2]
                not in tatil_haftalari
            }

        izin |= gunler

    izin_map[code] = izin
    off_t2_map[code] = off_t2
    off_t_map[code] = off_t


df_tam["izin_gun_sayisi"] = (
    df_tam["agent_user_code"]
    .astype(str)
    .str.strip()
    .map(
        lambda code: len(
            izin_map.get(
                code,
                set()
            )
        )
    )
)


print(
    "İzin günü toplamı:",
    sum(
        len(gunler)
        for gunler in izin_map.values()
    )
)

print(
    "off_t2 günü toplamı:",
    sum(
        len(gunler)
        for gunler in off_t2_map.values()
    )
)

print(
    "off_t günü toplamı:",
    sum(
        len(gunler)
        for gunler in off_t_map.values()
    )
)

# %% [HAZIRLIK] - HARD OFF MAP

hard_off_map = {}

for a_raw in AGENTS:

    a = str(a_raw).strip()

    hard_gunler = set()

    hard_gunler |= izin_map.get(
        a,
        set()
    )

    hard_gunler |= off_t2_map.get(
        a,
        set()
    )

    if ENABLE_OFF_T_HARD:

        hard_gunler |= off_t_map.get(
            a,
            set()
        )

    hard_off_map[a] = hard_gunler


print(
    "Hard OFF günü toplamı:",
    sum(
        len(gunler)
        for gunler in hard_off_map.values()
    )
)
