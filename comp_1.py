# %% [DEBUG] - MODEL VALIDATION VE BOYUT KONTROLÜ

validation = model.Validate()

if validation:
    print("MODEL VALIDATION HATASI:")
    print(validation)
    raise ValueError(validation)

print("Model validation OK.")

model_proto = model.Proto()

print("Değişken sayısı:", len(model_proto.variables))
print("Constraint sayısı:", len(model_proto.constraints))

if model_proto.HasField("objective"):
    print("Objective term sayısı:", len(model_proto.objective.vars))

if "lokasyon_aksam_gece_sapma_terms" in globals():
    print("Lokasyon sapma term sayısı:", len(lokasyon_aksam_gece_sapma_terms))

if "lokasyon_aksam_gece_debug_df" in globals():
    display(lokasyon_aksam_gece_debug_df)

if "lokasyon_aksam_gece_shift_df" in globals():
    print("Akşam/gece shift satır sayısı:", len(lokasyon_aksam_gece_shift_df))
