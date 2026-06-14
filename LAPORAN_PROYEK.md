# Laporan Proyek Akhir: NetCourier

## 1. Pendahuluan
### 1.1 Latar Belakang
Dalam era digitalisasi, aplikasi komunikasi waktu nyata (*real-time communication*) seperti *chat room* dan berbagi berkas (*file sharing*) menjadi kebutuhan fundamental. Tantangan utama dalam membangun sistem komunikasi terdistribusi adalah memastikan skalabilitas, keandalan pengiriman data (*reliability*), dan performa yang optimal ketika menangani banyak koneksi konkuren serta transfer berkas berukuran besar.

Sebagai pemenuhan tugas akhir mata kuliah Pemrograman Jaringan, proyek **NetCourier** dikembangkan. NetCourier adalah sebuah aplikasi *Multi-Chat Room* berbasis arsitektur *client-server* terdistribusi yang memanfaatkan protokol TCP (*Transmission Control Protocol*) pada *layer* transport. Pemilihan TCP didasarkan pada karakteristiknya yang berorientasi koneksi (*connection-oriented*), menjamin pengurutan data (*ordered*), dan mencegah kehilangan paket (*lossless*), yang sangat esensial untuk transfer berkas agar tidak terjadi korupsi data.

### 1.2 Ruang Lingkup
Fokus pengembangan NetCourier mencakup perancangan protokol kustom tingkat aplikasi, implementasi arsitektur jaringan yang dapat mendistribusikan beban (*Load Balancing*), serta mekanisme *Reliable File Transfer* yang dioptimasi pada lingkungan *socket programming* dasar tanpa bergantung pada *framework web* tingkat tinggi.

## 2. Deskripsi dan Tujuan Project
### 2.1 Deskripsi Umum
**NetCourier** adalah platform komunikasi hibrida yang memfasilitasi dua mode interaksi utama:
1. **Komunikasi Global:** Memungkinkan pengguna untuk saling berkirim pesan secara privat (*Private Message*), melihat daftar pengguna daring, dan mencari *room*, yang tetap berjalan secara asinkronus meskipun pengguna sedang tergabung di dalam *room* tertentu.
2. **Komunikasi Terisolasi (*Room*):** Menyediakan ruang obrolan (*chat room*) di mana banyak pengguna dapat saling mengirim pesan *broadcast* dan melakukan aktivitas transfer berkas (*upload* dan *download*).

### 2.2 Tujuan Proyek
Tujuan utama pengembangan proyek ini terbagi menjadi dua aspek:

**A. Aspek Fungsional (Memenuhi Spesifikasi Wajib)**
- Mengimplementasikan sistem Autentikasi (Registrasi, Login, Logout) dengan keamanan penyimpanan kata sandi (*hashing*).
- Menyediakan fungsionalitas *Room Management* (Create, Join, Leave, Room List).
- Mengimplementasikan perpesanan mencakup *Broadcast Message* dalam *room* dan *Private Message* antar-individu yang didukung oleh riwayat obrolan (*chat history*).
- Menyediakan pemantauan kehadiran pengguna (*Online User List*).

**B. Aspek Non-Fungsional (Fitur Pembeda dan Kinerja)**
- Merancang arsitektur sistem terdistribusi untuk memisahkan beban *routing* pesan ringan dari lalu lintas data berat (berkas).
- Mengimplementasikan *Reliable File Transfer* dengan teknik segmentasi (*chunking*), validasi integritas data (SHA-256), pelaporan progres transfer, dan kapabilitas *resume* transfer yang terputus.
- Menghasilkan aplikasi yang mampu lolos dari pengujian beban (*load test*), memiliki latensi rendah, dan *throughput* berkas yang mendekati kecepatan disk asli (*native*).

## 3. Arsitektur Sistem
Untuk menghindari *single point of failure* dan kemacetan jaringan (*bottleneck*), NetCourier mengadopsi pola **Distributed Client-Server Architecture** yang didegregasikan menjadi tiga komponen operasional utama.

