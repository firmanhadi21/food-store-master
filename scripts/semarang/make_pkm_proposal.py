#!/usr/bin/env python3
"""
Generate the PKM proposal .docx, following the structure of
"Proposal PKM RKAT FT UNDIP Batch II 2025.docx" exactly.

Framing note: this is **Pengabdian Kepada Masyarakat**, not penelitian. The deliverable is a
service to a named partner institution (mitra), so the map and dashboard are framed as
*teknologi tepat guna* handed over with training, not as research findings.
"""


from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

TEMPLATE = ("/Users/firmanhadi/Teaching/UNDIP/Research/PKM/2025/"
            "Proposal PKM RKAT FT UNDIP Batch II 2025.docx")
OUT = ("/private/tmp/claude-501/-Users-firmanhadi-GitHub-food-store-master/"
       "b14aa1b5-a9d2-4493-9ae7-8fedf2296c2a/scratchpad/"
       "Proposal_PKM_Ritel_Tembakau_Sekolah_Semarang.docx")

JUDUL = ("PEMETAAN SEBARAN RITEL PRODUK TEMBAKAU TERHADAP RADIUS PERLINDUNGAN "
         "SATUAN PENDIDIKAN BERDASARKAN PP NO. 28 TAHUN 2024 DI KOTA SEMARANG")

# Reuse the template so styles (Heading 1..4, Body Text, Caption, Title) carry over.
# Keep the trailing sectPr — removing it strips page setup and Document.sections raises
# IndexError on save.
doc = Document(TEMPLATE)
from docx.oxml.ns import qn  # noqa: E402
for el in list(doc.element.body):
    if el.tag != qn("w:sectPr"):
        doc.element.body.remove(el)


def P(text="", style=None, bold=False, align=None, size=None):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    r.bold = bold
    if size:
        r.font.size = Pt(size)
    if align:
        p.alignment = align
    return p


def H(text, level):
    return doc.add_heading(text, level=level)


def TODO(text):
    """Mark something the author must supply. Deliberately visible."""
    p = doc.add_paragraph()
    r = p.add_run(f"[LENGKAPI: {text}]")
    r.bold = True
    return p


C = WD_ALIGN_PARAGRAPH.CENTER

# ------------------------------------------------------------------ cover
P("PROPOSAL PENGABDIAN KEPADA MASYARAKAT", align=C, bold=True, size=14)
P("HIBAH BERSAING DANA RKAT FAKULTAS TEKNIK UNDIP", align=C, bold=True, size=14)
P("BATCH II - TAHUN ANGGARAN 2026", align=C, bold=True, size=14)
P()
P(JUDUL, align=C, bold=True, size=13)
P()
P("KETUA:", align=C, bold=True)
TODO("Nama Ketua Pengabdian dan NIP")
P()
P("ANGGOTA DOSEN:", align=C, bold=True)
P("Dr. Firman Hadi, S.Si., MT.\tNIP. H.7.197512212021041001", align=C)
TODO("Anggota dosen lain — disarankan minimal satu dari Fakultas Kesehatan "
     "Masyarakat untuk penguatan sisi kesehatan publik")
P()
P("ANGGOTA MAHASISWA:", align=C, bold=True)
TODO("Nama dan NIM mahasiswa (2 orang). Mahasiswa berperan pada verifikasi "
     "lapangan dan penyusunan basis data")
P()
P("DEPARTEMEN TEKNIK GEODESI", align=C, bold=True)
P("FAKULTAS TEKNIK UNIVERSITAS DIPONEGORO", align=C, bold=True)
P("TAHUN 2026", align=C, bold=True)
doc.add_page_break()

