# Deployment Guide - NetCourier

This document explains how to deploy and run NetCourier on localhost, LAN, and VPS environments.

---

## 1. Deployment Modes

### 1.1 Localhost Demo

All processes run on a single developer machine, distinguished by port numbers.

```txt
Gateway: 127.0.0.1:9000
Gateway backend-control: 127.0.0.1:9001
Server S1: 127.0.0.1:9101
Server S2: 127.0.0.1:9102
Database: SQLite local file
```

Suitable for:
- Development and debugging.
- Safe local demonstrations.
- Initial functional testing.

---

### 1.2 LAN Demo

The Gateway and Process Servers run on a single central machine. Other clients connect using the host machine's LAN IP address.

```txt
Gateway: 192.168.1.10:9000
S1: 192.168.1.10:9101
S2: 192.168.1.10:9102
```

Suitable for:
- Multi-client demonstrations utilizing multiple physical computers.
- Simulating local network behavior and latency.

---

### 1.3 VPS Demo

The Gateway and Process Servers are deployed on a public Virtual Private Server (VPS).

```txt
Gateway: <VPS_PUBLIC_IP>:9000
S1: <VPS_PUBLIC_IP>:9101
S2: <VPS_PUBLIC_IP>:9102
```

Suitable for:
- Remote deployment bonuses.
- Online/internet-based testing.

---

## 2. Running Locally

### Terminal 1 (Gateway):

```bash
PYTHONPATH=src python -m netcourier.gateway.main --host 0.0.0.0 --client-port 9000 --backend-port 9001
```

### Terminal 2 (Process Server S1):

```bash
PYTHONPATH=src python -m netcourier.server.main --server-id S1 --host 0.0.0.0 --port 9101 --gateway-host 127.0.0.1 --gateway-port 9001
```

### Terminal 3 (Process Server S2):

```bash
PYTHONPATH=src python -m netcourier.server.main --server-id S2 --host 0.0.0.0 --port 9102 --gateway-host 127.0.0.1 --gateway-port 9001
```

### Terminal 4 (Client UI / Web Bridge API):

```bash
PYTHONPATH=src python -m netcourier.client.main --gateway-host 127.0.0.1 --gateway-port 9000
```

---

## 3. Running on LAN

1. Obtain the local IP address of the server host machine:

   Windows:
   ```bash
   ipconfig
   ```

   Linux/macOS:
   ```bash
   ip addr
   ```

2. Clients connect to the server's LAN IP address:

   ```bash
   PYTHONPATH=src python -m netcourier.client.main --gateway-host 192.168.1.10 --gateway-port 9000
   ```

3. Ensure the firewall allows traffic on the following TCP ports:
   - 9000 (Gateway Client Port)
   - 9101 (Process Server S1)
   - 9102 (Process Server S2)

---

## 4. Running on VPS Ubuntu

1. Install system dependencies:

   ```bash
   sudo apt update
   sudo apt install python3 python3-pip tmux ufw
   ```

2. Open the required ports on the firewall:

   ```bash
   sudo ufw allow 9000/tcp
   sudo ufw allow 9101/tcp
   sudo ufw allow 9102/tcp
   sudo ufw enable
   ```

3. Run the components inside persistent `tmux` sessions:

   ```bash
   # Session for Gateway
   tmux new -s gateway
   PYTHONPATH=src python3 -m netcourier.gateway.main --host 0.0.0.0 --client-port 9000 --backend-port 9001
   ```

   ```bash
   # Session for S1
   tmux new -s s1
   PYTHONPATH=src python3 -m netcourier.server.main --server-id S1 --host 0.0.0.0 --port 9101 --gateway-host 127.0.0.1 --gateway-port 9001
   ```

   ```bash
   # Session for S2
   tmux new -s s2
   PYTHONPATH=src python3 -m netcourier.server.main --server-id S2 --host 0.0.0.0 --port 9102 --gateway-host 127.0.0.1 --gateway-port 9001
   ```

4. Clients connect using the public IP of the VPS:

   ```bash
   PYTHONPATH=src python3 -m netcourier.client.main --gateway-host <VPS_PUBLIC_IP> --gateway-port 9000
   ```

---

## 5. Environment Variables

Configure settings using a `.env` file:

```txt
GATEWAY_HOST=0.0.0.0
GATEWAY_CLIENT_PORT=9000
GATEWAY_BACKEND_PORT=9001
DATABASE_URL=sqlite:///data/netcourier.db
MAX_FILE_SIZE_MB=100
CHUNK_SIZE=65536
HEARTBEAT_INTERVAL=5
HEARTBEAT_TIMEOUT=15
```

> [!WARNING]
> Do not commit the `.env` file containing production credentials to version control.

---

## 6. Storage Layout

On each Process Server node, files are stored relative to the storage prefix path:

```txt
storage/
├── S1/
│   └── rooms/
│       └── fp-jaringan/
└── S2/
    └── rooms/
        └── kelompok-a/
```

---

## 7. Deployment Recommendation

For final project evaluations:
1. **Primary Demo:** Focus on a stable Localhost or LAN setup.
2. **Bonus:** Set up the public VPS only after all primary chat, database, and reliability requirements are fully implemented and verified locally.
3. Do not spend precious time troubleshooting VPS configurations at the cost of core feature functionality.

---

## 8. Nginx Reverse Proxy Considerations

Standard Nginx load balancing is not utilized as the primary load balancer because NetCourier requires stateful, room-aware routing.

The core load balancer logic is integrated into the Python Gateway to analyze:
- Room names
- Active room allocations
- Current server load metrics
- Room affinity mappings

Nginx may be deployed as an optional public TCP proxy/reverse proxy, but it does not replace the Gateway server.

---

## 9. Deployment Checklist

- [ ] Gateway is running.
- [ ] Process Server S1 is running.
- [ ] Process Server S2 is running.
- [ ] Backend heartbeats are being actively received by the Gateway.
- [ ] Clients can successfully register and log in.
- [ ] Clients can create chat rooms.
- [ ] Rooms are correctly mapped and clients are routed to S1 or S2.
- [ ] Clients can send and receive global Private Messages (PMs).
- [ ] Clients can send and receive messages within chat rooms.
- [ ] Chunked file uploads and downloads complete and verify successfully.
- [ ] System firewall ports are open.
- [ ] Logs are stored and readable.
