# Glossary - NetCourier

| Term | Meaning |
|---|---|
| Gateway | Server depan untuk login, PM global, room directory, dan load balancing |
| Process Server | Server yang menangani room chat dan file transfer |
| Waiting Room | Mode setelah login sebelum user join room |
| Room Affinity | Aturan bahwa satu room hanya ditangani oleh satu Process Server |
| Backend Registry | Daftar Process Server yang diketahui Gateway |
| Heartbeat | Pesan periodik dari Process Server ke Gateway untuk status hidup |
| Presence | Status online user, misalnya waiting, in_room, offline |
| PM | Private Message antar user lewat Gateway |
| Room Chat | Chat broadcast dalam room lewat Process Server |
| Chunking | Memecah file menjadi potongan kecil untuk transfer |
| Checksum | Hash untuk validasi integritas file |
| Resume Transfer | Melanjutkan transfer dari chunk terakhir setelah disconnect |
| Serialization | Pengubahan object/message menjadi format JSON |
| Framing | Mekanisme memberi batas packet di TCP stream |
| Malformed Packet | Packet rusak/tidak sesuai format |
| Throughput | Kecepatan transfer data |
| Latency | Waktu pulang-pergi request-response |
| Load Test | Simulasi banyak client untuk menguji stabilitas server |