# ------------------------------------------------------- halaman pengesahan
H("HALAMAN PENGESAHAN", 1)
P("PROPOSAL PENGABDIAN KEPADA MASYARAKAT", align=C, bold=True)
P()
rows = [
    ("Judul Pengabdian", JUDUL),
    ("Nama Mitra Pengabdian", "[LENGKAPI: Dinas Kesehatan Kota Semarang — disarankan; "
                              "lihat catatan pada Bab II]"),
    ("Ketua Pengabdian", ""),
    ("   Nama Lengkap", "[LENGKAPI]"),
    ("   NIP/NIDN", "[LENGKAPI]"),
    ("   Jabatan Fungsional", "[LENGKAPI]"),
    ("   Departemen", "Teknik Geodesi"),
    ("   Nomor HP", "[LENGKAPI]"),
    ("   Alamat e-mail", "[LENGKAPI]"),
    ("Anggota Tim", ""),
    ("   Jumlah Anggota Dosen", "[LENGKAPI] Orang"),
    ("   Mahasiswa terlibat", "2 Mahasiswa"),
    ("Lokasi Mitra Pengabdian", ""),
    ("   Kota", "Semarang"),
    ("   Provinsi", "Jawa Tengah"),
    ("Luaran Pengabdian", "Teknologi Tepat Guna"),
    ("Lama Pengabdian", "4 (empat) bulan"),
    ("Biaya Pengabdian", "Rp. 4.000.000,-"),
    ("Sumber Dana", "RKAT Fakultas Teknik UNDIP"),
]
t = doc.add_table(rows=len(rows), cols=3)
t.style = "Table Grid"
for i, (k, v) in enumerate(rows):
    t.rows[i].cells[0].text = k
    t.rows[i].cells[1].text = ":"
    t.rows[i].cells[2].text = v
P()
P("Semarang, [LENGKAPI tanggal] 2026")
P("Mengetahui,")
P("Ketua Departemen Teknik Geodesi\t\t\tKetua Pengabdian,")
P()
P("[LENGKAPI]\t\t\t\t\t[LENGKAPI]")
P()
P("Menyetujui,")
P("Dekan Fakultas Teknik UNDIP")
P()
P("[LENGKAPI]")
doc.add_page_break()

# ------------------------------------------------------------------ ringkasan
H("RINGKASAN", 1)
P(JUDUL, align=C, bold=True)
P()
P("Peraturan Pemerintah Nomor 28 Tahun 2024, yang merupakan aturan pelaksana Undang-Undang "
  "Nomor 17 Tahun 2023 tentang Kesehatan, melarang penjualan produk tembakau dalam radius "
  "200 meter dan pengiklanannya dalam radius 500 meter dari satuan pendidikan. Ketentuan "
  "berbasis radius tersebut menuntut ketersediaan data spasial pada tingkat gerai, sedangkan "
  "data semacam itu belum tersedia bagi pemerintah daerah. Akibatnya, baik pemantauan "
  "kepatuhan maupun penetapan prioritas pengawasan belum dapat dilakukan secara terukur.",
  style="Body Text")
P("Kegiatan pengabdian kepada masyarakat ini menyediakan bagi mitra sebuah peta dan sistem "
  "informasi geospasial yang menunjukkan posisi gerai ritel produk tembakau terhadap kedua "
  "radius tersebut di seluruh wilayah Kota Semarang. Sistem disusun dari sumber data terbuka, "
  "kelengkapannya diverifikasi terhadap statistik resmi, dan disajikan dalam bentuk peta "
  "interaktif yang dapat diakses tanpa perangkat lunak khusus.", style="Body Text")
P("Hasil awal yang telah diperoleh menunjukkan bahwa dari 949 minimarket berjaringan yang "
  "terpetakan di Kota Semarang, sebanyak 79,6% berada di dalam radius 200 meter dari satuan "
  "pendidikan, dan 97,7% berada di dalam radius 500 meter. Median jarak satuan pendidikan ke "
  "minimarket terdekat adalah 210 meter, praktis berimpit dengan ambang yang diatur. Angka "
  "tersebut merupakan batas bawah, karena warung dan toko kelontong belum tercakup.",
  style="Body Text")
P("Luaran kegiatan berupa teknologi tepat guna, yaitu peta interaktif berbasis web, basis "
  "data spasial yang dapat diperbarui, dokumentasi teknis, serta pelatihan singkat bagi staf "
  "mitra agar sistem dapat dipelihara secara mandiri.", style="Body Text")
P()
P("Kata kunci : pengendalian tembakau; PP 28/2024; sistem informasi geografis; "
  "lingkungan ritel; satuan pendidikan; Kota Semarang", bold=True)
doc.add_page_break()

