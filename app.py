import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(
    page_title="PlanWise AI | MTN Notification Engine",
    page_icon="🟡",
    layout="wide"
)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def parse_data_to_gb(val):
    """Convert '200mb', '1gb', '10gb', '2byte' etc. → float GB"""
    if pd.isna(val) or str(val).strip() in ("", "s sample"):
        return 0.0
    val = str(val).strip().lower()
    try:
        if "tb" in val:
            return float(val.replace("tb", "")) * 1024
        elif "gb" in val:
            return float(val.replace("gb", ""))
        elif "mb" in val:
            return float(val.replace("mb", "")) / 1024
        elif "kb" in val:
            return float(val.replace("kb", "")) / (1024 * 1024)
        elif "byte" in val:
            return 0.0
        else:
            return float(val)
    except ValueError:
        return 0.0

def parse_minutes(val):
    """Convert '56min', '100mins', '138mins' etc. → float"""
    if pd.isna(val) or str(val).strip() == "":
        return 0.0
    val = str(val).strip().lower().replace("mins", "").replace("min", "")
    try:
        return float(val)
    except ValueError:
        return 0.0

def build_ai_recommendation(row):
    """Return (recommendation_text, incentive_type, alert_priority)"""
    data_gb   = float(row.get("data_gb", 0) or 0)
    call_min  = float(row.get("call_min", 0) or 0)
    vas_sub   = str(row.get("vas_sub", "FALSE")).upper() == "TRUE"
    exp_data  = parse_data_to_gb(row.get("av_expired_data", 0))
    daily_d   = parse_data_to_gb(row.get("daily_data_used", 0))
    weekly_d  = parse_data_to_gb(row.get("Weekly_data_used", 0))
    monthly_d = parse_data_to_gb(row.get("Monthly_data_used", 0))
    daily_c   = parse_minutes(row.get("daily_av_call", 0))
    weekly_c  = parse_minutes(row.get("weekly_av_call", 0))
    monthly_c = parse_minutes(row.get("monthly_av_call", 0))

    recs      = []
    incentive = "None"
    priority  = "Low"

    # ── Expired data warning ──
    if exp_data > 0:
        recs.append(f"⚠️ {exp_data:.2f} GB expired unused — consider a smaller plan.")
        priority = "High"

    # ── Data usage vs plan size ──
    usage_ratio = monthly_d / data_gb if data_gb > 0 else 0
    if usage_ratio < 0.15 and data_gb > 0:
        recs.append("📉 Low data usage — downgrade or switch to Airtime bundle.")
        incentive = "Airtime Bonus"
        priority  = "High"
    elif usage_ratio > 0.85 and data_gb > 0:
        recs.append("📈 Near data cap — upgrade plan before throttling.")
        incentive = "Data Top-Up"
        priority  = "High"

    # ── Call minute analysis ──
    if monthly_c > 300 and call_min < 400:
        recs.append("📞 High call volume — switch to Unlimited Talk plan for savings.")
        incentive = "Airtime"
        priority  = "High" if priority == "Low" else priority
    elif weekly_c > 100 and call_min < 200:
        recs.append("📞 Moderate weekly calls — consider a Calling Bundle.")
        incentive = "Airtime" if incentive == "None" else incentive
        priority  = "Medium" if priority == "Low" else priority

    # ── VAS suggestion ──
    if not vas_sub and monthly_d > 5:
        recs.append("🎁 You qualify for VAS perks — activate Value-Added Services.")
        incentive = "Data/Airtime" if incentive == "None" else incentive

    # ── Heavy user ──
    if data_gb >= 5 and monthly_c >= 100:
        recs.append("🚀 Power user detected — MTN Mega Bundle (Data + Calls) recommended.")
        incentive = "Data/Airtime"
        priority  = "High"

    if not recs:
        recs.append("✅ Usage looks healthy. No changes needed.")

    return " | ".join(recs), incentive, priority


def build_sms_message(phone, row, rec_text, incentive):
    """Craft a personalised SMS under 160 chars where possible."""
    first_word = rec_text.split("—")[0].replace("📉","").replace("📈","").replace("📞","").replace("⚠️","").replace("🎁","").replace("🚀","").strip()
    msg = (
        f"PlanWise[MTN]: {first_word}. "
        f"Incentive: {incentive}. "
        f"Act now—Dial *131# or *121#."
    )
    return msg[:320]  # allow long SMS (2 segments)


def send_sms_notification(phone, message):
    """Simulate Africa's Talking SMS API call."""
    # Production:
    # requests.post("https://api.africastalking.com/version1/messaging",
    #               data={'username':'planwise','to': phone,'message': message},
    #               headers={'apiKey': AT_API_KEY})
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recipient": phone,
        "status":    "✅ Sent",
        "message":   message,
        "channel":   "SMS"
    }

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────

