import streamlit as st
import pandas as pd
import time
import re
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="PlanWise AI | MTN Notification Engine",
    page_icon="🟡",
    layout="wide"
)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def extract_plan_gb(plan_name: str) -> float:
    """
    Parse the GB capacity from a plan name string.
    Monthly 50GB → 50.0 (monthly)
    Weekly  5GB  → ~20.0 (monthly estimate: ×4.3)
    Daily   2GB  → ~60.0 (monthly estimate: ×30)
    BetaTalk     →  0.5  (minimal-data voice plan)
    """
    if not plan_name or pd.isna(plan_name):
        return 0.0
    plan = str(plan_name).lower()
    m = re.search(r'(\d+(?:\.\d+)?)\s*gb', plan)
    if not m:
        return 0.5          # BetaTalk / unknown voice plan
    gb = float(m.group(1))
    if 'monthly' in plan:
        return gb
    if 'weekly' in plan:
        return round(gb * 4.3, 2)
    if 'daily' in plan:
        return round(gb * 30, 2)
    return gb


def build_ai_recommendation(row: pd.Series):
    """
    Return (recommendation_text, incentive_type, alert_priority)
    based on the NEW subscriber schema.
    """
    phone              = str(row.get("phone", ""))
    device_type        = str(row.get("device_type", "Smartphone"))
    current_plan       = str(row.get("current_plan", ""))
    budget             = float(row.get("monthly_budget_naira", 0) or 0)
    avg_usage          = float(row.get("avg_data_usage_3months", 0) or 0)   # GB
    current_balance    = float(row.get("current_data_balance", 0) or 0)     # GB
    days_to_expiry     = float(row.get("days_to_expiry", 0) or 0)
    avg_expired        = float(row.get("last_3_months_avg_expiry_gb", 0) or 0)  # GB wasted
    active_vas         = int(row.get("active_vas_count", 0) or 0)
    vas_names          = str(row.get("vas_names", "None") or "None")
    vas_drain          = float(row.get("vas_monthly_drain", 0) or 0)        # ₦
    voice_pattern      = str(row.get("voice_usage_pattern", "Low") or "Low")
    pref_time          = str(row.get("preferred_time_of_usage", "") or "")

    plan_monthly_gb    = extract_plan_gb(current_plan)
    is_feature_phone   = "feature" in device_type.lower()

    recs      = []
    incentive = "None"
    priority  = "Low"

    # ── 1. Expired / wasted data ──────────────────────────────────────────
    if avg_expired > 2:
        recs.append(
            f"⚠️ Avg {avg_expired:.1f} GB expires unused each month — "
            f"consider downgrading to a smaller plan."
        )
        priority = "High"
    elif avg_expired > 0.5:
        recs.append(
            f"📉 ~{avg_expired:.1f} GB wasted monthly — a smaller or shorter plan could save money."
        )
        priority  = max(priority, "Medium") if priority != "High" else priority
        incentive = "Airtime Bonus"

    # ── 2. Usage vs plan capacity ─────────────────────────────────────────
    if plan_monthly_gb > 0:
        usage_ratio = avg_usage / plan_monthly_gb
        if usage_ratio < 0.15 and plan_monthly_gb > 1:
            recs.append(
                f"📉 You only use {avg_usage:.1f} GB of your ~{plan_monthly_gb:.0f} GB plan — "
                f"downgrade to a smaller bundle and save ₦."
            )
            incentive = "Airtime Bonus"
            priority  = "High"
        elif usage_ratio > 0.90:
            recs.append(
                f"📈 Nearing data cap ({avg_usage:.1f} GB / ~{plan_monthly_gb:.0f} GB) — "
                f"consider upgrading before throttling."
            )
            incentive = "Data Top-Up"
            priority  = "High"

    # ── 3. Expiry urgency ────────────────────────────────────────────────
    if days_to_expiry <= 2 and current_balance < 0.5:
        recs.append(
            f"⏰ Plan expires in {int(days_to_expiry)} day(s) with only {current_balance:.2f} GB left — renew now!"
        )
        incentive = "Data Top-Up"
        priority  = "High"
    elif days_to_expiry == 0 and current_balance > 0:
        recs.append(
            f"🚨 Plan has expired with {current_balance:.2f} GB remaining — renew to retain balance."
        )
        priority  = "High"
        incentive = "Data Top-Up"

    # ── 4. VAS drain analysis ────────────────────────────────────────────
    if active_vas > 0 and vas_drain > 0:
        vas_list = vas_names if vas_names != "None" else "subscriptions"
        # Flag if VAS drain exceeds 15 % of monthly budget
        if budget > 0 and (vas_drain / budget) > 0.15:
            recs.append(
                f"💸 VAS services ({vas_list}) drain ₦{vas_drain:,.0f}/month "
                f"— that's {vas_drain/budget*100:.0f}% of your budget. Review or cancel some."
            )
            incentive = "Airtime" if incentive == "None" else incentive
            priority  = "High"
        else:
            recs.append(
                f"🔔 Active VAS: {vas_list} cost ₦{vas_drain:,.0f}/month — verify you're using them."
            )
            priority = max(priority, "Medium") if priority != "High" else priority

    # ── 5. Feature phone – data-heavy plan mismatch ──────────────────────
    if is_feature_phone and plan_monthly_gb >= 20:
        recs.append(
            "📱 Feature phone detected — a large data plan may not suit your device. "
            "Consider a voice/SMS-focused bundle or smaller data plan."
        )
        incentive = "Airtime Bonus"
        priority  = max(priority, "Medium") if priority != "High" else priority

    # ── 6. Voice usage vs plan type ──────────────────────────────────────
    if voice_pattern in ("High", "Very-High"):
        if "betatalk" not in current_plan.lower() and "unlimited" not in current_plan.lower():
            recs.append(
                f"📞 {voice_pattern} call usage detected — switch to MTN BetaTalk or "
                f"an Unlimited Talk plan for significant savings."
            )
            incentive = "Airtime"
            priority  = "High" if priority == "Low" else priority

    # ── 7. Power user upsell ─────────────────────────────────────────────
    if avg_usage >= 8 and voice_pattern in ("High", "Very-High"):
        recs.append(
            "🚀 Power user profile — MTN Mega Bundle (Data + Calls) is recommended for max value."
        )
        incentive = "Data/Airtime"
        priority  = "High"

    # ── 8. Budget efficiency nudge ───────────────────────────────────────
    if budget > 0 and avg_expired > 1 and plan_monthly_gb > 10:
        potential_saving = avg_expired * (budget / plan_monthly_gb) if plan_monthly_gb > 0 else 0
        if potential_saving > 200:
            recs.append(
                f"💰 You could save ~₦{potential_saving:,.0f}/month by right-sizing your plan."
            )

    if not recs:
        recs.append("✅ Usage looks healthy — no changes needed at this time.")

    return " | ".join(recs), incentive, priority


