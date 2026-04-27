# database.py
# This file creates all the tables in our SQLite database

import sqlite3      # Lets us work with SQLite database
import hashlib      # Lets us encrypt passwords
import logging      # Lets us record activity logs
import os           # Lets us work with files/folders

# Set up logging - this records all activity to a file
logging.basicConfig(
    filename='northshore.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# This is the name of our database file
DATABASE_NAME = 'northshore.db'

def get_connection():
    """Connect to the database - think of this like opening a file"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Makes results easier to read
    return conn

def create_tables():
    """Create all the tables we need in the database"""
    conn = get_connection()
    cursor = conn.cursor()  # Cursor is like a pen that writes to the database

    # --- TABLE 1: Users (Login System) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL UNIQUE,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL CHECK(role IN ('admin','manager','warehouse_staff','driver')),
            full_name   TEXT NOT NULL,
            email       TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            is_active   INTEGER DEFAULT 1
        )
    ''')

    # --- TABLE 2: Warehouses ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Warehouses (
            warehouse_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            location        TEXT NOT NULL,
            capacity        INTEGER,
            manager_name    TEXT,
            phone           TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    ''')

    # --- TABLE 3: Drivers ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Drivers (
            driver_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name       TEXT NOT NULL,
            licence_number  TEXT NOT NULL UNIQUE,
            phone           TEXT,
            shift           TEXT CHECK(shift IN ('morning','afternoon','night')),
            warehouse_id    INTEGER,
            status          TEXT DEFAULT 'available',
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (warehouse_id) REFERENCES Warehouses(warehouse_id)
        )
    ''')

    # --- TABLE 4: Vehicles ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Vehicles (
            vehicle_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            registration        TEXT NOT NULL UNIQUE,
            vehicle_type        TEXT,
            capacity_kg         REAL,
            maintenance_due     TEXT,
            availability        TEXT DEFAULT 'available',
            warehouse_id        INTEGER,
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (warehouse_id) REFERENCES Warehouses(warehouse_id)
        )
    ''')

    # --- TABLE 5: Shipments ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Shipments (
            shipment_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number        TEXT NOT NULL UNIQUE,
            sender_name         TEXT NOT NULL,
            sender_address      TEXT,
            receiver_name       TEXT NOT NULL,
            receiver_address    TEXT,
            item_description    TEXT,
            weight_kg           REAL,
            status              TEXT DEFAULT 'in_transit' 
                                CHECK(status IN ('in_transit','delivered','delayed','returned')),
            driver_id           INTEGER,
            vehicle_id          INTEGER,
            warehouse_id        INTEGER,
            route_details       TEXT,
            delivery_date       TEXT,
            transport_cost      REAL,
            payment_status      TEXT DEFAULT 'unpaid',
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (driver_id)    REFERENCES Drivers(driver_id),
            FOREIGN KEY (vehicle_id)   REFERENCES Vehicles(vehicle_id),
            FOREIGN KEY (warehouse_id) REFERENCES Warehouses(warehouse_id)
        )
    ''')

    # --- TABLE 6: Inventory ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Inventory (
            inventory_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name       TEXT NOT NULL,
            warehouse_id    INTEGER,
            quantity        INTEGER DEFAULT 0,
            reorder_level   INTEGER DEFAULT 10,
            item_location   TEXT,
            last_updated    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (warehouse_id) REFERENCES Warehouses(warehouse_id)
        )
    ''')

    # --- TABLE 7: Incidents ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Incidents (
            incident_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id     INTEGER,
            incident_type   TEXT CHECK(incident_type IN 
                            ('delay','route_change','damaged','failed_delivery')),
            description     TEXT,
            reported_at     TEXT DEFAULT (datetime('now')),
            resolved        INTEGER DEFAULT 0,
            FOREIGN KEY (shipment_id) REFERENCES Shipments(shipment_id)
        )
    ''')

    # --- TABLE 8: Audit Log (Security) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS AuditLog (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT,
            action      TEXT,
            table_name  TEXT,
            timestamp   TEXT DEFAULT (datetime('now')),
            details     TEXT
        )
    ''')

    conn.commit()   # Save everything
    conn.close()    # Close the database connection
    print("✅ All tables created successfully!")
    logging.info("Database tables created successfully")

def hash_password(password):
    """
    Convert a plain password into an encrypted version.
    Example: 'mypassword123' → 'a8f5f167f...' (unreadable)
    This means even if someone sees the database, they can't read passwords.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def create_default_admin():
    """Create a default admin account so we can log in for the first time"""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if admin already exists
    cursor.execute("SELECT * FROM Users WHERE username = 'admin'")
    if cursor.fetchone() is None:
        # Create the admin user with encrypted password
        hashed_pw = hash_password('Admin123!')
        cursor.execute('''
            INSERT INTO Users (username, password, role, full_name, email)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', hashed_pw, 'admin', 'System Administrator', 'admin@northshore.com'))
        conn.commit()
        print("✅ Default admin created! Username: admin | Password: Admin123!")

    conn.close()

def initialise_database():
    """Run this once to set up the entire database"""
    print("Setting up Northshore Logistics Database...")
    create_tables()
    create_default_admin()
    print("✅ Database ready!")

# This runs the setup if you run this file directly
if __name__ == '__main__':
    initialise_database()