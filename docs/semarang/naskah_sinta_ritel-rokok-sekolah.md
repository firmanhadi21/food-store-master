# [DRAF NASKAH] Analisis Spasial Keberadaan Ritel Produk Tembakau terhadap Radius Perlindungan Satuan Pendidikan Berdasarkan PP No. 28 Tahun 2024 di Kota Semarang

> **Status: draf awal, belum siap submit.** Lihat §Catatan Penyunting di akhir untuk daftar
> hal yang masih harus dilengkapi. Angka pada naskah ini sudah final dan dapat direproduksi
> dari `scripts/semarang/`.
>
> Bahasa: Indonesia (mayoritas jurnal SINTA menerima; versi Inggris mudah diturunkan).
> Format: IMRaD. Target: jurnal geografi / geomatika terakreditasi SINTA.

**Firman Hadi**
Departemen Teknik Geodesi, Fakultas Teknik, Universitas Diponegoro, Semarang
*Korespondensi:* [email]

---

## Abstrak

Peraturan Pemerintah No. 28 Tahun 2024 melarang penjualan produk tembakau dalam radius 200 m
dan pengiklanannya dalam radius 500 m dari satuan pendidikan. Sampai saat ini belum tersedia
data tingkat gerai yang memungkinkan penilaian sebaran ritel terhadap ketentuan tersebut.
Penelitian ini memetakan minimarket berjaringan di Kota Semarang dan mengukur posisinya
terhadap kedua radius, dengan penekanan pada **verifikasi kelengkapan data** — langkah yang
umumnya diabaikan dalam penelitian berbasis *point of interest* (POI). Lapisan gerai disusun
dari Overture Maps, OpenStreetMap, dan Google Places, lalu jumlah sebenarnya diestimasi dengan
metode *capture–recapture* (penaksir Chapman). Lapisan satuan pendidikan disusun dari
OpenStreetMap dan Dukcapil, dan kelengkapannya diuji terhadap jumlah terbitan Dapodik.
Hasil menunjukkan **79,6% dari 949 minimarket berada dalam radius 200 m** dari satuan
pendidikan, **87,7% berada dalam radius 500 m**, dan **47,5% dari 2.553 satuan pendidikan**
memiliki sedikitnya satu minimarket dalam radius 200 m. Median jarak satuan pendidikan ke
minimarket terdekat adalah **207 m**, praktis berimpit dengan ambang yang diatur. Verifikasi
kelengkapan menunjukkan bahwa gabungan Overture dan OpenStreetMap hanya memuat **42%** gerai
berjaringan, dan ketidaklengkapan tersebut **tidak tersebar acak** melainkan bervariasi antara
0,19 dan 0,79 antarkecamatan mengikuti formalitas komersial wilayah. Temuan ini menegaskan
bahwa penelitian lingkungan ritel berbasis POI di Indonesia memerlukan verifikasi kelengkapan
eksplisit, dan bahwa seluruh angka yang dilaporkan merupakan batas bawah.

**Kata kunci:** analisis spasial; PP 28/2024; pengendalian tembakau; lingkungan ritel;
kelengkapan data POI; Kota Semarang

---

## 1. Pendahuluan

*(± 800–1.000 kata)*

**Alur argumen yang harus dibangun:**

1. **Konteks pengendalian tembakau di Indonesia.** Prevalensi merokok laki-laki dewasa
   termasuk tertinggi di dunia; Indonesia bukan pihak WHO FCTC; iklan produk tembakau masih
   luas dibandingkan sebagian besar negara. → *perlu sitasi: Riskesdas/SKI terbaru, GATS
   Indonesia, status FCTC.*
2. **PP 28/2024 sebagai perubahan regulatif.** Aturan pelaksanaan UU 17/2023, memuat larangan
   penjualan dalam radius 200 m dan iklan dalam radius 500 m dari satuan pendidikan, larangan
   penjualan eceran (*ketengan*), dan kenaikan batas usia menjadi 21 tahun.