### 3.1 Web Client & API Bridge
NetCourier menghindari pembuatan GUI *desktop* murni demi fleksibilitas, menggunakan antarmuka *Single Page Application* (SPA) berbasis HTML, CSS, dan JavaScript (*Vanilla*).
- **Web API Bridge (`web_api/server.py`):** Bertindak sebagai *middleware* yang menerjemahkan permintaan HTTP (REST API dan asinkronus *Long-Polling* `/api/events`) dari peramban menjadi paket TCP kustom. *Bridge* ini memelihara kumpulan *socket* (koneksi) TCP aktif untuk setiap sesi pengguna secara terus-menerus.

### 3.2 Gateway Server (`gateway/main.py`)
Gateway adalah titik masuk utama (pintu gerbang) bagi semua koneksi klien yang mengelola aspek manajerial (*Control Plane*). Tanggung jawab Gateway meliputi:
- **Autentikasi & Sesi:** Memvalidasi kredensial pengguna, mengeluarkan *session token*, dan menangani konflik duplikasi *login*.
- **Global Presence & Routing:** Mengelola daftar siapa yang daring dan meneruskan *Private Message* antarpengguna tanpa memperdulikan di server mana mereka berada.
- **Load Balancing & Room Directory:** Saat pengguna membuat *room* baru, Gateway menghitung beban tiap Process Server (berdasarkan jumlah koneksi dan transfer aktif). Gateway menggunakan algoritma nilai (*score-based*) untuk memilih server yang paling lengang.
- **Room Affinity:** Gateway memastikan bahwa semua pengguna yang masuk ke *room* tertentu selalu dialokasikan ke Process Server yang sama untuk menjaga konsistensi state percakapan dan kepemilikan berkas (tersimpan di disk fisik server tersebut).

### 3.3 Process Server / Data Node (`server/main.py`)
Merupakan simpul pekerja (*worker node*) di *Data Plane* yang menangani koneksi intensif. NetCourier dapat menjalankan banyak instansi Process Server (misalnya S1, S2, dst.).
- **Komunikasi Internal Room:** Menerima koneksi dari pengguna yang telah diarahkan oleh Gateway. Memproses *broadcast chat*, memberikan riwayat *chat*, dan melacak keanggotaan.
- **File Transfer Engine:** Melayani operasi I/O berat untuk mengunggah dan mengunduh berkas. Setiap Process Server menyimpan berkas fisiknya pada direktori lokal penyimpanan mereka sendiri (misal: `storage/S1/rooms/...`).

### 3.4 Skema Komunikasi Internal
Process Server dan Gateway juga saling terhubung via *Control Channel* TCP. Process Server secara berkala mengirimkan paket `HEARTBEAT` ke Gateway. Jika Gateway tidak menerima detak jantung dalam 15 detik, Process Server akan ditandai sebagai `down` dan trafik tidak akan diarahkan ke sana.

## 4. Desain Protokol Aplikasi
Mengingat sifat aliran (*stream*) TCP yang tidak memiliki batas paket yang jelas, NetCourier mendesain protokol pembingkaian paket khusus (*custom length-prefixed packet framing*) untuk mencegah masalah TCP *粘包* (paket menempel / *TCP stream fragmentation*).

### 4.1 Struktur Bingkai (*Packet Framing*)
Setiap transmisi data memiliki format biner sebagai berikut:
1. **Header Length (4 bytes):** Bilangan bulat tak bertanda (*unsigned int*) dalam format *Big-Endian* yang mengindikasikan ukuran *Header* JSON.
2. **JSON Header (n bytes):** Teks UTF-8 berisi metadata *request* seperti `type`, `request_id`, dan `payload` kustom.
3. **Binary Length (4 bytes, Opsiional):** Bilangan bulat ukuran *payload* biner. Hanya dikirim jika `type` berkaitan dengan transfer data biner.
4. **Binary Data (m bytes, Opsional):** Data *byte* mentah (misal: isi dari satu *chunk* berkas).

