# STCET - Automatic Mail Sender

A secure, premium, multi-department bulk email invitation system designed for STCET batches. The application allows users to maintain separate lists of recipients, customize email drafts, view real-time mock previews, and execute rate-limited email broadcasts via Gmail SMTP with Server-Sent Events (SSE) progress logs.

---

## 🚀 Key Features

* **Multi-Department Management**: Dedicated workspaces for five key departments:
  * **AI** (`ai23`)
  * **CSE23** (`cse23`)
  * **IT23** (`it23`)
  * **ECE23** (`ece23`)
  * **EE23** (`ee23`)
* **Auto-Formatted Email Mapping**: Automatically formats student email addresses based on department prefixes, e.g., `cse23.john.doe@stcet.ac.in`.
* **Personalized Invitations**: Automatically substitutes the `{name}` tag inside subject or body templates dynamically for each recipient.
* **Premium Glassmorphic Dashboard**: Sleek, modern dark-themed Single Page App (SPA) layout utilizing smooth navigation and real-time statistics.
* **Real-time Email Client Simulator**: Live preview viewport that resolves personalized greetings and subjects on the fly as you write the draft.
* **Background SSE Streaming**: Email broadcasts stream progress percentages and console output logs dynamically. Switching department tabs does not interrupt active broadcasts.
* **SMTP Diagnostic Utilities**: Quick handshake health checks from the settings menu to verify environment configurations.
* **Legacy Compatibility**: Automatically migrates old data lists (`NNames.csv`) on first start and maintains backward-compatible API endpoints.

---

## 📂 Project Structure

```
├── assets/
│   └── img1.png             # Default image attachment appended to outgoing emails
├── data/
│   ├── NNames.csv           # Legacy recipient name file (AI backup)
│   ├── ai23_names.csv       # AI recipient data sheet
│   ├── cse23_names.csv      # CSE23 recipient data sheet
│   ├── it23_names.csv       # IT23 recipient data sheet
│   ├── ece23_names.csv      # ECE23 recipient data sheet
│   ├── ee23_names.csv       # EE23 recipient data sheet
│   └── template.json        # Legacy fallback email template draft
├── src/
│   ├── app.py               # Main Flask backend server (routes, SMTP, SSE logs)
│   ├── main.py              # CLI version of the email sender (legacy standalone)
│   └── templates/
│       └── index.html       # Dynamic SPA dashboard front-end interface
├── .env.example             # Template for SMTP server credentials
├── .env                     # Secure credentials file (ignored by version control)
└── README.md                # Project documentation
```

---

## 🛠️ Setup and Installation

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system. 

### 2. Install Dependencies
Open your terminal in the project directory and install the required library packages:
```bash
pip install flask pandas openpyxl python-dotenv
```

### 3. Configure SMTP Credentials
1. Copy the `.env.example` file and rename it to `.env`:
   ```bash
   copy .env.example .env
   ```
2. Open `.env` and fill in your Gmail email address and App Password:
   ```env
   SENDER_EMAIL="your_stcet_or_gmail_address@stcet.ac.in"
   SENDER_PASSWORD="your_app_specific_password_here"
   ```
   > ⚠️ **Note**: For security, do not use your main account login password. Instead, generate a 16-digit **App Password** from your [Google Account App Passwords Settings](https://myaccount.google.com/apppasswords).

### 4. Event Attachment
If you wish to send an image (e.g. event banner or flyer card) along with the emails, save it as `img1.png` inside the `assets/` directory. If the file is not found, emails will send normally without an attachment.

---

## 🚦 How to Run the Application

1. Start the Flask application by running:
   ```bash
   python src/app.py
   ```
2. Once running, open your web browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```
3. **Run diagnostics**: Go to the **Settings** section in the sidebar menu and click **Run SMTP Diagnostic** to ensure the backend is connected to the Gmail servers.
4. **Manage lists**: Choose a department (e.g., **CSE23**), add student names, customize your template draft, and click **Start Email Broadcast** to watch the streaming console send invitations!
