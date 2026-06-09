# Feature Specification - NetCourier

Dokumen ini menjelaskan cara kerja setiap fitur NetCourier secara detail.

---

## 1. Feature: Register

### Actor
Guest.

### Description
Guest membuat akun baru melalui Gateway.

### Normal Flow
1. Guest membuka aplikasi desktop Tkinter.
2. Guest mengisi form Register: username, password, dan display name.
3. Guest menekan tombol **Register**.
4. Client mengirim packet `REGISTER` ke Gateway.
5. Gateway validasi input.
6. Gateway hash password.
7. Gateway simpan user ke database.
8. Gateway membalas `REGISTER_OK`.

### Error Flow
- Username sudah digunakan -> `ERROR USERNAME_TAKEN`.
- Password terlalu pendek -> `ERROR INVALID_PASSWORD`.
- Username mengandung karakter berbahaya -> `ERROR INVALID_USERNAME`.

### Acceptance Criteria
- User baru tersimpan di database.
- Password tidak tersimpan plain text.
- Username duplikat ditolak.

---

## 2. Feature: Login

### Actor
Registered user.

### Description
User login melalui Gateway untuk mendapatkan session token.

### Normal Flow
1. User mengisi form Login pada aplikasi Tkinter dan menekan tombol **Login**.
2. Client mengirim `LOGIN`.
3. Gateway cek username dan password hash.
4. Gateway cek duplicate login.
5. Gateway membuat session token.
6. Gateway menyimpan session.
7. Gateway mengubah presence menjadi online/waiting.
8. Gateway membalas `LOGIN_OK`.

### Error Flow
- Username/password salah -> `ERROR INVALID_CREDENTIALS`.
- User sudah login -> `ERROR DUPLICATE_LOGIN`.
- Database error -> `ERROR INTERNAL_ERROR`.

### Output
- token,
- user_id,
- username,
- display_name.

---

## 3. Feature: Waiting Room / Global Area

### Actor
Authenticated user.

### Description
Setelah login, user berada di waiting room Gateway. Waiting room bukan room chat biasa, tetapi area global untuk PM, online user list, room list, create room, dan join room.

### Available UI Actions
- Melihat online user pada panel **Online Users**.
- Mengirim PM melalui panel **Private Message**.
- Membuka PM history melalui tombol **History**.
- Melihat room list pada panel **Rooms**.
- Membuat room melalui form **Create Room**.
- Join room melalui tombol **Join** pada room yang dipilih.
- Logout melalui tombol **Logout**.
- Membuka help dialog melalui menu **Help**.

### Acceptance Criteria
- User bisa PM tanpa join room.
- User bisa menerima PM saat belum join room.
- User bisa melihat daftar room dari Gateway.

---


---

## 3.1 Feature: Tkinter Client UI

### Actor
Authenticated user and guest.

### Description
NetCourier menggunakan desktop GUI berbasis Tkinter sebagai UI utama. User tidak menggunakan CLI/TUI untuk mengakses fitur client. UI menyediakan form login/register, waiting room, online user list, private message panel, room list, room chat panel, file list, upload/download controls, transfer progress, dan status bar.

### Normal Flow
1. User menjalankan `python client/main.py`.
2. Aplikasi membuka jendela Tkinter.
3. User login/register melalui form.
4. Setelah login, user masuk ke Waiting Room window/panel.
5. User dapat mengirim PM, melihat user online, membuat/join room.
6. Saat join room, UI menampilkan Room Chat panel tanpa memutus koneksi Gateway.
7. Receiver thread menerima event dari Gateway dan Process Server, lalu mengirim update ke UI melalui thread-safe queue.

### Acceptance Criteria
- Semua fitur user-facing tersedia melalui GUI.
- GUI tidak freeze saat menerima chat, PM, upload, atau download.
- Update dari socket thread tidak memanggil widget Tkinter secara langsung; semua update masuk melalui UI queue dan diproses oleh main thread Tkinter.
- File upload menggunakan file picker.
- Progress upload/download tampil dengan progress bar.

---

## 4. Feature: Global Private Message

### Actor
Authenticated user.

### Description
User dapat mengirim private message ke user lain melalui Gateway, baik sender/recipient sedang di waiting room maupun sedang berada di room Process Server.

### Normal Flow
1. Sender memilih user tujuan pada panel Online Users atau mengetik username tujuan di panel Private Message.
2. Sender mengetik pesan dan menekan tombol **Send PM**.
3. Client mengirim `PRIVATE_MESSAGE_SEND` ke Gateway.
4. Gateway validasi token sender.
5. Gateway validasi recipient ada.
6. Gateway menyimpan PM ke database.
7. Jika recipient online, Gateway mengirim `PRIVATE_MESSAGE_RECEIVED` ke socket Gateway milik recipient.
8. Gateway mengirim status `delivered` ke sender.
9. Jika recipient offline, Gateway menyimpan status `stored_offline`.

