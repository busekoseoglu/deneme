# Vardiya Planlama Modeli — Güncel Notebook Özeti

Bu notebookta çağrı merkezi agentları için kişi bazlı vardiya planlama modeli kurulmuştur. Modelin amacı, her gün ve vardiya için ihtiyaç duyulan kişi sayısını karşılamak, agent çalışma kurallarını sağlamak, takım bütünlüğünü mümkün olan yerlerde korumak ve adil/uygulanabilir bir aylık roster üretmektir.

Model OR-Tools CP-SAT ile kurulmuştur.

---

## 1. Modelin Genel Amacı

Bu modelde her agent için:

* Hangi gün çalışacağı,
* Hangi vardiyada çalışacağı,
* Hangi gün OFF olacağı,
* Hangi hafta mesai yapıp yapmadığı,
* Gece/akşam vardiyası haftası alıp almadığı,
* Ay içinde peş peşe Cumartesi-Pazar OFF alıp almadığı

karar değişkenleri ve kısıtlar üzerinden belirlenir.

Coverage tarafında her vardiya için talep birebir karşılanmak zorunda değildir. Talep etrafında belirlenen buffer aralığı içinde kalmak hedeflenir.

---

## 2. Ana Karar Değişkenleri

### Agent–Gün–Vardiya Ataması

```python
x[(agent, tarih, vardiya)]
```

Agent ilgili tarihte ilgili vardiyada çalışıyorsa 1, aksi halde 0 değerini alır.

---

### Günlük Çalışma Değişkeni

```python
work[(agent, tarih)]
```

Agent ilgili gün çalışıyorsa 1, OFF ise 0 değerini alır.

Bu değişken, günlük vardiya atamalarıyla bağlanır. Böylece bir agent bir günde en fazla bir vardiya alabilir.

---

### Takım Haftalık Base Vardiya Değişkeni

```python
team_week_base[(takim, hafta, vardiya)]
```

Her takım için her hafta bir base vardiya seçilir.

Hafta içi günlerde agentlar kendi takımlarının base vardiyasına bağlı kalır. Hafta sonu takım bütünlüğü serbest bırakılmıştır.

---

### Coverage Buffer Değişkenleri

```python
under_buffer[(tarih, vardiya)]
over_buffer[(tarih, vardiya)]
```

Her gün-vardiya için atanan kişi sayısı, talebin belirli bir buffer aralığında kalmalıdır.

Bu notebookta buffer oranı parametrik olarak tutulur:

```python
BUFFER_RATE = 0.50
```

Örnek:

```text
Talep = 50
BUFFER_RATE = 0.50

Alt sınır = 25
Üst sınır = 75
```

Atanan kişi alt sınırın altında kalırsa `under_buffer`, üst sınırın üstüne çıkarsa `over_buffer` oluşur.

---

### Haftalık Mesai Değişkeni

```python
overtime_week[(agent, hafta)]
```

Agent ilgili haftada 6. gün çalışıyorsa mesai yapmış sayılır.

Kurallar:

```text
Haftalık normal hedef = 5 - izin günü
Çalışılan gün = normal hedef + overtime_week
Ayda maksimum 2 mesai olabilir
mesaiye_kalamaz_flg = 1 olan agentlara mesai yazılamaz
```

---

### Cumartesi-Pazar Peş Peşe OFF Değişkeni

```python
pair_off[(agent, weekend_pair)]
```

Agent ilgili Cumartesi-Pazar çiftinde iki gün de OFF ise 1 olur.

Her agent için ay içinde en az bir kez Cumartesi-Pazar peş peşe OFF zorunlu tutulur.

---

### Gece/Akşam Haftası Değişkeni

```python
night_week[(agent, hafta)]
```

Agent ilgili hafta en az bir gece/akşam vardiyası aldıysa 1 olur.

Gece/akşam vardiyası olarak kabul edilen vardiyalar:

```text
17:00 - 01:00
18:00 - 02:00
00:00 - 08:00
```

Kural:

```text
Bir agent ay içinde en fazla 2 farklı haftada gece/akşam vardiyası alabilir.
```

---

## 3. Modele Eklenen Ana Kurallar

### Coverage Buffer

Her vardiya için atanan kişi sayısının talep etrafında belirlenen buffer aralığında kalması hedeflenir.

```text
assigned + under_buffer >= lower_req
assigned - over_buffer <= upper_req
```

---

### Günde Maksimum 1 Vardiya

Bir agent aynı gün içinde yalnızca bir vardiyaya atanabilir.

---

### Haftalık Çalışma Hedefi

Agentların haftalık çalışma hedefi izin günlerine göre hesaplanır.

```text
İzin yoksa: 5 gün çalışma
1 gün izin varsa: 4 gün çalışma
2 gün izin varsa: 3 gün çalışma
```

Eksik haftalarda hedef, o hafta plan döneminde bulunan gün sayısına göre kırpılır.

---

### Mesai Kuralı

Agent haftada en fazla 6 gün çalışabilir. 6. gün mesai olarak modellenir.

```text
Ayda max 2 mesai
mesaiye_kalamaz_flg = 1 olanlara mesai yok
```

---

### Maksimum 6 Gün Üst Üste Çalışma

Herhangi 7 günlük pencerede agent en fazla 6 gün çalışabilir.

---

### 11 Saat Dinlenme

Bir agentın iki vardiyası arasında en az 11 saat dinlenme olmalıdır.

---

### Sabah Çalışır Kuralı

