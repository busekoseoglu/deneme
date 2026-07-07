# Vardiya Planlama Optimizasyon Modeli

Bu notebook, çağrı merkezi agentları için aylık vardiya planı üretmek amacıyla hazırlanmıştır. Model, günlük vardiya taleplerini karşılamaya çalışırken agent bazlı izin, mesai, özel gün, takım ve çalışma kurallarını birlikte dikkate alır.

## Amaç

Her gün ve vardiya için gerekli kişi sayısına mümkün olduğunca yakın atama yapmak, aynı zamanda operasyonel kurallara uygun ve kontrol edilebilir bir aylık plan üretmektir.

## Modelde Dikkate Alınan Ana Kurallar

- Her agent bir günde en fazla bir vardiyada çalışabilir.
- İzinli günlerde agent’a vardiya atanmaz.
- Haftalık çalışma hedefi, izin ve resmi tatil günleri dikkate alınarak hesaplanır.
- Normal mesai ayda en fazla 2 kez olacak şekilde sınırlandırılır.
- Resmi tatil mesaisi normal mesai limitinden ayrı değerlendirilir.
- Agent en fazla 6 gün üst üste çalışabilir.
- Vardiyalar arasında minimum 11 saat dinlenme kuralı uygulanır.
- Her agent için ayda en az bir Cumartesi-Pazar peş peşe OFF günü hedeflenir.
- Hamile, süt izni olan veya mesaiye kalamayan agentlar için özel kısıtlar uygulanır.
- Arife gününde kısıtlı agentlar özel 09:00–13:00 vardiyasına yönlendirilir.
- Resmi tatilde kısıtlı agentların çalışmaması sağlanır.
- Takımların hafta içi aynı vardiyada kalması hedeflenir; arife, resmi tatil ve hafta sonu günleri bu kuraldan ayrı değerlendirilir.
- Vardiya taleplerinde belirli toleranslar kullanılarak eksik/fazla atamalar minimize edilir.

## Özel Gün Mantığı

Arife ve resmi tatil günleri normal günlerden ayrı ele alınmıştır.  
Arife gününde kısıtlı agentlar için 09:00–13:00 özel vardiyası tanımlanmıştır.  
Resmi tatilde çalışan agentlar `RESMI_TATIL_MESAI` olarak ayrıca işaretlenir ve bu mesai normal aylık mesai limitine dahil edilmez.

## Çıktılar

Model sonucunda sadeleştirilmiş bir Excel çıktısı oluşturulur. Bu dosyada:

- Genel kontrol özeti
- Agent bilgileri
- OFF günleri
- Vardiya talep tablosu
- Aylık agent takvimi
- Coverage kontrolü
- Vardiya özetleri
- Agent aylık çalışma özeti

yer alır.

Takvim çıktısında normal çalışma, normal mesai, arife mesaisi, resmi tatil mesaisi, izin ve OFF günleri ayrı statülerle gösterilir.
