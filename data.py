import pandas as pd
import numpy as np
import random

def generate_mtn_data(n=1000):
    data = []
    plans = {
        "MTN Monthly 20GB": 5000,
        "MTN Monthly 10GB": 3000,
        "MTN Monthly 50GB": 10000,
        "MTN Weekly 5GB": 1500,
        "MTN Weekly 1GB": 500,
        "MTN Daily 2GB": 500,
        "MTN BetaTalk": 0
    }
    
    vas_options = ["MusicPlus", "CallerTune", "Comedy+", "Daily Devotional", "GameZone", "Sports SMS", "VideoVibe"]
    usage_patterns = ["Low", "Medium", "High", "Very-High"]
    times = ["Morning", "Evening", "Night", "All-Day"]

    for i in range(n):
        phone = f"0803{random.randint(1000000, 9999999)}"
        device = random.choices(["Smartphone", "Feature Phone"], weights=[80, 20])[0]
        
        # Logic to create specific "Problem Personas"
        persona = random.choices(["Waste", "Under", "VAS_Heavy", "Optimal"], weights=[30, 20, 25, 25])[0]
        
        if persona == "Waste":
            current_plan = random.choice(["MTN Monthly 20GB", "MTN Monthly 50GB"])
            avg_usage = random.uniform(0.5, 5.0)
            expiry_hist = random.uniform(10.0, 35.0)
            days_left = random.randint(1, 5)
        elif persona == "Under":
            current_plan = random.choice(["MTN Weekly 1GB", "MTN Daily 2GB"])
            avg_usage = random.uniform(8.0, 15.0)
            expiry_hist = 0.0
            days_left = random.randint(0, 2)
        else:
            current_plan = random.choice(list(plans.keys()))
            avg_usage = random.uniform(1.0, 10.0)
            expiry_hist = random.uniform(0.0, 2.0)
            days_left = random.randint(1, 25)

        # VAS Logic
        if persona == "VAS_Heavy" or random.random() < 0.3:
            num_vas = random.randint(1, 4)
            selected_vas = random.sample(vas_options, num_vas)
            vas_names = ", ".join(selected_vas)
            vas_drain = num_vas * random.choice([200, 300, 450])
        else:
            num_vas = 0
            vas_names = "None"
            vas_drain = 0

        data.append({
            "phone": phone,
            "device_type": device,
            "current_plan": current_plan,
            "monthly_budget_naira": plans[current_plan] + vas_drain + random.randint(500, 2000),
            "avg_data_usage_3months": round(avg_usage, 2),
            "current_data_balance": round(random.uniform(0, 5), 2),
            "days_to_expiry": days_left,
            "last_3_months_avg_expiry_gb": round(expiry_hist, 2),
            "active_vas_count": num_vas,
            "vas_names": vas_names,
            "vas_monthly_drain": vas_drain,
            "voice_usage_pattern": random.choice(usage_patterns),
            "preferred_time_of_usage": random.choice(times)
        })

    return pd.DataFrame(data)

# Generate and Save
df_1000 = generate_mtn_data(1000)
df_1000.to_csv("users.csv", index=False)
print("Successfully generated mtn_1000_users.csv")