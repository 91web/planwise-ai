import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="PlanWise AI | Notification Engine", layout="wide")

# --- MOCK NOTIFICATION FUNCTION ---
def send_sms_notification(phone, message, type="User"):
    """Simulates sending an SMS via a Gateway like Africa's Talking"""
    # In production: requests.post("https://api.africastalking.com/...", data={'to': phone, 'message': message})
    return {"status": "Sent", "recipient": phone, "time": datetime.now().strftime("%H:%M:%S"), "content": message}

# --- INITIALIZE DATA ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = pd.DataFrame([
        {"phone": "08031112222", "last_sub": "1GB", "plan": "Weekly", "used_24h": 0.02, "used_48h": 0.04, "status": "Pending"},
        {"phone": "09055556666", "last_sub": "10GB", "plan": "Monthly", "used_24h": 1.5, "used_48h": 3.2, "status": "Pending"}
    ])

if 'notif_logs' not in st.session_state:
    st.session_state.notif_logs = []

st.title("🟡 PlanWise AI: MTN Notification Gateway")

# --- SECTION 1: DATA IMPORT & API ---
with st.sidebar:
    st.header("📥 Data Ingestion")
    uploaded_file = st.file_uploader("Upload Subscriber CSV", type=["csv"])
    if uploaded_file:
        st.session_state.user_db = pd.read_csv(uploaded_file)
    
    st.divider()
    st.header("📡 API Connection")
    if st.button("Sync with MTN Core"):
        with st.spinner("Fetching live usage logs..."):
            time.sleep(1)
            st.success("Sync Complete")

# --- SECTION 2: AI ANALYSIS & NOTIFICATION CONTROL ---
st.header("🚀 AI Analysis & Smart Messaging")

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔔 Send Bulk Notifications", type="primary"):
        count = 0
        for idx, row in st.session_state.user_db.iterrows():
            avg = (row['used_24h'] + row['used_48h']) / 2
            if avg < 0.1:
                msg = f"PlanWise: We noticed you're not using your data. We've gifted you N200 Airtime instead! Dial *556# to check."
            else:
                msg = f"PlanWise: You're a heavy user! Switch to MTN 6GB Weekly to save N500 this week. Dial *121#."
            
            log_entry = send_sms_notification(row['phone'], msg)
            st.session_state.notif_logs.append(log_entry)
            count += 1
        st.success(f"Dispatched {count} personalized SMS alerts!")

# Display User Table with AI Recommendations
processed_data = st.session_state.user_db.copy()

def get_recommendation(row):
    avg = (row['used_24h'] + row['used_48h']) / 2
    if avg < 0.1:
        return "Switch to Airtime Bonus (Low Usage)"
    return "Upgrade to Weekly 6GB (High Usage)"

processed_data['AI_Recommendation'] = processed_data.apply(get_recommendation, axis=1)
st.dataframe(processed_data, use_container_width=True)

# --- SECTION 3: LIVE NOTIFICATION LOGS ---
st.divider()
st.subheader("📜 Live Transmission Logs (SMS Gateway)")

if st.session_state.notif_logs:
    log_df = pd.DataFrame(st.session_state.notif_logs)
    # Style the logs
    st.table(log_df.tail(10)) # Show last 10 notifications
else:
    st.info("No notifications sent yet. Click 'Send Bulk Notifications' above.")

# --- SECTION 4: INDIVIDUAL ACTION ---
st.divider()
st.subheader("🎯 Individual Manual Override")
selected_phone = st.selectbox("Select Phone Number to Notify Manually", st.session_state.user_db['phone'])
custom_msg = st.text_area("Custom Message", value="PlanWise: Your data is expiring soon. Dial *131# to renew.")

if st.button("Send Single SMS"):
    res = send_sms_notification(selected_phone, custom_msg)
    st.session_state.notif_logs.append(res)
    st.toast(f"Message sent to {selected_phone}")

st.markdown("""
---
**Note for Hackathon:** This module simulates the **Africa's Talking SMS API**. 
In a production environment, the `send_sms_notification` function would hit the telco's SMSC gateway to deliver real-time messages to Nigerian phone numbers.
""")