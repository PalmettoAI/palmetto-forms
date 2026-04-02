#!/usr/bin/env python3
import os
import json
import resend
from flask import Flask, request, redirect, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

resend.api_key = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "forms@palmettoaiautomation.com")
CLIENTS_FILE = os.path.join(os.path.dirname(__file__), "clients.json")

SKIP_FIELDS = {"client_id", "_redirect", "_honeypot"}


def load_clients():
    with open(CLIENTS_FILE) as f:
        entries = json.load(f)
    return {c["id"]: c for c in entries}


def build_email_html(client_name, fields):
    rows = "".join(
        f"<tr><td style='padding:6px 12px;font-weight:600;color:#555;white-space:nowrap'>"
        f"{k.replace('_', ' ').replace('-', ' ').title()}</td>"
        f"<td style='padding:6px 12px;color:#222'>{v}</td></tr>"
        for k, v in fields.items()
    )
    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1)">
    <div style="background:#CC0000;padding:20px 24px">
      <h2 style="margin:0;color:#fff;font-size:1.2rem">New Estimate Request</h2>
      <p style="margin:4px 0 0;color:rgba(255,255,255,0.85);font-size:0.9rem">{client_name}</p>
    </div>
    <div style="padding:24px">
      <table style="width:100%;border-collapse:collapse">
        {rows}
      </table>
    </div>
    <div style="padding:12px 24px;background:#f9f9f9;border-top:1px solid #eee">
      <p style="margin:0;font-size:0.75rem;color:#999">Sent by PalmettoAI Forms \u2014 palmettoaiautomation.com</p>
    </div>
  </div>
</body>
</html>"""


@app.route("/submit", methods=["POST"])
def submit():
    data = request.form.to_dict()

    if data.get("_honeypot", "").strip():
        return redirect(data.get("_redirect", "/"), 302)

    client_id = data.get("client_id", "").strip()
    redirect_url = data.get("_redirect", "/").strip()

    try:
        clients = load_clients()
    except Exception as e:
        app.logger.error(f"Failed to load clients.json: {e}")
        return jsonify({"error": "Service configuration error"}), 500

    client = clients.get(client_id)
    if not client:
        app.logger.warning(f"Unknown client_id: '{client_id}'")
        return jsonify({"error": f"Unknown client: {client_id}"}), 400

    fields = {k: v for k, v in data.items() if k not in SKIP_FIELDS and v.strip()}

    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": client["email"],
            "subject": f"New Estimate Request \u2014 {client['name']}",
            "html": build_email_html(client["name"], fields),
        })
        app.logger.info(f"Email sent for {client_id} \u2192 {client['email']}")
    except Exception as e:
        app.logger.error(f"Resend error for {client_id}: {e}")
        return jsonify({"error": "Failed to send email"}), 500

    return redirect(redirect_url, 302)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "clients": len(load_clients())}), 200


@app.route("/", methods=["GET"])
def index():
    return jsonify({"service": "palmetto-forms", "status": "running"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
