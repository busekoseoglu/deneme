## Mevcut Kurallar

Aşağıdaki kurallar modelde uygulanmaktadır:

- Günde maksimum 1 vardiya
- Coverage ihtiyacının buffer aralığında karşılanması
- Haftalık çalışma hedefinin izin gününe göre belirlenmesi
  - İzin yoksa 5 gün
  - 1 gün izin varsa 4 gün
  - 2 gün izin varsa 3 gün
- Haftada maksimum 6 gün çalışma
- 6. günün mesai olarak modellenmesi
- Ayda maksimum 2 mesai
- `mesaiye_kalamaz_flg = 1` olan agentlara mesai yazılmaması
- Maksimum 6 gün üst üste çalışma
- İki vardiya arasında minimum 11 saat dinlenme
- `sabah_calisir_flg = 1` olan agentların 20:00 sonrası biten vardiyalarda çalışmaması
- `hamile_flg = 1` veya `sut_izni_flg = 1` olan agentların hafta sonu çalışmaması
- İzinli günlerde agentların çalışmaması
- Hafta içi takım bütünlüğünün korunması
  - Pazartesi–Cuma takım aynı vardiyada kalır
- Hafta sonu takım bütünlüğünün serbest bırakılması
  - Cumartesi–Pazar agentlar farklı vardiyalara dağılabilir
- Her agent için ayda en az 1 kez Cumartesi-Pazar peş peşe OFF verilmesi

---

## Bu Notebookta Eklenen / Güncellenen Kurallar

Bir önceki notebooktan farklı olarak bu notebookta aşağıdaki eklemeler / güncellemeler yapılmıştır:

- Coverage buffer oranı değiştirilmiştir
  - Bu notebookta `BUFFER_RATE = 0.50` kullanılmıştır
- Gece / akşam vardiyası kuralı eklenmiştir
  - Aşağıdaki vardiyalar gece/akşam vardiyası olarak tanımlanmıştır:
    - `17:00 - 01:00`
    - `18:00 - 02:00`
    - `00:00 - 08:00`
- Bir agentın ay içinde en fazla 2 farklı haftada gece/akşam vardiyası alabilmesi kuralı eklenmiştir
- Böylece agentların tüm ay boyunca sürekli gececi / akşamcı çalışması engellenmiştir

---

## Gece / Akşam Vardiyası Kuralının Yorumu

Bu notebookta eklenen yeni gece/akşam kuralı şu anlama gelir:

- Eğer bir agent bir hafta içinde en az 1 kez aşağıdaki vardiyalardan birini alırsa, o hafta agent için “gece/akşam haftası” sayılır:
  - `17:00 - 01:00`
  - `18:00 - 02:00`
  - `00:00 - 08:00`
- Her agent için ay içinde bu şekilde en fazla 2 hafta olabilir
- Böylece aynı agentın bütün ay gece vardiyalarında çalıştırılması engellenir
