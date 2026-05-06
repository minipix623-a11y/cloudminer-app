import os
import sqlite3
import time
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), '../data/mining.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance REAL DEFAULT 0,
        total_earned REAL DEFAULT 0,
        referral_code TEXT UNIQUE,
        referred_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_miners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        miner_id INTEGER,
        quantity INTEGER DEFAULT 1,
        upgrade_level INTEGER DEFAULT 0,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, miner_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referral_id INTEGER,
        earnings REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        type TEXT,
        description TEXT,
        tx_hash TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        address TEXT,
        tx_hash TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

def create_user(user_id, username, first_name, referral_code=None, referred_by=None):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (user_id, username, first_name, referral_code, referred_by)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, username, first_name, referral_code, referred_by))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return dict(c.fetchone() or {})

def update_balance(user_id, amount, description=""):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    if amount > 0:
        c.execute('UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?', (amount, user_id))
    if description:
        c.execute('INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                  (user_id, amount, 'deposit' if amount > 0 else 'withdraw', description))
    conn.commit()
    conn.close()

def buy_miner(user_id, miner_id, quantity=1):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO user_miners (user_id, miner_id, quantity)
                 VALUES (?, ?, ?)
                 ON CONFLICT(user_id, miner_id) DO UPDATE SET quantity = quantity + ?''',
              (user_id, miner_id, quantity, quantity))
    conn.commit()
    conn.close()

def upgrade_miner(user_id, miner_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM user_miners WHERE user_id = ? AND miner_id = ?', (user_id, miner_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return None

    new_level = (row['upgrade_level'] or 0) + 1
    c.execute('UPDATE user_miners SET upgrade_level = ? WHERE user_id = ? AND miner_id = ?',
              (new_level, user_id, miner_id))
    conn.commit()
    conn.close()
    return new_level

def get_user_miners(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT miner_id, quantity, upgrade_level FROM user_miners WHERE user_id = ?', (user_id,))
    return [dict(row) for row in c.fetchall()]

def get_user_miners_full(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM user_miners WHERE user_id = ?', (user_id,))
    return [dict(row) for row in c.fetchall()]

def get_rating(limit=100):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT user_id, first_name, username,
                 (SELECT SUM(quantity * m.income_per_hour * (1 + COALESCE(um.upgrade_level, 0) * 0.1))
                  FROM user_miners um JOIN miners m ON um.miner_id = m.id
                  WHERE um.user_id = users.user_id) as income_per_hour
                 FROM users
                 ORDER BY income_per_hour DESC
                 LIMIT ?''', (limit,))
    return [dict(row) for row in c.fetchall()]

def get_referral_stats(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) as count, SUM(earnings) as total
                 FROM referrals WHERE referrer_id = ?''', (user_id,))
    result = c.fetchone()
    return {'count': result[0] or 0, 'total': result[1] or 0}

def credit_referral_earnings(referrer_id, referral_id, deposit_amount):
    """Credit referrer when referral makes a deposit (3% of deposit amount)"""
    conn = get_db()
    c = conn.cursor()

    earnings = round(deposit_amount * 0.03, 2)

    # Update referral record
    c.execute('INSERT INTO referrals (referrer_id, referral_id, earnings) VALUES (?, ?, ?)',
              (referrer_id, referral_id, earnings))

    # Credit referrer balance
    c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (earnings, referrer_id))

    conn.commit()
    conn.close()
    return earnings

def generate_referral_code(user_id):
    import base64
    return base64.urlsafe_b64encode(str(user_id).encode()).decode()[:12]

def create_deposit(user_id, amount):
    """Create pending deposit with mock wallet address"""
    conn = get_db()
    c = conn.cursor()

    # Mock wallet address - in production, integrate with payment provider
    deposit_address = f"TN3W4H6rK2z4ZuXvWXq3a3m8hN5kL9mQx-{user_id}-{int(time.time())}"
    deposit_id = secrets.token_hex(8)

    c.execute('''INSERT INTO deposits (user_id, amount, address, status)
                 VALUES (?, ?, ?, 'pending')''',
              (user_id, amount, deposit_address))

    conn.commit()
    conn.close()

    return {
        'deposit_id': deposit_id,
        'address': deposit_address,
        'amount': amount
    }

def confirm_deposit(user_id, deposit_id, tx_hash):
    """Confirm deposit after blockchain verification"""
    conn = get_db()
    c = conn.cursor()

    # For demo: just mark as confirmed and credit immediately
    # In production: verify tx_hash on blockchain first
    c.execute('''UPDATE deposits SET status = 'confirmed', tx_hash = ? WHERE user_id = ? AND address LIKE ?''',
              (tx_hash, user_id, f'%{deposit_id}%'))

    c.execute('SELECT * FROM deposits WHERE user_id = ? AND tx_hash = ?', (user_id, tx_hash))
    deposit = c.fetchone()

    if deposit:
        amount = deposit['amount']
        update_balance(user_id, amount, f'Deposit: {amount}$')

        # Credit referrer if exists
        user = get_user(user_id)
        if user and user.get('referred_by'):
            credit_referral_earnings(user['referred_by'], user_id, amount)

    conn.commit()
    conn.close()

    return {'success': True}

def get_deposits(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM deposits WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return [dict(row) for row in c.fetchall()]

# MINERS - 2 week payback
MINERS = [
    {'id': 1, 'name': 'Pico Miner', 'price': 5, 'income_per_hour': 0.015, 'icon': '🔌'},
    {'id': 2, 'name': 'Nano Miner', 'price': 15, 'income_per_hour': 0.045, 'icon': '📱'},
    {'id': 3, 'name': 'Micro Rig', 'price': 50, 'income_per_hour': 0.15, 'icon': '💻'},
    {'id': 4, 'name': 'Mini Farm', 'price': 100, 'income_per_hour': 0.30, 'icon': '🖥️'},
    {'id': 5, 'name': 'Office Rig', 'price': 250, 'income_per_hour': 0.75, 'icon': '🖥️'},
    {'id': 6, 'name': 'Garage Farm', 'price': 500, 'income_per_hour': 1.50, 'icon': '🏭'},
    {'id': 7, 'name': 'Industrial', 'price': 750, 'income_per_hour': 2.25, 'icon': '🏢'},
    {'id': 8, 'name': 'Mega Cluster', 'price': 1000, 'income_per_hour': 3.00, 'icon': '🌐'},
    {'id': 9, 'name': 'Quantum Core', 'price': 2000, 'income_per_hour': 6.00, 'icon': '⚛️'},
    {'id': 10, 'name': 'Hyper Reactor', 'price': 5000, 'income_per_hour': 15.00, 'icon': '⚡'},
]

def get_upgrade_cost(miner_id, current_level):
    """Upgrade cost = base_income * 168 * (level + 1)"""
    miner = next((m for m in MINERS if m['id'] == miner_id), None)
    if not miner:
        return 0
    return round(miner['income_per_hour'] * 168 * (current_level + 1), 2)

def get_upgraded_income(miner_id, upgrade_level):
    """Income with upgrade level: +10% per level"""
    miner = next((m for m in MINERS if m['id'] == miner_id), None)
    if not miner:
        return 0
    return round(miner['income_per_hour'] * (1 + upgrade_level * 0.1), 3)