### 4.2 Alur Reliable File Transfer
Alih-alih memuat seluruh berkas ke RAM, NetCourier memecah berkas (hingga ukuran 1 GB) menjadi *chunks* kecil (misal: 1 MB per *chunk*).
1. **Inisiasi (`UPLOAD_INIT`):** Klien mengirim metadata (nama, ukuran, ukuran *chunk*). Server menyiapkan entri di basis data, menyentuh (membuat) berkas kosong di disk, lalu membalas dengan status `UPLOAD_READY` beserta *transfer ID*.
2. **Transmisi Pararel (`UPLOAD_CHUNK`):** Klien (melalui *Worker Web UI*) mengunggah hingga 4 *chunk* berbeda secara bersamaan. Paket biner dikirim menggunakan desain protokol di atas.
3. **Konfirmasi (`CHUNK_ACK`):** Server merespons setiap *chunk* yang berhasil ditulis ke disk, memungkinkan klien memperbarui *progress bar*.
4. **Penyelesaian (`UPLOAD_FINISH`):** Setelah seluruh *chunk* terkirim, klien mengirim sinyal penyelesaian. Server kemudian membaca kembali berkas di disk, menghitung *hash* SHA-256, dan mencocokkannya dengan *hash* asli dari klien. Jika cocok, status diubah menjadi `available`.

Fitur **Resume Transfer** memanfaatkan basis data relasional. Jika klien terputus saat mengunduh berkas besar, klien yang menyambung ulang dapat mengirim paket `RESUME_TRANSFER` yang akan merespons daftar indeks *chunk* yang belum diterima, menghemat penggunaan pita lebar (*bandwidth*).

## 5. Pengujian Performa dan Beban Server
Untuk memvalidasi ketahanan arsitektur dan efisiensi implementasi transfer, dilakukan dua jenis pengujian menggunakan *script* automasi `tests/load_test.py` dan `tests/throughput_test.py`.

**A. Metodologi Latency Test**
- **Skenario:** Menstimulasi sejumlah klien (5 hingga 30) yang terkoneksi secara paralel. Setiap klien mengirim rentetan paket *PING* dan pesan *broadcast* ringan secara berulang.
- **Tujuan:** Mengukur waktu respon (RTT - *Round Trip Time*) Gateway dan Process Server dalam mengurai dan memproses antrean pesan JSON secara asinkron.

**B. Metodologi Throughput Test**
- **Skenario:** Pengujian terisolasi transfer berkas ukuran variatif (1 MB, 10 MB, dan spesifik 1 GB) di lingkungan jaringan *localhost*.
- **Tujuan:** Mengetahui efisiensi I/O disk dan jaringan untuk mencapai rasio MegaBytes per detik (MB/s) setinggi mungkin.

## 6. Hasil dan Analisis
### 6.1 Hasil Uji Beban dan Latensi (Latency Benchmarks)
| Concurrent Clients | Total Requests | Rata-rata Latensi | Persentil ke-95 | Latensi Minimum | Latensi Maksimum |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 5 | 20 | **10.20 ms** | 56.36 ms | 0.10 ms | 56.52 ms |
| 10 | 40 | **10.21 ms** | 56.71 ms | 0.11 ms | 61.62 ms |

**Analisis:** Arsitektur yang memisahkan *Gateway* dan *Process Server* terbukti sangat efektif. Dapat dilihat bahwa peningkatan jumlah klien (dari 5 ke 10) nyaris tidak mempengaruhi latensi rata-rata yang stabil di angka 10 ms. Sistem tidak mengalami degradasi performa (*bottleneck*) untuk pemrosesan JSON.

### 6.2 Hasil Uji Kecepatan Transfer (Throughput Benchmarks)
| Ukuran Berkas | Waktu Eksekusi | Throughput Rata-rata | Status Integritas (SHA-256) |
|:---:|:---:|:---:|:---:|
| 1 MB | 0.07 detik | 14.66 MB/s | Valid |
| 10 MB | 0.76 detik | 13.09 MB/s | Valid |
| **1024 MB (1 GB)** | 13.00 detik | **78.78 MB/s** | Valid |

