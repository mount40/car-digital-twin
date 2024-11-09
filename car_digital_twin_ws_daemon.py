import asyncio
import websockets
import json
import sqlite3
import bcrypt

# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()

    # Create table for user authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Create table for storing OBD-II data with more parameters
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS obd_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            battery_voltage REAL,
            engine_load REAL,
            rpm REAL,
            coolant_temp REAL,
            throttle_position REAL,
            fuel_level REAL,
            intake_pressure REAL,
            maf_rate REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create table for norm ranges
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS norm_ranges (
            metric_name TEXT PRIMARY KEY,
            min_value REAL,
            max_value REAL
        )
    ''')

    # Create table for logging out-of-norm events
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS out_of_norm_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            metric_name TEXT,
            value REAL,
            timestamp TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()

    # Create default admin account if not exists
    cursor.execute('''
        SELECT * FROM users WHERE username = ?
    ''', ('admin',))
    if cursor.fetchone() is None:
        hashed_password = bcrypt.hashpw('boogy332!'.encode('utf-8'), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (username, password)
            VALUES (?, ?)
        ''', ('admin', hashed_password))
        conn.commit()
        print("Admin account created with default credentials: username: admin, password: boogy332!")

    # Insert default norm ranges if not exists
    default_ranges = {
        'battery_voltage': (12.5, 14.8),
        'engine_load': (0, 100),
        'rpm': (700, 6000),
        'coolant_temp': (70, 120),
        'throttle_position': (0, 100),
        'fuel_level': (0, 100),
        'intake_pressure': (20, 100),
        'maf_rate': (0, 200)
    }

    for metric, (min_val, max_val) in default_ranges.items():
        cursor.execute('''
            INSERT OR IGNORE INTO norm_ranges (metric_name, min_value, max_value)
            VALUES (?, ?, ?)
        ''', (metric, min_val, max_val))

    conn.commit()
    conn.close()

# Function to check if user exists
def user_exists(user_id):
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM users WHERE id = ?
    ''', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

# Function to store OBD-II data in SQLite
def store_data_in_db(user_id, data):
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO obd_data (
            user_id, timestamp, battery_voltage, engine_load, rpm,
            coolant_temp, throttle_position, fuel_level, intake_pressure, maf_rate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        data.get('timestamp'),
        data.get('battery_voltage'),
        data.get('engine_load'),
        data.get('rpm'),
        data.get('coolant_temp'),
        data.get('throttle_position'),
        data.get('fuel_level'),
        data.get('intake_pressure'),
        data.get('maf_rate')
    ))
    conn.commit()
    conn.close()

# Function to get the normal range for a metric
def get_norm_range(metric_name):
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT min_value, max_value FROM norm_ranges WHERE metric_name = ?
    ''', (metric_name,))
    result = cursor.fetchone()
    conn.close()
    return result

# Function to log out-of-norm events
def log_out_of_norm(user_id, metric_name, value, timestamp):
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO out_of_norm_logs (user_id, metric_name, value, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, metric_name, value, timestamp))
    conn.commit()
    conn.close()

# WebSocket handler
async def obd_websocket(websocket, path):
    while True:
        try:
            # Receive data from WebSocket client
            message = await websocket.recv()
            data = json.loads(message)

            # Check if the user_id is valid
            if 'user_id' not in data:
                await websocket.send(json.dumps({"error": "user_id missing in message"}))
                continue

            user_id = data['user_id']
            if not user_exists(user_id):
                await websocket.send(json.dumps({"error": "Invalid user_id"}))
                continue

            # Store the incoming data in SQLite
            store_data_in_db(user_id, data)

            # Check if any metrics are out of norm
            out_of_norm_metrics = []
            for metric, value in data.items():
                if metric in ['battery_voltage', 'engine_load', 'rpm', 'coolant_temp',
                              'throttle_position', 'fuel_level', 'intake_pressure', 'maf_rate']:
                    norm_range = get_norm_range(metric)
                    if norm_range:
                        min_val, max_val = norm_range
                        if not (min_val <= value <= max_val):
                            out_of_norm_metrics.append(metric)
                            # Log out-of-norm event in the database
                            log_out_of_norm(user_id, metric, value, data.get('timestamp'))

            # Send alert if any metrics are out of norm
            if out_of_norm_metrics:
                warning_message = {
                    "warning": "Out of norm metrics detected",
                    "metrics": out_of_norm_metrics
                }
                await websocket.send(json.dumps(warning_message))

        except websockets.ConnectionClosed:
            print("Client disconnected")
            break

# WebSocket server coroutine
async def start_websocket_server():
    async with websockets.serve(obd_websocket, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    # Initialize SQLite database
    init_db()

    # Run WebSocket server
    asyncio.run(start_websocket_server())
