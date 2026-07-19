import os
import uuid
import sqlite3
from flask import Flask, request, jsonify, abort
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# SECURITY FOUNDATION: Set up system database and encryption keys
DB_FILE = 'stealth_vault.db'
KEY_FILE = 'master_secret.key'

def get_or_create_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key
    with open(KEY_FILE, 'rb') as f:
        return f.read()

ENCRYPTION_KEY = get_or_create_key()
cipher = Fernet(ENCRYPTION_KEY)

def init_database():
    """Initializes the isolated, secure SQLite local database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS secure_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stealth_uuid TEXT UNIQUE NOT NULL,
            knowledge_hash TEXT NOT NULL,
            encrypted_payload BLOB NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/robots.txt')
def block_search_engines():
    """Instructs search crawlers to never index or track any page on this site."""
    return "User-agent: *\nDisallow: /", 200, {'Content-Type': 'text/plain'}

@app.route('/<string:entry_id>', methods=['GET'])
def access_stealth_portal(entry_id):
    """
    Evaluates the incoming link. If the dynamic UUID is invalid, 
    the server explicitly mimics a standard dead link (404 error).
    """
    try:
        # Validate that the path follows a strict UUID format before executing database searches
        uuid.UUID(entry_id)
    except ValueError:
        abort(404)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT stealth_uuid FROM secure_nodes WHERE stealth_uuid = ?", (entry_id,))
    node = cursor.fetchone()
    conn.close()

    if not node:
        abort(404)

    # Serve the blank frontend interface if the hidden dynamic link exists
    return INDEX_HTML

@app.route('/api/verify/<string:entry_id>', methods=['POST'])
def verify_knowledge_key(entry_id):
    """Validates the knowledge-based passphrase to safely decrypt stored data."""
    data = request.get_json()
    if not data or 'secret_phrase' not in data:
        return jsonify({"status": "error", "message": "Malformed request"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT knowledge_hash, encrypted_payload FROM secure_nodes WHERE stealth_uuid = ?", (entry_id,))
    record = cursor.fetchone()
    conn.close()

    if not record:
        abort(404)

    stored_hash, encrypted_payload = record

    # Verify passphrases locally using secure cryptographic hashing
    if check_password_hash(stored_hash, data['secret_phrase']):
        decrypted_data = cipher.decrypt(encrypted_payload).decode('utf-8')
        return jsonify({"status": "success", "payload": decrypted_data})
    
    return jsonify({"status": "unauthorized"}), 401

def seed_initial_account(secret_passphrase, sensitive_data):
    """Utility function to pre-generate a hidden profile directly into the system database."""
    generated_uuid = str(uuid.uuid4())
    hashed_phrase = generate_password_hash(secret_passphrase)
    encrypted_payload = cipher.encrypt(sensitive_data.encode('utf-8'))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO secure_nodes (stealth_uuid, knowledge_hash, encrypted_payload) VALUES (?, ?, ?)",
            (generated_uuid, hashed_phrase, encrypted_payload)
        )
        conn.commit()
        print(f"\n[SUCCESS] Stealth Profile Instantiated.")
        print(f"Your Family Link: http://127.0.0{generated_uuid}\n")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Not Found</title>
    <style>
        body { background-color: #ffffff; color: #000000; font-family: monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; overflow: hidden; }
        .hidden-container { display: none; text-align: center; width: 90%; max-width: 400px; }
        input { width: 100%; padding: 12px; margin-top: 10px; border: 1px solid #000; background: #fff; box-sizing: border-box; font-family: monospace; }
        button { width: 100%; padding: 12px; margin-top: 10px; background-color: #000; color: #fff; border: none; cursor: pointer; font-family: monospace; }
        .display-box { display: none; margin-top: 20px; padding: 15px; border: 1px dashed #000; text-align: left; white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body>
    <div id="error-screen"><h1>404 Not Found</h1></div>
    <div id="auth-screen" class="hidden-container">
        <h3>Verify Security Authorization</h3>
        <input type="password" id="secretKey" placeholder="Enter Knowledge Passphrase">
        <button onclick="submitKey()">Execute Decryption</button>
        <div id="output" class="display-box"></div>
    </div>
    <script>
        // Knowledge-based trigger: Tap the '404 Not Found' text 5 times to reveal the interface
        let triggerCount = 0;
        document.getElementById('error-screen').addEventListener('click', () => {
            triggerCount++;
            if (triggerCount >= 5) {
                document.getElementById('error-screen').style.display = 'none';
                document.getElementById('auth-screen').style.display = 'block';
            }
        });

        async function submitKey() {
            const inputKey = document.getElementById('secretKey').value;
            const pathId = window.location.pathname.substring(1);
            const response = await fetch(`/api/verify/${pathId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ secret_phrase: inputKey })
            });
            const result = await response.json();
            const outputDiv = document.getElementById('output');
            if(result.status === 'success') {
                outputDiv.style.display = 'block';
                outputDiv.innerText = result.payload;
            } else {
                alert('Authorization Failure.');
            }
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    init_database()
    # SEEDING: Creating a test profile for your framework verification
    # Replace these strings with your family passphrases and real legacy notes during live execution
    seed_initial_account("MyFamilySecretKey2026", "Secure Family Vault Metadata: Routing Number XXXXX, Account Number XXXXX")
    app.run(debug=True, port=5000)
