# 🟡 PlanWise AI — Intelligent Data Plan Recommender for Telecom Users in Nigeria

> **Smarter plans. Lower costs. Happier users.**

PlanWise AI is an AI-powered subscriber intelligence platform built for Nigerian telecom operators (MTN Nigeria focus). It analyses subscriber behaviour, detects waste, generates personalised plan recommendations, fires bulk and individual SMS alerts, and — crucially — **converts unused data balance to a subscriber's most-used service before it expires**, ensuring zero value is lost.

---

## 📑 Table of Contents

- [Problem Statement](#-problem-statement)
- [Proposed Solution](#-proposed-solution)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Installation & Setup](#-installation--setup)
- [Running the App](#-running-the-app)
- [CSV Data Schema](#-csv-data-schema)
- [Conversion Rate Logic](#-conversion-rate-logic)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Team](#-team)
- [License](#-license)

---

## 🚨 Problem Statement

The Nigerian telecom landscape has over 100 different data plans and service subscriptions across MTN, Airtel, and Globacom. According to the NCC 2026 report, telecom subscriptions have surpassed **182.2 million** as data usage continues to surge.

Users consistently fall into three inefficient patterns:

| Pattern | Description | Impact |
|---|---|---|
| **Over-provisioning** | Buying large bundles that exceed actual needs | Data expires unused every cycle |
| **Under-provisioning** | Buying too little, falling back to expensive PAYG rates | Users overpay by 3–5× per GB |
| **Hidden VAS Drain** | Enrolled in recurring services without clear consent | Silent airtime deductions, billing distrust |

These issues cause billing surprises, perceived unfairness, and approximately **20% annual customer churn** across Nigerian telcos. Telecom operators currently lack tools to offer proactive, personalised subscription management.

---

## 💡 Proposed Solution

PlanWise AI is a three-feature intelligent platform:

### 1. 🧠 Intelligent Plan Recommendation System
Analyses 3-month historical data usage, call patterns, and subscription history to:
- Identify whether a user over-uses, under-uses, or wastes data
- Recommend the most cost-effective plan from available bundles
- Flag feature-phone users on data-heavy plans as mismatched

### 2. 🔔 Smart Subscription & VAS Control System
Continuously monitors all active VAS subscriptions to:
- Alert users before renewal or airtime deduction
- Flag VAS services consuming > 15% of monthly budget
- Recommend cancellation of unused or rarely accessed services

### 3. 🔄 Adaptive Value Conversion Engine *(Core Innovation)*
Dynamically converts unused data balance to the service the subscriber actually uses most — before it expires:
- **High voice users** → unused data converts to airtime credit
- **High data users** → balance rolls over as carry-over data for the next cycle
- **Heavy VAS subscribers** → balance converts to VAS credit
- **Feature phone users** → flagged so data-bonus incentives are redirected appropriately

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                              │
│  CSV upload / MTN SMSC sync / Africa's Talking API              │
│  Fields: usage history · call patterns · VAS subscriptions      │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       AI / LOGIC LAYER                           │
│  build_ai_recommendation()  · determine_primary_service()        │
│  calculate_conversion()     · extract_plan_gb()                  │
│  Priority scoring: High / Medium / Low                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    BUSINESS RULES LAYER                          │
│  Usage ratio thresholds · Budget % checks · Device type filters  │
│  Expiry urgency windows · VAS drain ceilings                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  EXECUTION & USER INTERFACE                       │
│  Streamlit Dashboard  ·  SMS Gateway (Africa's Talking)          │
│  In-App Notifications ·  Conversion Engine UI                    │
│  Bulk actions  ·  Individual overrides  ·  Exportable logs       │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

The application is divided into **8 dashboard sections**:

### Section 1 — Subscriber Intelligence Dashboard
- Full enriched table of all subscribers with computed AI columns
- Colour-coded priority column (🔴 High / 🟠 Medium / 🟢 Low)
- Four KPI tiles: High Priority count, Medium Priority count, Avg Monthly Waste (GB), Total VAS Drain (₦)

### Section 2 — Smart Bulk Notification Engine
- Multi-select filter by alert priority
- One-click **"Send Bulk Alerts"** dispatches personalised SMS to all matching subscribers
- Every dispatch is logged to both the SMS Gateway Log and the In-App Notification bell

### Section 3 — SMS Gateway Transmission Logs
- Live table of every SMS sent (timestamp, recipient, message, status)
- CSV export and log-clearing controls

### Section 4 — In-App Notification Log
- Persistent bell counter showing unread alerts
- Full history of all system-generated and manual notifications
- "Mark all as read" and "Clear" controls

### Section 5 — Individual Manual Override
- Subscriber profile card (device, plan, budget, VAS drain, usage, balance, voice pattern)
- AI recommendation pre-filled in an editable SMS composer
- Character counter with SMS segment indicator (160 / 320 chars)
- **"Send Single SMS"** button for targeted manual dispatch

### Section 6 — Plan Optimizer Quick Insights
- Sorted table of all subscribers wasting > 1 GB/month
- Prime downgrade candidates ranked by average expired data

### Section 7 — Adaptive Value Conversion Engine (Bulk)
- Expiry threshold slider (1–30 days)
- Live preview table showing: phone, plan, balance, days left, primary service, what they'll receive, naira equivalent
- Total-value-preserved KPI metric
- **"🔄 Convert All"** button: processes every eligible subscriber, logs conversion, posts in-app notification, and fires SMS confirmation
- Conversion Logs table with CSV export

### Section 8 — Individual Value Conversion
- Independent subscriber selector (no widget conflict with Section 5)
- Conversion preview card with balance, days left, AI-determined primary service, and ₦ estimate
- Plain-language conversion summary (e.g. *"1.12 GB → ₦280 airtime (~25 mins MTN-MTN)"*)
- Manual **override radio** to switch target to Data carry-over, Voice/Airtime, or VAS Credit
- **"✅ Execute Conversion"** button — disabled automatically when balance is zero
- All conversions flow into the shared Conversion Logs and SMS Gateway

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend / UI** | Streamlit | Interactive dashboard and all UI components |
| **Data Processing** | Pandas, NumPy | DataFrame manipulation, usage calculations |
| **AI / Logic** | Python rules engine | Scoring, recommendation, conversion logic |
| **SMS Gateway** | Africa's Talking API *(simulated)* | Subscriber notifications and confirmations |
| **Notifications** | Streamlit session state | In-app bell / notification feed |
| **Data Storage** | Session state → PostgreSQL / Firebase *(production)* | Conversion logs, SMS logs, alert history |
| **Deployment** | Streamlit Cloud / Docker | Hosting and containerisation |
| **CI/CD** | GitHub Actions | Automated testing and continuous integration |

---

## 📦 Installation & Setup

### Prerequisites

- Python **3.9 or higher**
- `pip` package manager

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/planwise-ai.git
cd planwise-ai
```

### 2. Create and activate a virtual environment *(recommended)*

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt`** contents:

```
streamlit>=1.35.0
pandas>=2.0.0
```

> No other third-party libraries are required. The app uses Python's built-in `re`, `datetime`, and `time` modules for all other functionality.

---

## ▶️ Running the App

```bash
streamlit run planwise_app.py
```

The app opens automatically at **`http://localhost:8501`**.

On first launch, five sample subscribers are pre-loaded so every section is immediately functional — no CSV upload required.

### Loading your own subscriber data

1. Prepare a CSV file matching the schema below.
2. Use the **"Upload Subscriber CSV"** button in the left sidebar.
3. All eight dashboard sections update automatically.

---

## 📋 CSV Data Schema

Your subscriber CSV must contain the following columns (column order does not matter):

| Column | Type | Description | Example |
|---|---|---|---|
| `phone` | string | Subscriber MSISDN (digits only) | `8033164749` |
| `device_type` | string | `Smartphone` or `Feature Phone` | `Smartphone` |
| `current_plan` | string | Active MTN bundle name | `MTN Monthly 50GB` |
| `monthly_budget_naira` | float | Estimated monthly telecom spend (₦) | `12461` |
| `avg_data_usage_3months` | float | 3-month average data consumption (GB) | `2.31` |
| `current_data_balance` | float | Remaining data balance right now (GB) | `1.12` |
| `days_to_expiry` | int | Days until current plan expires | `15` |
| `last_3_months_avg_expiry_gb` | float | Average GB expired unused per month | `1.87` |
| `active_vas_count` | int | Number of active VAS subscriptions | `2` |
| `vas_names` | string | Comma-separated VAS names (or `None`) | `Daily Devotional, MusicPlus` |
| `vas_monthly_drain` | float | Total monthly VAS cost (₦) | `900` |
| `voice_usage_pattern` | string | `Low` / `Medium` / `High` / `Very-High` | `High` |
| `preferred_time_of_usage` | string | `Morning` / `Evening` / `Night` / `All-Day` | `Morning` |

### Supported plan name formats

The engine automatically parses GB capacity from plan names:

| Plan Name Format | Monthly GB Estimate |
|---|---|
| `MTN Monthly 50GB` | 50.0 GB |
| `MTN Monthly 20GB` | 20.0 GB |
| `MTN Monthly 10GB` | 10.0 GB |
| `MTN Weekly 5GB` | 21.5 GB (× 4.3) |
| `MTN Weekly 1GB` | 4.3 GB |
| `MTN Daily 2GB` | 60.0 GB (× 30) |
| `MTN BetaTalk` | 0.5 GB (voice-primary plan) |

---

## 🔢 Conversion Rate Logic

The Adaptive Value Conversion Engine uses conservative MTN Nigeria market rates:

| Constant | Value | Source |
|---|---|---|
| `_NAIRA_PER_GB` | ₦250 per GB | Mid-tier MTN bundle rate |
| `_NAIRA_PER_MIN` | ₦11 per minute | MTN-MTN on-net call rate |

### Primary service scoring (`determine_primary_service`)

Each subscriber is scored 0–4 across three services and assigned to the highest scorer:

```
voice_score = {"Very-High": 4, "High": 3, "Medium": 2, "Low": 1}
data_score  = min(4, avg_usage_gb / plan_monthly_gb × 4)
vas_score   = min(4, active_vas_count + (vas_monthly_drain / monthly_budget × 4))
```

### Conversion outcomes

| Primary Service | What Happens | Example |
|---|---|---|
| **Voice/Airtime** | Balance × ₦250/GB → airtime credit | 1.12 GB → ₦280 (~25 MTN-MTN mins) |
| **Data** | Balance preserved as carry-over for next renewal | 2.5 GB → 2.5 GB carry-over |
| **VAS Credit** | Balance × ₦250/GB → VAS subscription credit | 2 GB → ₦500 (~0.5 mo VAS coverage) |

Subscribers with **zero data balance** are automatically flagged as ineligible and the Execute button is disabled.

---

## 📁 Project Structure

```
planwise-ai/
│
├── planwise_app.py          # Main Streamlit application (all 8 sections)
├── requirements.txt         # Python dependencies
├── README.md                # This file
│
├── data/
│   └── sample_subscribers.csv   # Sample dataset (optional, for testing)
│
└── docs/
    ├── PlanWise_AI_Pitch_Deck.pptx          # Project pitch deck
    └── Intelligent_Data_Plan_Recommender.docx  # Full system design report
```

---

## 🗺 Roadmap

### Prototype (current)
- [x] Rule-based AI recommendation engine
- [x] Bulk SMS alert dispatch (Africa's Talking simulation)
- [x] In-app notification feed
- [x] Individual manual override with SMS composer
- [x] Plan Optimizer waste detection
- [x] Bulk pre-expiry value conversion
- [x] Individual value conversion with manual override
- [x] Exportable SMS and conversion logs

### v2 — ML Integration
- [ ] Scikit-learn / XGBoost model replacing rule-based scoring
- [ ] Prophet / LSTM forecasting for future data consumption
- [ ] Subscriber segmentation (clustering)
- [ ] A/B testing framework for incentive effectiveness

### v3 — Production Deployment
- [ ] Live Africa's Talking SMS API integration
- [ ] PostgreSQL backend for persistent logs
- [ ] Firebase FCM push notifications for mobile
- [ ] REST API (FastAPI) for telecom operator backend integration
- [ ] USSD fallback interface for feature phone users
- [ ] Multi-operator support (Airtel, Glo)
- [ ] Role-based access (admin vs. agent)

---

## 👥 Team

| Name | Role |
|---|---|
| **Yusuf Babatunde** | Prototype Developer |
| **Onibon-Bello Fatima** | Solution Documentation |
| **Yusuf Kolawole** | Software Architecture |

---

## 📄 License

This project is released under the **MIT License**.

```
MIT License

Copyright (c) 2026 PlanWise AI Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgements

- [Streamlit](https://streamlit.io/) — for making data apps fast to build
- [Africa's Talking](https://africastalking.com/) — SMS gateway powering the notification layer
- [NCC Nigeria](https://ncc.gov.ng/) — for the 2026 telecom subscription data referenced in the problem statement
- MTN Nigeria — for the plan structures used in prototype data generation

---

> Built with ❤️ for the Nigerian telecom ecosystem.  
> *PlanWise AI — turning billing frustration into billing transparency.*
