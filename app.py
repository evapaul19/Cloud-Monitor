# app.py
from flask import Flask, jsonify, render_template, send_from_directory
from threading import Thread, Event
import time, requests, json, os
from datetime import datetime
from dotenv import load_dotenv
import smtplib

load_dotenv()

# Configuration (can also be set via environment variables)
MONITOR_URL = os.getenv("MONITOR_URL", "https://api.github.com")  # service endpoint to monitor
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))  # seconds between checks
LATENCY_THRESHOLD = float(os.getenv("LATENCY_THRESHOLD", "1.0"))  # seconds
INCIDENT_FILE = os.getenv("INCIDENT_FILE", "incidents.json")

# Email alert settings (optional)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") if os.getenv("SMTP_PORT") else 0)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_TO = os.getenv("ALERT_TO", "")  # comma-separated

app = Flask(__name__, static_folder="static", template_folder="templates")

# Utility: read/write incidents
def load_incidents():
    if not os.path.exists(INCIDENT_FILE):
        return []
    with open(INCIDENT_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_incident(inc):
    incidents = load_incidents()
    incidents.insert(0, inc)  # newest first
    incidents = incidents[:200]  # keep size bounded
    with open(INCIDENT_FILE, "w") as f:
        json.dump(incidents, f, indent=2)

def send_email_alert(subject, body):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS or not ALERT_TO:
        return False
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            msg = f"Subject: {subject}\n\n{body}"
            server.sendmail(SMTP_USER, ALERT_TO.split(","), msg)
        return True
    except Exception as e:
        print("Failed to send email:", e)
        return False

# Monitor thread
stop_event = Event()

def monitor_loop():
    print("Monitor started. Monitoring:", MONITOR_URL)
    last_status = None
    while not stop_event.is_set():
        timestamp = datetime.utcnow().isoformat() + "Z"
        try:
            start = time.time()
            r = requests.get(MONITOR_URL, timeout=10)
            latency = round(time.time() - start, 3)
            status = r.status_code
            healthy = (status == 200 and latency <= LATENCY_THRESHOLD)

            record = {
                "timestamp": timestamp,
                "url": MONITOR_URL,
                "status": status,
                "latency": latency,
                "healthy": healthy
            }

            # Log incidents when unhealthy or status changed to unhealthy
            if not healthy:
                inc = {
                    "timestamp": timestamp,
                    "type": "UNHEALTHY",
                    "details": record
                }
                save_incident(inc)
                print("[ALERT]", inc)
                # send email
                subject = f"[CloudPulse] ALERT: {MONITOR_URL} unhealthy ({status})"
                body = f"Time: {timestamp}\nStatus: {status}\nLatency: {latency}s\nURL: {MONITOR_URL}"
                send_email_alert(subject, body)

            # Optional: log recoveries
            if last_status is not None and last_status != status and status == 200:
                rec = {
                    "timestamp": timestamp,
                    "type": "RECOVERY",
                    "details": record
                }
                save_incident(rec)
                print("[RECOVERY]", rec)
            last_status = status

        except Exception as e:
            # service unreachable -> incident
            inc = {
                "timestamp": timestamp,
                "type": "ERROR",
                "details": {"error": str(e)}
            }
            save_incident(inc)
            print("[ERROR] Could not reach service:", e)
            subject = f"[CloudPulse] ERROR: {MONITOR_URL} unreachable"
            body = f"Time: {timestamp}\nError: {e}\nURL: {MONITOR_URL}"
            send_email_alert(subject, body)

        # sleep with early stop ability
        for _ in range(int(CHECK_INTERVAL)):
            if stop_event.is_set():
                break
            time.sleep(1)

# Flask routes
@app.route("/")
def index():
    return render_template("index.html", monitor_url=MONITOR_URL, latency_threshold=LATENCY_THRESHOLD)

@app.route("/api/status")
def api_status():
    incidents = load_incidents()
    latest = incidents[0] if incidents else {"timestamp": None, "type": "OK", "details": {}}
    return jsonify({
        "monitored_url": MONITOR_URL,
        "latest_incident": latest,
        "incidents": incidents[:20]
    })

@app.route("/static/<path:path>")
def static_proxy(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    # Start monitor thread
    t = Thread(target=monitor_loop, daemon=True)
    t.start()
    try:
        app.run(host="0.0.0.0", port=5000)
    finally:
        stop_event.set()
        t.join()
