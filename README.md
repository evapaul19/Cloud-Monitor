# CloudPulse — Mini Cloud Service Health Monitor

## What it is
A compact Python + Flask project that simulates proactive cloud monitoring:
- Periodically checks a service endpoint for status & latency
- Logs incidents to `incidents.json`
- (Optional) Sends email alerts via SMTP
- Provides a lightweight dashboard to view current status and recent incidents

## Run locally
1. Create a virtualenv and install:
   ```bash
   python -m venv venv
   source venv/bin/activate    # windows: venv\Scripts\activate
   pip install -r requirements.txt
