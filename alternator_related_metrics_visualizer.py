import asyncio
import websockets
import json
import streamlit as st
import pandas as pd
import time

# Initialize Streamlit components
st.title("Real-time OBD-II Data Visualization with Graphs")

# Create columns for the layout
col1, col2, col3 = st.columns(3)

# Create placeholders for the current values and charts in separate columns
with col1:
    battery_voltage_display = st.empty()
    battery_voltage_chart = st.line_chart([])

with col2:
    engine_load_display = st.empty()
    engine_load_chart = st.line_chart([])

with col3:
    rpm_display = st.empty()
    rpm_chart = st.line_chart([])

# Data containers for the charts
battery_voltage_data = []
engine_load_data = []
rpm_data = []
timestamps = []

# WebSocket handler
async def obd_websocket(websocket, path):
    global battery_voltage_data, engine_load_data, rpm_data, timestamps
    while True:
        try:
            # Receive data from WebSocket client
            message = await websocket.recv()
            data = json.loads(message)

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

            # Limit the number of data points to show in the graph to 20
            if len(timestamps) > 20:
                timestamps.pop(0)
                battery_voltage_data.pop(0)
                engine_load_data.pop(0)
                rpm_data.pop(0)

            # Update the charts with new data
            battery_voltage_chart.add_rows(pd.DataFrame({'Battery Voltage (V)': battery_voltage_data}))
            engine_load_chart.add_rows(pd.DataFrame({'Engine Load (%)': engine_load_data}))
            rpm_chart.add_rows(pd.DataFrame({'RPM': rpm_data}))

        except websockets.ConnectionClosed:
            print("Client disconnected")
            break

# WebSocket server coroutine
async def start_websocket_server():
    async with websockets.serve(obd_websocket, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()  # Run forever

# Main function to run the WebSocket server and Streamlit
if __name__ == "__main__":
    # Run the WebSocket server asynchronously
    asyncio.run(start_websocket_server())
