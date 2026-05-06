import pandas as pd
import random

# ─────────────────────────────────────────────
# MTN PREFIXES ONLY
# ─────────────────────────────────────────────
MTN_PREFIXES = [803, 806, 703, 706, 813, 816, 903, 906]

def generate_phone():
    return str(random.choice(MTN_PREFIXES)) + str(random.randint(1000000, 9999999))

def usage_profile():
    r = random.random()
    if r < 0.30:
        return "low"
    elif r < 0.65:
        return "balanced"
    elif r < 0.90:
        return "heavy"
    else:
        return "very_heavy"

def generate_usage(profile):
    if profile == "low":
        data = round(random.uniform(0.01, 0.3), 2)
        calls = random.randint(100, 400)
    elif profile == "balanced":
        data = round(random.uniform(0.5, 3), 2)
        calls = random.randint(50, 150)
    elif profile == "heavy":
        data = round(random.uniform(3, 8), 2)
        calls = random.randint(30, 120)
    else:
        data = round(random.uniform(8, 25), 2)
        calls = random.randint(10, 100)
    return data, calls

def to_gb(val):
    if val < 1:
        return f"{int(val * 1024)}mb"
    return f"{round(val,2)}gb"

def to_min(val):
    return f"{val}min"

rows = []

for _ in range(1000):
    phone = generate_phone()
    profile = usage_profile()

    data_gb, call_min = generate_usage(profile)

    # usage behavior
    daily_data = random.uniform(0.01, 2)
    weekly_data = daily_data * random.uniform(4, 7)
    monthly_data = weekly_data * random.uniform(3, 5)

    expired_data = random.uniform(0, data_gb)

    daily_call = random.randint(0, 60)
    weekly_call = daily_call * random.randint(4, 7)
    monthly_call = weekly_call * random.randint(3, 5)

    vas_sub = random.random() < 0.6  # 60% VAS users

    rows.append({
        "phone": phone,
        "data_gb": data_gb,
        "call_min": call_min,
        "vas_sub": vas_sub,
        "daily_data_used": to_gb(daily_data),
        "Weekly_data_used": to_gb(weekly_data),
        "Monthly_data_used": to_gb(monthly_data),
        "av_expired_data": to_gb(expired_data),
        "daily_av_call": to_min(daily_call),
        "weekly_av_call": to_min(weekly_call),
        "monthly_av_call": to_min(monthly_call),
        "manual_recommendation": "Auto-generated MTN recommendation",
        "manual_incentive": random.choice(["Airtime", "Data", "None"])
    })

df = pd.DataFrame(rows)
df.to_csv("planwise_mtn_1000.csv", index=False)

print("✅ MTN dataset generated: planwise_mtn_1000.csv")