3. **Masalah: aturan berbasis radius memerlukan data spasial tingkat gerai, dan data itu
   belum ada.** Penegakan maupun evaluasi kebijakan tidak dapat dilakukan tanpa mengetahui
   di mana gerai berada relatif terhadap satuan pendidikan.
4. **Literatur lingkungan ritel dan sekolah.** Kepadatan ritel tembakau di sekitar sekolah
   berhubungan dengan inisiasi merokok remaja. → *perlu sitasi internasional + Indonesia
   (studi Jakarta/Yogyakarta bila ada).*
5. **Celah metodologis: kelengkapan data POI.** Penelitian lingkungan pangan/ritel banyak
   memakai POI sekunder yang kelengkapannya bervariasi menurut jenis gerai dan wilayah
   (Burgoine & Harrison, 2013; Chen, 2025). Di Indonesia hal ini belum diuji.
6. **Tujuan penelitian:** (a) menyusun lapisan ritel dan satuan pendidikan yang terverifikasi
   kelengkapannya untuk Kota Semarang; (b) mengukur sebarannya terhadap radius PP 28/2024;
   (c) menguji apakah ketidaklengkapan data memengaruhi kesimpulan.

---

## 2. Metode

### 2.1 Wilayah studi

Kota Semarang, ibu kota Provinsi Jawa Tengah, luas ± 373,8 km², 16 kecamatan, penduduk
± 1,65 juta jiwa. Dipilih karena mewakili kota besar di Jawa dengan gradien kepadatan yang
jelas: kawasan pusat niaga dan pesisir di utara hingga perbukitan semi-perdesaan
(Gunungpati, Mijen) di selatan. Batas administrasi diambil dari OpenStreetMap
(relasi 8409116); hasil perakitan poligon diverifikasi melalui luas terhitung
**389,5 km²** terhadap luas resmi 373,8 km² (rasio 1,042).

### 2.2 Definisi satuan pendidikan

Cakupan mengikuti **Penjelasan Pasal 518 ayat (1) PP 28/2024 (hlm. 570)** — satu-satunya
definisi dalam peraturan tersebut:

> “Satuan pendidikan antara lain pendidikan anak usia dini, sekolah/madrasah, pesantren,
> perguruan tinggi, atau nama lain yang sejenis dengan pendidikan formal.”

Karena itu analisis mencakup PAUD/TK, SD/MI, SMP/MTs, SMA/SMK/MA, SLB, dan perguruan tinggi.
Frasa “tempat bermain anak” pada Pasal 434 ayat (1) huruf e dipahami sebagai *kelompok
bermain*, yaitu salah satu bentuk PAUD, sehingga telah tercakup. Lembaga nonformal
(*learning center*) dikecualikan karena tidak “sejenis dengan pendidikan formal”.

### 2.3 Sumber data

| Lapisan | Sumber | Peran |
|---|---|---|
| Ritel (minimarket) | Overture Maps (rilis 2026-06-17.0), OpenStreetMap, Google Places API (New) | Penyusunan posisi |
| Satuan pendidikan | OpenStreetMap, Dukcapil Kemendagri (*Fasilitas_Pendidikan* FeatureServer) | Penyusunan posisi |
| Verifikasi jumlah | Dapodik Kemendikdasmen (jumlah terbitan per kabupaten/kota) | Uji kelengkapan |
| Batas wilayah | OpenStreetMap | Pembatas analisis |

### 2.4 Penyusunan lapisan ritel

Ekstraksi Overture dilakukan atas seluruh POI dalam kotak pembatas Kota Semarang tanpa
penyaringan kategori, karena pemeriksaan awal menunjukkan kategori Overture di wilayah ini
tidak dapat diandalkan: **98,1% rekaman berasal dari Meta** (bandingkan Jepang 39,8%),
sedangkan AllThePlaces — hasil pengambilan dari *store locator* resmi — hanya menyumbang
**0,2%** (Jepang 25,7%). Akibatnya klasifikasi dilakukan **berbasis nama** dengan kategori
sebagai prior lemah, kebalikan dari praktik lazim.

