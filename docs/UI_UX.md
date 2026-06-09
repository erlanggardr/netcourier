# UI/UX Specification - NetCourier Tkinter Desktop GUI

NetCourier menggunakan **Tkinter desktop GUI** sebagai UI utama client. Client **tidak boleh berbasis CLI/TUI**. CLI hanya boleh digunakan untuk menjalankan Gateway, Process Server, dan script testing.

UI harus sederhana, stabil, mudah didemokan, dan tetap memperlihatkan konsep jaringan utama: koneksi Gateway, koneksi Process Server, PM global, room chat, file transfer, progress transfer, dan status koneksi.

---

## 1. UI Mode

Client memiliki dua area utama:

1. **Gateway / Waiting Area**
   - User sudah login tetapi belum tentu berada di room.
   - PM global aktif.
   - Online user list aktif.
   - Room list aktif.
   - Create/join room tersedia.

2. **Room Area**
   - User berada di room tertentu.
   - Room chat aktif.
   - Room member list aktif.
   - File list aktif.
   - File upload/download aktif.
   - PM global tetap aktif melalui koneksi Gateway.

Desain paling praktis adalah satu window utama dengan layout tab atau panel:

```txt
+--------------------------------------------------------------+
| NetCourier                                      user: erlangga |
+----------------------+---------------------------------------+
| Sidebar / Navigation | Main Content                          |
| - Gateway            | - Waiting Room / Room Chat            |
| - Rooms              | - Private Message                     |
| - Files              | - Transfer Progress                   |
+----------------------+---------------------------------------+
| Status: Gateway connected | Room: FP-Jaringan @ S1 | 12 ms   |
+--------------------------------------------------------------+
```

---

## 2. Window Structure

### 2.1 Auth Window

Komponen:
- App title: NetCourier.
- Gateway host input.
- Gateway port input.
- Login form:
  - username entry,
  - password entry,
  - Login button.
- Register form:
  - username entry,
  - display name entry,
  - password entry,
  - Register button.
- Status label untuk error/success.

Rules:
- Password field menggunakan masking.
- Tombol Login/Register disabled saat request sedang diproses.
- Error login tampil di status label atau messagebox.
- Setelah login sukses, buka Main Window.

---

## 3. Main Window Layout

Main Window muncul setelah login berhasil.

Rekomendasi layout:

```txt
+--------------------------------------------------------------------------------+
| NetCourier - erlangga                                           [Logout] [Help] |
+-------------------------+------------------------------------------------------+
| Global Panel            | Room Panel                                           |
|                         |                                                      |
| Online Users            | Room Header: FP-Jaringan @ S1                        |
| [search user]           | [Leave Room] [Refresh History] [Ping Room]           |
| - budi      in_room     |                                                      |
| - nadia     waiting     | Chat History                                         |
|                         | ---------------------------------------------------- |
| Private Message         | [20:20] budi: Halo                                  |
| To: [budi         v]    | [20:21] erlangga: Aku upload laporan ya             |
| Message: [          ]   |                                                      |
| [Send PM] [History]     | Message: [                              ] [Send]     |
|                         |                                                      |
| Rooms                   | Files                                                |
| [Create Room input]     | ID | Filename | Size | Uploader | Status           |
| [Create]                | 1  | laporan.pdf | 2.4 MB | erlangga | available   |
| Room table              | [Upload] [Download Selected] [Resume]               |
+-------------------------+------------------------------------------------------+
| Transfer Progress: laporan.pdf [########------] 67% | 780 KB/s | ETA 2s        |
| Status: Gateway connected | Room Server S1 connected | Last error: -                  |
+--------------------------------------------------------------------------------+
```

---

## 4. Auth Flow UX

### 4.1 Register

User flow:
1. User membuka aplikasi `python client/main.py`.
2. User mengisi Gateway Host dan Gateway Port.
3. User mengisi username, display name, dan password.
4. User menekan tombol **Register**.
5. Client mengirim packet `REGISTER` ke Gateway.
6. Jika berhasil, UI menampilkan pesan: `Register success. Please login.`

