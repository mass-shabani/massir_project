# Database Example

This example demonstrates the `system_database` module for working with relational databases.

## Features Demonstrated

- **Schema Management (DDL)**: Creating tables with columns, indexes, and foreign keys
- **Record Operations (DML)**: Insert, update, delete, and query records
- **Transactions**: Using transactions with commit/rollback
- **Batch Operations**: Inserting multiple records efficiently
- **Raw SQL**: Executing custom SQL queries
- **Connection Pooling**: Managing database connections efficiently
- **Query Caching**: Caching query results for better performance

## Supported Databases

- **SQLite** (default for this example)
- **PostgreSQL**
- **MySQL**

## Running the Example

```bash
cd Examples/database_example
python main.py
```

## API Endpoints

Once running, the following endpoints are available:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all users |
| GET | `/users/{id}` | Get a specific user |
| POST | `/users` | Create a new user |
| PUT | `/users/{id}` | Update a user |
| DELETE | `/users/{id}` | Delete a user |
| POST | `/users/batch` | Create multiple users |
| GET | `/users/count` | Count total users |
| POST | `/users/transaction` | Transaction example |
| GET | `/db/stats` | Database statistics |

## Example Requests

### Create a User
```bash
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "full_name": "John Doe"}'
```

### List Users
```bash
curl http://localhost:8080/users
```

### Update a User
```bash
curl -X PUT http://localhost:8080/users/1 \
  -H "Content-Type: application/json" \
  -d '{"full_name": "John Smith"}'
```

### Delete a User
```bash
curl -X DELETE http://localhost:8080/users/1
```

## Configuration

The database configuration is in `app_settings.json`:

```json
{
    "database": {
        "connections": [
            {
                "name": "default",
                "driver": "sqlite",
                "path": "{app_dir}/data/example.db",
                "cache_enabled": true,
                "cache_ttl": 300
            }
        ]
    }
}
```

### PostgreSQL Configuration

```json
{
    "name": "postgres_db",
    "driver": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "myapp",
    "user": "admin",
    "password": "secret",
    "pool_min_size": 5,
    "pool_max_size": 20
}
```

### MySQL Configuration

```json
{
    "name": "mysql_db",
    "driver": "mysql",
    "host": "localhost",
    "port": 3306,
    "database": "myapp",
    "user": "admin",
    "password": "secret",
    "charset": "utf8mb4",
    "pool_min_size": 5,
    "pool_max_size": 20
}
```

## Using Multiple Databases

You can configure multiple database connections:

```json
{
    "database": {
        "connections": [
            {
                "name": "main",
                "driver": "postgresql",
                "host": "localhost",
                "database": "main_db"
            },
            {
                "name": "cache",
                "driver": "sqlite",
                "path": "{app_dir}/data/cache.db"
            }
        ]
    }
}
```

Access specific connections:

```python
# Use default connection
await db.find_many("users")

# Use specific connection
await db.find_many("users", connection="cache")