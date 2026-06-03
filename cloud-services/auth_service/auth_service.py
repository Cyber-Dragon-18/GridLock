import sqlite3
import bcrypt
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
CORS(app)
app.config['JWT_SECRET_KEY'] = 'mysecretkey'
jwt = JWTManager(app)
DB_PATH = 'users.db'

# Storage tiers (bytes). Demo-friendly so enforcement is easy to show.
TIERS = {
    "free":       {"label": "Free",       "limit_bytes": 1 * 1024 * 1024 * 1024},    # 1 GB
    "pro":        {"label": "Pro",        "limit_bytes": 5 * 1024 * 1024 * 1024},    # 5 GB
    "enterprise": {"label": "Enterprise", "limit_bytes": 10 * 1024 * 1024 * 1024},  # 10 GB
}
DEFAULT_TIER = "free"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tier_column():
    """Add Storage_Tier column if it doesn't exist yet (safe to run repeatedly)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(USER)")
    cols = [r["name"] for r in cur.fetchall()]
    if "Storage_Tier" not in cols:
        cur.execute("ALTER TABLE USER ADD COLUMN Storage_Tier TEXT DEFAULT 'free'")
        conn.commit()
    conn.close()


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO USER (Email, Password, First_Name, Last_Name, Storage_Tier)
            VALUES (?, ?, ?, ?, ?)
        """, (email, hashed, first_name, last_name, DEFAULT_TIER))
        conn.commit()
        conn.close()
        return jsonify({'message': 'User registered successfully!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 409


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USER WHERE Email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    if bcrypt.checkpw(password.encode('utf-8'), user['Password']):
        token = create_access_token(identity=str(user['User_ID']))
        return jsonify({'token': token}), 200
    else:
        return jsonify({'error': 'Wrong password'}), 401


@app.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT User_ID, First_Name, Last_Name, Email, Storage_Tier FROM USER WHERE User_ID = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    tier_key = (user['Storage_Tier'] or DEFAULT_TIER)
    tier = TIERS.get(tier_key, TIERS[DEFAULT_TIER])
    return jsonify({
        'user_id': user['User_ID'],
        'first_name': user['First_Name'],
        'last_name': user['Last_Name'],
        'email': user['Email'],
        'storage_tier': tier_key,
        'storage_label': tier['label'],
        'storage_limit_bytes': tier['limit_bytes'],
    }), 200


@app.route('/tiers', methods=['GET'])
def tiers():
    """Public list of available tiers so the UI can render the picker."""
    return jsonify([
        {"key": k, "label": v["label"], "limit_bytes": v["limit_bytes"]}
        for k, v in TIERS.items()
    ]), 200


@app.route('/profile/tier', methods=['POST'])
@jwt_required()
def update_tier():
    user_id = get_jwt_identity()
    data = request.get_json()
    new_tier = data.get('storage_tier')
    if new_tier not in TIERS:
        return jsonify({'error': 'Invalid tier'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE USER SET Storage_Tier = ? WHERE User_ID = ?", (new_tier, user_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'updated', 'storage_tier': new_tier, 'storage_label': TIERS[new_tier]['label']}), 200


# Internal endpoint: storage service asks "what's this user's limit?" by email.
@app.route('/limit', methods=['GET'])
def limit_for_email():
    email = request.args.get('email')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Storage_Tier FROM USER WHERE Email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    tier_key = (user['Storage_Tier'] if user and user['Storage_Tier'] else DEFAULT_TIER)
    tier = TIERS.get(tier_key, TIERS[DEFAULT_TIER])
    return jsonify({'storage_tier': tier_key, 'limit_bytes': tier['limit_bytes']}), 200


if __name__ == '__main__':
    ensure_tier_column()
    app.run(port=5001, debug=True)