`sabah_calisir_flg = 1` olan agentlar 20:00 sonrası biten vardiyalarda çalışamaz.

Bu flag hamile ve süt izni olan agentları da kapsadığı için, bu kişiler de geç vardiyalara atanmaz.

---

### Hamile / Süt İzni Hafta Sonu Kuralı

`hamile_flg = 1` veya `sut_izni_flg = 1` olan agentlar hafta sonu çalışamaz.

---

### İzinli Gün Çalışma Yasağı

`izin_map` içinde izinli görünen günlerde agent için çalışma engellenir.

---

### Takım Bütünlüğü

Takım bütünlüğü sadece hafta içi hard constraint olarak uygulanır.

```text
Pazartesi-Cuma: Takım aynı vardiyada kalır
Cumartesi-Pazar: Takım bölünebilir
```

---

### Ayda En Az 1 Cumartesi-Pazar Peş Peşe OFF

Her agent ay içinde en az bir hafta sonunda hem Cumartesi hem Pazar OFF olacak şekilde planlanır.

---

### Gece/Akşam Vardiyası Maksimum 2 Hafta

Agentlar ay içinde en fazla 2 farklı haftada gece/akşam vardiyası alabilir.

Bu kural, agentların tüm ay boyunca sürekli gececi/akşamcı çalışmasını engellemek için eklenmiştir.

---

## 4. Objective

Objective üç ana parçadan oluşur:

```text
1. Under buffer minimize edilir
2. Over buffer minimize edilir
3. Gereksiz mesai minimize edilir
```

Ağırlıklar:

```python
UNDER_BUFFER_W = 100000
OVER_BUFFER_W = 1000
OVERTIME_W = 5000
```

Under buffer en yüksek cezaya sahiptir. Çünkü ihtiyacın altında kalmak, fazla atamadan daha kritik kabul edilmiştir.

---

## 5. Bu Notebookta Önceki Notebooktan Farklı Olanlar

Bu notebook, bir önceki checkpoint modelinin üzerine yeni kurallar ve parametre değişiklikleri eklenmiş halidir.

### 1. Buffer oranı değiştirildi

Önceki notebookta coverage buffer oranı daha dar tutulmuştu.

Bu notebookta:

```python
BUFFER_RATE = 0.50
```

olarak çalıştırılmıştır.

Bu nedenle coverage daha esnek hale gelmiştir. Talebin %50 altı ve %50 üstü aralığında kalan atamalar buffer içinde kabul edilir.

---

### 2. Gece/Akşam Vardiyası Kuralı Eklendi

Önceki notebookta agentların kaç hafta gece/akşam vardiyası aldığı kontrol edilmiyordu.

Bu notebookta aşağıdaki vardiyalar gece/akşam vardiyası olarak tanımlandı:

```text
17:00 - 01:00
18:00 - 02:00
00:00 - 08:00
```

Ve şu kural eklendi:

```text
Her agent ay içinde en fazla 2 hafta gece/akşam vardiyası alabilir.
```

Bu kural için `night_week[(agent, hafta)]` değişkeni oluşturuldu.

---

### 3. Agentların Sürekli Gececi Çalışması Engellendi

Yeni gece/akşam kuralı sayesinde aynı agentın tüm ay boyunca gece vardiyalarına yazılması engellenir.

Bir hafta içinde bir gün bile gece/akşam vardiyası alırsa, o hafta ilgili agent için gece/akşam haftası sayılır.

---

### 4. Mevcut Kurallar Korundu

Önceki notebooktan gelen aşağıdaki kurallar aynen korunmuştur:

```text
- Günde max 1 vardiya
- Haftalık çalışma = 5 - izin günü
- 6. gün mesai
- Ayda max 2 mesai
- mesaiye_kalamaz_flg = 1 olanlara mesai yok
- Max 6 gün üst üste çalışma
- 11 saat dinlenme
- sabah_calisir_flg = 1 olanlar 20:00 sonrası çalışmaz
- hamile / süt izni hafta sonu çalışmaz
- izinli günde çalışma yok
- Hafta içi takım bütünlüğü
- Hafta sonu takım serbestliği
- Ayda en az 1 Cumartesi-Pazar peş peşe OFF
```

---

## 6. Kontrol Çıktıları

Model solve edildikten sonra aşağıdaki kontroller yapılır:

```text
- Her agent kaç gün çalışmış?
- Her agent kaç gün OFF kalmış?
- Her agent kaç gün izinli?
- Her agent kaç mesai yapmış?
- Coverage under/over buffer toplamları
- Hafta içi takım bölünmesi var mı?
- Ayda en az 1 Cumartesi-Pazar peş peşe OFF almayan agent var mı?
- 2 haftadan fazla gece/akşam vardiyası alan agent var mı?
- 11 saat dinlenme ihlali var mı?
- Max 6 gün üst üste çalışma ihlali var mı?
```

Bu kontroller Excel dosyasına da aktarılabilir.

---

## 7. Not

`BUFFER_RATE = 0.50` test ve esneklik açısından kullanışlıdır, ancak iş çıktısı için oldukça geniş bir toleranstır.

Final iş kuralı olarak daha sıkı bir coverage istenirse buffer oranı tekrar düşürülebilir:

```python
BUFFER_RATE = 0.10
BUFFER_RATE = 0.15
BUFFER_RATE = 0.20
```

Buffer oranı düşürüldüğünde model daha sıkı hale gelir ve solve süresi / under-over değerleri tekrar kontrol edilmelidir.