### Important Design Rule
Client yang sudah join room tetap menjaga koneksi ke Gateway. Karena itu, PM dari waiting room ke user di room tetap bisa masuk.

### Error Flow
- Recipient tidak ditemukan -> `ERROR USER_NOT_FOUND`.
- Message kosong -> `ERROR EMPTY_MESSAGE`.
- Sender terkena rate limit -> `ERROR RATE_LIMIT_EXCEEDED`.

### Acceptance Criteria
- PM dari waiting room ke user di room berhasil.
- PM antar user beda Process Server berhasil.
- PM history tersimpan.
- PM offline dapat dibaca setelah login.

---

## 5. Feature: Online User List

### Actor
Authenticated user.

### Description
Gateway menampilkan daftar user online global.

### Output
```txt
username | status | active_room | server_id
erlangga | waiting | - | -
budi | in_room | FP-Jaringan | S1
nadia | in_room | Kelompok-A | S2
```

### Status Values
- `waiting`
- `in_room`
- `offline`

### Acceptance Criteria
- User yang login muncul online.
- User yang logout hilang/menjadi offline.
- User yang join room berubah status `in_room`.

---

## 6. Feature: Create Room

### Actor
Authenticated user.

### Description
User membuat room melalui Gateway. Gateway memilih Process Server berdasarkan load.

### Normal Flow
1. User mengisi nama room `FP-Jaringan` pada form Create Room dan menekan tombol **Create Room**.
2. Client mengirim `CREATE_ROOM` ke Gateway.
3. Gateway validasi nama room.
4. Gateway memilih backend server hidup dengan beban paling ringan.
5. Gateway menyimpan room dan room_mapping.
6. Gateway membalas `ROOM_ASSIGNED`.
7. Client otomatis connect ke Process Server yang diberikan.
8. Process Server validasi token ke Gateway.
9. Process Server membuat room context dan user join.

### Load Balancing Rule
Prioritas pemilihan server:
1. status server = alive,
2. active_rooms paling sedikit,
3. active_clients paling sedikit,
4. fallback round-robin.

### Acceptance Criteria
- Room baru tersimpan di database.
- Room mapping tersimpan.
- Creator menjadi room admin.
- Client diarahkan ke Process Server yang benar.

---

## 7. Feature: Join Room

### Actor
Authenticated user.

### Description
User join room yang sudah ada.

### Normal Flow
1. User memilih room `FP-Jaringan` dari tabel Rooms dan menekan tombol **Join Room**.
2. Client mengirim `JOIN_ROOM` ke Gateway.
3. Gateway mencari room_mapping.
4. Gateway membalas lokasi Process Server.
5. Client connect ke Process Server jika belum connect.
6. Client mengirim `AUTH_BACKEND` ke Process Server.
7. Process Server validasi token ke Gateway.
8. Process Server menambahkan user ke room.
9. Process Server mengirim chat history 50 pesan terakhir.
10. Process Server broadcast system message: user joined.

### Acceptance Criteria
- Semua user dalam room yang sama diarahkan ke server yang sama.
- User menerima chat history.
- User lain menerima notifikasi join.

---

## 8. Feature: Leave Room

### Actor
Room member.

### Description
User keluar dari room tetapi tetap login di Gateway.

### Normal Flow
1. User menekan tombol **Leave Room** pada Room Panel.
2. Client mengirim `LEAVE_ROOM` ke Process Server.
3. Process Server mengubah membership menjadi inactive.
4. Process Server broadcast system message.
5. Client menutup room connection atau kembali ke waiting mode.
6. Gateway update presence user menjadi waiting.

### Acceptance Criteria
- User tidak menerima room broadcast setelah leave.
- User tetap dapat PM melalui Gateway.

---

## 9. Feature: Broadcast Room Chat

### Actor
Room member.

### Description
User mengirim pesan ke semua user dalam room.

### Normal Flow
1. User mengetik pesan pada input Room Chat dan menekan tombol **Send**.
2. Client mengirim `ROOM_CHAT_SEND` ke Process Server.
3. Process Server validasi user anggota room.
4. Process Server simpan pesan ke database.
5. Process Server broadcast `ROOM_CHAT_BROADCAST` ke seluruh client dalam room.
6. Sender menerima ACK.

### Error Flow
- User belum join room -> `ERROR NOT_IN_ROOM`.
- Message kosong -> `ERROR EMPTY_MESSAGE`.
- User terkena rate limit -> `ERROR RATE_LIMIT_EXCEEDED`.

