from flask import Flask, jsonify, render_template_string
import requests
import time
from datetime import datetime

app = Flask(__name__)

MONITOR_URL = "https://api.github.com"
LATENCY_THRESHOLD = 1.0

status_data = {"status": "Checking...", "latency": None, "last_checked": None}

@app.route("/")
def dashboard():
    return render_template_string("""
        <html>
        <head>
            <title>🌩️ Cloud Monitor Dashboard</title>
            <style>
                body {
                    font-family: 'Segoe UI', sans-serif;
                    background-color: #0f172a;
                    color: white;
                    text-align: center;
                    padding-top: 100px;
                }
                .status-box {
                    display: inline-block;
                    padding: 20px 40px;
                    border-radius: 15px;
                    background-color: #1e293b;
                    box-shadow: 0px 0px 20px rgba(0,0,0,0.3);
                }
                .ok { color: #4ade80; }
                .fail { color: #f87171; }
            </style>
        </head>
        <body>
            <h1>🌩️ Cloud Monitor Dashboard</h1>
            <h3>Monitoring: {{ url }}</h3>
            <div class="status-box">
                <p id="status">Status: Checking...</p>
                <p id="latency">Latency: --</p>
                <p id="checked">Last Checked: --</p>
            </div>

            <script>
                async function updateStatus() {
                    const res = await fetch('/status');
                    const data = await res.json();

                    document.getElementById('status').innerHTML = 
                        'Status: ' + (data.status === 'UP' ? '✅ <span class="ok">UP</span>' : '❌ <span class="fail">DOWN</span>');
                    document.getElementById('latency').innerHTML = 'Latency: ' + data.latency.toFixed(2) + ' ms';
                    document.getElementById('checked').innerHTML = 'Last Checked: ' + data.last_checked;
                }

                setInterval(updateStatus, 3000);
                updateStatus();
            </script>
        </body>
        </html>
    """, url=MONITOR_URL)


@app.route("/status")
def get_status():
    try:
        start = time.time()
        response = requests.get(MONITOR_URL, timeout=3)
        latency = (time.time() - start) * 1000
        status_data["status"] = "UP" if response.status_code == 200 else "DOWN"
        status_data["latency"] = latency
    except Exception:
        status_data["status"] = "DOWN"
        status_data["latency"] = 0

    status_data["last_checked"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return jsonify(status_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
