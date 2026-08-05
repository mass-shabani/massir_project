# 🧪 Network Nodes Test Example

Comprehensive test suite for `system_network` module demonstrating all capabilities under both socket and websocket transports.

## 🎯 Features Tested

| Feature | Description |
|---------|-------------|
| **Transport Agnostic** | Socket + WebSocket in same network |
| **Topology Management** | Mesh topology with auto-connections |
| **Node Registry** | 4 nodes with metadata and capabilities |
| **Direct Messaging** | Single-hop message delivery |
| **Broadcast** | Send to all nodes |
| **Capability Messaging** | Send to nodes with specific capabilities |
| **Multi-Hop Routing** | Message routing through intermediate nodes |
| **Message Envelope** | TTL, routing info, trace ID |
| **Network Monitoring** | Health status, connection tracking |
| **Event System** | on_message, on_peer_connected, on_peer_disconnected |
| **Auto-Shutdown** | Graceful shutdown after test duration |
| **Final Report** | Comprehensive test results table |

## 📂 Project Structure

```
network_nodes_test_example/
├── main.py                      # Entry point
├── app_settings.json            # Default config
├── configs/
│   ├── node1.json              # Socket transport
│   ├── node2.json              # Socket transport
│   ├── node3.json              # Socket transport
│   └── node4.json              # WebSocket transport
├── certs/                       # TLS certificates
├── scripts/
│   └── generate_certs.py       # Certificate generator
└── app/
    ├── network_tester/         # Test runner
    └── network_reporter/       # Report generator
```

## 🚀 Quick Start

### 1. Generate Certificates

```bash
cd Examples/network_nodes_test_example
python scripts/generate_certs.py
```

### 2. Update IP Addresses

Edit `configs/node*.json` files to match your network IPs.

### 3. Run Nodes

Open 4 terminals and run:

```bash
# Terminal 1
NODE_ID=node1 python main.py

# Terminal 2
NODE_ID=node2 python main.py

# Terminal 3
NODE_ID=node3 python main.py

# Terminal 4
NODE_ID=node4 python main.py
```

### 4. Watch the Test

Nodes will:
1. Start servers (socket or websocket)
2. Connect to all peers
3. Run comprehensive tests
4. Display results
5. Auto-shutdown after 60 seconds
6. Show final report

## ⚙️ Configuration

### Test Duration

In `configs/node*.json`:

```json
{
    "test_config": {
        "test_duration_seconds": 60,
        "warmup_seconds": 10,
        "test_interval_seconds": 5
    }
}
```

### Tests to Run

```json
{
    "network_tester": {
        "tests": [
            "network_status",
            "direct_messaging",
            "broadcast",
            "capability_messaging",
            "routing_table",
            "multi_hop",
            "envelope_inspection",
            "event_handlers"
        ]
    }
}
```

## 📊 Sample Output

### Test Execution

```
╔════════════════════════════════════════════════════════════╗
║  Network Test - NODE 1 (Socket Transport)                  ║
╚════════════════════════════════════════════════════════════╝

[INFO] NetworkTesterModule loaded
[INFO] NetworkReporterModule loaded
[INFO] SystemNetworkModule loaded - node='node1', transports=['socket']

╔════════════════════════════════════════════════════════════╗
║  🖥️  SOCKET SERVER STARTED                                 ║
╠════════════════════════════════════════════════════════════╣
║  Node ID:  node1                                           ║
║  Address:  0.0.0.0:8443                                    ║
╚════════════════════════════════════════════════════════════╝

✅ PEER CONNECTED: node2
✅ PEER CONNECTED: node3
✅ PEER CONNECTED: node4

🧪 Test configuration: warmup=10s, duration=60s, interval=5s
⏳ Warmup phase: waiting 10s for connections...
✅ Warmup complete, starting tests...
```

### Final Report

```
════════════════════════════════════════════════════════════
  📊 COMPREHENSIVE SYSTEM_NETWORK TEST REPORT
════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│  🧪 TEST RESULTS                                            │
├─────────────────────────────────────────────────────────────┤
│  Test Name                    │ Status  │ Details           │
├─────────────────────────────────────────────────────────────┤
│  network_status               │ ✅ PASS │ Health: 100%      │
│  direct_messaging             │ ✅ PASS │ Direct            │
│  broadcast                    │ ✅ PASS │ 3 peers           │
│  capability_messaging         │ ✅ PASS │ 5 capabilities    │
│  routing_table                │ ✅ PASS │ 3/3 direct        │
│  multi_hop                    │ ✅ PASS │ N/A               │
│  envelope_inspection          │ ✅ PASS │ 12 envelopes      │
│  event_handlers               │ ✅ PASS │ 3 connections     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  📈 STATISTICS                                              │
├─────────────────────────────────────────────────────────────┤
│  Messages Sent                  │         24                │
│  Messages Received              │         18                │
│  Broadcasts Sent                │          6                │
│  Capability Messages            │         12                │
│  Peer Connections               │          3                │
│  Peer Disconnections            │          0                │
├─────────────────────────────────────────────────────────────┤
│  Duration: 70.5s                                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🌐 FINAL NETWORK STATUS                                    │
├─────────────────────────────────────────────────────────────┤
│  Self Node                        │ node1                   │
│  Topology                         │ mesh                    │
│  Total Nodes                      │ 4                       │
│  Required Peers                   │ 3                       │
│  Connected Peers                  │ 3                       │
│  Health                           │ 100.0%                  │
│  Fully Connected                  │ Yes                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  📋 SUMMARY                                                 │
├─────────────────────────────────────────────────────────────┤
│  Total Tests                    │ 8                         │
│  Passed                         │ 8 ✅                      │
│  Failed                         │ 0 ✅                      │
│  Success Rate                   │ 100.0%                    │
├─────────────────────────────────────────────────────────────┤
│  🎉 ALL TESTS PASSED - SYSTEM_NETWORK FULLY OPERATIONAL     │
└─────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════
  ✅ REPORT COMPLETE - SHUTDOWN INITIATED
════════════════════════════════════════════════════════════
```

## 🔧 Customization

### Change Topology

In `configs/node*.json`:

```json
{
    "system_network": {
        "topology": {
            "type": "star",
            "hub_node": "node1"
        }
    }
}
```

### Add More Nodes

1. Add node config in `configs/node5.json`
2. Update all other node configs to include node5
3. Generate certificate: `python scripts/generate_certs.py`
4. Run: `NODE_ID=node5 python main.py`

### Disable Auto-Shutdown

In `configs/node*.json`:

```json
{
    "test_config": {
        "test_duration_seconds": 0
    }
}
```

## 📝 Notes

- Node 1, 2, 3 use **socket transport** (TCP/TLS)
- Node 4 uses **websocket transport** (WSS)
- All nodes can communicate seamlessly
- Tests run periodically during test duration
- Report is generated during shutdown
- All tests are transport-agnostic

## 📜 License

Part of the **Massir** project. Licensed under the MIT License.