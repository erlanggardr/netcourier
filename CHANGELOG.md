# Changelog - NetCourier

All notable changes to this project documentation will be documented in this file.

---

## [1.0.0] - 2026-06-14

### Added
- **Web-based UI (HTML/CSS/JS SPA)**: Menggantikan seluruh konteks Tkinter lama dengan antarmuka web modern di browser yang dilayani via HTTP API Bridge (`web_api/server.py`).
- **Emoji Reactions**: Memberikan kemampuan bagi user room untuk memberi reaksi emoji secara real-time.
- **Admin Kick & File Deletion**: Pemilik room dapat mendepak user lain dan menghapus file secara logis.
- **ROOM_DELETE_FILE_BROADCAST**: Broadcast dinamis untuk menghapus bubble chat file dari layar semua user room secara real-time saat file dihapus oleh admin.
- **Paralel Chunk Upload**: Fitur browser Web UI untuk mengunggah berkas biner chunk 1MB secara paralel (hingga 4 konkurensi).
- **Safe Out-of-order Writes**: Mekanisme Process Server untuk menulisi data chunk paralel pada offset file yang tepat (`seek(offset)`) dan aman.
- **TCP_NODELAY**: Socket TCP dikonfigurasi tanpa delay Nagle di seluruh pipeline localhost (Gateway, Server S1/S2, Web API).

### Changed
- **Bypass Body Decodes**: Mengabaikan parse UTF-8 pada REST API upload chunk di Web API server, menurunkan pemakaian CPU secara drastis.
- **Progress Caching (DB Batching)**: Process Server menyimpan progress transfer dalam in-memory cache dan hanya mengkomit ke database SQLite setiap 20 chunk sekali, melesatkan performa localhost.
- **Logical Delete**: File didelete secara logis dari DB dan ditolak secara aman jika ada request download berkas yang bersangkutan.

### Fixed
- **File Deletion Parameter**: Tombol *delete* mengirimkan parameter `file_id` riil dan memperbarui pesan secara lokal tanpa re-koneksi room (`joinRoom()`) yang memicu error "Failed to locate room".
- **Dynamic DOM updates**: Bubble chat reaksi emoji dan berkas terhapus kini memperbarui DOM UI secara instan via SSE/polling events.

---

## [0.1.0] - 2026-06-09

### Added
- Struktur dokumentasi awal untuk project NetCourier.