def build_sms_message(phone: str, row: pd.Series, rec_text: str, incentive: str) -> str:
    """Craft a personalised SMS (≤ 320 chars / 2 segments)."""
    # Strip emojis for SMS
    clean = re.sub(r'[^\x00-\x7F]+', '', rec_text)
    first_part = clean.split('|')[0].strip()[:100]
    msg = (
        f"PlanWise[MTN]: {first_part}. "
        f"Incentive: {incentive}. "
        f"Manage plan: *131# or *121#."
    )
    return msg[:320]


def send_sms_notification(phone: str, message: str) -> dict:
    """Simulate Africa's Talking SMS API call."""
    # Production: POST https://api.africastalking.com/version1/messaging
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recipient": str(phone),
        "status":    "✅ Sent",
        "message":   message,
        "channel":   "SMS"
    }


# ─────────────────────────────────────────────
# CONVERSION ENGINE HELPERS
# ─────────────────────────────────────────────

# MTN Nigeria approximate conversion rates
_NAIRA_PER_GB  = 250.0   # ₦250 per GB  (conservative mid-tier rate)
_NAIRA_PER_MIN = 11.0    # ₦11 per min  (MTN-MTN on-net approx)


def determine_primary_service(row: pd.Series) -> tuple:
    """
    Score Data / Voice-Airtime / VAS Credit from usage signals and
    return (service_label: str, emoji: str) for the highest scorer.
    """
    voice_pattern = str(row.get("voice_usage_pattern", "Low") or "Low")
    avg_usage     = float(row.get("avg_data_usage_3months", 0) or 0)
    current_plan  = str(row.get("current_plan", "") or "")
    active_vas    = int(row.get("active_vas_count", 0) or 0)
    vas_drain     = float(row.get("vas_monthly_drain", 0) or 0)
    budget        = float(row.get("monthly_budget_naira", 0) or 0)
    plan_gb       = extract_plan_gb(current_plan)

    # 0–4 score per service
    voice_score = {"Very-High": 4, "High": 3, "Medium": 2, "Low": 1}.get(voice_pattern, 1)
    data_score  = min(4.0, (avg_usage / plan_gb * 4)) if plan_gb > 0 else 0.0
    vas_score   = min(4.0, active_vas + (vas_drain / budget * 4 if budget > 0 else 0))

    scores  = {"Data": data_score, "Voice/Airtime": voice_score, "VAS Credit": vas_score}
    primary = max(scores, key=scores.get)
    emoji   = {"Data": "📶", "Voice/Airtime": "📞", "VAS Credit": "🎁"}[primary]
    return primary, emoji


