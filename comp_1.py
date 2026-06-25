# Vardiya Planlama Modeli — Güncel Versiyon Özeti

Bu versiyonda amaç, agent–gün–vardiya atamasını yaparken coverage ihtiyacını %10 buffer içinde karşılamak, kişi bazlı çalışma kurallarını korumak ve takım bütünlüğünü hafta içi sağlamak.

---

## 1. Ana Karar Değişkenleri

### Agent vardiya ataması

```python
x[(agent, tarih, vardiya)]
```

Agent ilgili tarihte ilgili vardiyada çalışıyorsa 1, aksi halde 0.

---

### Agent günlük çalışma değişkeni

```python
work[(agent, tarih)]
```

Agent o gün çalışıyorsa 1, çalışmıyorsa 0.

Bu değişken `x` ile bağlandı:

```python
sum(x[(a, ds, v)] for v in gun_vardiyalari[ds]) == work[(a, ds)]
```

Böylece agent bir günde maksimum 1 vardiya alabiliyor.

---

### Takım haftalık base vardiya değişkeni

```python
team_week_base[(takim, hafta, vardiya)]
```

Her takım için her hafta 1 tane ana vardiya seçiliyor.

Hafta içi günlerde takım bütünlüğü korunuyor:

```python
x[(a, ds, v)] <= team_week_base[(takim, hafta, v)]
```

Bu kısıt sadece Pazartesi–Cuma için uygulanıyor. Cumartesi-Pazar günleri takım serbest bırakıldı.

---

### Coverage buffer değişkenleri

```python
under_buffer[(tarih, vardiya)]
over_buffer[(tarih, vardiya)]
```

Talep birebir karşılanmak zorunda değil. %10 buffer verildi.

Örnek:

```text
Talep = 50
Alt sınır = 45
Üst sınır = 55

Atanan 46 ise OK
Atanan 55 ise OK
Atanan 43 ise under_buffer = 2
Atanan 58 ise over_buffer = 3
```

Coverage kısıtı:

```python
assigned + under_buffer[(ds, v)] >= lower_req
assigned - over_buffer[(ds, v)] <= upper_req
```

---

### Mesai değişkeni

```python
overtime_week[(agent, hafta)]
```

Agent ilgili haftada mesai yaptıysa 1, yapmadıysa 0.

Bu versiyonda mesai 6. gün çalışma olarak modellendi.

Kurallar:

```text
Haftalık normal hedef = 5 - izin günü
Çalışılan gün = normal hedef + overtime_week
Ayda maksimum 2 mesai
mesaiye_kalamaz_flg = 1 olan agentlara mesai yazılamaz
```

---

### Cumartesi-Pazar peş peşe OFF değişkeni

```python
pair_off[(agent, hafta_sonu_cifti)]
```

Agent ilgili Cumartesi-Pazar çiftinde iki gün de OFF ise 1.

Her agent için ayda en az 1 kez Cumartesi-Pazar peş peşe OFF zorunlu tutuldu:

```python
sum(pair_off[(a, i)] for i in weekend_pairs) >= 1
```

---

## 2. Eklenen Ana Kurallar

### Günlük maksimum 1 vardiya

Her agent bir günde en fazla 1 vardiyada çalışabilir.

---

### Haftalık çalışma hedefi

Önceki modelde agent haftada 5 gün çalışıyordu.

Yeni modelde izin günleri dikkate alındı:

```text
İzin yoksa: 5 gün çalışır
1 gün izin varsa: 4 gün çalışır
2 gün izin varsa: 3 gün çalışır
```

Mesai varsa hedefin 1 gün üstüne çıkabilir.

---

### Maksimum 6 gün üst üste çalışma

Herhangi 7 günlük pencerede en fazla 6 çalışma günü olabilir.

---

### 11 saat dinlenme

Agent’ın iki vardiyası arasında minimum 11 saat dinlenme olmalı.

---

### Sabah çalışan kısıtı

`sabah_calisir_flg = 1` olan agentlar 20:00 sonrası biten vardiyalarda çalışamaz.

---

### Hamile / süt izni kısıtı

`hamile_flg = 1` veya `sut_izni_flg = 1` olan agentlar hafta sonu çalışamaz.

---

### İzinli günde çalışma yasağı

`izin_map` içinde izinli görünen günlerde agent için vardiya değişkeni açılmadı / çalışma engellendi.

---

### Takım bütünlüğü

Hafta içi takım bütünlüğü hard constraint olarak uygulandı.

```text
Pazartesi-Cuma: Takım aynı vardiyada kalır.
Cumartesi-Pazar: Takım bölünebilir.
```

---

### Ayda en az 1 Cumartesi-Pazar peş peşe OFF

Her agent ay içinde en az bir hafta sonunda hem Cumartesi hem Pazar OFF olacak şekilde planlanır.

---

## 3. Objective

Objective sade tutuldu.

Öncelikler:

1. `under_buffer` minimize edilsin.
2. `over_buffer` minimize edilsin.
3. Gereksiz mesai minimize edilsin.

Ağırlıklar:

```python
UNDER_BUFFER_W = 100000
OVER_BUFFER_W = 1000
OVERTIME_W = 5000
```

---

## 4. Son Solve Sonucu

1500 saniye limit ile çözüm alındı.

Sonuç:

```text
under_buffer = 0
over_buffer = 37
toplam mesai = 0
objective = 37,000
best_bound = 37,000
```

Bu sonuçta model optimal kapanmıştır.

Hiçbir vardiyada %10 alt sınırın altına düşülmemiştir. Sadece toplam 37 kişilik %10 üst sınır aşımı kalmıştır.

---

## 5. Excel Kontrol Dosyası

Son çözüm için kişi bazlı final kontrol Excel’i oluşturuldu:

```text
vardiya_final_kisi_bazli_kontrol.xlsx
```

Sheet’ler:

```text
00_summary
01_agent_day_detail
02_agent_calendar
03_agent_month_summary
04_agent_week_check
05_coverage_buffer
06_team_date_check
07_team_base
08_weekend_pair_off
09_weekend_off_summary
```

Kontrol için özellikle bakılacak alanlar:

```text
03_agent_month_summary → genel_ok
04_agent_week_check → haftalik_calisma_ok
05_coverage_buffer → under_buffer / over_buffer / buffer_ici
06_team_date_check → hafta içi takim_butunlugu_ok
09_weekend_off_summary → pes_pese_hafta_sonu_off_ok
```
