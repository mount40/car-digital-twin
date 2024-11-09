import sqlite3
import streamlit as st
import bcrypt
import time
import pandas as pd
import time
from datetime import datetime, timedelta
import subprocess
import os

# Function to authenticate user
def authenticate_user(username, password):
    # conn = sqlite3.connect('obd_data.db')
    # cursor = conn.cursor()
    # cursor.execute('SELECT id, password FROM users WHERE username = ?', (username,))
    # user = cursor.fetchone()
    # conn.close()

    # if user:
    user_id, hashed_password = 1, b'$2b$12$.J/6wuzG0kDYwVkIwa9/Y.lk13g3bRUBn./JjiA6.tGXKXGg87dWO'
    # if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
    return user_id
    # return None

# Function to retrieve the latest 20 OBD-II entries for the logged-in user
def get_latest_obd_data(user_id):
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, battery_voltage, engine_load, rpm, 
               coolant_temp, throttle_position, fuel_level, 
               intake_pressure, maf_rate
        FROM obd_data
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 30
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows[::-1]  # Reverse to get chronological order

# Streamlit login function using st.form
def login():
    st.title("Login to Car Data Dashboard")

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
# Function to retrieve the most recent timestamp in the obd_data table
def get_most_recent_timestamp(user_id):
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp FROM obd_data 
        WHERE user_id = ? 
        ORDER BY id DESC 
        LIMIT 1
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
    return None

# Function to get all out-of-norm logs and join with norm ranges
def get_out_of_norm_logs():
    conn = sqlite3.connect('obd_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT logs.id, logs.metric_name, logs.value, logs.timestamp, 
               ranges.min_value, ranges.max_value
        FROM out_of_norm_logs logs
        JOIN norm_ranges ranges ON logs.metric_name = ranges.metric_name
        ORDER BY logs.timestamp DESC
    ''')
    logs = cursor.fetchall()
    conn.close()
    return logs

# Function to visualize data in Streamlit
def visualize_obd_data():
    st.title("Car Data Dashboard")

    # Display GIF at the top
    car_gif = st.empty()

    # Create placeholder for the logs table
    st.subheader("Out-of-Norm Events Log")
    out_of_norm_logs_placeholder = st.empty()

    # Fetch out-of-norm logs
    logs = get_out_of_norm_logs()

    if logs:
        # Convert logs to a DataFrame for better visualization and sorting
        df_logs = pd.DataFrame(logs, columns=[
            'Log ID', 'Metric Name', 'Value', 'Timestamp', 'Min Value', 'Max Value'
        ])
        
        # Display the logs as a sortable dataframe
        out_of_norm_logs_placeholder.dataframe(df_logs)

    user_id = st.session_state['user_id']

    # Create placeholders for the charts
    col1, col2, col3 = st.columns(3)
    battery_voltage_display = col1.empty()
    engine_load_display = col2.empty()
    rpm_display = col3.empty()

    # Additional columns for the new parameters
    col4, col5, col6 = st.columns(3)
    coolant_temp_display = col4.empty()
    throttle_position_display = col5.empty()
    fuel_level_display = col6.empty()

    col7, col8 = st.columns(2)
    intake_pressure_display = col7.empty()
    maf_rate_display = col8.empty()

    # Create placeholders for line charts
    battery_voltage_chart = col1.line_chart([])
    engine_load_chart = col2.line_chart([])
    rpm_chart = col3.line_chart([])

    coolant_temp_chart = col4.line_chart([])
    throttle_position_chart = col5.line_chart([])
    fuel_level_chart = col6.line_chart([])

    intake_pressure_chart = col7.line_chart([])
    maf_rate_chart = col8.line_chart([])

    while True:
        # Fetch the latest 20 records
        data = get_latest_obd_data(user_id)
        
        if data:
            (timestamps, battery_voltage, engine_load, rpm, 
             coolant_temp, throttle_position, fuel_level, 
             intake_pressure, maf_rate) = zip(*data)

            # Check if the last entry's timestamp is within the last 2 seconds
            last_timestamp_str = timestamps[-1]
            last_timestamp = datetime.strptime(last_timestamp_str, '%Y-%m-%d %H:%M:%S')
            current_time = datetime.now()

            # Check if the last data entry is within the past 2 seconds
            # if current_time - timedelta(seconds=2) <= last_timestamp:
            car_gif.image('engine-miata-engine.gif', use_column_width=True)
            # else:
            #     car_gif.image('engine-miata-engine-stopped.tiff', use_column_width=True)

            # Fetch out-of-norm logs
            logs = get_out_of_norm_logs()

            if logs:
                # Convert logs to a DataFrame for better visualization and sorting
                df_logs = pd.DataFrame(logs, columns=[
                    'Log ID', 'Metric Name', 'Value', 'Timestamp', 'Min Value', 'Max Value'
                ])
        
            # Display the logs as a sortable dataframe
            out_of_norm_logs_placeholder.dataframe(df_logs)
                
            # Update the last entry display for each parameter
            battery_voltage_display.markdown(f"**Battery Voltage (Last Entry):** {battery_voltage[-1]} V")
            engine_load_display.markdown(f"**Engine Load (Last Entry):** {engine_load[-1]} %")
            rpm_display.markdown(f"**RPM (Last Entry):** {rpm[-1]} RPM")

            coolant_temp_display.markdown(f"**Coolant Temp (Last Entry):** {coolant_temp[-1]} °C")
            throttle_position_display.markdown(f"**Throttle Position (Last Entry):** {throttle_position[-1]} %")
            fuel_level_display.markdown(f"**Fuel Level (Last Entry):** {fuel_level[-1]} %")

            intake_pressure_display.markdown(f"**Intake Pressure (Last Entry):** {intake_pressure[-1]} kPa")
            maf_rate_display.markdown(f"**MAF Rate (Last Entry):** {maf_rate[-1]} g/s")

            # Prepare data for plotting as a DataFrame
            chart_data = pd.DataFrame({
                'Battery Voltage (V)': battery_voltage,
                'Engine Load (%)': engine_load,
                'RPM': rpm,
                'Coolant Temp (°C)': coolant_temp,
                'Throttle Position (%)': throttle_position,
                'Fuel Level (%)': fuel_level,
                'Intake Pressure (kPa)': intake_pressure,
                'MAF Rate (g/s)': maf_rate
            }, index=timestamps)

            # Update the line charts with horizontal (time-based) data
            battery_voltage_chart.line_chart(chart_data[['Battery Voltage (V)']])
            engine_load_chart.line_chart(chart_data[['Engine Load (%)']])
            rpm_chart.line_chart(chart_data[['RPM']])

            coolant_temp_chart.line_chart(chart_data[['Coolant Temp (°C)']])
            throttle_position_chart.line_chart(chart_data[['Throttle Position (%)']])
            fuel_level_chart.line_chart(chart_data[['Fuel Level (%)']])

            intake_pressure_chart.line_chart(chart_data[['Intake Pressure (kPa)']])
            maf_rate_chart.line_chart(chart_data[['MAF Rate (g/s)']])

        time.sleep(1)  # Refresh every second

# Main app function
def main():
    # if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = True
    st.session_state['user_id'] = authenticate_user("", "")


    # if not st.session_state['logged_in']:
    #     login()  # Show login form if not logged in
    # else:
    visualize_obd_data()  # Show the dashboard

if __name__ == "__main__":
    main()