Error:
- Username kosong -> `Username is required.`
- Username sudah dipakai -> `Username already taken.`
- Password terlalu pendek -> `Password is too short.`
- Gateway tidak tersambung -> `Cannot connect to Gateway.`

### 4.2 Login

User flow:
1. User mengisi username dan password.
2. User menekan tombol **Login**.
3. Client mengirim packet `LOGIN` ke Gateway.
4. Jika berhasil, Auth Window diganti ke Main Window.
5. Status bar menampilkan `Gateway connected`.

Error:
- Credential salah -> `Invalid username or password.`
- Duplicate login -> `User already logged in.`
- Timeout -> `Login timeout. Please try again.`

---

## 5. Waiting Area UX

Waiting Area adalah area global setelah login.

Komponen:
- Online Users table.
- Private Message panel.
- Room List table.
- Create Room form.
- Join Room button.
- PM History button.

### 5.1 Online Users Table

Kolom:
- Username.
- Display name.
- Status: `waiting`, `in_room`, `offline` jika ditampilkan dari history.
- Active room.
- Server ID.

Action:
- Double click user -> isi target PM.
- Refresh button -> request `ONLINE_USERS_REQUEST`.

### 5.2 Private Message Panel

Komponen:
- Recipient dropdown/input.
- Message text entry.
- Send PM button.
- PM History button.
- PM conversation display.

Tampilan pesan:

```txt
[PM from budi | 20:15:01] Bro, file sudah aku download.
[PM to budi | delivered] Oke sip.
[PM to nadia | stored_offline] User offline. Message saved.
```

Rules:
- PM masuk harus tetap tampil walaupun user sedang berada di room.
- PM prefix harus berbeda dari room chat.
- PM history diambil dari Gateway/Central DB.

### 5.3 Room List

Kolom:
- Room name.
- Server ID.
- Active users.
- File count.
- Visibility.

Action:
- Create Room -> request ke Gateway.
- Join Room -> Gateway mengembalikan lokasi Process Server.
- Setelah join sukses, Room Panel aktif.

---

## 6. Room Area UX

Room Area aktif setelah user join room.

Komponen:
- Room header.
- Room chat history.
- Message input.
- Send button.
- Room members list.
- File list.
- Upload button.
- Download selected button.
- Resume transfer button.
- Progress bar transfer.

### 6.1 Room Chat

Tampilan:

```txt
[ROOM FP-Jaringan | 20:20:01] budi: Halo semua
[ROOM FP-Jaringan | 20:20:05] erlangga: Aku upload laporan ya
[SYSTEM | 20:20:06] erlangga started uploading laporan.pdf
```

Rules:
- Room chat hanya untuk room yang sedang aktif.
- Room chat dikirim ke Process Server, bukan Gateway.
- Chat history dimuat saat join room.
- Text area chat read-only.
- Message input clear setelah send sukses.

### 6.2 Room Members

Kolom:
- Username.
- Role.
- Status.

Action:
- Select member -> bisa langsung dijadikan target PM.

### 6.3 File List

Kolom:
- File ID.
- Filename.
- Size.
- Uploader.
- Checksum status.
- Upload time.
- Availability status.

Action:
- Upload -> buka file picker.
- Download Selected -> download file terpilih.
- Resume -> lanjutkan transfer interrupted.
- Refresh -> request file list terbaru.

---

## 7. File Transfer UX

### 7.1 Upload

User flow:
1. User menekan tombol **Upload**.
2. UI membuka file picker.
3. User memilih file.
4. UI menampilkan metadata file:
   - filename,
   - size,
   - chunk size,
   - total chunks,
   - checksum preview.
5. User konfirmasi upload.
6. Upload berjalan pada worker thread.
7. Progress bar diperbarui melalui UI event queue.
8. Setelah selesai, UI menampilkan checksum valid/failed.

Progress display:

