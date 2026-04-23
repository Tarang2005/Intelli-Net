# Intelli-Net
### Smart Incident & Telemetry Response Orchestrator
**SRM IST | Department of Networking and Communications | Minor Project**

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in your API keys
```

---

## Folder Structure

```
SICRO/
├── core/
│   ├── poller.py            ← live DNAC monitor (auto GenAI + Discord)
│   ├── genai.py             ← manual AI analysis
│   ├── webhook.py           ← manual Discord alert
│   └── engine.py            ← automated demo pipeline
│
├── tools/
│   ├── simulate_failure.py  ← inject fake failure for demo
│   ├── manual_resolver.py   ← resolve tickets manually
│   ├── view_tickets.py      ← view DB in terminal
│   └── resetdb.py           ← clear DB for fresh demo
│
├── data/                    ← JSON snapshots from DNAC
├── dashboard.py             ← Streamlit NOC dashboard
├── dnac.py                  ← fetch fresh data from DNAC
├── paths.py                 ← shared path config
├── .env                     ← API keys (never commit this)
└── requirements.txt
```

---

## Running the Demo (Dummy Data)

**Terminal 1 — Dashboard:**
```bash
streamlit run dashboard.py
```

**Terminal 2 — Automated pipeline:**
```bash
python core/engine.py
```

Or run manually step by step:
```bash
python tools/simulate_failure.py   # inject failure
python core/genai.py               # AI analysis
python core/webhook.py             # Discord alert
python tools/manual_resolver.py    # resolve ticket
```

---

## Running Live (Cisco DevNet Sandbox)

1. Connect Cisco AnyConnect VPN
2. Fill in `.env` with sandbox credentials
3. Run:
```bash
python dnac.py                     # fetch fresh data
streamlit run dashboard.py         # open dashboard
python core/poller.py              # start live monitoring
```

Poller automatically: detects failures → creates tickets → runs GenAI → pings Discord → resolves on recovery.

---

## Discord
Join the alert channel: https://discord.gg/4zqaT7Mw

---

## Team
- Tarang Patra — RA2311029010026
- Pranav K. Roy — RA2311029010055
- Karthik Saravanamuthu — RA2311029010057

**Guide:** Dr. Venkatesh K | Professor, Dept. of Networking and Communications
