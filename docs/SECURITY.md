# Security Specification - NetCourier

Dokumen ini menjelaskan aturan keamanan minimum untuk NetCourier.

---

## 1. Security Goals

1. Mencegah akses tanpa login.
2. Mencegah password tersimpan plain text.
3. Mencegah user memakai token invalid.
4. Mencegah packet rusak menyebabkan server crash.
5. Mencegah path traversal pada upload/download file.
6. Mencegah spam chat/PM dan transfer berlebihan.
7. Menjaga file yang diterima tidak corrupt melalui checksum.

---

## 2. Authentication Security

## 2.1 Password Hashing

Password tidak boleh disimpan plain text.

Rekomendasi:
- `bcrypt` jika tersedia.
- Jika tidak, gunakan `hashlib.pbkdf2_hmac`.

Minimal:
```txt
password_hash = PBKDF2(password, salt, iterations=100000)
```

Simpan:
- salt,
- hash,
- algorithm.

---

## 2.2 Session Token

Setelah login, Gateway membuat random token.

Rules:
- token panjang minimal 32 bytes random,
- token dikirim ke client setelah login,
- database menyimpan hash token, bukan token plain,
- token inactive setelah logout,
- token invalid ditolak.

---

## 2.3 Duplicate Login

Rekomendasi untuk scope project:
- satu username hanya boleh aktif di satu session,
- login kedua ditolak dengan `ERROR DUPLICATE_LOGIN`.

Alternatif:
- login kedua memutus session lama.

---

## 3. Authorization Rules

| Action | Required |
|---|---|
| Register | Guest |
| Login | Guest |
| PM | Authenticated |
| List rooms | Authenticated |
| Create room | Authenticated |
| Join room | Authenticated |
| Room chat | Room member |
| Upload/download | Room member |
| Delete file | Room admin |
| Kick user | Room admin |

---

## 4. Packet Validation

Setiap packet harus dicek:

- `type` ada,
- `request_id` ada,
- `payload` ada,
- field wajib lengkap,
- token valid jika dibutuhkan,
- payload_size sesuai,
- message type dikenal,
- tipe data benar.

Jika invalid:
- balas `ERROR INVALID_PACKET`,
- catat log,
- jangan crash.

---

## 5. Rate Limiting

Terapkan rate limit sederhana:

| Action | Limit |
|---|---|
| Chat room | 5 pesan / 3 detik |
| PM | 5 pesan / 3 detik |
| Login gagal | 5 percobaan / menit |
| Upload aktif | max 2 transfer/user |
| File size | max 100 MB untuk demo |

Jika limit terlampaui:
- return `ERROR RATE_LIMIT_EXCEEDED`.

---

## 6. File Security

## 6.1 Filename Sanitization

Filename tidak boleh mengandung:
- `../`
- `..\\`
- absolute path `/`
- absolute path `C:\`
- null byte
- karakter kontrol.

Gunakan stored filename yang dibuat server:

```txt
<timestamp>_<random>_<safe_original_filename>
```

## 6.2 Storage Path

File harus disimpan di folder:

```txt
storage/<server_id>/rooms/<room_name>/
```

Server tidak boleh menulis file di luar folder storage.

## 6.3 File Size Limit

Default:
```txt
MAX_FILE_SIZE = 100 MB
```

## 6.4 Checksum

Setiap upload/download harus menggunakan SHA-256.

Jika checksum mismatch:
- file status `corrupted`,
- download ditolak sampai file diperbaiki,
- log dicatat.

---

## 7. Gateway Security

Gateway harus:
- validasi login,
- menyimpan session,
- validasi token untuk Process Server,
- tidak memproses file besar,
- tidak menerima room assignment dari client,
- memastikan backend yang dipakai status alive.

---

## 8. Process Server Security

Process Server harus:
- menolak client tanpa token valid,
- menolak user yang bukan member room,
- menolak upload ke room yang tidak diikuti,
- menolak file path berbahaya,
- validasi chunk transfer,
- menutup transfer timeout.

---

## 9. Logging Security

Jangan log:
- password,
- token plain,
- isi file binary.

Boleh log:
- username,
- event type,
- room,
- file metadata,
- IP,
- error code.

---

## 10. Public Hosting Minimum Rules

Jika di-host di VPS:
1. Jangan jalankan sebagai root.
2. Buka hanya port yang diperlukan.
3. Gunakan firewall.
4. Batasi ukuran file.
5. Matikan debug verbose untuk public.
6. Jangan taruh secret di repository.
7. Gunakan `.env` untuk konfigurasi.
8. Tambahkan TLS jika waktu cukup.

---

## 11. Security Acceptance Criteria

- [ ] Password tidak plain text.
- [ ] Token invalid ditolak.
- [ ] User tanpa login tidak bisa join room.
- [ ] User bukan member tidak bisa chat/upload.
- [ ] Filename `../../etc/passwd` ditolak.
- [ ] File checksum mismatch ditandai corrupted.
- [ ] Malformed packet tidak crash.
- [ ] Spam chat dibatasi.
