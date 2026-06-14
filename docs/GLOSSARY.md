# Glossary - NetCourier

| Term | Meaning |
|---|---|
| Gateway | Front server handling authentication, global PM routing, room directories, and load balancing |
| Process Server | Core server handling chat room broadcasting, reactions, status updates, and file transfers |
| Waiting Room / Lobby | User dashboard state after logging in, prior to joining a specific chat room |
| Room Affinity | Rule stating that a chat room is strictly hosted by a single designated Process Server |
| Backend Registry | Registry database of Process Servers registered with the Gateway |
| Heartbeat | Periodic signaling packet sent from Process Servers to the Gateway to indicate alive status |
| Presence | User availability state (waiting in lobby, in_room, offline) |
| PM | Private Message routed globally between users via the Gateway |
| Room Chat | Message broadcasted within a specific room via the assigned Process Server |
| Chunking | Splitting a file into smaller sequential byte blocks for network transfer |
| Checksum | Cryptographic hash (SHA-256) computed to validate file integrity |
| Resume Transfer | Continuing file transfer from the last verified written chunk index after a network drop |
| Serialization | Converting structured objects/messages into JSON formatting |
| Framing | Pre-pending message lengths (length-prefixing) to define boundaries in a continuous TCP byte stream |
| Malformed Packet | Packet containing syntax errors or missing required fields |
| Throughput | Net speed rate of successful data transfer over the network connection |
| Latency | Round-trip duration taken for a request to receive its corresponding response |
| Load Test | Simulated concurrency benchmarks designed to test server stability and performance limits |