Aturan klasifikasi disusun setelah pemeriksaan langsung terhadap data, bukan secara *a priori*.
Pencocokan substring sederhana terbukti keliru karena kata umum bahasa Indonesia: *griya*
(rumah) menghasilkan 136 positif palsu berupa indekos dan perumahan; *yogya* menjaring
Yogyakarta International Airport; *toko* menjaring toko emas dan toko sepeda. Aturan final
memakai batas kata dan kemunculan bersama dengan kata bermakna pangan.

Penggabungan sumber dilakukan sebagai **gabungan (union)**, bukan sumber tunggal. Uji sapuan
radius pencocokan menunjukkan tingkat kecocokan Alfamart antar-sumber mendatar pada rentang
yang dapat ditafsirkan (17 pada 50 m; 18 pada 100 m; 22 pada 200 m), sementara jarak
antar-gerai sesama merek memiliki median 524 m — sehingga radius di atas 200 m hanya
menjaring gerai lain, bukan gerai yang sama. Sebanyak 119 minimarket yang hanya ada di
OpenStreetMap tidak memiliki satu pun *convenience store* Overture dalam radius 100 m,
menandakan kedua sumber benar-benar saling melengkapi.

Penghapusan duplikat memerhatikan kekhasan Indonesia: **Alfamart dan Indomaret kerap
berhadapan langsung**. Penggabungan hanya berdasarkan kategori dan jarak akan meleburkan dua
gerai berbeda menjadi satu. Kunci merek karena itu disertakan dalam syarat pencocokan;
verifikasi menemukan 21 pasangan Alfamart×Indomaret berjarak rata-rata 35 m yang benar
merupakan gerai berbeda.

### 2.5 Estimasi jumlah sebenarnya (*capture–recapture*)

*Store locator* resmi kedua jaringan tidak dapat diakses secara terprogram (Alfagift
mengembalikan HTTP 401; klikindomaret HTTP 403), dan penggunaan otentikasi untuk memanen
basis data gerai bertentangan dengan ketentuan layanan kedua perusahaan sehingga tidak
ditempuh. Sebagai sumber ketiga yang independen digunakan **Google Places API (New)**,
dengan pencarian teks pada grid 2 km yang meliputi wilayah kota.

Jumlah populasi diestimasi dengan penaksir **Chapman**:

$$\hat{N} = \frac{(n_1+1)(n_2+1)}{m+1} - 1$$

dengan $n_1$ dan $n_2$ jumlah gerai pada masing-masing sumber dan $m$ jumlah yang tercocokkan
(radius 100 m). Sebelum estimasi, data Google dibersihkan dari entitas bukan gerai
(mis. “ATM BCA Indomaret”, badan hukum) dan duplikat dalam radius 50 m.

### 2.6 Analisis radius

Jarak dihitung dengan **hampiran ekuirektangular** (proyeksi bidang datar terkoreksi lintang);
pada lintang −7° faktor koreksi bujur cos(7°) ≈ 0,993 sehingga galat hampiran dapat diabaikan
pada skala ratusan meter. Pendekatan ini dipilih karena fungsi `ST_Distance_Spheroid` pada
lingkungan komputasi yang digunakan mengembalikan nilai tak-hingga.

Dua ukuran dilaporkan, dan **perbedaan keduanya penting** (lihat §4.3):

- **Berbasis gerai** — proporsi minimarket yang berada dalam radius tertentu dari satuan
  pendidikan.
- **Berbasis satuan pendidikan** — proporsi satuan pendidikan yang memiliki sedikitnya satu
  minimarket dalam radius tertentu.

---

## 3. Hasil

### 3.1 Kelengkapan lapisan ritel

**Tabel 1.** Estimasi jumlah gerai dan cakupan tiap sumber

| Jaringan | Basis data gabungan | Google (bersih) | Tercocokkan | $\hat{N}$ | Cakupan basis data | Cakupan Google |
|---|---:|---:|---:|---:|---:|---:|
| Alfamart | 182 | 310 | 130 | **433** | 42,0% | 71,5% |
| Indomaret | 216 | 387 | 160 | **522** | 41,4% | 74,1% |

