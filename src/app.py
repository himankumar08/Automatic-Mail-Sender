import os
import json
import time
import pandas as pd
import smtplib
from flask import Flask, jsonify, request, render_template, Response
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

app = Flask(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE_LEGACY = os.path.join(BASE_DIR, "data", "NNames.csv")
IMAGE_FILE = os.path.join(BASE_DIR, "assets", "img1.png")
TEMPLATE_FILE_LEGACY = os.path.join(BASE_DIR, "data", "template.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

# List of supported departments
DEPARTMENTS = ["ai23", "cse23", "it23", "ece23", "ee23"]

# Default email template
DEFAULT_TEMPLATE = {
    "subject": "Invitation to Farewell",
    "body": """Dear {name},

Greetings!

You are cordially invited to attend our event.

Event Details:
Date: 15 June 2026
Time: 10:00 AM
Venue: STCET Campus

We would be delighted by your presence.

Best Regards,
Event Team"""
}


def load_credentials():
    if os.path.exists(ENV_FILE):
        try:
            from dotenv import load_dotenv
            load_dotenv(ENV_FILE)
        except ImportError:
            # Fallback manual parser if python-dotenv is not installed
            with open(ENV_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip().strip('"').strip("'")
    return os.getenv("SENDER_EMAIL"), os.getenv("SENDER_PASSWORD")


def get_dept_paths(dept):
    # Sanitize department code to prevent directory traversal
    dept = "".join(c for c in dept if c.isalnum()).lower()
    dept_csv = os.path.join(BASE_DIR, "data", f"{dept}_names.csv")
    dept_template = os.path.join(BASE_DIR, "data", f"template_{dept}.json")

    # Migrate legacy ai23 data if applicable
    if dept == "ai23" and not os.path.exists(dept_csv):
        if os.path.exists(CSV_FILE_LEGACY):
            try:
                import shutil
                shutil.copy2(CSV_FILE_LEGACY, dept_csv)
            except Exception as e:
                print(f"Error migrating legacy NNames.csv: {e}")

    return dept_csv, dept_template


def load_template(dept):
    _, template_file = get_dept_paths(dept)
    if os.path.exists(template_file):
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback to legacy general template
    if os.path.exists(TEMPLATE_FILE_LEGACY):
        try:
            with open(TEMPLATE_FILE_LEGACY, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_TEMPLATE


def save_template(dept, template_data):
    _, template_file = get_dept_paths(dept)
    os.makedirs(os.path.dirname(template_file), exist_ok=True)
    with open(template_file, "w", encoding="utf-8") as f:
        json.dump(template_data, f, indent=4)


def load_recipients(dept):
    csv_file, _ = get_dept_paths(dept)
    if not os.path.exists(csv_file):
        os.makedirs(os.path.dirname(csv_file), exist_ok=True)
        df = pd.DataFrame(columns=["Name", "Email", "Subject", "Body"])
        df.to_csv(csv_file, index=False)
        return []
    try:
        df = pd.read_csv(csv_file)
        df = df.dropna(subset=["Name"])
        # Ensure all columns exist
        for col in ["Email", "Subject", "Body"]:
            if col not in df.columns:
                df[col] = ""
        df = df.fillna("")
        recipients = []
        for _, row in df.iterrows():
            recipients.append({
                "name": str(row["Name"]).strip(),
                "email": str(row["Email"]).strip(),
                "subject": str(row["Subject"]).strip(),
                "body": str(row["Body"]).strip()
            })
        return recipients
    except Exception as e:
        print(f"Error loading CSV for dept {dept}: {e}")
        return []


def save_recipients(dept, recipients):
    csv_file, _ = get_dept_paths(dept)
    # Ensure directory exists
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    df = pd.DataFrame(recipients)
    if not df.empty:
        # Rename columns to capitalize for CSV headers
        df = df.rename(columns={
            "name": "Name",
            "email": "Email",
            "subject": "Subject",
            "body": "Body"
        })
    else:
        df = pd.DataFrame(columns=["Name", "Email", "Subject", "Body"])
    df.to_csv(csv_file, index=False)


def load_names(dept):
    recipients = load_recipients(dept)
    return [r["name"] for r in recipients]


def save_names(dept, names):
    recipients = [{"name": n, "email": "", "subject": "", "body": ""} for n in names]
    save_recipients(dept, recipients)


@app.route("/")
def index():
    return render_template("index.html")


# --- Multi-Department API Routes ---

@app.route("/api/names/<dept>", methods=["GET"])
def get_names_dept(dept):
    if dept not in DEPARTMENTS:
        return jsonify({"error": f"Unsupported department: {dept}"}), 400
    return jsonify({"names": load_recipients(dept)})


@app.route("/api/names/<dept>", methods=["POST"])
def add_name_dept(dept):
    if dept not in DEPARTMENTS:
        return jsonify({"error": f"Unsupported department: {dept}"}), 400
    data = request.json or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()

    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

    recipients = load_recipients(dept)
    if any(r["name"].lower() == name.lower() for r in recipients):
        return jsonify({"error": "Name already exists"}), 400

    recipients.append({
        "name": name,
        "email": email,
        "subject": subject,
        "body": body
    })
    save_recipients(dept, recipients)
    return jsonify({"names": recipients})


@app.route("/api/names/<dept>", methods=["DELETE"])
def delete_name_dept(dept):
    if dept not in DEPARTMENTS:
        return jsonify({"error": f"Unsupported department: {dept}"}), 400
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

    recipients = load_recipients(dept)
    updated_recipients = [r for r in recipients if r["name"].lower() != name.lower()]
    if len(updated_recipients) == len(recipients):
        return jsonify({"error": "Name not found"}), 404

    save_recipients(dept, updated_recipients)
    return jsonify({"names": updated_recipients})


@app.route("/api/template/<dept>", methods=["GET"])
def get_template_dept(dept):
    if dept not in DEPARTMENTS:
        return jsonify({"error": f"Unsupported department: {dept}"}), 400
    return jsonify(load_template(dept))


@app.route("/api/template/<dept>", methods=["POST"])
def save_template_dept(dept):
    if dept not in DEPARTMENTS:
        return jsonify({"error": f"Unsupported department: {dept}"}), 400
    data = request.json or {}
    subject = data.get("subject", "").strip()
    body = data.get("body", "")

    if not subject:
        return jsonify({"error": "Subject cannot be empty"}), 400

    save_template(dept, {"subject": subject, "body": body})
    return jsonify({"message": "Template saved successfully"})


# --- Dashboard Stats and SMTP verification ---

@app.route("/api/stats", methods=["GET"])
def get_stats():
    stats = {}
    for d in DEPARTMENTS:
        stats[d] = len(load_names(d))
    
    sender_email, _ = load_credentials()
    smtp_configured = bool(sender_email)
    
    return jsonify({
        "stats": stats,
        "smtp_configured": smtp_configured,
        "sender_email": sender_email if smtp_configured else None
    })


@app.route("/api/test_smtp", methods=["POST"])
def test_smtp():
    sender_email, sender_password = load_credentials()
    if not sender_email or not sender_password:
        return jsonify({"success": False, "message": "SMTP credentials not found in .env"}), 400
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.quit()
        return jsonify({"success": True, "message": "SMTP credentials validated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"SMTP connection failed: {str(e)}"}), 500


@app.route("/api/send_custom", methods=["POST"])
def send_custom_email():
    sender_email, sender_password = load_credentials()
    if not sender_email or not sender_password:
        return jsonify({"success": False, "message": "SMTP credentials not found in .env"}), 400

    data = request.json or {}
    email_address = data.get("email", "").strip()
    name = data.get("name", "").strip()
    subject = data.get("subject", "").strip()
    body = data.get("body", "")
    attach_image = data.get("attach_image", True)

    if not email_address:
        return jsonify({"success": False, "message": "Recipient email address is required"}), 400
    if not subject:
        return jsonify({"success": False, "message": "Subject is required"}), 400
    if not body:
        return jsonify({"success": False, "message": "Body is required"}), 400

    # Apply personalized substitution if name is present
    if name:
        try:
            personalized_body = body.format(name=name)
        except Exception:
            personalized_body = body.replace("{name}", name)
    else:
        personalized_body = body

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email_address
        msg["Subject"] = subject
        msg.attach(MIMEText(personalized_body, "plain"))

        # Attach image if selected
        if attach_image:
            if os.path.exists(IMAGE_FILE):
                try:
                    with open(IMAGE_FILE, 'rb') as attachment:
                        img = MIMEImage(attachment.read())
                        img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(IMAGE_FILE))
                        msg.attach(img)
                except Exception as e:
                    return jsonify({"success": False, "message": f"Could not attach image: {str(e)}"}), 500

        # SMTP logic
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email_address, msg.as_string())
        server.quit()

        return jsonify({"success": True, "message": f"Email successfully sent to {email_address}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to send email: {str(e)}"}), 500


# --- Legacy API Endpoints (Fallback to ai23 for backward compatibility) ---

@app.route("/api/names", methods=["GET"])
def get_names():
    return jsonify({"names": load_names("ai23")})


@app.route("/api/names", methods=["POST"])
def add_name():
    return add_name_dept("ai23")


@app.route("/api/names", methods=["DELETE"])
def delete_name():
    return delete_name_dept("ai23")


@app.route("/api/template", methods=["GET"])
def get_template_api():
    return jsonify(load_template("ai23"))


@app.route("/api/template", methods=["POST"])
def save_template_api():
    return save_template_dept("ai23")


# --- Broadcast Logic ---

def generate_send_stream(dept, subject, body):
    sender_email, sender_password = load_credentials()
    if not sender_email or not sender_password:
        yield f"data: {json.dumps({'type': 'error', 'message': 'SMTP credentials not found in .env'})}\n\n"
        return

    recipients = load_recipients(dept)
    if not recipients:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No recipients in the list to send emails to.'})}\n\n"
        return

    yield f"data: {json.dumps({'type': 'info', 'message': f'Starting email broadcast to {len(recipients)} recipients in {dept.upper()}...'})}\n\n"

    # Connect to SMTP
    try:
        yield f"data: {json.dumps({'type': 'info', 'message': 'Connecting to SMTP server (smtp.gmail.com:587)...'})}\n\n"
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        yield f"data: {json.dumps({'type': 'info', 'message': 'SMTP connection established successfully.'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to connect to SMTP server: {str(e)}'})}\n\n"
        return

    total = len(recipients)
    for idx, recipient in enumerate(recipients, 1):
        name = recipient["name"]
        
        # Use custom email if defined, otherwise generate it
        email_address = recipient["email"]
        if not email_address:
            email_address = f"{dept}.{name.lower().replace(' ', '.') }@stcet.ac.in"
        
        # Use custom subject/body if defined, otherwise fall back to template default
        rec_subject = recipient["subject"] if recipient["subject"] else subject
        rec_body = recipient["body"] if recipient["body"] else body

        # Apply name replacement to template fallback body
        if not recipient["body"]:
            try:
                personalized_body = rec_body.format(name=name)
            except Exception:
                personalized_body = rec_body.replace("{name}", name)
        else:
            personalized_body = rec_body

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email_address
        msg["Subject"] = rec_subject
        msg.attach(MIMEText(personalized_body, "plain"))

        # Attach image
        if os.path.exists(IMAGE_FILE):
            try:
                with open(IMAGE_FILE, 'rb') as attachment:
                    img = MIMEImage(attachment.read())
                    img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(IMAGE_FILE))
                    msg.attach(img)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'warning', 'message': f'Could not attach image: {str(e)}'})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'warning', 'message': f'Attachment not found at: {IMAGE_FILE}'})}\n\n"

        # Send
        try:
            server.sendmail(sender_email, email_address, msg.as_string())
            yield f"data: {json.dumps({'type': 'success', 'message': f'[{idx}/{total}] Successfully sent to {name} ({email_address})'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'fail', 'message': f'[{idx}/{total}] Failed to send to {name} ({email_address}): {str(e)}'})}\n\n"

        # Delay to avoid Gmail rate limits
        if idx < total:
            time.sleep(2)

    try:
        server.quit()
    except Exception:
        pass

    yield f"data: {json.dumps({'type': 'done', 'message': f'All emails processed for {dept.upper()}.'})}\n\n"


@app.route("/api/send/<dept>", methods=["POST"])
def send_emails_dept(dept):
    if dept not in DEPARTMENTS:
        return jsonify({"error": f"Unsupported department: {dept}"}), 400
    data = request.json or {}
    subject = data.get("subject", "").strip()
    body = data.get("body", "")

    if not subject:
        template = load_template(dept)
        subject = template["subject"]
        body = template["body"]
    else:
        save_template(dept, {"subject": subject, "body": body})

    return Response(generate_send_stream(dept, subject, body), mimetype="text/event-stream")


@app.route("/api/send", methods=["POST"])
def send_emails():
    # Legacy default route falls back to ai23
    return send_emails_dept("ai23")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