# ------------------------------------------------------------------ bab I
H("Pendahuluan", 1)
H("Analisis Situasi", 2)
P("Indonesia memiliki prevalensi merokok yang termasuk tertinggi di dunia dan merupakan satu "
  "dari sedikit negara yang belum menjadi pihak dalam WHO Framework Convention on Tobacco "
  "Control. Global Youth Tobacco Survey 2019 mencatat prevalensi merokok pada remaja sebesar "
  "19,2%, dengan prevalensi pada remaja laki-laki mencapai 38,3% (1). Survei Kesehatan "
  "Indonesia 2023 mencatat prevalensi pada kelompok usia 15–19 tahun sebesar 16,7%.",
  style="Body Text")
P("Sejumlah penelitian menunjukkan bahwa kepadatan gerai penjual produk tembakau di sekitar "
  "sekolah berhubungan dengan inisiasi merokok pada remaja (2)(3). Di Indonesia, kajian di "
  "Kabupaten Banyuwangi memetakan kepadatan penjual rokok di sekitar sekolah beserta "
  "penjualan kepada anak di bawah umur (4), sementara kajian pada empat kabupaten/kota "
  "mencatat 21.460 gerai ritel, 30,4% di antaranya menjual rokok, serta 13.660 iklan rokok "
  "luar ruang, dengan kepadatan yang meningkat seiring makin dekatnya jarak ke sekolah (5). "
  "Kajian-kajian tersebut menggunakan pendataan lapangan menyeluruh sehingga menghasilkan "
  "cakupan yang sangat baik, namun memerlukan sumber daya besar dan sulit diulang secara "
  "berkala.", style="Body Text")
P("Peraturan Pemerintah Nomor 28 Tahun 2024 yang ditetapkan pada 26 Juli 2024 mengubah "
  "kerangka pengendalian tembakau di Indonesia (6). Pasal 434 ayat (1) huruf e melarang "
  "penjualan produk tembakau dalam radius 200 meter dari satuan pendidikan dan tempat "
  "bermain anak, sedangkan ketentuan mengenai iklan menetapkan radius 500 meter. Penjelasan "
  "Pasal 518 ayat (1) mendefinisikan satuan pendidikan sebagai mencakup pendidikan anak usia "
  "dini, sekolah/madrasah, pesantren, dan perguruan tinggi.", style="Body Text")
P("Ketentuan berbasis radius hanya dapat diawasi apabila tersedia data posisi gerai dan "
  "posisi satuan pendidikan. Sampai saat ini Pemerintah Kota Semarang belum memiliki basis "
  "data semacam itu. Tanpa data tersebut, pengawasan hanya dapat dilakukan berdasarkan "
  "laporan atau kunjungan insidental, sehingga sulit menetapkan prioritas wilayah maupun "
  "mengukur perkembangan dari waktu ke waktu.", style="Body Text")
P("Perkembangan data geospasial terbuka membuka peluang untuk menyusun basis data tersebut "
  "dengan biaya jauh lebih rendah daripada pendataan lapangan menyeluruh. Namun data terbuka "
  "memiliki keterbatasan kelengkapan yang tidak merata antarwilayah, sehingga tidak dapat "
  "digunakan begitu saja. Kegiatan ini menempuh pendekatan dua lapis: posisi gerai diambil "
  "dari data terbuka, sedangkan kelengkapannya diverifikasi terhadap statistik resmi dan "
  "sumber independen, sehingga tingkat ketidaklengkapan diketahui dan dilaporkan, bukan "
  "diabaikan.", style="Body Text")

H("Tujuan Kegiatan", 2)
P("Kegiatan ini bertujuan:", style="Title")
doc.add_paragraph("Menyediakan basis data dan peta sebaran gerai ritel produk tembakau "
                  "terhadap radius 200 meter dan 500 meter dari satuan pendidikan di Kota "
                  "Semarang bagi mitra pengabdian.", style="List Paragraph")
doc.add_paragraph("Menyediakan sistem informasi geospasial berbasis web yang dapat diakses "
                  "dan diperbarui oleh mitra tanpa memerlukan perangkat lunak berbayar.",
                  style="List Paragraph")