def calculate_conversion(row: pd.Series) -> dict:
    """
    Work out what unused data balance would be converted into and its
    naira-equivalent value.  Returns a plain dict consumed by the UI.
    """
    balance_gb = float(row.get("current_data_balance", 0) or 0)
    days       = float(row.get("days_to_expiry", 0) or 0)
    vas_drain  = float(row.get("vas_monthly_drain", 0) or 0)
    primary, _ = determine_primary_service(row)
    naira_val  = round(balance_gb * _NAIRA_PER_GB, 2)

    if balance_gb <= 0:
        return {
            "eligible":        False,
            "reason":          "No data balance available for conversion.",
            "primary_service": primary,
            "from_value":      "0.00 GB",
            "to_service":      primary,
            "converted_value": "₦0",
            "detail":          "—",
            "naira_value":     0.0,
            "days_to_expiry":  int(days),
        }

    if primary == "Voice/Airtime":
        mins   = int(naira_val / _NAIRA_PER_MIN)
        cvt    = f"₦{naira_val:,.0f} airtime (~{mins} mins MTN-MTN)"
        detail = (
            f"{balance_gb:.2f} GB unused data → ₦{naira_val:,.0f} airtime credit "
            f"(approx. {mins} on-net minutes)."
        )
    elif primary == "VAS Credit":
        months = round(naira_val / vas_drain, 1) if vas_drain > 0 else 0
        cvt    = f"₦{naira_val:,.0f} VAS credit (~{months} mo coverage)"
        detail = (
            f"{balance_gb:.2f} GB unused data → ₦{naira_val:,.0f} credited toward "
            f"active VAS subscriptions (~{months} month(s) covered)."
        )
    else:  # Data carry-over
        cvt    = f"{balance_gb:.2f} GB carry-over data"
        detail = (
            f"{balance_gb:.2f} GB preserved as carry-over and rolled into the "
            f"subscriber's next renewal cycle."
        )

    return {
        "eligible":        True,
        "primary_service": primary,
        "from_value":      f"{balance_gb:.2f} GB",
        "to_service":      primary,
        "converted_value": cvt,
        "detail":          detail,
        "naira_value":     naira_val,
        "days_to_expiry":  int(days),
    }


# ─────────────────────────────────────────────
# DEFAULT SAMPLE USERS  (new schema)
# ─────────────────────────────────────────────

