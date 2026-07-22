# 🔌 Socket Example

A working example of a multi-node distributed network built with the **Massir framework**. This project demonstrates how to use the `network_socket`, `network_ssl`, and `system_encryption` service modules to create a secure mesh network where each node runs the same codebase with different configurations.

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## Overview

This example creates a full-mesh TLS network where each node:

- **Starts a TLS server** to accept inbound connections from peers
- **Connects to all configured peers** as a TLS client
- **Exchanges framed messages** using a length-prefix JSON protocol
- **Reconnects automatically** if a peer goes offline
- **Monitors peer health** using periodic heartbeats

The project runs identically on every server — only the configuration file differs per node.

### When to Use

- Private networks (LAN, VPN, datacenter)
- Virtual machines (VirtualBox, VMware, Proxmox)
- VPS with full root access and open ports
- Kubernetes clusters with TCP services

> **Note:** For environments restricted to ports 80/443 with HTTP inspection (Cloudflare, managed PaaS), use the `network_websocket` module instead.

---

## Project Structure

```
socket_example/
├── main.py
├── requirements.txt
├── app_settings.json
│
├── configs/
│   ├── node1.json
│   ├── node2.json
│   └── node3.json
│
├── certs/
│   ├── ca.crt / ca.key
│   ├── node1.crt / node1.key
│   ├── node2.crt / node2.key
│   └── node3.crt / node3.key
│
├── scripts/
│   └── generate_certs.py
│
└── app/
    ├── socket_node/        # Node lifecycle: server + peer connections
    ├── message_demo/       # Message Mode: framed JSON broadcasts
    └── stream_demo/        # Stream Mode: raw byte file transfer
```

### Application Modules

| Module | Service Provided | Purpose |
|--------|-----------------|---------|
| `socket_node` | `node_service` | Manages server, peer connections, and message routing |
| `message_demo` | — | Demonstrates periodic broadcasts using Message Mode |
| `stream_demo` | `stream_service` | Demonstrates file transfer using Stream Mode |

---

## Setup

### 1. Generate TLS Certificates

Each node needs a unique certificate signed by a shared CA.

```bash
cd Examples/socket_example
pip install -r requirements.txt
python scripts/generate_certs.py
```

This creates per-node certificate pairs in the `certs/` directory.

### 2. Configure Nodes

Each node's configuration is in `configs/nodeX.json`. The key sections are:

**Node Identity and Peers:**
```json
{
    "socket_node": {
        "node_id": "node1",
        "listen_host": "0.0.0.0",
        "listen_port": 8443,
        "use_tls": true,
        "auto_start_server": true,
        "auto_connect_on_start": true,
        "peers": [
            {"node_id": "node2", "host": "192.168.1.102", "port": 8443},
            {"node_id": "node3", "host": "192.168.1.103", "port": 8443}
        ]
    }
}
```

**TLS Certificate Paths:**
```json
{
    "network_ssl": {
        "tls_version": "1.3",
        "verify_client_certs": true,
        "verify_server_certs": true,
        "check_hostname": false,
        "nodes": {
            "default": {
                "cert_file": "node1.crt",
                "key_file": "node1.key",
                "ca_file": "ca.crt"
            }
        }
    }
}
```

**Socket Behavior:**
```json
{
    "network_socket": {
        "client": {
            "reconnect_enabled": true,
            "reconnect_initial_delay_seconds": 2.0,
            "reconnect_max_delay_seconds": 30.0,
            "reconnect_backoff_multiplier": 2.0,
            "reconnect_max_attempts": 0
        },
        "heartbeat": {
            "enabled": true,
            "interval_seconds": 10.0,
            "timeout_seconds": 30.0,
            "missed_threshold": 3
        }
    }
}
```

### 3. Deploy