doc.add_paragraph("Meningkatkan kemampuan staf mitra dalam memelihara dan memutakhirkan "
                  "basis data tersebut melalui pelatihan singkat.", style="List Paragraph")

H("Manfaat Kegiatan", 2)
P("Manfaat kegiatan pengabdian kepada masyarakat ini:", style="Title")
doc.add_paragraph("Mitra memperoleh dasar terukur untuk menetapkan prioritas wilayah "
                  "pengawasan pelaksanaan PP 28/2024.", style="List Paragraph")
doc.add_paragraph("Mitra memperoleh data awal (baseline) yang dapat dibandingkan pada "
                  "periode berikutnya untuk menilai perkembangan.", style="List Paragraph")
doc.add_paragraph("Tersedianya informasi terbuka mengenai lingkungan ritel di sekitar satuan "
                  "pendidikan yang dapat dimanfaatkan sekolah, orang tua, dan masyarakat.",
                  style="List Paragraph")
doc.add_paragraph("Mahasiswa memperoleh pengalaman penerapan sistem informasi geografis pada "
                  "permasalahan kesehatan masyarakat.", style="List Paragraph")
doc.add_page_break()

# ------------------------------------------------------------------ bab II
H("Target dan Luaran", 1)
H("Target Kegiatan", 2)
P("Target dari kegiatan pengabdian kepada masyarakat ini adalah "
  "[LENGKAPI: Dinas Kesehatan Kota Semarang], sebagai instansi yang menyelenggarakan "
  "pengawasan Kawasan Tanpa Rokok dan pelaksanaan ketentuan pengendalian produk tembakau di "
  "wilayah Kota Semarang.", style="Title")
P()
P("Catatan pemilihan mitra: Dinas Kesehatan Kota Semarang disarankan karena kewenangan "
  "pengawasan berada padanya dan keluaran kegiatan langsung dapat digunakan. Alternatif yang "
  "dapat dipertimbangkan adalah Dinas Pendidikan Kota Semarang, apabila penekanan diarahkan "
  "pada perlindungan lingkungan sekolah, atau Bapelitbangda Kota Semarang apabila keluaran "
  "hendak diintegrasikan ke dalam sistem satu data daerah. Kesediaan mitra perlu dipastikan "
  "sebelum pengajuan karena surat persetujuan mitra menjadi Lampiran A.", style="Body Text")

H("Luaran Kegiatan", 2)
P("Luaran dari kegiatan pengabdian ini adalah:", style="Title")
doc.add_paragraph("Teknologi tepat guna berupa peta interaktif berbasis web yang menampilkan "
                  "sebaran gerai ritel produk tembakau terhadap radius 200 meter dan 500 "
                  "meter dari satuan pendidikan di Kota Semarang, dapat diakses melalui "
                  "peramban tanpa perangkat lunak khusus.", style="List Paragraph")
doc.add_paragraph("Basis data spasial satuan pendidikan dan gerai ritel dalam format terbuka "
                  "(GeoJSON dan CSV) beserta metadata dan catatan tingkat kelengkapannya.",
                  style="List Paragraph")
doc.add_paragraph("Dokumentasi teknis dan prosedur pemutakhiran data, serta pelatihan "
                  "singkat bagi staf mitra.", style="List Paragraph")
doc.add_paragraph("Publikasi ilmiah pada jurnal nasional terakreditasi SINTA.",
                  style="List Paragraph")
doc.add_page_break()

# ------------------------------------------------------------------ bab III
H("Metode Pelaksanaan", 1)
H("Permasalahan Target Kegiatan", 2)
P("Mitra menghadapi satu permasalahan pokok: ketentuan radius pada PP 28/2024 tidak dapat "
  "diawasi tanpa data posisi gerai dan satuan pendidikan, sedangkan pendataan lapangan "
  "menyeluruh atas seluruh wilayah kota memerlukan sumber daya yang tidak tersedia. "
  "Kegiatan ini menjawab permasalahan tersebut melalui penyusunan basis data dari sumber "
  "terbuka yang **kelengkapannya diukur dan dilaporkan**, sehingga mitra mengetahui sejauh "
  "mana data dapat dipercaya dan pada bagian mana diperlukan verifikasi lapangan.",
  style="Title")

