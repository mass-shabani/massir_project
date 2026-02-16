"""
Script to populate sample data for users and products tables.
Run this script while the server is running or independently.
"""
import asyncio
import random
from datetime import datetime, timedelta


async def seed_data():
    """Populate sample data for users and products."""
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from massir.modules.system_database import DatabaseService, TableDef, ColumnDef, ColumnType
    
    # Initialize database service
    db = DatabaseService()
    
    # Configure SQLite connection
    db_configs = [
        {
            "name": "default",
            "driver": "sqlite",
            "path": "Examples/database_example/data/example.db",
            "cache_enabled": True,
            "cache_ttl": 300
        }
    ]
    
    await db.initialize(db_configs)
    
    try:
        # Create products table if not exists
        if not await db.default.table_exists("products"):
            products_table = TableDef(
                name="products",
                columns=[
                    ColumnDef(name="id", type=ColumnType.INTEGER, primary_key=True, auto_increment=True, nullable=False),
                    ColumnDef(name="name", type=ColumnType.VARCHAR, length=100, nullable=False),
                    ColumnDef(name="description", type=ColumnType.TEXT, nullable=True),
                    ColumnDef(name="price", type=ColumnType.DECIMAL, precision=10, scale=2, nullable=False),
                    ColumnDef(name="stock", type=ColumnType.INTEGER, default=0, nullable=False),
                    ColumnDef(name="is_available", type=ColumnType.BOOLEAN, default=True, nullable=False),
                    ColumnDef(name="created_at", type=ColumnType.TIMESTAMP, nullable=True)
                ],
                primary_key=["id"],
                if_not_exists=True
            )
            result = await db.default.schema.create_table(products_table)
            if result.success:
                print("✅ Products table created")
            else:
                print(f"❌ Failed to create products table: {result.error}")
        
        # Sample user data
        first_names = ["Ali", "Reza", "Mohammad", "Hassan", "Hossein", "Mehdi", "Amir", "Saman", 
                       "Sara", "Zahra", "Maryam", "Fateme", "Narges", "Leila", "Mina"]
        last_names = ["Ahmadi", "Hosseini", "Mohammadi", "Rezaei", "Karimi", "Jafari", "Sadeghi",
                      "Kashani", "Tehrani", "Shirazi", "Esfahani", "Mashhadi", "Tabrizi", "Qomi"]
        domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "mail.ir"]
        
        users_data = []
        for i in range(1, 31):
            first = random.choice(first_names)
            last = random.choice(last_names)
            username = f"{first.lower()}{last.lower()}{i}"
            domain = random.choice(domains)
            email = f"{username}@{domain}"
            full_name = f"{first} {last}"
            is_active = random.choice([True, True, True, False])  # 75% active
            created_at = datetime.now() - timedelta(days=random.randint(1, 365))
            
            users_data.append({
                "username": username,
                "email": email,
                "password_hash": f"hashed_password_{i}",
                "full_name": full_name,
                "is_active": is_active,
                "created_at": created_at.isoformat(),
                "updated_at": created_at.isoformat()
            })
        
        # Insert users
        result = await db.insert_many("users", users_data)
        if result.success:
            print(f"✅ Inserted {result.affected_rows} users")
        else:
            print(f"❌ Failed to insert users: {result.error}")
        
        # Sample product data
        product_names = [
            ("Laptop Pro 15", "High-performance laptop with 15-inch display", 1299.99),
            ("Wireless Mouse", "Ergonomic wireless mouse with precision tracking", 29.99),
            ("Mechanical Keyboard", "RGB mechanical keyboard with Cherry MX switches", 149.99),
            ("USB-C Hub", "7-in-1 USB-C hub with HDMI and card reader", 49.99),
            ("Monitor 27\"", "4K IPS monitor with HDR support", 399.99),
            ("Webcam HD", "1080p webcam with built-in microphone", 79.99),
            ("External SSD 1TB", "Portable SSD with USB 3.2 connectivity", 119.99),
            ("Wireless Earbuds", "True wireless earbuds with noise cancellation", 199.99),
            ("Gaming Chair", "Ergonomic gaming chair with lumbar support", 349.99),
            ("Desk Lamp LED", "Adjustable LED desk lamp with color temperature control", 39.99),
            ("Bluetooth Speaker", "Portable Bluetooth speaker with 20h battery", 59.99),
            ("Graphics Tablet", "Digital drawing tablet with pressure sensitivity", 89.99),
            ("USB Microphone", "Condenser microphone for streaming and recording", 129.99),
            ("Laptop Stand", "Adjustable aluminum laptop stand for better ergonomics", 49.99),
            ("Cable Organizer", "Desk cable management system", 19.99),
            ("Power Bank 20000mAh", "High-capacity power bank with fast charging", 39.99),
            ("Smart Watch", "Fitness tracker with heart rate monitor", 249.99),
            ("Wireless Charger", "Qi wireless charging pad", 29.99),
            ("Router WiFi 6", "Dual-band WiFi 6 router with 4 antennas", 149.99),
            ("Ethernet Switch", "8-port Gigabit Ethernet switch", 34.99),
            ("HDMI Cable 2m", "High-speed HDMI cable with Ethernet", 12.99),
            ("Mouse Pad XL", "Extended mouse pad with stitched edges", 24.99),
            ("Headphone Stand", "Aluminum headphone stand with USB port", 34.99),
            ("Screen Cleaner Kit", "Screen cleaning spray and microfiber cloth", 14.99),
            ("Privacy Screen 15\"", "Laptop privacy filter for 15-inch screens", 49.99),
            ("USB Flash Drive 64GB", "USB 3.0 flash drive with metal casing", 14.99),
            ("Webcam Cover", "Slide webcam cover pack of 6", 7.99),
            ("Cable Ties Pack", "Reusable cable ties pack of 100", 9.99),
            ("Monitor Light Bar", "LED light bar for monitor top", 59.99),
            ("Wrist Rest", "Memory foam wrist rest for keyboard", 19.99)
        ]
        
        products_data = []
        for i, (name, desc, price) in enumerate(product_names, 1):
            stock = random.randint(0, 100)
            is_available = stock > 0
            created_at = datetime.now() - timedelta(days=random.randint(1, 180))
            
            products_data.append({
                "name": name,
                "description": desc,
                "price": price,
                "stock": stock,
                "is_available": is_available,
                "created_at": created_at.isoformat()
            })
        
        # Insert products
        result = await db.insert_many("products", products_data)
        if result.success:
            print(f"✅ Inserted {result.affected_rows} products")
        else:
            print(f"❌ Failed to insert products: {result.error}")
        
        print("\n📊 Summary:")
        user_count = await db.count("users")
        product_count = await db.count("products")
        print(f"   Total users: {user_count}")
        print(f"   Total products: {product_count}")
        
    finally:
        await db.close_all()


if __name__ == "__main__":
    asyncio.run(seed_data())
