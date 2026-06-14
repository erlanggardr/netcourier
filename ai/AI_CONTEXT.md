# AI Context - NetCourier (Updated)

Kamu adalah AI coding assistant untuk project **NetCourier**.
Tujuanmu adalah membantu mengembangkan project sesuai arsitektur terbaru yang sudah beralih ke **Web-based UI** dengan performa tinggi.

---

## 1. Arsitektur Terkini (Modern Stack)

NetCourier telah bertransformasi dari Tkinter ke Web UI:
```txt
Browser (HTML/JS) <--> Web API Bridge (8080) <--> Gateway (9000) <--> Process Server S1/S2 (9101+)
```

- **Web UI**: Menggunakan Tailwind CSS, Vanilla JS, dan SSE-style polling untuk real-time updates.
- **Web API Bridge**: Bertindak sebagai jembatan HTTP-to-Socket. Mengelola `WebSession`, `GatewayConnection`, dan `RoomConnection`.
- **Gateway**: Auth, Session, PM Global, Load Balancing, Presence.
- **Process Server**: Room Chat, History, High-speed File Transfer, Admin Tools.

---

## 2. Fitur Utama yang Sudah Implement (Phase 1-9+)

- **High-Speed Transfer**: Menggunakan **1 MB chunks** (sebelumnya 64KB) dan **DB Batching** (commit setiap 10 chunk atau akhir transfer). Kecepatan mencapai **120+ MB/s** di localhost.
- **True Resume Transfer**: Mendukung penghentian dan kelanjutan upload/download dari potongan terakhir yang sukses menggunakan protokol `RESUME_TRANSFER` dan `file.slice()`.
- **Hybrid Upload Queue**: Antrean upload di Web UI dengan batas maksimal **2 transfer aktif** secara paralel untuk menjaga kestabilan bandwidth.
- **Admin Tools**: Fitur **Kick User** dan **Delete File** terintegrasi dengan verifikasi kepemilikan room (`created_by`).
- **Real-time UX**: 
  - **Emoji Reactions**: Tambah/Hapus reaksi pada pesan secara real-time.
  - **Typing Indicator**: Notifikasi "User is typing..." di dalam room.
  - **Member List Sidebar**: Daftar anggota room yang otomatis terupdate.
  - **Presence**: User online terdeteksi global segera setelah login (status `waiting`).

---

## 3. Aturan Teknis Penting (Non-Negotiable)

1. **Thread Safety**: Seluruh class koneksi (`GatewayConnection`, `RoomConnection`) **WAJIB** menggunakan `threading.Lock()` untuk memproteksi `pending_requests` karena Web API melayani permintaan secara concurrent.
2. **Web API Capacity**: Batas maksimal *request body* di `web_api/server.py` adalah **1024 MB (1GB)**. Jangan menurunkan batas ini karena akan merusak fitur upload file besar.
3. **Chunking Standard**: Gunakan **1 MB (1048576 bytes)** sebagai standar ukuran chunk di Client, Web API, dan Server.
4. **Database persistence**: Seluruh pesan room dan PM **WAJIB** disimpan ke SQLite sebelum di-broadcast.
5. **Protocol**: Tetap menggunakan **Length-Prefixed JSON Framing** (4 byte length header) untuk komunikasi socket.

---

## 4. Konteks Pengembangan Selanjutnya (Roadmap)

Tugas yang belum selesai dan menjadi prioritas AI selanjutnya:

1. **Read Receipts (Indikator Dibaca)**:
   - Tambahkan kolom `is_read` di tabel `room_messages`.
   - Implementasi event `ROOM_MESSAGE_READ` saat user menscroll pesan di Web UI.
2. **Chat History Search**:
   - Buat API di Web API untuk mencari konten chat menggunakan query `LIKE %query%`.
   - Tambahkan UI search bar di atas chat area.
3. **Web Dashboard Monitoring**:
   - Gunakan `psutil` di server untuk mengambil statistik CPU/RAM/Traffic.
   - Tampilkan grafik sederhana di Web UI untuk memantau kesehatan S1/S2.
4. **TLS/SSL Security**:
   - Implementasi `ssl.wrap_socket` untuk mengamankan data plaintext yang dikirim antar node.
5. **Dockerization**:
   - Buat `Dockerfile` untuk Gateway, Server, dan Web API.
   - Susun `docker-compose.yml` untuk menjalankan seluruh stack dengan satu perintah.

---

## 5. File Referensi Utama

- `common/constants.py`: Daftar lengkap `MESSAGE_TYPES` (Sekarang berupa Dictionary, bukan Set).
- `web_api/server.py`: Logika bridging HTTP ke Socket.
- `web_ui/app.js`: Logika `UploadQueue` dan `Real-time Polling`.
- `server/main.py`: Core logic Process Server & File Transfer.
- `tests/`: Gunakan `auto_binary_test.py` dan `test_transfer_controls.py` untuk verifikasi regresi.

---

## 6. Tips untuk AI Selanjutnya
- Jika menemukan **"Network Error"** saat upload, cek apakah ada *crash* di Web API (biasanya karena race condition atau batasan ukuran body).
- Selalu gunakan `taskkill /F /IM python.exe` sebelum melakukan restart layanan secara masal untuk menghindari port conflict.
- Database berada di `data/netcourier.db`. Skema awal ada di `migrations/001_init.sql`.
