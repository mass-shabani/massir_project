# Web API Example

This example demonstrates how to use the `network_fastapi` module to create a web application with Massir framework.

## Features

- **Users API**: CRUD operations for user management
- **Network Info**: Network utilities and information endpoints
- **No FastAPI imports**: Uses `http_api`, `router_api`, and `net_api` abstractions

## Running the Example

```bash
cd Examples/web_api_example
python main.py
```

The API will be available at `http://127.0.0.1:8000`

## API Endpoints

### System Endpoints

| Method | Path | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| GET | `/info` | Service information |
| GET | `/network` | Network information |

### Users API

| Method | Path | Description |
|--------|-------|-------------|
| GET | `/users` | Get all users |
| GET | `/users/{id}` | Get user by ID |
| POST | `/users` | Create new user |
| PUT | `/users/{id}` | Update user |
| DELETE | `/users/{id}` | Delete user |

### Network Info

| Method | Path | Description |
|--------|-------|-------------|
| GET | `/hostname` | Get system hostname |
| GET | `/ip` | Get IP address |
| GET | `/network/info` | Get network information |
| GET | `/network/validate/{ip}` | Validate IP address |
| GET | `/network/port/{port}` | Check port availability |
| GET | `/network/parse` | Parse URL |
| GET | `/network/build` | Build URL |

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Example Requests

### Create a User

```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

### Get All Users

```bash
curl http://127.0.0.1:8000/users
```

### Get Network Info

```bash
curl http://127.0.0.1:8000/network/info
```

### Validate IP Address

```bash
curl http://127.0.0.1:8000/network/validate/192.168.1.1
```

## Module Structure

```
web_api_example/
├── main.py                 # Application entry point
├── app_settings.json        # Configuration
├── README.md              # This file
└── app/
    ├── users_api/          # Users management module
    │   ├── manifest.json
    │   └── module.py
    └── network_info/        # Network utilities module
        ├── manifest.json
        └── module.py
```

## Key Concepts

### Using http_api

The `http_api` provides decorators for creating HTTP routes without importing FastAPI:

```python
@self.http_api.get("/users", tags=["users"])
async def get_users():
    return {"users": []}
```

### Using net_api

The `net_api` provides network utilities:

```python
hostname = self.net_api.get_hostname()
ip_address = self.net_api.get_ip_address()
is_available = self.net_api.is_port_available(8000)
```

### Using router_api

The `router_api` allows creating separate routers:

```python
router = self.router_api.create(prefix="/api/v1", tags=["api"])
```