H("Tahapan Kegiatan", 2)
H("Pengumpulan Data", 3)
P("Kegiatan dilaksanakan di seluruh wilayah Kota Semarang, meliputi 16 kecamatan dengan luas "
  "sekitar 373,8 km². Data yang digunakan mencakup:", style="Body Text")
for lbl, desc in [
    ("Data gerai ritel",
     "Overture Maps Places dan OpenStreetMap sebagai sumber posisi, dilengkapi layanan peta "
     "pihak ketiga untuk verifikasi kelengkapan. Gerai berjaringan (minimarket) dapat "
     "diidentifikasi dari nama merek, sedangkan warung dan toko kelontong memerlukan "
     "verifikasi lapangan."),
    ("Data satuan pendidikan",
     "OpenStreetMap dan basis data fasilitas pendidikan Direktorat Jenderal Kependudukan dan "
     "Pencatatan Sipil, dengan verifikasi jumlah terhadap data terbitan Dapodik Kementerian "
     "Pendidikan Dasar dan Menengah. Cakupan mengikuti definisi pada Penjelasan Pasal 518 "
     "ayat (1) PP 28/2024, yaitu PAUD, sekolah/madrasah, pesantren, dan perguruan tinggi."),
    ("Data batas wilayah",
     "Batas administrasi Kota Semarang dan batas kecamatan untuk keperluan agregasi."),
    ("Data verifikasi lapangan",
     "Pengamatan langsung pada sejumlah kelurahan terpilih untuk mengukur tingkat "
     "ketidaklengkapan data terbuka, khususnya pada gerai informal."),
]:
    p = doc.add_paragraph(style="List Paragraph")
    p.add_run(f"{lbl}. ").bold = True
    p.add_run(desc)

H("Tahapan Analisis", 3)
H("Penyusunan Basis Data", 4)
P("Data dari berbagai sumber digabungkan dengan memperhatikan dua hal yang khas pada konteks "
  "Indonesia. Pertama, klasifikasi jenis gerai dilakukan berbasis nama karena kategori pada "
  "data terbuka kurang dapat diandalkan di wilayah ini. Kedua, penghapusan duplikat "
  "memperhatikan kebiasaan gerai berjaringan yang kerap berlokasi berhadapan langsung, "
  "sehingga penggabungan hanya berdasarkan jarak akan meleburkan dua gerai berbeda menjadi "
  "satu.", style="Body Text")

H("Verifikasi Kelengkapan Data", 4)
P("Tahap ini merupakan pembeda utama kegiatan ini dan menentukan sejauh mana keluaran dapat "
  "dipercaya oleh mitra. Kelengkapan diukur melalui dua cara. Pertama, jumlah gerai "
  "berjaringan diestimasi dengan metode capture–recapture memanfaatkan dua sumber yang saling "
  "bebas. Kedua, jumlah satuan pendidikan dibandingkan terhadap jumlah terbitan Dapodik. "
  "Hasil verifikasi dilaporkan secara terbuka, termasuk apabila menunjukkan bahwa data masih "
  "jauh dari lengkap.", style="Body Text")

H("Analisis Radius", 4)
P("Untuk setiap satuan pendidikan dihitung jumlah gerai yang berada dalam radius 200 meter "
  "dan 500 meter, serta jarak ke gerai terdekat. Dua ukuran dilaporkan, yaitu proporsi gerai "
  "yang berada di dalam radius, dan proporsi satuan pendidikan yang memiliki gerai di dalam "
  "radius. Ukuran kedua dijadikan ukuran utama karena lebih peka terhadap kelengkapan data "
  "dan lebih relevan bagi kebijakan, yakni menyatakan berapa banyak satuan pendidikan yang "
  "berada dalam kondisi yang diatur.", style="Body Text")

H("Verifikasi Lapangan", 4)
P("Verifikasi dilakukan pada beberapa kelurahan terpilih yang mewakili gradien kepadatan, "
  "dari pusat kota hingga wilayah pinggiran. Mahasiswa melakukan pengamatan langsung untuk "
  "mengukur selisih antara data terbuka dan keadaan sebenarnya, khususnya pada warung dan "
  "toko kelontong. Hasilnya digunakan sebagai faktor koreksi dan sebagai dasar rekomendasi "
  "kepada mitra mengenai wilayah yang memerlukan pendataan lanjutan.", style="Body Text")

