from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import sqlite3

app = Flask(__name__)

# Datenbank initialisieren
def init_db():
    conn = sqlite3.connect('cash_register.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkouts (
            checkout_id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkout_datetime TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchased_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkout_id INTEGER,
            item_name TEXT,
            item_price REAL,
            FOREIGN KEY (checkout_id) REFERENCES checkouts(checkout_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Startseite mit HTML-UI laden
@app.route('/')
def index():
    return render_template('index.html')

# API für Checkout-Transaktion
@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    total_price = data.get('total_price')
    items = data.get('items')
    given_amount = data.get('given_amount')

    # Rückgeld berechnen
    change = given_amount - total_price
    if change < 0:
        return jsonify({"error": "Erhaltener Betrag ist zu gering."}), 400

    # Datenbank speichern
    conn = sqlite3.connect('cash_register.db')
    cursor = conn.cursor()
    checkout_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO checkouts (checkout_datetime) VALUES (?)', (checkout_datetime,))
    checkout_id = cursor.lastrowid

    for item in items:
        cursor.execute('INSERT INTO purchased_items (checkout_id, item_name, item_price) VALUES (?, ?, ?)',
                       (checkout_id, item['name'], item['price']))
    conn.commit()
    conn.close()

    return jsonify({"change": change, "total_price": total_price, "items": items, "given_amount": given_amount})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