DEFAULT_USERS = [
    {
        "phone": "8033164749",
        "device_type": "Smartphone",
        "current_plan": "MTN Monthly 50GB",
        "monthly_budget_naira": 12461,
        "avg_data_usage_3months": 2.31,
        "current_data_balance": 1.12,
        "days_to_expiry": 15,
        "last_3_months_avg_expiry_gb": 1.87,
        "active_vas_count": 2,
        "vas_names": "Daily Devotional, MusicPlus",
        "vas_monthly_drain": 900,
        "voice_usage_pattern": "High",
        "preferred_time_of_usage": "Morning"
    },
    {
        "phone": "8035079990",
        "device_type": "Smartphone",
        "current_plan": "MTN Monthly 20GB",
        "monthly_budget_naira": 7184,
        "avg_data_usage_3months": 1.74,
        "current_data_balance": 3.99,
        "days_to_expiry": 4,
        "last_3_months_avg_expiry_gb": 33.24,
        "active_vas_count": 3,
        "vas_names": "VideoVibe, Comedy+, GameZone",
        "vas_monthly_drain": 900,
        "voice_usage_pattern": "Very-High",
        "preferred_time_of_usage": "All-Day"
    },
    {
        "phone": "8032512680",
        "device_type": "Feature Phone",
        "current_plan": "MTN Monthly 20GB",
        "monthly_budget_naira": 5834,
        "avg_data_usage_3months": 4.47,
        "current_data_balance": 4.75,
        "days_to_expiry": 1,
        "last_3_months_avg_expiry_gb": 28.83,
        "active_vas_count": 0,
        "vas_names": "None",
        "vas_monthly_drain": 0,
        "voice_usage_pattern": "Medium",
        "preferred_time_of_usage": "Night"
    },
    {
        "phone": "8037808650",
        "device_type": "Smartphone",
        "current_plan": "MTN Weekly 1GB",
        "monthly_budget_naira": 2104,
        "avg_data_usage_3months": 11.93,
        "current_data_balance": 1.60,
        "days_to_expiry": 0,
        "last_3_months_avg_expiry_gb": 0,
        "active_vas_count": 0,
        "vas_names": "None",
        "vas_monthly_drain": 0,
        "voice_usage_pattern": "High",
        "preferred_time_of_usage": "Night"
    },
    {
        "phone": "8033511902",
        "device_type": "Smartphone",
        "current_plan": "MTN Monthly 20GB",
        "monthly_budget_naira": 7947,
        "avg_data_usage_3months": 9.40,
        "current_data_balance": 2.77,
        "days_to_expiry": 24,
        "last_3_months_avg_expiry_gb": 1.04,
        "active_vas_count": 4,
        "vas_names": "GameZone, VideoVibe, CallerTune, Sports SMS",
        "vas_monthly_drain": 1200,
        "voice_usage_pattern": "Low",
        "preferred_time_of_usage": "All-Day"
    },
]

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────

if "user_db" not in st.session_state:
    st.session_state.user_db = pd.DataFrame(DEFAULT_USERS)

if "sms_logs" not in st.session_state:
    st.session_state.sms_logs = []

if "inapp_notifs" not in st.session_state:
    st.session_state.inapp_notifs = []

if "conversion_logs" not in st.session_state:
    st.session_state.conversion_logs = []

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/MTN_Logo.svg/200px-MTN_Logo.svg.png",
        width=80
    )
    st.title("PlanWise AI")
    st.caption("MTN Subscriber Intelligence Engine")
    st.divider()

    st.header("📥 Data Ingestion")
    uploaded_file = st.file_uploader("Upload Subscriber CSV", type=["csv"])
    if uploaded_file:
        df_upload = pd.read_csv(uploaded_file, sep=None, engine="python")
        df_upload["phone"] = df_upload["phone"].astype(str)
        st.session_state.user_db = df_upload
        st.success(f"Loaded {len(df_upload):,} subscribers.")

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
            for n in reversed(st.session_state.inapp_notifs[-20:]):
                colour = "#ffcc00" if not n.get("read") else "#888"
                st.markdown(
                    f"<div style='border-left:3px solid {colour};padding:4px 8px;margin:4px 0;"
                    f"background:#1e1e1e;border-radius:4px;font-size:0.82rem'>"
                    f"<b>{n['timestamp']}</b><br>{n['body']}</div>",
                    unsafe_allow_html=True
                )
            if st.button("Mark all as read"):
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