H("Penyusunan Sistem dan Serah Terima", 4)
P("Keluaran disajikan sebagai peta interaktif berbasis web yang dapat diakses melalui "
  "peramban. Sistem dirancang agar dapat dipelihara oleh mitra: data disimpan dalam format "
  "terbuka, prosedur pemutakhiran didokumentasikan, dan seluruh kode sumber disediakan "
  "secara terbuka. Kegiatan ditutup dengan pelatihan singkat bagi staf mitra mengenai "
  "penggunaan dan pemutakhiran sistem.", style="Body Text")
P("Peta menyajikan jarak, bukan penilaian hukum. Penetapan pelanggaran merupakan kewenangan "
  "instansi berwenang. Agregasi disajikan pada tingkat kecamatan dan tidak ditujukan untuk "
  "menunjuk pelaku usaha tertentu.", style="Body Text")

H("Pembagian Tugas", 4)
P("Ketua Tim: koordinasi kegiatan, komunikasi dengan mitra, serta pelaporan.",
  style="Body Text")
P("Anggota Dosen (Firman Hadi): penyusunan basis data spasial, verifikasi kelengkapan, "
  "analisis radius, dan pengembangan sistem berbasis web.", style="Body Text")
TODO("Pembagian tugas anggota dosen lain")
P("Mahasiswa: verifikasi lapangan, pengumpulan data pendukung, dan penyusunan dokumentasi.",
  style="Body Text")
doc.add_page_break()

# ------------------------------------------------------------------ bab IV
H("BIAYA DAN JADWAL PENGABDIAN", 1)
H("Anggaran Biaya", 2)
P(f"Komponen biaya kegiatan pengabdian kepada masyarakat dengan judul “{JUDUL}” "
  "dapat dilihat pada Tabel IV.1 dan Lampiran B.", style="Body Text")
P("Tabel IV.1 Ringkasan Anggaran Belanja", style="Caption")
budget = [
    ("I", "BELANJA HONORARIUM", "216.000"),
    ("II", "BELANJA OPERASIONAL", "384.000"),
    ("III", "BELANJA NON OPERASIONAL", "1.400.000"),
    ("IV", "BELANJA PERJALANAN", "2.000.000"),
    ("", "TOTAL", "4.000.000"),
]
tb = doc.add_table(rows=len(budget) + 1, cols=3)
tb.style = "Table Grid"
tb.rows[0].cells[0].text = "NO"
tb.rows[0].cells[1].text = "KOMPONEN"
tb.rows[0].cells[2].text = "JUMLAH (Rp)"
for i, (no, k, v) in enumerate(budget, start=1):
    tb.rows[i].cells[0].text = no
    tb.rows[i].cells[1].text = k
    tb.rows[i].cells[2].text = v
P()
P("Belanja perjalanan dialokasikan terutama untuk verifikasi lapangan pada kelurahan "
  "terpilih dan koordinasi dengan mitra. Belanja non operasional mencakup penggandaan "
  "laporan, bahan pelatihan, dan biaya layanan data. Rincian disajikan pada Lampiran B.",
  style="Body Text")
TODO("Sesuaikan rincian anggaran dengan pagu dan standar biaya yang berlaku")

H("Jadwal Kegiatan", 2)
P(f"Kegiatan pengabdian kepada masyarakat dengan judul “{JUDUL}” akan dilaksanakan "
  "selama 4 (empat) bulan.", style="Title")
P("Tabel IV.2 Jadwal Kegiatan", style="Caption")
acts = ["Studi literatur dan korespondensi mitra",
        "Pengumpulan data sekunder",
        "Penyusunan basis data spasial",
        "Verifikasi kelengkapan data",
        "Verifikasi lapangan",
        "Pengembangan sistem berbasis web",
        "Pelatihan dan serah terima kepada mitra",
        "Pelaporan dan penyusunan publikasi"]