DEFAULT_USERS = [
    {
        "phone": "8031112222",
        "data_gb": 0.05,
        "call_min": 300,
        "vas_sub": False,
        "daily_data_used": "20mb",
        "Weekly_data_used": "200mb",
        "Monthly_data_used": "1gb",
        "av_expired_data": "1gb",
        "daily_av_call": "56min",
        "weekly_av_call": "100mins",
        "monthly_av_call": "200mins",
        "manual_recommendation": "Switch to calling plan to get lower call rate",
        "manual_incentive": "Airtime"
    },
    {
        "phone": "9055556666",
        "data_gb": 3.5,
        "call_min": 120,
        "vas_sub": True,
        "daily_data_used": "10gb",
        "Weekly_data_used": "30gb",
        "Monthly_data_used": "60gb",
        "av_expired_data": "100gb",
        "daily_av_call": "39min",
        "weekly_av_call": "120mins",
        "monthly_av_call": "138mins",
        "manual_recommendation": "Higher rate — consider bundle upgrade",
        "manual_incentive": "Data/Airtime"
    },
    {
        "phone": "7012345678",
        "data_gb": 8,
        "call_min": 60,
        "vas_sub": True,
        "daily_data_used": "2gb",
        "Weekly_data_used": "",
        "Monthly_data_used": "",
        "av_expired_data": "",
        "daily_av_call": "",
        "weekly_av_call": "",
        "monthly_av_call": "",
        "manual_recommendation": "Sample user — monitor usage",
        "manual_incentive": "None"
    }
]

if "user_db" not in st.session_state:
    st.session_state.user_db = pd.DataFrame(DEFAULT_USERS)

if "sms_logs" not in st.session_state:
    st.session_state.sms_logs = []          # SMS gateway logs

if "inapp_notifs" not in st.session_state:
    st.session_state.inapp_notifs = []       # In-app notification bell

if "notif_read" not in st.session_state:
    st.session_state.notif_read = False

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/MTN_Logo.svg/200px-MTN_Logo.svg.png", width=80)
    st.title("PlanWise AI")
    st.caption("MTN Subscriber Intelligence Engine")
    st.divider()

    st.header("📥 Data Ingestion")
    uploaded_file = st.file_uploader("Upload Subscriber CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        df["phone"] = df["phone"].astype(str)
        st.session_state.user_db = df
        st.success(f"Loaded {len(df)} subscribers.")

    st.divider()
    st.header("📡 MTN Core Sync")
    if st.button("🔄 Sync Live Usage", use_container_width=True):
        with st.spinner("Fetching usage logs from MTN SMSC..."):
            time.sleep(1.5)
        st.success("Sync complete ✔")

    st.divider()
    # ── In-App Notification Bell ──
    unread = [n for n in st.session_state.inapp_notifs if not n.get("read")]
    badge  = f"🔔 Notifications ({len(unread)} new)" if unread else "🔔 Notifications"
    with st.expander(badge, expanded=bool(unread)):
        if st.session_state.inapp_notifs:
            for i, n in enumerate(reversed(st.session_state.inapp_notifs[-20:])):
                colour = "#ffcc00" if not n.get("read") else "#888"
                st.markdown(
                    f"<div style='border-left:3px solid {colour};padding:4px 8px;margin:4px 0;"
                    f"background:#1e1e1e;border-radius:4px;font-size:0.82rem'>"
                    f"<b>{n['timestamp']}</b><br>{n['body']}</div>",
                    unsafe_allow_html=True
                )
            if st.button("Mark all as read", key="mark_read"):
                for n in st.session_state.inapp_notifs:
                    n["read"] = True
                st.rerun()
        else:
            st.info("No in-app alerts yet.")

# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────

st.title("🟡 PlanWise AI — MTN Notification Gateway")
st.caption("AI-powered subscriber analysis & personalised alert engine")

# ─────────────────────────────────────────────
# SECTION 1: ENRICHED SUBSCRIBER TABLE
# ─────────────────────────────────────────────

st.header("📊 Subscriber Intelligence Dashboard")

df = st.session_state.user_db.copy()
df["phone"] = df["phone"].astype(str)

# Compute AI columns
ai_results = df.apply(build_ai_recommendation, axis=1)
df["AI_Recommendation"] = [r[0] for r in ai_results]
df["AI_Incentive"]      = [r[1] for r in ai_results]
df["Alert_Priority"]    = [r[2] for r in ai_results]

# Priority colour highlight
def priority_colour(val):
    colours = {"High": "background-color:#ff4b4b;color:white",
                "Medium": "background-color:#ffa500;color:white",
                "Low": "background-color:#21c45d;color:white"}
    return colours.get(val, "")

display_cols = [
    "phone", "data_gb", "call_min", "vas_sub",
    "daily_data_used", "Weekly_data_used", "Monthly_data_used",
    "av_expired_data", "daily_av_call", "weekly_av_call", "monthly_av_call",
    "AI_Recommendation", "AI_Incentive", "Alert_Priority"
]
available_cols = [c for c in display_cols if c in df.columns]

styled = (
    df[available_cols]
    .style
    .map(priority_colour, subset=["Alert_Priority"])
)
st.dataframe(styled, use_container_width=True, height=260)

# ─────────────────────────────────────────────
# SECTION 2: BULK NOTIFICATION ENGINE
# ─────────────────────────────────────────────

st.divider()
st.header("🚀 Smart Bulk Notification Engine")

filter_priority = st.multiselect(
    "Send alerts to subscribers with priority:",
    ["High", "Medium", "Low"],
    default=["High", "Medium"]
)

col_btn1, col_btn2 = st.columns([1, 3])
with col_btn1:
    send_bulk = st.button("🔔 Send Bulk Alerts", type="primary", use_container_width=True)

if send_bulk:
    targets = df[df["Alert_Priority"].isin(filter_priority)]
    count = 0
    for _, row in targets.iterrows():
        rec_text  = row["AI_Recommendation"]
        incentive = row["AI_Incentive"]
        phone     = str(row["phone"])
        sms_body  = build_sms_message(phone, row, rec_text, incentive)

        # ── SMS gateway log ──
        sms_entry = send_sms_notification(phone, sms_body)
        st.session_state.sms_logs.append(sms_entry)

        # ── In-app notification ──
        st.session_state.inapp_notifs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "body": f"Alert sent to {phone} | Priority: {row['Alert_Priority']} | {rec_text[:80]}…",
            "read": False,
            "channel": "SMS"
        })
        count += 1

    st.success(f"✅ {count} personalised SMS alerts dispatched!")
    st.balloons()
    st.rerun()