**Analisis:**
Sistem berhasil menangani transfer berkas masif sebesar 1 GB dalam waktu ~13 detik. Angka kecepatan **78.78 MB/s** sangat memuaskan untuk operasi *socket I/O* di lapisan aplikasi. Keberhasilan ini diatributkan pada beberapa optimasi krusial yang diuraikan di bab selanjutnya.

### 6.3 Evaluasi Keamanan dan Keandalan
- **Packet Sanitization:** Server menolak muatan (*payload*) yang cacat secara bentuk (*Malformed JSON*) atau melewati batas toleransi memori (>20MB) tanpa menyebabkan *crash* pada *thread* utama.
- **Path Traversal Protection:** Celah keamanan pengunggahan file berhasil ditangani. Karakter direktori relatif seperti `../` dibersihkan dari nama berkas, mengunci berkas di *folder storage* masing-masing *room*.
- **Rate Limiting:** Pengiriman spam secara cepat pada fungsionalitas obrolan (*chat*) langsung ditahan (diblokir) oleh *buffer* pencegah *flooding*.

## 7. Kendala dan Solusi
Selama siklus pengembangan, ditemukan beberapa tantangan teknis kompleks yang membutuhkan optimasi aras bawah (*low-level optimization*):

1. **Memory Bloating & OOM Killed pada HTTP Bridge**
   - *Masalah:* Klien web mengirim *chunk* berkas berupa representasi teks Base64 atau dibungkus utuh sebagai string JSON. Hal ini menyebabkan HTTP API Server (*Bridge*) harus melakukan dekode UTF-8 yang rakus memori. Pada berkas sangat besar, sistem kehabisan memori.
   - *Solusi:* Memisahkan format data. Protokol direvisi untuk memiliki *Header* (JSON) dan *Body* (Binary Raw). Di sisi *Bridge*, antarmuka HTTP REST API dirancang untuk menerima transfer dalam bentuk *multipart/form-data* (khusus biner), dan menjembataninya langsung ke *Socket Stream* Process Server tanpa proses pembongkaran (dekode teks) UTF-8.

2. **Batasan Throughput di Localhost akibat Nagle's Algorithm**
   - *Masalah:* Meskipun jaringan *localhost* tidak berbatas secara fisik, kecepatan transfer awal sangat rendah (tersendat setiap 40ms). Hal ini terjadi karena mekanisme *Delayed ACK* dan *Nagle's Algorithm* bawaan sistem operasi pada protokol TCP yang mencoba melakukan *buffer* data kecil.
   - *Solusi:* Menonaktifkan Nagle's Algorithm secara eksplisit di semua instansi *socket* (baik klien maupun server) menggunakan perintah konfigurasi `socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)`. Hasilnya, latensi respons berkurang drastis, memungkinkan *throughput* mencapai 78+ MB/s.

3. **Race Condition akibat Pengunggahan Chunk Paralel**
   - *Masalah:* Karena *Client Web UI* memaksimalkan pita lebar dengan mengunggah 4 *chunk* berbarengan (asinkron), urutan paket yang tiba di Process Server menjadi tidak teratur (*Out-Of-Order*). Menggunakan perintah *append* sederhana berakibat pada berkas yang korup.
   - *Solusi:* Server dikonfigurasi menggunakan mode penulisan raw biner ganda (`r+b`). Setiap *chunk* di dalam protokol menyertakan meta-informasi nilai *offset byte*-nya. Server mengeksekusi instruksi penyelarasan kursor `file.seek(offset)` sebelum memanggil `file.write()`. Ini menjamin *chunk* diletakkan pada posisi absolut yang benar terlepas dari urutan kedatangannya, memungkinkan paralelisasi dengan aman.

