# 🔌 Socket Example: Multi-Node Distributed Network

A production-ready demonstration of the `network_socket` module within the **Massir framework**. This example showcases a distributed network of interconnected nodes communicating over TLS 1.3 with mutual authentication (mTLS).

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![TLS](https://img.shields.io/badge/TLS-1.3-orange.svg)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Deployment Guide](#-deployment-guide)
- [Configuration](#-configuration)
- [Testing Scenarios](#-testing-scenarios)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [API Reference](#-api-reference)

---

## 🎯 Overview

This example demonstrates a **fully meshed distributed network** where multiple nodes communicate securely over TLS. Each node runs the same codebase but with different configurations, making it ideal for deployment across multiple servers or containers.

### Use Cases

- **Distributed microservices** with secure inter-service communication
- **IoT gateway networks** with node-to-node messaging
- **Multi-region deployments** with automatic reconnection
- **High-availability clusters** with heartbeat monitoring
- **Real-time data streaming** with zero-copy byte transfer

---

## ✨ Key Features

### 🔐 Security
- **TLS 1.3** encryption for all communications
- **Mutual TLS (mTLS)** - bidirectional certificate verification
- **Per-node certificates** signed by a common CA
- **Subject Alternative Names (SAN)** for flexible hostname validation

### 🚀 Communication Modes
- **Message Mode**: Length-prefixed JSON messages with automatic framing
- **Stream Mode**: Zero-copy raw byte passthrough (ideal for file transfer, proxies)
- **Pluggable codecs**: JSON, MessagePack, or custom implementations

### 🛡️ Reliability
- **Automatic reconnection** with exponential backoff
- **Heartbeat monitoring** with dead peer detection
- **Connection pooling** with round-robin load balancing
- **Send queue** for backpressure handling
- **Graceful shutdown** with proper resource cleanup

### 🏗️ Architecture
- **Modular design** - each feature is a separate Massir module
- **Service-based API** - clean interfaces between modules
- **Event-driven** - callbacks for all lifecycle events
- **Hot configuration** - node-specific settings via JSON

---

## 🏛️ Architecture

### Network Topology

```
┌─────────────────────────────────────────────────────────┐
│                  Massir Distributed Network              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│    ┌──────────┐  mTLS  ┌──────────┐  mTLS  ┌──────────┐│
│    │  Node 1  │◄══════►│  Node 2  │◄══════►│  Node 3  ││
│    │  :8443   │        │  :8443   │        │  :8443   ││
│    └────┬─────┘        └────┬─────┘        └────┬─────┘│
│         │                   │                    │      │
│         └───────────────────┴────────────────────┘      │
│                      Full Mesh                           │
│                                                          │
│    Each node provides:                                   │
│    ├─ TLS Server (accepts inbound connections)          │
│    ├─ TLS Client (connects to all peers)                │
│    ├─ Heartbeat Monitor (ping/pong every 10s)           │
│    ├─ Connection Pool (multiple connections per peer)   │
│    └─ Auto-Reconnect (exponential backoff)              │
└─────────────────────────────────────────────────────────┘
```

### Module Layers

```
┌─────────────────────────────────────────────┐
│  Application Layer                          │
│  ├─ socket_node     (node management)       │
│  ├─ message_demo    (Message Mode tests)    │
│  └─ stream_demo     (Stream Mode tests)     │
├─────────────────────────────────────────────┤
│  Transport Layer                            │
│  └─ network_socket  (socket_api service)    │
├─────────────────────────────────────────────┤
│  Security Layer                             │
│  └─ network_ssl     (ssl_api service)       │
├─────────────────────────────────────────────┤
│  Foundation Layer                           │
│  ├─ system_logger   (core_logger service)   │
│  └─ system_config   (core_config service)   │
└─────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13 or higher
- `cryptography` library (42.0.0+)
- Network connectivity between nodes

### Step 1: Generate Certificates

Generate a Certificate Authority (CA) and per-node certificates:

```bash
cd Examples/socket_example
pip install -r requirements.txt
python scripts/generate_certs.py
```

This creates the following files in the `certs/` directory:
- `ca.crt` / `ca.key` - Certificate Authority
- `node1.crt` / `node1.key` - Node 1 certificate
- `node2.crt` / `node2.key` - Node 2 certificate  
- `node3.crt` / `node3.key` - Node 3 certificate

### Step 2: Prepare Deployment Packages

Each node needs a specific subset of files:

**For Node 1:**
```
📦 node1-deployment/
├── main.py
├── requirements.txt
├── configs/node1.json
├── certs/
│   ├── ca.crt          ← Same CA for all nodes
│   ├── node1.crt       ← Node-specific certificate
│   └── node1.key       ← Node-specific private key
└── app/
    ├── socket_node/
    ├── message_demo/
    └── stream_demo/
```

### Step 3: Deploy to Each Server/Container

Transfer the appropriate deployment package to each target server or container.

### Step 4: Set Environment Variable

On each node, set the `NODE_ID` environment variable:

```bash
# Node 1
export NODE_ID=node1

# Node 2
export NODE_ID=node2

# Node 3
export NODE_ID=node3
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Start the Node

```bash
python main.py
```

---

## 🌐 Deployment Guide

### Scenario A: Pre-Existing Containers (Most Common)

For environments where containers are already running and you deploy code via a specialized tool:

#### Deployment Checklist

- [ ] Certificates generated (`scripts/generate_certs.py`)
- [ ] Each node has its own `configs/nodeX.json`
- [ ] `NODE_ID` environment variable set on each container
- [ ] Same `ca.crt` deployed to all containers
- [ ] Each container has its own certificate (`nodeX.crt` + `nodeX.key`)
- [ ] Peer hostnames are resolvable between containers
- [ ] Port 8443 is open on all containers
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Network connectivity verified between containers

#### Deployment Commands

```bash
# On each container, after code deployment:
export NODE_ID=node1  # Adjust per container
pip install -r requirements.txt
python main.py
```

### Scenario B: Multiple Physical Servers

For deployment across separate physical or virtual servers:

1. **Generate certificates** on a secure machine
2. **Update hostnames** in `configs/nodeX.json` to use real IPs/DNS names
3. **Update SAN entries** in `scripts/generate_certs.py` with actual hostnames
4. **Regenerate certificates** after updating hostnames
5. **Distribute certificates** securely (scp, rsync, etc.)
6. **Configure firewall** to allow port 8443 between servers
7. **Start each node** with appropriate `NODE_ID`

### Scenario C: Local Development (Multiple Terminals)

For quick local testing without Docker:

```bash
# Terminal 1
export NODE_ID=node1
python main.py

# Terminal 2
export NODE_ID=node2
python main.py

# Terminal 3
export NODE_ID=node3
python main.py
```

---

## ⚙️ Configuration

### Node Configuration Structure

Each node's configuration is defined in `configs/nodeX.json`:

```json
{
    "socket_node": {
        "node_id": "node1",
        "listen_host": "0.0.0.0",
        "listen_port": 8443,
        "advertise_host": "node1",
        "peers": [
            {"node_id": "node2", "host": "node2", "port": 8443},
            {"node_id": "node3", "host": "node3", "port": 8443}
        ],
        "use_tls": true,
        "auto_connect_on_start": true,
        "auto_start_server": true
    },
    
    "network_ssl": {
        "tls_version": "1.3",
        "verify_client_certs": true,
        "verify_server_certs": true,
        "nodes": {
            "default": {
                "cert_file": "node1.crt",
                "key_file": "node1.key",
                "ca_file": "ca.crt"
            }
        }
    },
    
    "network_socket": {
        "client": {
            "reconnect_enabled": true,
            "reconnect_initial_delay_seconds": 2.0,
            "reconnect_max_delay_seconds": 30.0
        },
        "heartbeat": {
            "enabled": true,
            "interval_seconds": 10.0,
            "timeout_seconds": 30.0
        }
    },
    
    "message_demo": {
        "auto_broadcast_on_start": true,
        "broadcast_interval_seconds": 5.0,
        "broadcast_message": "Hello from node1!"
    }
}
```

### Configuration Parameters

#### `socket_node` Section

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `node_id` | string | `"node1"` | Unique identifier for this node |
| `listen_host` | string | `"0.0.0.0"` | Host to bind the server to |
| `listen_port` | int | `8443` | Port for the TLS server |
| `peers` | array | `[]` | List of peer nodes to connect to |
| `use_tls` | bool | `true` | Enable TLS encryption |
| `auto_connect_on_start` | bool | `true` | Connect to peers automatically |
| `auto_start_server` | bool | `true` | Start server automatically |

#### `network_socket` Section

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reconnect_enabled` | bool | `true` | Enable automatic reconnection |
| `reconnect_initial_delay_seconds` | float | `2.0` | Initial delay before reconnect |
| `reconnect_max_delay_seconds` | float | `30.0` | Maximum delay (backoff limit) |
| `reconnect_backoff_multiplier` | float | `2.0` | Exponential backoff multiplier |
| `reconnect_max_attempts` | int | `0` | Max attempts (0 = unlimited) |
| `heartbeat.interval_seconds` | float | `10.0` | Ping interval |
| `heartbeat.timeout_seconds` | float | `30.0` | Peer timeout threshold |

---

## 🧪 Testing Scenarios

### Scenario 1: Verify Connectivity

Check that all nodes successfully connect to each other:

```bash
# Expected log output on each node:
[INFO] ✅ Connected to peer 'node2' at node2:8443
[INFO] ✅ Connected to peer 'node3' at node3:8443
```

### Scenario 2: Message Broadcasting

Observe periodic message exchange:

```bash
# Expected log output:
[INFO] 📢 Broadcast #1: 2/2 peers
[INFO] 📨 Message from 'node2' type=data: {'event': 'periodic_hello', ...}
[INFO] 📨 Message from 'node3' type=data: {'event': 'periodic_hello', ...}
```

### Scenario 3: Connection Resilience

Test automatic reconnection by stopping one node:

```bash
# Stop node2
# Observe on node1 and node3:
[WARNING] ⚠️ Reconnect attempt 1 to node2:8443 in 2.0s
[WARNING] ⚠️ Reconnect attempt 2 to node2:8443 in 4.0s

# Restart node2
# Observe automatic reconnection:
[INFO] ✅ Connected to peer 'node2' at node2:8443
```

### Scenario 4: Heartbeat Failure Detection

Simulate a network partition (block traffic between nodes):

```bash
# After timeout_seconds (default 30s):
[WARNING] Peer 'node2' declared dead (last_pong: 35.2s ago)
```

### Scenario 5: Stream Mode File Transfer

Test zero-copy byte streaming:

```python
# In your code or console:
stream_service = app.services.get("stream_service")
await stream_service.send_test_file("node2")
```

---

## 📁 Project Structure

```
socket_example/
├── main.py                          # Entry point for each node
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── app_settings.json                # Default configuration template
│
├── configs/                         # Per-node configurations
│   ├── node1.json
│   ├── node2.json
│   └── node3.json
│
├── certs/                           # TLS certificates (generated)
│   ├── ca.crt                       # Certificate Authority (shared)
│   ├── ca.key                       # CA private key (keep secure!)
│   ├── node1.crt / node1.key        # Node 1 certificate pair
│   ├── node2.crt / node2.key        # Node 2 certificate pair
│   └── node3.crt / node3.key        # Node 3 certificate pair
│
├── scripts/
│   └── generate_certs.py            # Certificate generation script
│
└── app/                             # Application modules
    ├── socket_node/                 # Node management module
    │   ├── manifest.json
    │   └── module.py
    ├── message_demo/                # Message Mode demonstration
    │   ├── manifest.json
    │   └── module.py
    └── stream_demo/                 # Stream Mode demonstration
        ├── manifest.json
        └── module.py
```

---

## 🔧 Troubleshooting

### Issue: "Connection Refused"

**Symptoms:**
```
⚠️ Failed to connect to peer 'node2' at node2:8443
```

**Possible Causes:**
- Server not started on the target node
- Firewall blocking port 8443
- Incorrect hostname or port

**Solutions:**
```bash
# Verify server is running on target node
# Check logs for: "🖥️ Server started on 0.0.0.0:8443"

# Test connectivity
telnet <target-hostname> 8443
nc -zv <target-hostname> 8443

# Check firewall rules
sudo iptables -L | grep 8443
```

### Issue: "Certificate Verify Failed"

**Symptoms:**
```
❌ SSL handshake failed: certificate verify failed
```

**Possible Causes:**
- Different `ca.crt` on different nodes
- Certificate hostname mismatch
- Certificate expired

**Solutions:**
```bash
# Verify all nodes have identical ca.crt
md5sum certs/ca.crt  # Should match across all nodes

# Check certificate SAN entries
openssl x509 -in certs/node1.crt -text -noout | grep -A1 "Subject Alternative Name"

# Verify certificate validity
openssl x509 -in certs/node1.crt -noout -dates
```

### Issue: "Peer Not Connecting"

**Symptoms:**
- No "Connected to peer" messages
- Heartbeat failures

**Possible Causes:**
- Hostname not resolvable
- Network isolation between containers/servers
- Incorrect peer configuration

**Solutions:**
```bash
# Test DNS resolution
ping node2
nslookup node2

# If hostname doesn't resolve, use IP addresses in configs:
# Change: {"node_id": "node2", "host": "node2", "port": 8443}
# To:     {"node_id": "node2", "host": "10.0.0.102", "port": 8443}

# Verify network connectivity
traceroute node2
```

### Issue: "Port Already in Use"

**Symptoms:**
```
❌ Failed to start server on 0.0.0.0:8443: Address already in use
```

**Solutions:**
```bash
# Find process using the port
lsof -i :8443
netstat -tulpn | grep 8443

# Stop the conflicting process, or use a different port:
# Edit configs/nodeX.json:
# "listen_port": 8444

# Regenerate certificates with new port in SAN if needed
```

### Issue: "Module Load Failed"

**Symptoms:**
```
❌ Failed to load module: socket_node
❌ Missing required service: socket_api
```

**Solutions:**
```bash
# Verify module dependencies in app_settings.json
# Ensure these modules are loaded in order:
# 1. system_logger
# 2. network_ssl
# 3. network_socket
# 4. socket_node (application module)

# Check PYTHONPATH includes massir framework
echo $PYTHONPATH
```

---

## 📚 API Reference

### Using `socket_api` in Your Modules

```python
from massir.core.interfaces import IModule
from massir.modules.network_socket.core.types import (
    SocketMessage,
    MessageType,
)

class MyModule(IModule):
    name = "my_module"
    requires = ["socket_api", "core_logger"]
    
    async def load(self, context):
        self.socket = context.services.get("socket_api")
        self.logger = context.services.get("core_logger")
    
    async def start(self, context):
        # Connect to a peer
        client = await self.socket.connect_to_peer(
            peer_id="node-02",
            host="192.168.1.102",
            port=8443,
            mode="message",  # or "stream"
            use_tls=True,
        )
        
        # Send a message
        msg = SocketMessage(
            type=MessageType.DATA,
            payload={"action": "sync", "data": [1, 2, 3]},
        )
        await self.socket.send_message("node-02", msg)
        
        # Send raw bytes (Stream Mode)
        await self.socket.send_bytes("node-02", b"binary data")
        
        # Register message handler
        async def on_message(msg, conn):
            print(f"Received from {conn.peer_id}: {msg.payload}")
        
        self.socket.on_inbound_message(on_message)
```

### Using `node_service` in Application Modules

```python
class MyApplicationModule(IModule):
    name = "my_app"
    requires = ["node_service", "core_logger"]
    
    async def load(self, context):
        self.node = context.services.get("node_service")
    
    async def start(self, context):
        # Get connected peers
        peers = self.node.get_connected_peers()
        print(f"Connected to: {peers}")
        
        # Send to specific peer
        msg = SocketMessage(type=MessageType.DATA, payload="hello")
        success = await self.node.send_to_peer("node2", msg)
        
        # Broadcast to all peers
        results = await self.node.broadcast(msg)
        print(f"Broadcast results: {results}")
        
        # Check peer status
        if self.node.is_connected_to("node2"):
            print("node2 is online")
```

---

## 🔒 Security Best Practices

### Certificate Management

1. **Keep `ca.key` secure** - The CA private key should never be deployed to production nodes
2. **Use unique certificates** - Each node must have its own certificate/key pair
3. **Rotate certificates regularly** - Regenerate certificates before expiry
4. **Restrict key permissions** - Use `chmod 600` for `.key` files

```bash
# Recommended permissions
chmod 600 certs/*.key
chmod 644 certs/*.crt
```

### Network Security

1. **Use firewalls** - Only allow port 8443 between trusted nodes
2. **Enable mTLS** - Always verify both client and server certificates
3. **Monitor heartbeats** - Detect unauthorized nodes via heartbeat failures
4. **Audit connections** - Log all connection events for security monitoring

### Production Recommendations

1. **Use real CA** - For production, use Let's Encrypt or enterprise PKI
2. **Implement certificate pinning** - Verify specific certificate fingerprints
3. **Enable certificate hot-reload** - Update certificates without restart
4. **Monitor expiry dates** - Set up alerts for certificates expiring within 30 days

---

## 📊 Expected Output

When running a 3-node network successfully:

```
==========================================================
    Socket Example - NODE 1
    1.0.0
    Node 1 of distributed network
==========================================================

[INFO]    NetworkSSLModule loaded - TLS 1.3 ready
[INFO]    Server cert loaded: CN=node1 (expires in 364 days)
[INFO]    NetworkSocketModule loaded - Message/Stream modes ready
[INFO]    SocketNodeModule loaded - Node ID: node1

[INFO]    🖥️  Server started on 0.0.0.0:8443 (TLS)
[INFO]    ✅ Connected to peer 'node2' at node2:8443
[INFO]    ✅ Connected to peer 'node3' at node3:8443
[INFO]    SocketNode 'node1' ready - 2 peers configured

[INFO]    📢 Initial broadcast: 2/2 peers received
[INFO]    📨 Message from 'node2' type=data: {
              'event': 'periodic_hello',
              'node_id': 'node2',
              'message': 'Hello from node2!',
              'counter': 1
          }
[INFO]    📨 Message from 'node3' type=data: {
              'event': 'periodic_hello',
              'node_id': 'node3',
              'message': 'Hello from node3!',
              'counter': 1
          }
```

---

## 🎓 Learning Resources

- **Massir Framework**: [GitHub Repository](https://github.com/mass-shabani/massir_project)
- **TLS 1.3 Specification**: [RFC 8446](https://tools.ietf.org/html/rfc8446)
- **Python asyncio**: [Official Documentation](https://docs.python.org/3/library/asyncio.html)
- **cryptography Library**: [Documentation](https://cryptography.io/)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Submit a pull request

---

## 📜 License

This example is part of the **Massir** project and is licensed under the **MIT License**.

---

## 🎯 Next Steps

After mastering this example, explore:

1. **`system_network`** module - Advanced topology management (star, mesh, ring)
2. **`network_messaging`** module - Pub/Sub and Request/Reply patterns
3. **Custom protocols** - Build domain-specific protocols on top of `socket_api`
4. **Load balancing** - Implement round-robin or weighted distribution
5. **Monitoring** - Add metrics collection and alerting

---

<p align="center">
  <strong>Built with ❤️ using the Massir Framework</strong>
</p>