### Acceptance Criteria
- Pesan hanya diterima user di room yang sama.
- Pesan masuk history.
- Pesan memiliki timestamp.

---

## 10. Feature: Room Chat History

### Actor
Room member.

### Description
User dapat melihat history room.

### Normal Flow
1. User menekan tombol **Refresh History** atau history dimuat otomatis saat join room.
2. Client mengirim `ROOM_HISTORY_REQUEST`.
3. Process Server query database.
4. Process Server mengirim 50 pesan terakhir.

### Acceptance Criteria
- User baru join menerima history otomatis.
- User bisa request history manual.
- Pesan system/file event bisa ikut ditampilkan.

---

## 11. Feature: File List

### Actor
Room member.

### Description
User melihat file yang tersedia di room.

### Normal Flow
1. User membuka tab/panel **Files** atau menekan tombol **Refresh Files**.
2. Client mengirim `FILE_LIST_REQUEST`.
3. Process Server query file metadata.
4. Client menerima daftar file.

### Output
```txt
ID | Filename | Size | Uploader | Status | Uploaded At
12 | laporan.pdf | 2.4 MB | erlangga | available | 2026-06-09 20:00
```

---

## 12. Feature: Upload File

### Actor
Room member.

### Description
User upload file ke room melalui Process Server.

### Normal Flow
1. User menekan tombol **Upload File** dan memilih `laporan.pdf` melalui file picker.
2. Client menghitung file size, total chunk, checksum SHA-256.
3. Client mengirim `UPLOAD_INIT`.
4. Process Server membuat transfer session.
5. Process Server membalas `UPLOAD_READY`.
6. Client mengirim chunk satu per satu.
7. Process Server mengirim `CHUNK_ACK`.
8. Client menampilkan progress.
9. Client mengirim `UPLOAD_FINISH`.
10. Process Server menghitung checksum.
11. Jika valid, metadata file status `available`.
12. Process Server broadcast system event file baru.

### Error Flow
- File terlalu besar -> `ERROR FILE_TOO_LARGE`.
- File path tidak valid -> client error.
- Checksum gagal -> `ERROR CHECKSUM_FAILED`.
- Transfer timeout -> `ERROR TRANSFER_TIMEOUT`.

### Acceptance Criteria
- File tersimpan di storage Process Server.
- Metadata file tersimpan di database.
- Checksum cocok.
- User lain mendapat notifikasi file baru.

---

## 13. Feature: Download File

### Actor
Room member.

### Description
User download file dari room.

### Normal Flow
1. User memilih file pada tabel File List dan menekan tombol **Download Selected**.
2. Client mengirim `DOWNLOAD_REQUEST`.
3. Process Server validasi file tersedia.
4. Process Server mengirim `DOWNLOAD_READY`.
5. Process Server mengirim chunk satu per satu.
6. Client menulis chunk ke file lokal.
7. Client menampilkan progress.
8. Setelah selesai, client menghitung checksum.
9. Client menampilkan hasil valid/invalid.

### Acceptance Criteria
- File hasil download sama dengan file server.
- Checksum valid.
- Progress tampil.

---

## 14. Feature: Resume Transfer

### Actor
Room member.

### Description
Upload/download dapat dilanjutkan setelah disconnect.

### Normal Flow Download Resume
1. Client download file.
2. Koneksi putus di chunk 40.
3. Client reconnect ke Process Server.
4. Client mengirim `RESUME_TRANSFER` dengan transfer_id dan last_chunk.
5. Server melanjutkan dari chunk 41.
6. Transfer selesai dan checksum valid.

### Acceptance Criteria
- Transfer tidak mulai dari nol.
- Resume status tercatat di database.
- Checksum tetap valid setelah resume.

---

## 15. Feature: Backend Heartbeat

### Actor
Process Server.

### Description
Process Server mengirim heartbeat ke Gateway.

### Payload
```json
{
  "server_id": "S1",
  "active_rooms": 3,
  "active_clients": 12,
  "active_transfers": 2
}
```

### Acceptance Criteria
- Gateway tahu server hidup/mati.
- Gateway tidak mengarahkan room baru ke server down.

---

## 16. Feature: Load Test

### Actor
Server operator.

### Description
Script melakukan simulasi beban.

### Scenario
- 30 client login.
- 10 room dibuat.
- 100 pesan room dikirim.
- 50 PM dikirim.
- 5 file 1 MB upload/download.
- 5 malformed packet dikirim.

### Output
- total success,
- total failed,
- average latency,
- max latency,
- throughput,
- error rate.