Gabungan Overture dan OpenStreetMap — praktik yang lazim dalam penelitian POI — hanya memuat
**sekitar 42%** gerai berjaringan. Gabungan ketiga sumber mencapai ± 85% dari estimasi.

### 3.2 Ketidaklengkapan bersifat terstruktur secara ruang

**Tabel 2.** Cakupan basis data terhadap Google per kecamatan (kutipan)

| Kecamatan | Google | Basis data | Cakupan |
|---|---:|---:|---:|
| Tugu | 26 | 5 | **0,19** |
| Gayamsari | 26 | 7 | 0,27 |
| … | | | |
| Semarang Utara | 25 | 18 | 0,72 |
| Semarang Tengah | 48 | 38 | **0,79** |

Rentang cakupan 0,19–0,79 (rasio 4×). Yang perlu dicatat secara metodologis: korelasi antara
cakupan dan **jarak dari pusat kota hanya −0,140**, sehingga uji berbasis jarak akan
menyimpulkan “acak” secara keliru. Pola baru terlihat pada stratifikasi administratif.
Cakupan tertinggi berada di kawasan pusat niaga, kota lama, dan kawasan permukiman
menengah-atas serta kampus — wilayah dengan kehadiran daring usaha yang padat — sedangkan
terendah di kawasan industri. Mengingat 98,1% rekaman Overture berasal dari Meta, pewarisan
pola kepadatan halaman usaha daring merupakan mekanisme yang dapat diduga.

### 3.3 Kelengkapan lapisan satuan pendidikan

**Tabel 3.** Lapisan satuan pendidikan terhadap jumlah terbitan Dapodik

| Jenjang | Lapisan | Dapodik | Cakupan |
|---|---:|---:|---:|
| SD (termasuk MI) | 507 | 615 | 82,4% |
| SMP (termasuk MTs) | 145 | 244 | **59,4%** |
| SMA (termasuk SMK) | 153 | 195 | 78,5% |
| TK/PAUD | 1.462 | 1.439 | 101,6% |
| **SD+SMP+SMA** | **805** | **1.054** | **76,4%** |

### 3.4 Sebaran terhadap radius PP 28/2024

**Tabel 4.** Ritel dan satuan pendidikan terhadap kedua radius (n = 2.553 satuan pendidikan;
949 minimarket)

| Ukuran | Nilai |
|---|---:|
| Minimarket dalam radius 200 m (larangan jual) | **755 / 949 = 79,6%** |
| Minimarket dalam radius 500 m (larangan iklan) | 832 / 949 = 87,7% |
| Satuan pendidikan dengan ≥1 minimarket dalam 200 m | **1.213 / 2.553 = 47,5%** |
| Median jarak satuan pendidikan ke minimarket terdekat | **207 m** |
| Kuartil 1 / Kuartil 3 | 122 m / 337 m |

---

## 4. Pembahasan

### 4.1 Skala keterpaparan

Empat dari lima minimarket di Kota Semarang berada di dalam radius yang penjualannya dilarang.
Median jarak 207 m berimpit dengan ambang 200 m, sehingga sebaran ritel di kota ini secara
praktis tidak selaras dengan asumsi keruangan yang mendasari PP 28/2024. Karena jarak diukur
antartitik dan bukan dari batas persil satuan pendidikan, **angka sebenarnya lebih tinggi**.

### 4.2 Implikasi kebijakan

*(Bahas: kelayakan penegakan bila mayoritas gerai berada dalam radius; opsi kebijakan —
ketentuan peralihan, penegakan bertahap, atau pengalihan fokus dari lokasi ke pembatasan
pajangan dan iklan; keberatan APRINDO dan AMLI yang menyoroti ketidakjelasan ketentuan radius.)*

### 4.3 Kontribusi metodologis: arah penyebut menentukan kesimpulan

Ketika lapisan ritel diperbaiki dari cakupan 42% menjadi ± 85%, kedua ukuran bereaksi sangat
berbeda:

| Ukuran | Lapisan 42% | Lapisan 85% | Perubahan |
|---|---:|---:|---|
| Berbasis gerai (dalam 200 m) | 46,7% | 47,1% | **+0,4 poin** |
| Berbasis satuan pendidikan | 33,2% | 49,4% | **+16,2 poin** |