# Ensure numeric columns are correctly typed
numeric_cols = [
    "monthly_budget_naira", "avg_data_usage_3months", "current_data_balance",
    "days_to_expiry", "last_3_months_avg_expiry_gb",
    "active_vas_count", "vas_monthly_drain"
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# Compute AI columns
ai_results = df.apply(build_ai_recommendation, axis=1)
df["AI_Recommendation"] = [r[0] for r in ai_results]
df["AI_Incentive"]      = [r[1] for r in ai_results]
df["Alert_Priority"]    = [r[2] for r in ai_results]

# Priority colour highlight
def priority_colour(val):
    colours = {
        "High":   "background-color:#ff4b4b;color:white",
        "Medium": "background-color:#ffa500;color:white",
        "Low":    "background-color:#21c45d;color:white"
    }
    return colours.get(val, "")

display_cols = [
    "phone", "device_type", "current_plan",
    "monthly_budget_naira", "avg_data_usage_3months",
    "current_data_balance", "days_to_expiry",
    "last_3_months_avg_expiry_gb", "active_vas_count",
    "vas_names", "vas_monthly_drain",
    "voice_usage_pattern", "preferred_time_of_usage",
    "AI_Recommendation", "AI_Incentive", "Alert_Priority"
]
available_cols = [c for c in display_cols if c in df.columns]

styled = (
    df[available_cols]
    .style
    .map(priority_colour, subset=["Alert_Priority"])
)
st.dataframe(styled, use_container_width=True, height=280)

# ── Summary KPIs ──────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
high_count   = (df["Alert_Priority"] == "High").sum()
medium_count = (df["Alert_Priority"] == "Medium").sum()
avg_waste    = df["last_3_months_avg_expiry_gb"].mean() if "last_3_months_avg_expiry_gb" in df.columns else 0
total_vas    = df["vas_monthly_drain"].sum() if "vas_monthly_drain" in df.columns else 0

k1.metric("🔴 High Priority", int(high_count))
k2.metric("🟠 Medium Priority", int(medium_count))
k3.metric("📦 Avg Monthly Waste (GB)", f"{avg_waste:.2f}")
k4.metric("💸 Total VAS Drain (₦)", f"₦{total_vas:,.0f}")

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

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    send_bulk = st.button("🔔 Send Bulk Alerts", type="primary", use_container_width=True)

if send_bulk:
    targets = df[df["Alert_Priority"].isin(filter_priority)]
    count   = 0
    for _, row in targets.iterrows():
        rec_text  = row["AI_Recommendation"]
        incentive = row["AI_Incentive"]
        phone     = str(row["phone"])
        sms_body  = build_sms_message(phone, row, rec_text, incentive)

        sms_entry = send_sms_notification(phone, sms_body)
        st.session_state.sms_logs.append(sms_entry)

        st.session_state.inapp_notifs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "body":  f"Alert → {phone} | {row['Alert_Priority']} | {rec_text[:90]}…",
            "read":  False,
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
# SECTION 4: IN-APP NOTIFICATION LOG
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

phone_list      = df["phone"].tolist()
selected_phone  = st.selectbox("Select subscriber phone number", phone_list)

sel_row = df[df["phone"] == selected_phone].iloc[0] if selected_phone else None

# Show subscriber profile card
if sel_row is not None:
    with st.expander("👤 Subscriber Profile", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Device", sel_row.get("device_type", "—"))
        c2.metric("Current Plan", sel_row.get("current_plan", "—"))
        c3.metric("Budget (₦)", f"₦{int(sel_row.get('monthly_budget_naira', 0)):,}")
        c4.metric("VAS Drain (₦)", f"₦{int(sel_row.get('vas_monthly_drain', 0)):,}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Avg Usage (GB)", sel_row.get("avg_data_usage_3months", "—"))
        c6.metric("Balance (GB)", sel_row.get("current_data_balance", "—"))
        c7.metric("Days to Expiry", int(sel_row.get("days_to_expiry", 0)))
        c8.metric("Voice Pattern", sel_row.get("voice_usage_pattern", "—"))

        st.info(f"🤖 AI: {sel_row.get('AI_Recommendation', '—')}")

default_msg = build_sms_message(
    selected_phone, sel_row,
    sel_row["AI_Recommendation"], sel_row["AI_Incentive"]
) if sel_row is not None else ""

custom_msg  = st.text_area("Message (edit as needed)", value=default_msg, height=80)
char_count  = len(custom_msg)
st.caption(
    f"{char_count}/320 characters "
    f"({(char_count // 160) + 1} SMS segment{'s' if char_count > 160 else ''})"
)

if st.button("📤 Send Single SMS", type="secondary"):
    if custom_msg.strip():
        sms_entry = send_sms_notification(selected_phone, custom_msg)
        st.session_state.sms_logs.append(sms_entry)
        st.session_state.inapp_notifs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "body":  f"Manual alert → {selected_phone}: {custom_msg[:80]}…",
            "read":  False,
            "channel": "SMS (Manual)"
        })
        st.toast(f"✅ Message sent to {selected_phone}", icon="📲")
        st.rerun()
    else:
        st.warning("Message cannot be empty.")

