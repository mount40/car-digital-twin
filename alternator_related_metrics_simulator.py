import asyncio
import websockets
import random
import json
import time

# Assuming "admin" has user_id 1 (you can check the exact value in the SQLite database)
admin_user_id = 1

# Function to simulate battery voltage, engine load, and RPM
def simulate_obd_data():
    # Simulate battery voltage between 12.5V and 14.8V
    battery_voltage = round(random.uniform(12.5, 14.8), 2)

    # Simulate engine load between 0% and 100%
    engine_load = round(random.uniform(0, 100), 2)

    # Simulate RPM between 700 and 6000 RPM
    rpm = round(random.uniform(700, 6000), 0)

    return {
        "user_id": admin_user_id,  # Include the admin user_id
        "battery_voltage": f"{battery_voltage} V",
        "engine_load": f"{engine_load} %",
        "rpm": f"{rpm} RPM"
    }

# WebSocket client function to send data to the server
async def send_obd_data(uri):
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                # Simulate OBD-II data
                obd_data = simulate_obd_data()
                obd_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                # Send data as JSON via WebSocket
                await websocket.send(json.dumps(obd_data))
                print(f"Sent simulated data: {obd_data}")

                # Wait for 1 second before sending the next batch of simulated data
                await asyncio.sleep(1)

            except websockets.ConnectionClosed:
                print("Connection to server closed")
                break

# Main function to initiate the WebSocket client
if __name__ == "__main__":
    uri = "ws://localhost:8765"  # Change this URI to point to the WebSocket server you want to connect to

    try:
        asyncio.run(send_obd_data(uri))
    except KeyboardInterrupt:
        print("WebSocket client stopped.")
