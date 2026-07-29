# %% [KONTROL] - HAFTALIK ÇALIŞMA EŞİTLİĞİ YAPILABİLİRLİK KONTROLÜ

# Bu hücre modele kısıt eklemez.
#
# Her agent-hafta için şunları karşılaştırır:
#
# minimum gerekli çalışma:
#     normal_target - extra_off_count
#
# modelde çalışılabilecek maksimum gün:
#     O hafta agent için en az bir x değişkeni bulunan,
#     resmî tatil olmayan gün sayısı
#
# minimum gerekli çalışma > maksimum çalışılabilir gün ise
# haftalık eşitlik kesinlikle infeasible olur.

haftalik_esitlik_kontrol_rows = []

resmi_tatil_kontrol_set = {
    pd.to_datetime(ds).date()
    for ds in resmi_tatil_plan_gunleri
}

partial_week_kontrol_set = {
    str(wk).strip()
    for wk in partial_weeks
}


for a_raw in AGENTS:

    a = str(a_raw).strip()

    agent_izin_dates = {
        pd.to_datetime(d).date()
        for d in izin_map.get(a, set())
    }

    agent_off_t2_dates = {
        pd.to_datetime(d).date()
        for d in off_t2_map.get(a, set())
    }

    agent_hard_off_t_dates = set()

    if ENABLE_OFF_T_HARD:

        agent_hard_off_t_dates = {
            pd.to_datetime(d).date()
            for d in off_t_map.get(a, set())
        }

    agent_hard_off_talep_dates = (
        agent_off_t2_dates
        | agent_hard_off_t_dates
    )

    for wk in WEEKS:

        wk_key = str(wk).strip()
        week_ds = week_days.get(wk, [])

        week_dates = {
            pd.to_datetime(ds).date()
            for ds in week_ds
        }

        week_izin_dates = (
            agent_izin_dates
            & week_dates
        )

        week_resmi_tatil_dates = (
            resmi_tatil_kontrol_set
            & week_dates
        )

        hedef_dusuren_dates = (
            week_izin_dates
            | week_resmi_tatil_dates
        )

        normal_target = max(
            NORMAL_WORK_DAYS
            - len(hedef_dusuren_dates),
            0
        )

        # Mevcut haftalık kısıtta kullandığımız hesapla aynı
        week_hard_off_talep_dates = (
            agent_hard_off_talep_dates
            & week_dates
        ) - hedef_dusuren_dates

        hard_off_talep_count = len(
            week_hard_off_talep_dates
        )

        extra_off_count = max(
            hard_off_talep_count - 2,
            0
        )

        minimum_gerekli_calisma = (
            normal_target
            - extra_off_count
        )

        calisilabilir_gunler = []

        for ds in week_ds:

            ds_date = pd.to_datetime(ds).date()

            # Haftalık normal_work_vars resmî tatili saymıyor
            if ds_date in resmi_tatil_kontrol_set:
                continue

            # O gün agent için en az bir vardiya değişkeni var mı?
            gun_x_varlari = [
                x[(a, ds, v)]
                for v in gun_vardiyalari.get(ds, [])
                if (a, ds, v) in x
            ]

            if gun_x_varlari:
                calisilabilir_gunler.append(ds)

        maksimum_calisilabilir_gun = len(
            calisilabilir_gunler
        )

        partial_week_mi = (
            SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS
            and wk_key in partial_week_kontrol_set
        )

        kesin_imkansiz = (
            not partial_week_mi
            and minimum_gerekli_calisma
            > maksimum_calisilabilir_gun
        )

        haftalik_esitlik_kontrol_rows.append({
            "agent_user_code": a,
            "week": wk_key,
            "partial_week": partial_week_mi,
            "normal_target": normal_target,
            "izin_gun_sayisi": len(week_izin_dates),
            "resmi_tatil_sayisi": len(
                week_resmi_tatil_dates
            ),
            "hard_off_talep_sayisi": (
                hard_off_talep_count
            ),
            "extra_off_count": extra_off_count,
            "minimum_gerekli_calisma": (
                minimum_gerekli_calisma
            ),
            "maksimum_calisilabilir_gun": (
                maksimum_calisilabilir_gun
            ),
            "calisilabilir_gunler": [
                pd.to_datetime(ds).strftime("%Y-%m-%d")
                for ds in calisilabilir_gunler
            ],
            "hard_off_talep_gunleri": sorted(
                str(d)
                for d in week_hard_off_talep_dates
            ),
            "izin_gunleri": sorted(
                str(d)
                for d in week_izin_dates
            ),
            "kesin_imkansiz": kesin_imkansiz,
        })


haftalik_esitlik_kontrol_df = pd.DataFrame(
    haftalik_esitlik_kontrol_rows
)

haftalik_kesin_imkansiz_df = (
    haftalik_esitlik_kontrol_df[
        haftalik_esitlik_kontrol_df[
            "kesin_imkansiz"
        ]
    ]
    .copy()
    .sort_values(
        [
            "agent_user_code",
            "week",
        ]
    )
)


print(
    "Kontrol edilen agent-hafta:",
    len(haftalik_esitlik_kontrol_df)
)

print(
    "Haftalık eşitliği kesin imkânsız agent-hafta:",
    len(haftalik_kesin_imkansiz_df)
)

display(
    haftalik_kesin_imkansiz_df
)