# ─────────────────────────────────────────────
# SECTION 6: PLAN OPTIMIZER PREVIEW
# ─────────────────────────────────────────────

st.divider()
st.subheader("💡 Plan Optimizer — Quick Insights")

if "last_3_months_avg_expiry_gb" in df.columns:
    waste_df = df[df["last_3_months_avg_expiry_gb"] > 1][
        ["phone", "current_plan", "avg_data_usage_3months",
         "last_3_months_avg_expiry_gb", "monthly_budget_naira"]
    ].copy()
    waste_df.columns = ["Phone", "Current Plan", "Avg Usage (GB)",
                        "Avg Expired (GB)", "Budget (₦)"]
    waste_df = waste_df.sort_values("Avg Expired (GB)", ascending=False)

    if not waste_df.empty:
        st.markdown(f"**{len(waste_df)} subscriber(s) wasting > 1 GB/month — prime downgrade candidates:**")
        st.dataframe(waste_df, use_container_width=True, height=200)
    else:
        st.success("No significant data waste detected across subscribers.")

# ─────────────────────────────────────────────
# SECTION 7: ADAPTIVE VALUE CONVERSION ENGINE
#            — Bulk Pre-Expiry Conversion
# ─────────────────────────────────────────────

st.divider()
st.header("🔄 Adaptive Value Conversion Engine")
st.caption(
    "Convert unused data balance to each subscriber's most-used service "
    "before it expires — no value wasted."
)

st.subheader("⚡ Bulk Pre-Expiry Conversion")

expiry_threshold = st.slider(
    "Target subscribers whose plan expires within (days):",
    min_value=1, max_value=30, value=5, step=1,
    key="bulk_conv_threshold"
)

# Build per-subscriber conversion preview
_conv_rows = []
for _, _r in df.iterrows():
    _c = calculate_conversion(_r)
    _conv_rows.append({
        "phone":          str(_r["phone"]),
        "current_plan":   str(_r.get("current_plan", "—")),
        "balance_gb":     float(_r.get("current_data_balance", 0) or 0),
        "days_to_expiry": int(float(_r.get("days_to_expiry", 0) or 0)),
        "primary_service":_c["primary_service"],
        "converts_to":    _c.get("converted_value", "—"),
        "eligible":       _c["eligible"],
        "naira_value":    _c.get("naira_value", 0.0),
    })

conv_preview_df = pd.DataFrame(_conv_rows)
eligible_bulk   = conv_preview_df[
    (conv_preview_df["days_to_expiry"] <= expiry_threshold) &
    (conv_preview_df["eligible"])
].copy()