# ─────────────────────────────────────────────
# SECTION 3: SMS GATEWAY TRANSMISSION LOGS
# ─────────────────────────────────────────────

st.divider()
st.subheader("📜 SMS Gateway Transmission Logs")

if st.session_state.sms_logs:
    log_df = pd.DataFrame(st.session_state.sms_logs)
    st.dataframe(log_df.tail(20), use_container_width=True, height=220)

    col_dl, col_clr = st.columns([1, 5])
    with col_dl:
        csv_data = log_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Export Logs CSV", csv_data, "planwise_sms_logs.csv", "text/csv")
    with col_clr:
        if st.button("🗑 Clear SMS Logs"):
            st.session_state.sms_logs = []
            st.rerun()
else:
    st.info("No SMS transmissions yet. Use 'Send Bulk Alerts' above.")

# ─────────────────────────────────────────────
# SECTION 4: IN-APP NOTIFICATION LOG (full view)
# ─────────────────────────────────────────────

st.divider()
st.subheader("🔔 In-App Notification Log")

if st.session_state.inapp_notifs:
    notif_df = pd.DataFrame(st.session_state.inapp_notifs)[["timestamp", "body", "channel", "read"]]
    notif_df["read"] = notif_df["read"].map({True: "✔ Read", False: "🆕 Unread"})
    st.dataframe(notif_df.iloc[::-1].reset_index(drop=True), use_container_width=True, height=220)

    if st.button("🗑 Clear In-App Notifications"):
        st.session_state.inapp_notifs = []
        st.rerun()
else:
    st.info("In-app notifications will appear here after alerts are sent.")

# ─────────────────────────────────────────────
# SECTION 5: INDIVIDUAL MANUAL OVERRIDE
# ─────────────────────────────────────────────

st.divider()
st.subheader("🎯 Individual Manual Override")

phone_list = df["phone"].tolist()
selected_phone = st.selectbox("Select subscriber phone number", phone_list)

# Auto-fill with AI recommendation
sel_row = df[df["phone"] == selected_phone].iloc[0] if selected_phone else None
default_msg = ""
if sel_row is not None:
    default_msg = build_sms_message(
        selected_phone, sel_row,
        sel_row["AI_Recommendation"], sel_row["AI_Incentive"]
    )

custom_msg = st.text_area("Message (edit as needed)", value=default_msg, height=80)
char_count = len(custom_msg)
st.caption(f"{char_count}/320 characters ({(char_count // 160)+1} SMS segment{'s' if char_count > 160 else ''})")

if st.button("📤 Send Single SMS", type="secondary"):
    if custom_msg.strip():
        sms_entry = send_sms_notification(selected_phone, custom_msg)
        st.session_state.sms_logs.append(sms_entry)

        st.session_state.inapp_notifs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "body": f"Manual alert sent to {selected_phone}: {custom_msg[:80]}…",
            "read": False,
            "channel": "SMS (Manual)"
        })
        st.toast(f"✅ Message sent to {selected_phone}", icon="📲")
        st.rerun()
    else:
        st.warning("Message cannot be empty.")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.divider()
st.markdown("""
>  SMS delivery simulates the **Africa's Talking API**.  
> In production, `send_sms_notification()` calls the MTN SMSC gateway  
> (`POST https://api.africastalking.com/version1/messaging`) with real API keys.  
> In-app notifications are persisted in Streamlit session state and can be wired  
> to a PostgreSQL / Firebase backend for multi-session persistence.
""")