# %% [DEBUG] - HAFİF MODEL BOYUT KONTROLÜ
# model.Validate() yok.
# HasField yok.
# Sadece proto boyutlarını okumaya çalışıyoruz.

try:
    model_proto = model.Proto()

    print("Model proto alındı.")
    print("Değişken sayısı:", len(model_proto.variables))
    print("Constraint sayısı:", len(model_proto.constraints))

    try:
        print("Objective term sayısı:", len(model_proto.objective.vars))
    except Exception:
        print("Objective term sayısı okunamadı.")

except Exception as e:
    print("Model proto okunurken hata:", e)

if "lokasyon_aksam_gece_sapma_terms" in globals():
    print("Lokasyon sapma term sayısı:", len(lokasyon_aksam_gece_sapma_terms))

if "lokasyon_aksam_gece_debug_df" in globals():
    display(lokasyon_aksam_gece_debug_df)

if "lokasyon_aksam_gece_shift_df" in globals():
    print("Akşam/gece shift satır sayısı:", len(lokasyon_aksam_gece_shift_df))
