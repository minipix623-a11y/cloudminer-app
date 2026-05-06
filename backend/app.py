import os
import requests
import time
import secrets
from dotenv import load_dotenv
from flask import Flask, request, jsonify
load_dotenv()
from models import (
    init_db, create_user, get_user, update_balance, buy_miner,
    get_user_miners_full, get_rating, get_referral_stats, MINERS,
    generate_referral_code, upgrade_miner, get_upgrade_cost, get_upgraded_income,
    create_deposit, confirm_deposit, get_deposits
)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET', 'dev-key-change-me')

init_db()

# NOWPayments credentials
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY', '')
DEPOSIT_WALLET = os.getenv('DEPOSIT_WALLET', '')
IPN_SECRET = os.getenv('NOWPAYMENTS_IPN_SECRET', '')

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'app': 'CloudMiner API'})

@app.route('/api/miners')
def miners():
    return jsonify(MINERS)

@app.route('/api/user/<int:user_id>')
def user(user_id):
    user_data = get_user(user_id)
    if not user_data:
        return jsonify({'error': 'User not found'}), 404

    user_miners = get_user_miners_full(user_id)
    miners_with_income = []
    total_income = 0

    for um in user_miners:
        miner = next((m for m in MINERS if m['id'] == um['miner_id']), None)
        if miner:
            level = um.get('upgrade_level', 0)
            income = get_upgraded_income(um['miner_id'], level)
            total = income * um['quantity']
            total_income += total
            miners_with_income.append({
                **miner,
                'quantity': um['quantity'],
                'upgrade_level': level,
                'income_per_hour': income,
                'total_income': total,
                'upgrade_cost': get_upgrade_cost(um['miner_id'], level)
            })

    return jsonify({
        **user_data,
        'miners': miners_with_income,
        'income_per_hour': round(total_income, 3)
    })

@app.route('/api/user', methods=['POST'])
def upsert_user():
    data = request.json
    user_id = data.get('user_id')
    username = data.get('username', '')
    first_name = data.get('first_name', '')
    referral_code = data.get('referral_code')
    referred_by = data.get('referred_by')

    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    existing = get_user(user_id)
    if not existing:
        code = generate_referral_code(user_id)
        create_user(user_id, username, first_name, code, referred_by)

        # Credit referrer bonus on signup
        if referred_by:
            referrer = get_user(referred_by)
            if referrer:
                update_balance(referred_by, 1.0, f'Referral bonus: {first_name} joined')

    return jsonify(get_user(user_id))

@app.route('/api/buy', methods=['POST'])
def buy():
    data = request.json
    user_id = data.get('user_id')
    miner_id = data.get('miner_id')
    quantity = data.get('quantity', 1)

    miner = next((m for m in MINERS if m['id'] == miner_id), None)
    if not miner:
        return jsonify({'error': 'Invalid miner'}), 400

    cost = miner['price'] * quantity
    user = get_user(user_id)

    if user.get('balance', 0) < cost:
        return jsonify({'error': 'Insufficient balance'}), 400

    update_balance(user_id, -cost, f'Purchase: {miner["name"]} x{quantity}')
    buy_miner(user_id, miner_id, quantity)

    updated_user = get_user(user_id)
    return jsonify({
        'success': True,
        'balance': updated_user.get('balance', 0),
        'miner': miner
    })

@app.route('/api/upgrade', methods=['POST'])
def upgrade():
    data = request.json
    user_id = data.get('user_id')
    miner_id = data.get('miner_id')

    user_miners = get_user_miners_full(user_id)
    user_miner = next((um for um in user_miners if um['miner_id'] == miner_id), None)

    if not user_miner:
        return jsonify({'error': 'You don\'t own this miner'}), 400

    current_level = user_miner.get('upgrade_level', 0)
    cost = get_upgrade_cost(miner_id, current_level)
    user = get_user(user_id)

    if user.get('balance', 0) < cost:
        return jsonify({'error': 'Insufficient balance'}), 400

    update_balance(user_id, -cost, f'Upgrade miner {miner_id}')
    new_level = upgrade_miner(user_id, miner_id)

    return jsonify({
        'success': True,
        'new_level': new_level,
        'balance': user.get('balance', 0) - cost
    })

@app.route('/api/income/<int:user_id>')
def income(user_id):
    user_miners = get_user_miners_full(user_id)
    total_income = 0

    for um in user_miners:
        miner = next((m for m in MINERS if m['id'] == um['miner_id']), None)
        if miner:
            level = um.get('upgrade_level', 0)
            income = get_upgraded_income(um['miner_id'], level)
            total_income += income * um['quantity']

    return jsonify({'income_per_hour': round(total_income, 3)})

@app.route('/api/rating')
def rating():
    return jsonify(get_rating())

@app.route('/api/referrals/<int:user_id>')
def referrals(user_id):
    stats = get_referral_stats(user_id)
    return jsonify(stats)

# ============ DEPOSIT SYSTEM ============