tj = doc.add_table(rows=len(acts) + 1, cols=5)
tj.style = "Table Grid"
hdr = ["KEGIATAN", "Bulan 1", "Bulan 2", "Bulan 3", "Bulan 4"]
for j, h in enumerate(hdr):
    tj.rows[0].cells[j].text = h
for i, a in enumerate(acts, start=1):
    tj.rows[i].cells[0].text = a
doc.add_page_break()

# ------------------------------------------------------------------ pustaka
H("DAFTAR PUSTAKA", 1)
refs = [
 "Tobacco advertising, promotion, sponsorship and youth smoking behavior: The Indonesian 2019 "
 "Global Youth Tobacco Survey (GYTS). Tobacco Induced Diseases. 2023.",
 "Marsh L, Vaneckova P, Robertson L, Johnson TO, Doscher C, Raskind IG, et al. Association "
 "between density and proximity of tobacco retail outlets with smoking: A systematic review "
 "of youth studies. Health & Place. 2021;67:102275.",
 "Finan LJ, Lipperman-Kreda S, Abadi M, Grube JW, Kaner E, Balassone A, et al. Tobacco Outlet "
 "Density and Smoking Among Young People: A Systematic Methodological Review. Nicotine & "
 "Tobacco Research. 2021;23(2):239–48.",
 "Density of cigarette retailers near schools and sales to minors in Banyuwangi, Indonesia: "
 "A GIS mapping. Tobacco Induced Diseases. 2020;18:07.",
 "Exposure to outdoor cigarette advertisements and cigarette retailers near Indonesian "
 "schools: Density, proximity, and students' self-report of exposure. Tobacco Prevention & "
 "Cessation. 2024.",
 "Republik Indonesia. Peraturan Pemerintah Nomor 28 Tahun 2024 tentang Peraturan Pelaksanaan "
 "Undang-Undang Nomor 17 Tahun 2023 tentang Kesehatan. Jakarta; 2024.",
 "Astuti PAS, Assunta M, Freeman B. Is Youth Smoking Related to the Density and Proximity of "
 "Outdoor Tobacco Advertising Near Schools? Evidence from Indonesia. International Journal of "
 "Environmental Research and Public Health. 2021;18(5):2556.",
 "Burgoine T, Harrison F. Comparing the accuracy of two secondary food environment data "
 "sources in the UK across socio-economic and urban/rural divides. International Journal of "
 "Health Geographics. 2013;12:2.",
 "Chen X, et al. Assessing the Validity of OpenStreetMap for Food Environment Research. "
 "Geographical Analysis. 2025.",
 "Barrington-Leigh C, Millard-Ball A. The world's user-generated road map is more than 80% "
 "complete. PLOS ONE. 2017;12(8):e0180698.",
]
for i, r in enumerate(refs, start=1):
    doc.add_paragraph(f"{i}.\t{r}")
TODO("Lengkapi nama penulis pada rujukan 1, 4, 5, dan 9 — belum diverifikasi dari naskah asli")
doc.add_page_break()

# ------------------------------------------------------------------ lampiran
H("LAMPIRAN A : PERSETUJUAN MITRA PENGABDIAN", 1)
TODO("Surat persetujuan mitra. Perlu dikomunikasikan dan diperoleh sebelum pengajuan")
doc.add_page_break()
H("LAMPIRAN B : Justifikasi Anggaran Pengabdian", 1)
TODO("Rincian anggaran sesuai standar biaya yang berlaku")
doc.add_page_break()
H("LAMPIRAN C : STRUKTUR ORGANISASI TIM PELAKSANA DAN PEMBAGIAN TUGAS", 1)
P("Koordinator kegiatan dan komunikasi mitra\t: [LENGKAPI]")
P("Koordinator basis data dan sistem\t\t: Dr. Firman Hadi, S.Si., M.T.")
P("Koordinator verifikasi lapangan\t\t: [LENGKAPI]")
P("Koordinator pelaporan dan publikasi\t\t: [LENGKAPI]")
doc.add_page_break()
H("LAMPIRAN D : BIODATA KETUA PENGABDIAN MASYARAKAT", 1)
TODO("Biodata ketua")

doc.save(OUT)
print(f"wrote: {OUT}")
