# NetCourier Final Performance Report

## 1. Latency Benchmarks (Gateway & Process Server)
Measured using `tests/load_test.py` with concurrent PING requests.

| Concurrent Clients | Total Requests | Avg Latency | 95th Percentile | Min Latency | Max Latency |
|--------------------|----------------|-------------|-----------------|-------------|-------------|
| 5                  | 20             | 10.20 ms    | 56.36 ms        | 0.10 ms     | 56.52 ms    |
| 10                 | 40             | 10.21 ms    | 56.71 ms        | 0.11 ms     | 61.62 ms    |

## 2. Throughput Benchmarks (Reliable File Transfer)
Measured using `tests/throughput_test.py` and `tests/benchmark_100mb.py` with optimized socket options and parallel transfers.

| File Size | Time Taken | Throughput |
|-----------|------------|------------|
| 1 MB      | 0.07 s     | 14.66 MB/s |
| 10 MB     | 0.76 s     | 13.09 MB/s |
| 1024 MB (1 GB) | 13.00 s | **78.78 MB/s** |

*Catatan: Kecepatan 78.78 MB/s dicapai setelah mengaktifkan `TCP_NODELAY` untuk menghilangkan delay Nagle's algorithm (40ms), melakukan chunking paralel di sisi klien (konkurensi 4 worker), dan menghindari pembongkaran byte UTF-8 di sisi HTTP/TCP Bridge.*

## 3. Reliability & Security Verification
| Test Case | Status | Result |
|-----------|--------|--------|
| Malformed Header | Passed | Server rejected (Header too large) |
| Invalid JSON | Passed | Server rejected (JSON Decode Error) |
| Large Payload (>20MB) | Passed | Server rejected (Payload too large) |
| Rate Limiting (Chat) | Passed | Blocked after rapid messaging |
| Filename Sanitization | Passed | Path traversal characters stripped |
| Reconnection | Passed | Auto-cleanup of stale sessions |
| Admin File Deletion | Passed | Logically deleted and dynamically removed from clients' DOM |

## 4. Conclusion
NetCourier demonstrates high efficiency for both real-time chat and large file transfers. The distributed architecture with Gateway and dedicated Process Servers successfully scales across concurrent users without significant latency degradation.
