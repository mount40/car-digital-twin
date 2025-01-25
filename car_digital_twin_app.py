import asyncio
import websockets
import json
import streamlit as st
import pandas as pd
import sqlite3
import bcrypt  # For password hashing
import threading

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

    # Create table for storing OBD-II data with user association
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS obd_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            battery_voltage REAL,
            engine_load REAL,
            rpm REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()

    # Create a default admin account if it doesn't exist
    cursor.execute('''
        SELECT * FROM users WHERE username = ?
    ''', ('admin',))
    if cursor.fetchone() is None:
        # Hash the default password (new complex password: "boogy332!")
        hashed_password = bcrypt.hashpw('boogy332!'.encode('utf-8'), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (username, password)
            VALUES (?, ?)
        ''', ('admin', hashed_password))
        conn.commit()
        print("Admin account created with default credentials: username: admin, password: boogy332!")

    conn.close()

# Function to authenticate user
def authenticate_user(username, password):
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, password FROM users WHERE username = ?
    ''', (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_id, hashed_password = user
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            return user_id
    return None

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

# Function to store data in SQLite
def store_data_in_db(user_id, timestamp, battery_voltage, engine_load, rpm):
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO obd_data (user_id, timestamp, battery_voltage, engine_load, rpm)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, timestamp, battery_voltage, engine_load, rpm))
    conn.commit()
    conn.close()

# Streamlit login function using st.form
def login():
    st.title("Login to OBD-II Data Dashboard")

    # Create a login form using st.form
    with st.form(key="login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            user_id = authenticate_user(username, password)
            if user_id:
                st.session_state['user_id'] = user_id
                st.session_state['logged_in'] = True
                st.success("Login successful!")
            else:
                st.error("Invalid username or password")

# WebSocket handler
async def obd_websocket(websocket, path):
    global battery_voltage_data, engine_load_data, rpm_data, timestamps
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

            # Update the text displays
            battery_voltage_display.markdown(f"**Battery Voltage:** {data['battery_voltage']}")
            engine_load_display.markdown(f"**Engine Load:** {data['engine_load']}")
            rpm_display.markdown(f"**RPM:** {data['rpm']}")

            # Parse the numeric values for graphing
            battery_voltage_value = float(data['battery_voltage'].split()[0])
            engine_load_value = float(data['engine_load'].split()[0])
            rpm_value = float(data['rpm'].split()[0])

            # Append the values to the data containers
            timestamps.append(data['timestamp'])
            battery_voltage_data.append(battery_voltage_value)
            engine_load_data.append(engine_load_value)
            rpm_data.append(rpm_value)

            # Store the incoming data in SQLite, associated with the provided user_id
            store_data_in_db(user_id, data['timestamp'], battery_voltage_value, engine_load_value, rpm_value)

            # Trim the lists to the last 20 records
            if len(timestamps) > 20:
                timestamps = timestamps[-20:]
                battery_voltage_data = battery_voltage_data[-20:]
                engine_load_data = engine_load_data[-20:]
                rpm_data = rpm_data[-20:]

            # Update the charts by re-creating them with the last 20 records
            battery_voltage_chart.line_chart(pd.DataFrame({'Battery Voltage (V)': battery_voltage_data}, index=timestamps))
            engine_load_chart.line_chart(pd.DataFrame({'Engine Load (%)': engine_load_data}, index=timestamps))
            rpm_chart.line_chart(pd.DataFrame({'RPM': rpm_data}, index=timestamps))

        except websockets.ConnectionClosed:
            print("Client disconnected")
            break

# WebSocket server coroutine
async def start_websocket_server():
    async with websockets.serve(obd_websocket, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()  # Run forever

# Main function to run the WebSocket server and Streamlit
def main():
    # Initialize SQLite database
    init_db()

    # Handle user login
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login()  # Show the login form
    else:
        # Create columns for the layout
        col1, col2, col3 = st.columns(3)

        # Create placeholders for the current values and charts in separate columns
        with col1:
            global battery_voltage_display, battery_voltage_chart
            battery_voltage_display = st.empty()
            battery_voltage_chart = st.line_chart([])

        with col2:
            global engine_load_display, engine_load_chart
            engine_load_display = st.empty()
            engine_load_chart = st.line_chart([])

        with col3:
            global rpm_display, rpm_chart
            rpm_display = st.empty()
            rpm_chart = st.line_chart([])

        # Data containers for the charts
        global battery_voltage_data, engine_load_data, rpm_data, timestamps
        battery_voltage_data = []
        engine_load_data = []
        rpm_data = []
        timestamps = []

        # Run the WebSocket server asynchronously
        asyncio.run(start_websocket_server())

if __name__ == "__main__":
    main()