@app.route('/api/deposit/create', methods=['POST'])
def deposit_create():
    """Create a deposit invoice via NOWPayments"""
    data = request.json
    user_id = data.get('user_id')
    amount = float(data.get('amount', 10))

    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    if amount < 1:
        return jsonify({'error': 'Minimum deposit is 1$'}), 400

    if not NOWPAYMENTS_API_KEY or not DEPOSIT_WALLET:
        # Fallback to demo mode
        deposit = create_deposit(user_id, amount)
        return jsonify({
            'success': True,
            'deposit_id': deposit['deposit_id'],
            'address': DEPOSIT_WALLET or 'DEMO_WALLET',
            'amount': amount,
            'network': 'TRC20',
            'memo': deposit['deposit_id'],
            'message': f'Send exactly {amount}$ USDT (TRC20) to address above.'
        })

    try:
        # Create invoice via NOWPayments
        invoice_data = {
            'price_amount': amount,
            'price_currency': 'USD',
            'pay_currency': 'USDT',
            'ipn_callback_url': f'http://31.129.99.202/api/deposit/callback',
            'order_id': f'{user_id}_{secrets.token_hex(8)}',
            'success_url': 'https://cloudminer-app.vercel.app/?deposit=success',
            'cancel_url': 'https://cloudminer-app.vercel.app/?deposit=cancel'
        }

        resp = requests.post(
            'https://api.nowpayments.io/v1/invoice',
            json=invoice_data,
            headers={
                'x-api-key': NOWPAYMENTS_API_KEY,
                'Content-Type': 'application/json'
            },
            timeout=10
        )

        if resp.status_code == 200:
            result = resp.json()
            deposit = create_deposit(user_id, amount)
            return jsonify({
                'success': True,
                'deposit_id': deposit['deposit_id'],
                'invoice_url': result.get('invoice_url'),
                'address': DEPOSIT_WALLET,
                'amount': amount,
                'network': 'TRC20',
                'memo': deposit['deposit_id'],
                'message': f'Click the link to pay {amount}$ USDT'
            })
        else:
            # Fallback to manual address
            deposit = create_deposit(user_id, amount)
            return jsonify({
                'success': True,
                'deposit_id': deposit['deposit_id'],
                'address': DEPOSIT_WALLET,
                'amount': amount,
                'network': 'TRC20',
                'memo': deposit['deposit_id'],
                'message': f'Send exactly {amount}$ USDT (TRC20) to address above.'
            })
    except Exception as e:
        deposit = create_deposit(user_id, amount)
        return jsonify({
            'success': True,
            'deposit_id': deposit['deposit_id'],
            'address': DEPOSIT_WALLET,
            'amount': amount,
            'network': 'TRC20',
            'memo': deposit['deposit_id'],
            'message': f'Send exactly {amount}$ USDT (TRC20) to address above.'
        })

@app.route('/api/deposit/confirm', methods=['POST'])
def deposit_confirm():
    """Confirm deposit after user sends USDT - demo version auto-confirms"""
    data = request.json
    user_id = data.get('user_id')
    deposit_id = data.get('deposit_id')
    tx_hash = data.get('tx_hash', 'demo_' + deposit_id)

    if not user_id or not deposit_id:
        return jsonify({'error': 'user_id and deposit_id required'}), 400

    # In production: verify tx_hash on blockchain first
    result = confirm_deposit(user_id, deposit_id, tx_hash)

    return jsonify(result)

@app.route('/api/deposits/<int:user_id>')
def deposits(user_id):
    """Get user's deposit history"""
    return jsonify(get_deposits(user_id))

@app.route('/api/deposit/callback', methods=['POST'])
def deposit_callback():
    """NOWPayments IPN callback - called when payment is confirmed"""
    try:
        data = request.json
        print(f"NOWPayments callback: {data}")

        payment_status = data.get('payment_status')
        pay_amount = float(data.get('pay_amount', 0))
        pay_currency = data.get('pay_currency', '')
        order_id = data.get('order_id', '')

        # Parse user_id from order_id (format: userid_tokenhex)
        parts = order_id.split('_')
        if len(parts) >= 2:
            try:
                user_id = int(parts[0])
            except:
                return jsonify({'status': 'error'}), 400
        else:
            return jsonify({'status': 'error'}), 400

        if payment_status == 'finished' or payment_status == 'confirmed':
            # Credit user balance
            user = get_user(user_id)
            if user:
                update_balance(user_id, pay_amount, f'Deposit: {pay_amount} {pay_currency}')

                # Credit referrer if exists
                if user.get('referred_by'):
                    credit_referral_earnings(user['referred_by'], user_id, pay_amount)

        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Callback error: {e}")
        return jsonify({'status': 'error'}), 500

def credit_referral_earnings(referrer_id, referral_id, deposit_amount):
    """Credit referrer with 3% of deposit"""
    earnings = round(deposit_amount * 0.03, 2)
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO referrals (referrer_id, referral_id, earnings) VALUES (?, ?, ?)',
              (referrer_id, referral_id, earnings))
    c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (earnings, referrer_id))
    conn.commit()
    conn.close()
    return earnings

def get_db():
    from models import get_db
    return get_db()

# ============ ADMIN ============

@app.route('/api/admin/stats')
def admin_stats():
    from models import get_db

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]

    c.execute('SELECT SUM(balance) FROM users')
    total_balance = c.fetchone()[0] or 0

    c.execute('SELECT SUM(total_earned) FROM users')
    total_earned = c.fetchone()[0] or 0

    c.execute('SELECT SUM(amount) FROM deposits WHERE status = "confirmed"')
    total_deposits = c.fetchone()[0] or 0

    conn.close()

    return jsonify({
        'total_users': total_users,
        'total_balance': round(total_balance, 2),
        'total_earned': round(total_earned, 2),
        'total_deposits': round(total_deposits, 2)
    })

@app.route('/api/admin/users')
def admin_users():
    from models import get_db

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id, username, first_name, balance, total_earned, created_at FROM users ORDER BY balance DESC LIMIT 100')
    users = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(users)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