4. **Kegagalan Memuat Riwayat Chat (Room History) Akibat Batas Header**
   - *Masalah:* Pada ruangan yang sangat aktif dengan banyak pesan dan reaksi emoji, respon `ROOM_HISTORY_RESPONSE` sering kali gagal dimuat. Setelah didiagnosa, ditemukan bahwa ukuran JSON *header* melebihi batas *sanity check* awal sebesar 64KB, sehingga klien menganggap paket tersebut sebagai pelanggaran protokol (*Protocol Violation*).
   - *Solusi:* Menaikkan batas toleransi *header* biner menjadi 1MB secara global di `common/protocol.py` (sesuai konstanta `MAX_HEADER_SIZE`). Selain itu, dilakukan implementasi `encodeURIComponent` pada sisi klien JS untuk menangani nama ruangan yang mengandung spasi agar tidak memutus jalur *parsing* URL pada Web API Server.

5. **Ketidaksinkronan Daftar Pengguna (Online Users) Saat Logout**
   - *Masalah:* Daftar pengguna daring tidak segera diperbarui saat salah satu pengguna menekan tombol *Logout*. Pengguna tersebut tetap terlihat daring hingga terjadi *session timeout* (5 menit). Hal ini terjadi karena klien web hanya menghapus *state* lokal di peramban tanpa memutus hubungan secara formal ke *Gateway*.
   - *Solusi:* Dibuat *endpoint* baru `/api/logout` pada Web API *Bridge* yang secara eksplisit mengirimkan paket `LOGOUT` ke TCP *Gateway*. *Gateway* kemudian memicu fungsi `_cleanup_session` untuk mengubah status *presence* pengguna menjadi `offline` di basis data secara instan sebelum menutup *socket*.

## 8. Kesimpulan dan Saran
### 8.1 Kesimpulan
Proyek pengembangan **NetCourier** dapat dinyatakan berhasil memenuhi, bahkan melampaui seluruh indikator spesifikasi tugas Pemrograman Jaringan. Sistem bukan hanya mengimplementasikan fitur dasar aplikasi obrolan banyak ruang (*multi-chat room*), tetapi mendemonstrasikan perancangan arsitektur terdistribusi (*Gateway-Process Server*) yang efisien.

Algoritma pemilahan server (*Load Balancing*) dikombinasikan dengan afinitas ruangan (*Room Affinity*) secara efektif memastikan tidak terjadi *bottleneck*. Penerapan metode transfer data tersegmentasi (*chunking*), validasi integritas, pengabaian Nagle's Algorithm, serta isolasi alur data biner dari data UTF-8, terbukti menghasilkan performa transfer hingga nyaris 80 MB/s untuk menangani berkas berskala Gigabyte. 

### 8.2 Saran Pengembangan Ke Depan
Demi menyempurnakan kualitas perangkat lunak ini di skenario produksi publik, beberapa pembaruan diusulkan:
1. **Keamanan Lapisan Transportasi:** Mengintegrasikan sertifikat enkripsi asimetris SSL/TLS (*Transport Layer Security*) yang melapisi pembungkus *Socket* agar metadata pengguna, kata sandi, dan berkas privat terlindungi dari serangan intersepsi (*Packet Sniffing / Man-In-The-Middle*).
2. **Dashboard Administrasi Global:** Mengembangkan panel monitor antarmuka grafis atau Web Dasbor yang tersambung ke port observasi Gateway untuk menyajikan data *real-time* utilitas *CPU*, pemakaian RAM, dan metrik jaringan setiap prosen *node*.
3. **Penyimpanan Objek Terpusat:** Beralih dari penyimpanan berkas lokal (per-*node*) menuju implementasi layanan kompatibel S3 (contoh: MinIO/AWS S3) untuk menghilangkan keharusan dependensi fisis antara *room* dengan Process Server tertentu, sehingga infrastruktur dapat disimulasikan sebagai *stateless container* penuh menggunakan Docker atau Kubernetes.