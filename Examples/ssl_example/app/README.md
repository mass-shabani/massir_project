# 🔐 SSL Example

This example project provides a comprehensive demonstration of the `network_ssl` module within the **Massir framework**. It showcases how to integrate TLS/SSL operations into a modular application architecture.

## 🎯 Features Demonstrated

### 1. TLS 1.3 Support
- Server and client SSL context creation
- TLS 1.3 as default with TLS 1.2 fallback
- Security hardening (no compression, secure cipher suites)

### 2. mTLS (Mutual TLS)
- Client certificate authentication
- Server verification of client certificates
- Bidirectional certificate validation

### 3. Certificate Management
- Certificate loading and parsing
- Information extraction (subject, issuer, SAN, expiry)
- Validation and expiry checking
- Hot-reload support for certificate updates

### 4. SNI (Server Name Indication)
- Client context creation with SNI hostname
- Support for multiple domains on single IP

### 5. Real TLS Connections
- Secure server creation with asyncio
- Client connections with certificate verification
- End-to-end encrypted communication

## 📦 Project Modules

### `ssl_tester`
An automated testing module that executes a full suite of SSL/TLS operations on startup, including real server/client connections.

### `ssl_demo`
A demonstration module that provides `ssl_service` for other modules and runs a complete demo of secure communications.

## 🚀 How to Run

### Step 1: Generate Test Certificates

Before running the example, generate self-signed certificates:

```bash
cd Examples/ssl_example
python scripts/generate_certs.py
```

This will create the following files in the certs/ directory:

    ca.crt / ca.key - Certificate Authority
    server.crt / server.key - Server certificate
    client.crt / client.key - Client certificate (for mTLS)

Step 2: Run the Example

bash
1

📊 Expected Output

text
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
97
98
99
100
101
102
103
104
105
106
107
108
109
110
111
112
113
114
115
116
117
118
119
120
121
122
123
124
125
126
127
128
129
130
131
132
133
134
135
136
137
138

⚙️ Configuration
The network_ssl module settings are managed via app_settings.json:

json
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23

📝 Using ssl_api in Your Own Modules

python
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27

🔧 Certificate Structure
The test certificates follow this chain:

1
2
3
4
5
6
7
8

📜 License
This example is part of the Massir project and is licensed under the MIT License.