On each server, place these files:
- `main.py`
- `requirements.txt`
- `configs/nodeX.json` (only this node's config)
- `certs/` (with `ca.crt` + this node's `.crt` and `.key`)
- `app/` (all application modules)

### 4. Run

```bash
export NODE_ID=node1
pip install -r requirements.txt
python main.py
```

The `NODE_ID` environment variable selects which config file to load (`configs/node1.json`).

---

## How It Works

### Module Load Order

Modules are loaded in this dependency order:

```
system_logger → network_ssl → network_socket → socket_node → message_demo / stream_demo
```

Each module registers a **service** that later modules can retrieve via `context.services.get("service_name")`.

### Communication Modes

**Message Mode** (default):
Messages are framed with a 4-byte length prefix and encoded as JSON.
Best for structured data exchange, pub/sub, and request/reply patterns.

**Stream Mode**:
Raw bytes are passed through with zero framing overhead.
Best for file transfer, proxy tunneling, and binary protocols.

### Peer Connection Lifecycle

1. Node starts a TLS server on the configured port
2. Node attempts to connect to each configured peer
3. If a connection fails, auto-reconnect retries with exponential backoff (2s → 4s → 8s → ... → 30s max)
4. Once connected, heartbeat pings are sent every `interval_seconds`
5. If no pong is received within `timeout_seconds`, the peer is declared dead
6. Reconnection continues indefinitely until the peer is reachable again

---

## Using the Services

### `socket_api` — Low-level socket operations

```python
async def load(self, context):
    self.socket = context.services.get("socket_api")

    # Connect to a peer
    client = await self.socket.connect_to_peer(
        peer_id="node-02",
        host="192.168.1.102",
        port=8443,
        mode="message",
        use_tls=True,
    )

    # Create and send a message
    msg = self.socket.create_message("data", payload={"key": "value"})
    await self.socket.send_message("node-02", msg)

    # Send raw bytes
    await self.socket.send_bytes("node-02", b"binary data")

    # Handle incoming messages
    async def on_message(msg, conn):
        print(f"From {conn.peer_id}: {msg.payload}")
    self.socket.on_inbound_message(on_message)
```

### `node_service` — High-level node management

```python
async def load(self, context):
    self.node = context.services.get("node_service")

    # Get connected peers
    peers = self.node.get_connected_peers()

    # Create a message (no direct type imports needed)
    msg = self.node.create_message("data", payload={"event": "hello"})

    # Send to one peer
    await self.node.send_to_peer("node2", msg)

    # Broadcast to all connected peers
    results = await self.node.broadcast(msg)
```

### `ssl_api` — TLS context management

```python
async def load(self, context):
    self.ssl = context.services.get("ssl_api")

    # Get server TLS context
    server_ctx = self.ssl.get_server_context("default")

    # Get client TLS context for connecting to a peer
    client_ctx = self.ssl.get_client_context("node2")

    # Check certificate expiry
    info = self.ssl.get_cert_info("default")
    print(f"Expires in {info.days_until_expiry} days")
```

### `encryption_api` — Cryptographic operations

```python
async def load(self, context):
    self.crypto = context.services.get("encryption_api")

    # Symmetric encryption
    key = self.crypto.generate_symmetric_key()
    encrypted = self.crypto.encrypt(b"secret data", key)
    decrypted = self.crypto.decrypt(encrypted, key)

    # Asymmetric encryption
    pub, priv = self.crypto.generate_keypair()
    ciphertext = self.crypto.encrypt_with_public(b"data", pub)

    # HMAC
    hmac_key = self.crypto.generate_hmac_key()
    signature = self.crypto.create_hmac(b"message", hmac_key)
    is_valid = self.crypto.verify_hmac(b"message", signature, hmac_key)
```

---

## Configuration Reference

### `socket_node`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `node_id` | string | `"node1"` | Unique node identifier |
| `listen_host` | string | `"0.0.0.0"` | Server bind address |
| `listen_port` | int | `8443` | Server listen port |
| `peers` | array | `[]` | List of peer objects `{node_id, host, port}` |
| `use_tls` | bool | `true` | Enable TLS encryption |
| `auto_start_server` | bool | `true` | Start server on module start |
| `auto_connect_on_start` | bool | `true` | Connect to peers on module start |

### `network_socket`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `client.reconnect_enabled` | bool | `true` | Enable auto-reconnect |
| `client.reconnect_initial_delay_seconds` | float | `2.0` | Initial backoff delay |
| `client.reconnect_max_delay_seconds` | float | `30.0` | Maximum backoff delay |
| `client.reconnect_max_attempts` | int | `0` | Max retries (0 = unlimited) |
| `heartbeat.interval_seconds` | float | `10.0` | Ping interval |
| `heartbeat.timeout_seconds` | float | `30.0` | Dead peer threshold |

### `network_ssl`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tls_version` | string | `"1.3"` | Minimum TLS version |
| `verify_client_certs` | bool | `true` | Require client certificates (mTLS) |
| `verify_server_certs` | bool | `true` | Verify server certificates |
| `check_hostname` | bool | `false` | Verify hostname matches cert SAN |
| `nodes.default.cert_file` | string | — | Server certificate filename |
| `nodes.default.key_file` | string | — | Server private key filename |
| `nodes.default.ca_file` | string | — | CA certificate filename |

### `message_demo`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `true` | Enable the module |
| `auto_broadcast_on_start` | bool | `true` | Start broadcasting automatically |
| `broadcast_interval_seconds` | float | `5.0` | Seconds between broadcasts |
| `broadcast_message` | string | `"Hello from {node_id}!"` | Message template |

---

## Architecture Note

This example uses the **Factory Pattern** to maintain loose coupling. Application modules never import types directly from framework modules:

```python
# ❌ Creates tight coupling
from massir.modules.network_socket.core.types import SocketMessage, MessageType

# ✅ Loose coupling via service API
msg = self.socket_api.create_message("data", payload={...})
```

This ensures that if the internal structure of a framework module changes, application code remains unaffected.

---

## License

Part of the **Massir** project. Licensed under the MIT License.