if not eligible_bulk.empty:
    st.markdown(
        f"**{len(eligible_bulk)} subscriber(s)** with plans expiring in "
        f"≤ {expiry_threshold} day(s) and a convertible balance:"
    )
    st.dataframe(
        eligible_bulk.rename(columns={
            "phone":           "Phone",
            "current_plan":    "Current Plan",
            "balance_gb":      "Balance (GB)",
            "days_to_expiry":  "Days Left",
            "primary_service": "Primary Service",
            "converts_to":     "Will Convert To",
            "naira_value":     "Naira Equiv (₦)",
        }).drop(columns=["eligible"]),
        use_container_width=True, height=220
    )

    _total_naira = eligible_bulk["naira_value"].sum()
    st.metric("💰 Total Value Being Preserved", f"₦{_total_naira:,.0f}")

    _cb1, _cb2 = st.columns([1, 5])
    with _cb1:
        do_bulk_convert = st.button(
            "🔄 Convert All", type="primary",
            use_container_width=True, key="bulk_convert_btn"
        )

    if do_bulk_convert:
        _count = 0
        for _, _er in eligible_bulk.iterrows():
            _orig  = df[df["phone"] == _er["phone"]].iloc[0]
            _cv    = calculate_conversion(_orig)
            _phone = _er["phone"]

            st.session_state.conversion_logs.append({
                "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "phone":       _phone,
                "from_value":  _cv["from_value"],
                "to_service":  _cv["primary_service"],
                "converted":   _cv.get("converted_value", "—"),
                "naira_value": f"₦{_cv['naira_value']:,.0f}",
                "days_left":   _cv["days_to_expiry"],
                "method":      "Bulk Auto-Conversion",
                "status":      "✅ Done",
            })
            st.session_state.inapp_notifs.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "body": (
                    f"[Conversion] {_phone} | {_cv['from_value']} → "
                    f"{_cv['primary_service']} | {_cv.get('converted_value','')} "
                    f"| {_cv['days_to_expiry']}d left"
                ),
                "read":    False,
                "channel": "Conversion",
            })
            _sms = (
                f"PlanWise[MTN]: Your {_cv['from_value']} unused data has been "
                f"converted to {_cv['primary_service']} "
                f"({_cv.get('converted_value','')}) before expiry. "
                f"Dial *131# to confirm."
            )[:320]
            st.session_state.sms_logs.append(send_sms_notification(_phone, _sms))
            _count += 1

        st.success(f"✅ {_count} conversion(s) processed — SMS confirmations sent!")
        st.balloons()
        st.rerun()
else:
    st.info(
        f"No subscribers with plans expiring within {expiry_threshold} day(s) "
        "and a convertible balance. Adjust the slider above."
    )

# ── Conversion Logs ───────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Conversion Logs")

if st.session_state.conversion_logs:
    _clog_df = pd.DataFrame(st.session_state.conversion_logs)
    st.dataframe(_clog_df.tail(30), use_container_width=True, height=220)

    _lc1, _lc2 = st.columns([1, 5])
    with _lc1:
        _csv_bytes = _clog_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Export Conversion Log", _csv_bytes,
            "planwise_conversion_logs.csv", "text/csv",
            key="dl_conv_log"
        )
    with _lc2:
        if st.button("🗑 Clear Conversion Logs", key="clr_conv_log"):
            st.session_state.conversion_logs = []
            st.rerun()
else:
    st.info("No conversions yet. Run 'Convert All' above or use Individual Conversion below.")

# ─────────────────────────────────────────────
# SECTION 8: INDIVIDUAL VALUE CONVERSION
# ─────────────────────────────────────────────

st.divider()
st.subheader("🎯 Individual Value Conversion")
st.caption(
    "Convert a single subscriber's unused data balance to their most-used "
    "service on demand — with optional manual override of the target service."
)

_ind_phones   = df["phone"].tolist()
ind_selected  = st.selectbox(
    "Select subscriber to convert:", _ind_phones,
    key="ind_conv_phone"
)