Gerai dan satuan pendidikan sama-sama terkonsentrasi pada koridor niaga yang sama, sehingga
penambahan gerai hampir tidak mengubah proporsi gerai yang kebetulan berdekatan dengan satuan
pendidikan; sebaliknya banyak satuan pendidikan baru melewati ambang 200 m untuk pertama kali.

**Konsekuensinya penting:** penelitian yang memakai penyebut sisi gerai akan tampak stabil
dalam analisis sensitivitas meskipun lapisannya kehilangan lebih dari separuh data. Ukuran
berbasis pihak yang terpapar lebih peka terhadap kelengkapan, sekaligus lebih relevan secara
kebijakan.

### 4.4 Keterbatasan

1. Jarak antartitik, bukan dari batas persil → **taksiran rendah**.
2. Kedekatan bukan penetapan pelanggaran; ketentuan peralihan tidak diperiksa.
3. Lapisan satuan pendidikan 76,4% lengkap pada jenjang SD–SMA; arah pengaruh kekurangan
   249 satuan pendidikan **tidak dapat ditentukan** tanpa mengetahui sebarannya.
4. `businessStatus` tidak diminta pada pemanggilan Google Places, sehingga gerai yang telah
   tutup permanen belum tersaring.
5. Pesantren belum menjadi lapisan tersendiri.
6. **Warung dan toko kelontong tidak tercakup.** Gerai informal penjual rokok jauh lebih
   banyak dan tidak tersedia pada sumber POI mana pun; diperlukan survei lapangan.
7. Google Places bukan sensus; *capture–recapture* menaksir populasi dari dua sumber yang
   sama-sama tidak lengkap, dengan asumsi ketertangkapan setara yang kemungkinan dilanggar.

---

## 5. Kesimpulan

*(Ringkas: skala keterpaparan; ketidaklengkapan POI di Indonesia bersifat besar dan
terstruktur; anjuran memakai penyebut sisi terpapar dan memverifikasi kelengkapan; seluruh
angka merupakan batas bawah.)*

## Ucapan Terima Kasih · Ketersediaan Data

Kode dan data olahan tersedia terbuka pada `github.com/firmanhadi21/food-store-master`;
peta interaktif pada `firmanhadi21.github.io/atlas-ruang-publik/`. Data turunan OpenStreetMap
tunduk pada ODbL 1.0. Titik gerai bersumber Google Places tidak diterbitkan ulang sesuai
ketentuan layanannya; statistik turunan dilaporkan.

---

## Catatan Penyunting — yang masih harus dikerjakan

**Menghambat submit:**

1. **Tinjauan pustaka belum ditulis.** Perlu: pengendalian tembakau Indonesia (Riskesdas/SKI,
   GATS), kepadatan ritel tembakau–inisiasi remaja, kelengkapan POI (Burgoine & Harrison 2013;
   Chen 2025, *Geographical Analysis*), studi serupa di Indonesia bila ada.
2. **Pilih jurnal sasaran** — format, panjang, dan bahasa mengikuti pedoman jurnal.
   Kandidat: *Jurnal Geodesi Undip*, *Majalah Ilmiah Globe* (BIG), *Jurnal Ilmiah Geomatika*,
   *GeoEco* (UNS), jurnal geografi UNNES.
3. **Selang kepercayaan** untuk estimasi Chapman (rumus varians baku tersedia).
4. **Peta hasil** — minimal: sebaran satuan pendidikan berdasarkan status radius, dan peta
   koroplet cakupan data per kecamatan (mendukung §3.2).

**Memperkuat:**

5. Ulangi pemanggilan Google dengan `places.businessStatus` (± US$8) untuk menyingkirkan gerai
   tutup.
6. *Geocoding* daftar satuan pendidikan Dapodik untuk menutup celah 76,4%.
7. Uji kepekaan: apakah kesimpulan berubah bila hanya kecamatan bercakupan tinggi dianalisis.
8. Pertimbangkan penulis pendamping dari FKM Undip untuk penguatan sisi kesehatan masyarakat.
