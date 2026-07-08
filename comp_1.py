    # --------------------------------------------------
    # AY SINIRI / YARIM HAFTA PARAMETRELERİ
    # --------------------------------------------------
    # Amaç:
    # Ay başı veya ay sonunda model haftanın sadece bir kısmını görüyor olabilir.
    #
    # Örnek:
    # Haziran 2026'da 2026-W27 haftasında sadece 29-30 Haziran var.
    # Bu hafta aslında Temmuz ile devam ettiği için Haziran modelinde
    # haftalık çalışma hedefi bu iki günde kapatılmamalı.
    #
    # True:
    # Eksik haftalarda haftalık çalışma hedefi kurulmaz.
    "SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS": True,

    # Haftalık hedefin uygulanması için model içinde görülmesi gereken
    # normal hafta içi gün sayısı.
    #
    # Pazartesi-Cuma tam hafta = 5 gün.
    # Eğer bir haftada model sadece 2 gün görüyorsa, o hafta partial kabul edilir.
    "FULL_WEEKDAY_COUNT": 5,

    # Partial week günlerinde talebin üstüne en fazla kaç kişi çıkılabilir?
    #
    # 0:
    # assigned <= required olur.
    #
    # Eğer model infeasible olursa 1 veya 2 denenebilir.
    "PARTIAL_WEEK_MAX_FAZLA_ATAMA": 0,



# --------------------------------------------------
# AY SINIRI / YARIM HAFTA PARAMETRELERİ
# --------------------------------------------------

SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS = CONFIG["SKIP_WEEKLY_TARGET_FOR_PARTIAL_WEEKS"]
FULL_WEEKDAY_COUNT = CONFIG["FULL_WEEKDAY_COUNT"]
PARTIAL_WEEK_MAX_FAZLA_ATAMA = CONFIG["PARTIAL_WEEK_MAX_FAZLA_ATAMA"]
