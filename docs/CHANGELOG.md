# Changelog - NetCourier

All notable changes to this project will be documented in this file.

---

## [1.1.0] - 2026-06-14

### Added
- **Dynamic Chunk Scaling**: Implemented auto-scaling of chunk sizes (1MB up to 16MB) depending on the file size. For files like 1GB, the system dynamically scales the chunk size to 11MB to prevent localhost TCP port exhaustion (`TIME_WAIT` saturation).
- **Auto-Initialization of Test Rooms**: Updated the `full_verification.py` script to automatically initialize the 'General' room dynamically if it is not present in a clean database.

### Changed
- **Deterministic Handshake Sync**: Standardized chunk calculations in both the Web UI frontend (`app.js`) and HTTP Web API Bridge (`server.py`) to keep the calculated chunk sizes completely deterministic and support pause/resume out-of-the-box.

---

## [1.0.0] - 2026-06-14

### Added
- **Web-based UI (HTML/CSS/JS SPA)**: Replaced the legacy Tkinter GUI with a modern, responsive Single Page Application Web UI, served through an HTTP/SSE Web API Bridge (`src/netcourier/web/api/main.py`).
- **Emoji Reactions**: Enabled real-time emoji reactions (add/remove) on messages in chat rooms.
- **Admin Kick & File Deletion**: Granted room owners the administrative power to kick members and delete uploaded files.
- **ROOM_DELETE_FILE_BROADCAST**: Implemented dynamic broadcasting of file deletion events to instantly remove file cards from the DOM of all active room members.
- **Parallel Chunk Upload**: Implemented concurrent file slicing and chunk uploading (up to 4 parallel workers) directly in the browser's Web UI.
- **Safe Out-of-order Writes**: Process Server now supports safe parallel block writing at specific file offsets using `seek(offset)`.
- **TCP_NODELAY Option**: Enabled Nagle's algorithm bypass across all localhost pipeline sockets (Gateway, S1/S2, and Web API Bridge) to eliminate latency overhead.

### Changed
- **Bypass Body Decodes**: Disabled UTF-8 decoding for binary REST upload request bodies in the Web API, decreasing server-side CPU utilization.
- **Progress Caching (DB Batching)**: Process Server now buffers file transfer progress updates in memory and batches SQLite database commits every 20 chunks to speed up transfer rates on localhost.
- **Logical File Deletion**: Added logical file deletion in the database, blocking any subsequent download attempts.

### Fixed
- **File Deletion Parameter**: Resolved parameter mismatch by passing real `file_id` during deletes and updating DOM nodes dynamically without invoking full room refreshes.
- **Dynamic DOM updates**: Integrated SSE and API polling to dynamically refresh emoji reactions and user lists.

---

## [0.1.0] - 2026-06-09

### Added
- Initial structural documentation for the NetCourier project.