```txt
Uploading laporan.pdf to Server S1
67% | 1.60 MB / 2.40 MB | 780 KB/s | ETA 2s
```

### 7.2 Download

User flow:
1. User memilih file dari File List.
2. User menekan tombol **Download Selected**.
3. UI membuka folder picker atau menggunakan folder default `downloads/`.
4. Download berjalan pada worker thread.
5. Progress bar diperbarui.
6. Setelah selesai, UI menampilkan lokasi file dan checksum status.

### 7.3 Resume Transfer

Jika transfer interrupted:
- Transfer muncul di transfer panel dengan status `interrupted`.
- User dapat menekan tombol **Resume**.
- Client mengirim `RESUME_TRANSFER`.
- Progress lanjut dari chunk terakhir yang sudah sukses.

---

## 8. Status Bar

Status bar harus selalu terlihat.

Isi status bar:
- Gateway connection: connected/disconnected.
- Current room server: S1/S2/disconnected.
- Current room name.
- Last latency.
- Last error pendek.

Contoh:

```txt
Gateway: connected | Room: FP-Jaringan @ S1 | Latency: 12 ms | Status: Ready
```

---

## 9. Error UX

Error biasa tampil di status bar. Error penting boleh menggunakan messagebox.

Contoh error:
- `Invalid username or password.`
- `Room not found.`
- `Server S1 is down. Please try again later.`
- `File too large. Max size is 100 MB.`
- `Checksum mismatch. File marked as corrupted.`
- `Invalid packet received. Connection remains active.`

Rules:
- Jangan tampilkan raw JSON ke user biasa.
- Error teknis detail tetap masuk log file.
- UI harus tetap aktif setelah error.

---

## 10. Threading and UI Safety

Tkinter hanya boleh di-update dari main thread. Semua event dari socket thread harus masuk ke UI queue.

Required pattern:

```python
# worker/receiver thread
ui_queue.put({"type": "PM_RECEIVED", "payload": payload})

# tkinter main thread
root.after(50, process_ui_queue)
```

Receiver thread:
- Gateway receiver thread menerima PM, online user update, room directory response.
- Room receiver thread menerima room chat, system event, file event.

Worker thread:
- Upload worker.
- Download worker.
- Checksum worker jika file besar.

Rules:
- Jangan memanggil `text_widget.insert(...)` dari socket thread.
- Jangan memanggil `progressbar['value'] = ...` dari upload thread.
- Semua update widget harus lewat `process_ui_queue()`.

---

## 11. Suggested Tkinter Files

```txt
client/
├── main.py                 # entry point
├── app.py                  # NetCourierApp root controller
├── auth_view.py            # login/register UI
├── waiting_view.py         # online users, PM, room list
├── room_view.py            # room chat, files, transfer panel
├── widgets.py              # reusable widgets
├── gateway_connection.py   # Gateway socket client
├── room_connection.py      # Process Server socket client
├── uploader.py             # upload worker
├── downloader.py           # download worker
└── ui_events.py            # event type constants / queue helpers
```

---

## 12. Help Dialog

Help tidak berupa `/help` command. Gunakan menu atau tombol **Help**.

Isi help:
- Cara login/register.
- Cara mengirim PM.
- Cara membuat/join room.
- Cara chat di room.
- Cara upload/download file.
- Penjelasan status Gateway dan Room Server.

---

## 13. UX Rules

1. UI utama wajib Tkinter desktop GUI.
2. Jangan gunakan CLI/TUI sebagai UI client utama.
3. PM prefix harus berbeda dari room chat.
4. System event harus berbeda dari user message.
5. File transfer harus memiliki progress bar.
6. User harus bisa menerima PM walaupun sedang berada di room.
7. Waiting Area dan Room Area harus terlihat berbeda.
8. Button yang memicu request network harus disabled sementara saat request berjalan bila perlu.
9. GUI tidak boleh freeze saat upload/download atau menerima banyak pesan.
10. Semua update UI dari thread jaringan harus melalui queue dan `root.after`.
