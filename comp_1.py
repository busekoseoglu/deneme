# Vardiya Planlama Modeli — Önceki Çalışan Versiyon Notları

Bu notebook’ta call center vardiya planlama problemi için CP-SAT modeli kurulmuştur. Amaç, agent–gün–vardiya atamalarını oluştururken coverage ihtiyacını karşılamak, agent çalışma kurallarını korumak ve takımların birlikte hareket etmesini sağlamaktır.

Bu versiyon, yeni öğrenilen mesai ve hafta sonu takım esnekliği kuralları eklenmeden önceki çalışan versiyondur.

---

## 1. Kullanılan Ana Girdiler

Modelde kullanılan temel girdiler:

* `df_talep`: Gün–vardiya bazlı ihtiyaç tablosu
* `df_tam`: Planlamaya dahil edilen tam zamanlı agent listesi
* `AGENTS`: Planlanacak agent listesi
* `PLAN_GUNLER`: Planlanacak tarih listesi
* `gun_vardiyalari`: Her gün için açık vardiya listesi
* `talep[(ds, v)]`: İlgili gün-vardiya için kişi ihtiyacı
* `saat[(ds, v)]`: Vardiyanın başlangıç ve bitiş saati
* `izin_map`: Agent bazında izinli günler
* `TAKIMLAR`: Takım listesi
* `agent_team`: Agent’ın bağlı olduğu takım
* `WEEKS`: Plan dönemindeki ISO hafta bilgileri
* `week_vardiyalari`: Her hafta kullanılabilecek vardiyalar

---

## 2. Karar Değişkenleri

Modelde ana karar değişkenleri şunlardır:

### Agent–gün–vardiya ataması

```python
x[(a, ds, v)]
```

Anlamı:

```text
Agent a, ds tarihinde v vardiyasında çalışıyorsa 1.
Aksi halde 0.
```

İzinli günlerde ilgili agent için `x` değişkeni açılmamıştır.

---

### Agent–gün çalışma değişkeni

```python
work[(a, ds)]
```

Anlamı:

```text
Agent a, ds tarihinde çalışıyorsa 1.
Çalışmıyorsa 0.
```

Bu değişken, aynı gün maksimum 1 vardiya kuralı ile `x` değişkenlerine bağlanmıştır.

---

### Takım–hafta base vardiya değişkeni

```python
team_week_base[(t, wk, v)]
```

Anlamı:

```text
Takım t için hafta wk içinde ana vardiya v ise 1.
```

Her takım-her hafta için yalnızca bir tane base vardiya seçilmiştir.

---

### Coverage buffer değişkenleri

Coverage birebir talebe zorlanmamıştır. Bunun yerine %10 tolerans verilmiştir.

```python
under_buffer[(ds, v)]
over_buffer[(ds, v)]
```

Anlamı:

```text
under_buffer: Atanan kişi sayısı, talebin %10 alt sınırının altına düşerse oluşan eksik kişi sayısı.
over_buffer: Atanan kişi sayısı, talebin %10 üst sınırının üstüne çıkarsa oluşan fazla kişi sayısı.
```

Örnek:

```text
Talep = 50
Alt sınır = 45
Üst sınır = 55

Atanan = 46 → OK
Atanan = 55 → OK
Atanan = 43 → under_buffer = 2
Atanan = 58 → over_buffer = 3
```

---

## 3. Coverage Kısıtı

Eski yaklaşım:

```python
assigned >= required
```

Bu yapı modelin infeasible olmasına neden olabiliyordu.

Bu yüzden coverage kısıtı %10 buffer ile yeniden kurulmuştur:

```python
assigned + under_buffer[(ds, v)] >= lower_req
assigned - over_buffer[(ds, v)] <= upper_req
```

Burada:

```python
lower_req = floor(required * 0.90)
upper_req = ceil(required * 1.10)
```

Bu sayede model talebi birebir karşılamak zorunda değildir. %10 bandın içinde kalan eksik/fazla atamalar kabul edilmektedir.

---

## 4. Günde Maksimum 1 Vardiya Kısıtı

Her agent bir günde en fazla bir vardiyada çalışabilir.