if ind_selected:
    _ind_row  = df[df["phone"] == ind_selected].iloc[0]
    _ind_conv = calculate_conversion(_ind_row)
    _prim_svc, _prim_emoji = determine_primary_service(_ind_row)

    with st.expander("🔍 Conversion Preview", expanded=True):
        _ic1, _ic2, _ic3, _ic4 = st.columns(4)
        _ic1.metric("Balance (GB)",     f"{float(_ind_row.get('current_data_balance', 0) or 0):.2f}")
        _ic2.metric("Days to Expiry",   int(float(_ind_row.get("days_to_expiry", 0) or 0)))
        _ic3.metric("Primary Service",  f"{_prim_emoji} {_prim_svc}")
        _ic4.metric("Est. Value (₦)",   f"₦{_ind_conv.get('naira_value', 0):,.0f}")

        if _ind_conv["eligible"]:
            st.success(
                f"**Conversion Plan:** {_ind_conv['from_value']} data  →  "
                f"{_prim_emoji} **{_prim_svc}**\n\n"
                f"📌 {_ind_conv.get('detail', '')}"
            )
        else:
            st.warning(f"⚠️ {_ind_conv['reason']}")

    # Optional override
    _override = st.radio(
        "Override target service "
        "(leave on 'Auto' to use AI recommendation):",
        ["Auto (AI Recommended)", "Data (Carry-Over)",
         "Voice/Airtime", "VAS Credit"],
        horizontal=True,
        key="ind_conv_override"
    )

    _svc_map  = {
        "Data (Carry-Over)": "Data",
        "Voice/Airtime":     "Voice/Airtime",
        "VAS Credit":        "VAS Credit",
    }
    _final_svc = _prim_svc if _override == "Auto (AI Recommended)" else _svc_map[_override]

    # Recompute display if manually overridden
    _bal  = float(_ind_row.get("current_data_balance", 0) or 0)
    _nval = round(_bal * _NAIRA_PER_GB, 2)
    if _override != "Auto (AI Recommended)":
        if _final_svc == "Voice/Airtime":
            _override_display = (
                f"₦{_nval:,.0f} airtime (~{int(_nval / _NAIRA_PER_MIN)} mins MTN-MTN)"
            )
        elif _final_svc == "VAS Credit":
            _vd = float(_ind_row.get("vas_monthly_drain", 0) or 0)
            _mc = round(_nval / _vd, 1) if _vd > 0 else 0
            _override_display = f"₦{_nval:,.0f} VAS credit (~{_mc} mo coverage)"
        else:
            _override_display = f"{_bal:.2f} GB data carry-over"
        st.info(f"🔁 Override active — target: **{_final_svc}** → {_override_display}")
    else:
        _override_display = _ind_conv.get("converted_value", "—")

    if st.button(
        "✅ Execute Conversion",
        type="primary",
        disabled=not _ind_conv["eligible"],
        key="ind_conv_btn"
    ):
        _method = (
            "Individual (Override)" if _override != "Auto (AI Recommended)"
            else "Individual (Auto)"
        )
        st.session_state.conversion_logs.append({
            "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "phone":       ind_selected,
            "from_value":  f"{_bal:.2f} GB",
            "to_service":  _final_svc,
            "converted":   _override_display,
            "naira_value": f"₦{_nval:,.0f}",
            "days_left":   int(float(_ind_row.get("days_to_expiry", 0) or 0)),
            "method":      _method,
            "status":      "✅ Done",
        })
        st.session_state.inapp_notifs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "body": (
                f"[Individual Conversion] {ind_selected} | {_bal:.2f} GB → "
                f"{_final_svc} | {_override_display}"
            ),
            "read":    False,
            "channel": "Conversion (Individual)",
        })
        _sms_body = (
            f"PlanWise[MTN]: Your {_bal:.2f} GB unused data has been converted to "
            f"{_final_svc} ({_override_display}) before expiry. "
            f"Dial *131# to confirm."
        )[:320]
        st.session_state.sms_logs.append(
            send_sms_notification(ind_selected, _sms_body)
        )
        st.toast(f"✅ Conversion done for {ind_selected}", icon="🔄")
        st.rerun()

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.divider()
st.markdown("""
> **PlanWise AI** — SMS delivery simulates the **Africa's Talking API**.  
> In production, `send_sms_notification()` posts to the MTN SMSC gateway  
> (`POST https://api.africastalking.com/version1/messaging`) with real API keys.  
> In-app notifications live in Streamlit session state and can be wired to  
> PostgreSQL / Firebase for multi-session persistence.   
> voice_usage_pattern · preferred_time_of_usage`
""")