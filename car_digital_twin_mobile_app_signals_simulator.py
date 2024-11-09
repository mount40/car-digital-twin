import asyncio
import websockets
import random
import json
import time

# Assuming "admin" has user_id 1 (you can check the exact value in the SQLite database)
admin_user_id = 1

# Hard-coded normal ranges for OBD-II parameters
NORMAL_RANGES = {
    'battery_voltage': (12.5, 14.8),
    'engine_load': (0, 100),
    'rpm': (700, 6000),
    'coolant_temp': (70, 120),
    'throttle_position': (0, 100),
    'fuel_level': (0, 100),
    'intake_pressure': (20, 100),
    'maf_rate': (0, 200)
}

# Function to randomly generate out-of-norm values (with some probability)
def generate_out_of_norm_value(param_name, normal_value):
    # 10% chance to generate out-of-norm value
    if random.random() < 0.1:  
        min_val, max_val = NORMAL_RANGES[param_name]
        # Generate a value that is slightly outside the normal range
        if random.choice([True, False]):
            # Generate below the minimum
            return round(min_val - random.uniform(0.1, 1.0), 2)
        else:
            # Generate above the maximum
            return round(max_val + random.uniform(0.1, 1.0), 2)
    return normal_value

# Function to simulate all available OBD-II parameters
def simulate_obd_data():
    # Simulate normal data within the normal ranges
    battery_voltage = round(random.uniform(12.5, 14.8), 2)
    engine_load = round(random.uniform(0, 100), 2)
    rpm = round(random.uniform(700, 6000), 0)
    coolant_temp = round(random.uniform(70, 120), 2)
    throttle_position = round(random.uniform(0, 100), 2)
    fuel_level = round(random.uniform(0, 100), 2)
    intake_pressure = round(random.uniform(20, 100), 2)
    maf_rate = round(random.uniform(0, 200), 2)

    # Randomly generate out-of-norm values for some parameters
    battery_voltage = generate_out_of_norm_value('battery_voltage', battery_voltage)
    engine_load = generate_out_of_norm_value('engine_load', engine_load)
    rpm = generate_out_of_norm_value('rpm', rpm)
    coolant_temp = generate_out_of_norm_value('coolant_temp', coolant_temp)
    throttle_position = generate_out_of_norm_value('throttle_position', throttle_position)
    fuel_level = generate_out_of_norm_value('fuel_level', fuel_level)
    intake_pressure = generate_out_of_norm_value('intake_pressure', intake_pressure)
    maf_rate = generate_out_of_norm_value('maf_rate', maf_rate)

    return {
        "user_id": admin_user_id,  # Include the admin user_id
        "battery_voltage": battery_voltage,
        "engine_load": engine_load,
        "rpm": rpm,
        "coolant_temp": coolant_temp,
        "throttle_position": throttle_position,
        "fuel_level": fuel_level,
        "intake_pressure": intake_pressure,
        "maf_rate": maf_rate,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # Add timestamp
    }

# WebSocket client function to send data to the server
async def send_obd_data(uri):
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                # Simulate OBD-II data
                obd_data = simulate_obd_data()

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