```python
sum(x[(a, ds, v)] for v in gun_vardiyalari[ds]) == work[(a, ds)]
```

Eğer agent’ın o gün çalışabileceği hiçbir vardiya yoksa:

```python
work[(a, ds)] == 0
```

---

## 5. Haftada 5 Gün Çalışma Kısıtı

Bu versiyonda her agent için haftalık çalışma hedefi 5 gün olarak uygulanmıştır.

Eksik hafta veya izin nedeniyle çalışılabilir gün sayısı 5’ten azsa hedef, çalışılabilir gün sayısına göre sınırlandırılmıştır.

Bu versiyonda henüz şu yeni kural eklenmemiştir:

```text
Agent o hafta yıllık izin aldıysa haftalık çalışma hedefi 5 - izin günü olmalı.
```

Bu yeni kural sonraki versiyonda eklenecektir.

---

## 6. Maksimum 6 Gün Üst Üste Çalışma

Agent’ın 7 gün üst üste çalışması engellenmiştir.

Her 7 günlük pencerede maksimum 6 çalışma günü olabilir:

```python
sum(work[(a, ds)] for ds in 7_gunluk_pencere) <= 6
```

Bu kısıt hard constraint olarak uygulanmıştır.

---

## 7. Sabah Çalışır Kısıtı

`sabah_calisir_flg = 1` olan agentlar, bitiş saati 20:00 sonrasına taşan vardiyalarda çalışamaz.

Gece dönen vardiyalar için bitiş saati ertesi güne taşacak şekilde normalize edilmiştir.

Örnek:

```text
18:00 - 02:00 vardiyası sabah çalışır agent için uygun değildir.
```

---

## 8. Hamile / Süt İzni Hafta Sonu Çalışamaz

Aşağıdaki flag’lerden biri 1 olan agentlar hafta sonu çalışamaz:

```text
hamile_flg = 1
sut_izni_flg = 1
```

Cumartesi ve Pazar günleri bu agentlar için ilgili tüm vardiya değişkenleri 0’a sabitlenmiştir.

---

## 9. 11 Saat Dinlenme Kısıtı

Bir agent’ın ardışık iki vardiyası arasında en az 11 saat dinlenme olması gerekmektedir.

Vardiya başlangıç ve bitiş saatleri datetime formatına çevrilmiştir. Gece dönen vardiyalarda bitiş zamanı ertesi güne taşınmıştır.

Eğer iki vardiya arasında 11 saatten az dinlenme varsa:

```python
x[(a, ds1, v1)] + x[(a, ds2, v2)] <= 1
```

kısıtı eklenmiştir.

---

## 10. Takım Haftalık Base Vardiya Kısıtı

Başlangıçta takım base vardiya kuralı soft olarak kurulmuştu. Yani agent takımın base vardiyası dışına çıkarsa `exception` değişkeni açılıyordu.

Ancak bu durumda bazı takımlar aynı gün 6 farklı vardiyaya bölünebildi.

Bu yüzden son çalışan versiyonda takım kuralı hard hale getirildi:

```python
x[(a, ds, v)] <= team_week_base[(t, wk, v)]
```

Anlamı:

```text
Agent çalışıyorsa, sadece takımının o hafta seçilen base vardiyasında çalışabilir.
```

Bu kural sonucunda takımlar aynı gün farklı vardiyalara bölünmemiştir.

Bu versiyonda takım bütünlüğü hafta içi ve hafta sonu birlikte uygulanmaktadır.

Henüz şu yeni bilgi eklenmemiştir:

```text
Takım bütünlüğü sadece hafta içi zorunlu olacak.
Hafta sonu agentlar ihtiyaca göre farklı vardiyalara dağıtılabilecek.
```

Bu yeni kural sonraki versiyonda eklenecektir.

---

## 11. Objective Fonksiyonu

Bu versiyonda objective sade tutulmuştur.

Öncelikler:

1. %10 buffer altına düşmeyi minimize etmek
2. %10 buffer üstüne çıkmayı minimize etmek

Kullanılan ağırlıklar:

```python
UNDER_BUFFER_W = 100000
OVER_BUFFER_W = 1000
```

Objective:

```python
objective_terms = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        objective_terms.append(UNDER_BUFFER_W * under_buffer[(ds, v)])
        objective_terms.append(OVER_BUFFER_W * over_buffer[(ds, v)])

model.Minimize(sum(objective_terms))
```

Takım bölünmesi objective içinde cezalandırılmamıştır; çünkü takım bütünlüğü hard constraint olarak sağlanmıştır.

---

## 12. Solve Sonrası Kontrol Dosyası

Çözümden sonra kişi bazlı Excel kontrol dosyası oluşturulmuştur.

Dosya adı:

```text
vardiya_kisi_bazli_full_kontrol.xlsx
```

Excel içindeki sheet’ler:

### 01_agent_day_detail

Her agent için her tarih gelir.

Çalışıyorsa:

```text
durum = WORK
```

Çalışmıyorsa:

```text
durum = OFF
```

İzinliyse:

```text
durum_detay = OFF_IZIN
```

Bu sheet kişi bazlı detay kontrol için ana tablodur.

---

### 02_agent_calendar

Agent satırda, tarihler kolonlardadır.

Gözle kontrol için en pratik sayfadır.

Bir takım filtrelenerek o takımın ay içindeki vardiya düzeni görülebilir.

---

### 03_agent_month_summary

Agent bazında aylık özet kontrol tablosudur.

Önemli kolonlar:

```text
base_vardiya_ihlali
dinlenme_11_saat_ihlali
sabah_calisir_ihlali
hamile_sut_hafta_sonu_ihlali
izin_ihlali
max_6_gun_ok
genel_ok
```

---

### 04_agent_week_check

Agent-hafta bazında çalışma günü kontrolüdür.

Bu versiyonda haftalık 5 gün çalışma kontrolü yapılmaktadır.

---

### 05_coverage_buffer

Gün-vardiya bazında coverage kontrolüdür.

Önemli kolonlar:

```text
talep
lower_10pct
upper_10pct
atanan
gap
under_buffer
over_buffer
buffer_ici
```

`gap` tek başına problem değildir. Önemli olan `buffer_ici` değeridir.

---

### 06_team_base

Takımın hafta bazında seçilen base vardiyasını gösterir.

---

### 07_team_date_check

Takım-tarih bazında takımın bölünüp bölünmediğini kontrol eder.

Önemli kolon:

```text
takim_bolunmedi_ok
```

Son hard takım constraint sonrası bu kolonun TRUE olması beklenir.

---

## 13. Bu Versiyonda Henüz Eklenmeyen Yeni Kurallar

Aşağıdaki yeni bilgiler sonraki notebook/versiyonda eklenecektir:

### 1. Yıllık izin haftalık çalışma gününü azaltır

Yeni kural:

```text
Agent o hafta 1 gün izin aldıysa 5 yerine 4 gün çalışır.
2 gün izin aldıysa 3 gün çalışır.
```

Yani:

```text
weekly_normal_target = 5 - izin_count_this_week
```

---

### 2. Ayda en az 1 Cumartesi-Pazar peş peşe OFF

Yeni kural:

```text
Her agent ay içinde en az bir Cumartesi-Pazar çiftinde peş peşe OFF olmalı.
```

---

### 3. Takım bütünlüğü sadece hafta içi zorunlu

Yeni kural:

```text
Pazartesi-Cuma: takım aynı vardiyada kalmalı.
Cumartesi-Pazar: takım bölünebilir.
```

---

### 4. Mesai / 6. gün çalışma

Yeni kural:

```text
Agent haftada maksimum 6 gün çalışabilir.
6. gün mesai sayılır.
Bir agent ayda maksimum 2 gün mesai yapabilir.
mesaiye_kalamaz_flg = 1 olan agentlara mesai yazılamaz.
```

Bu kural için sonraki versiyonda `overtime_week` değişkeni eklenecektir.

---

## 14. Son Durum

Bu versiyonda model feasible çözüm üretmiştir.

Takım bölünmesi hard constraint ile engellenmiştir.

Coverage tarafında %10 buffer uygulanmıştır.

Excel kontrol dosyasında kişi, hafta, takım, coverage ve özel kural kontrolleri yapılabilir hale getirilmiştir.
