from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime
import serial
import sqlite3
import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import threading

app = Flask(__name__)
socketio = SocketIO(app)

# Initialisiere das serielle Interface beim Start der App
try:
    ser = serial.Serial('/dev/ttyUSB2', 38400, timeout=1, dsrdtr=True)
    print("Serielles Interface erfolgreich geöffnet.")
except serial.SerialException as e:
    ser = None
    print(f"Fehler beim Öffnen des seriellen Interfaces: {e}")

# Initialisiere den NFC-Reader
reader = SimpleMFRC522()

# Variable, um den aktiven Benutzer zu verfolgen
current_user = None

def init_db():
    conn = sqlite3.connect('cash_register.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkouts (
            checkout_id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkout_datetime TEXT,
            user TEXT
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

# === Konfigurationsbereich für Produkte ===
products = [
    {"name": "Produkt 1", "price": 2.50, "bondruck": True},
    {"name": "Produkt 2", "price": 3.00, "bondruck": True},
    {"name": "Produkt 3", "price": 4.00, "bondruck": True},
    {"name": "Produkt 4", "price": 5.50, "bondruck": True},
    {"name": "Produkt 5", "price": 6.00, "bondruck": True},
    {"name": "Produkt 6", "price": 7.50, "bondruck": True},
    {"name": "Produkt 7", "price": 8.00, "bondruck": True},
    {"name": "Produkt 8", "price": 9.50, "bondruck": True},
    {"name": "Produkt 9", "price": 10.00, "bondruck": True},
    {"name": "Produkt 10", "price": 11.50, "bondruck": True},
    {"name": "Produkt 11", "price": 12.00, "bondruck": True},
    {"name": "Produkt 12", "price": 13.50, "bondruck": True},
    {"name": "Produkt 13", "price": 14.00, "bondruck": True},
    {"name": "Produkt 14", "price": 15.50, "bondruck": True},
    {"name": "Pfand Tasse zurück", "price": -2.50, "bondruck": False},
    {"name": "Pfand Geschirr zurück", "price": -4.50, "bondruck": False}
]
# === Ende des Konfigurationsbereichs ===

club_name = "Oldtimerfreunde Forst e.V."

users = [
    {"name": "Admin", "nfc_id": "27460418333"},
    {"name": "Bedienung1", "nfc_id": "nfc_bedienung1_id"},
    {"name": "Bedienung2", "nfc_id": "nfc_bedienung2_id"},
    {"name": "Bedienung3", "nfc_id": "nfc_bedienung3_id"},
    {"name": "Bedienung4", "nfc_id": "nfc_bedienung4_id"},
]

@app.route('/')
def index():
    return render_template('index.html', products=products, users=users, current_user=current_user)

# Funktion zum Ausführen des Bondrucks auf der seriellen Konsole
def print_receipt(club_name, product_name, price):
    if ser is not None and ser.is_open:
        try:
            ser.write(b'\x1B\x61\x01')  # ESC a 1 (zentrierte Ausrichtung)
            ser.write(f"{club_name}\n".encode('ascii'))
            ser.write(b'\x1B\x61\x00')  # ESC a 0 (linksbündige Ausrichtung)
            ser.write(b'\n')
            ser.write(b'\x1D\x21\x11')  # GS ! 17 (doppelte Höhe und Breite)
            ser.write(f" {product_name}\n".encode('ascii'))
            ser.write(b'\x1D\x21\x00')  # GS ! 0 (Standardgröße)
            ser.write(f"{price:>9.2f} EUR\n".encode('ascii'))
            ser.write(b'\n')
            ser.write(b'\x1B\x61\x01')  # ESC a 1 (zentrierte Ausrichtung)
            ser.write("Vielen Dank!\n".encode('ascii'))
            ser.write(b'\n' * 4)
            ser.write(b'\x1B\x61\x00')  # ESC a 0 (linksbündige Ausrichtung)
            ser.write(b'\x1Bm')  # ESC m
            print(f"Bondruck gesendet:\n{club_name}\n{product_name}\n{price:>9.2f} EUR\nVielen Dank!")
        except serial.SerialException as e:
            print(f"Fehler beim Bondruck: {e}")
    else:
        print("Serielles Interface ist nicht geöffnet. Kein Bondruck möglich.")

# Funktion zum Auslesen der NFC-ID
def read_nfc():
    global current_user
    while True:
        try:
            time.sleep(0.5)
            #print("Warte auf NFC-Tag...")
            id, text = reader.read_no_block()  # NFC-Tag wird hier gelesen
            if id:
                print(f"NFC-Tag erkannt: {id}")
                # Vergleiche die NFC-ID mit der Benutzerliste
                user_found = next((user for user in users if user["nfc_id"] == str(id)), None)
                if user_found:
                    current_user = user_found["nfc_id"]  # Setze den aktuellen Benutzer auf den gefundenen Namen
                    print(f"{current_user} aktiviert.")
                else:
                    print("Unbekannter Benutzer.")
                    current_user = None
            else:
                print("Kein Tag")
                current_user = None
            socketio.emit('user_changed', {'current_user': current_user})
        except Exception as e:
            print(f"Fehler beim Lesen des NFC-Tags: {e}")

# Starte den NFC-Lesethread
nfc_thread = threading.Thread(target=read_nfc, daemon=True)
nfc_thread.start()

@app.route('/users', methods=['GET'])
def get_users():
    return jsonify(users)


@app.route('/current_user', methods=['GET'])
def get_current_user():
    return jsonify({"current_user": current_user})

@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    total_price = data.get('total_price')
    items = data.get('items')
    given_amount = data.get('given_amount', 0)
    user = data.get('user')

    print("Warenkorb:")
    for item in items:
        print(f"Produkt: {item['name']} | Preis: {float(item['price']):.2f} €")

        # Bondruck für das Produkt ausführen, falls bondruck auf True gesetzt ist
        product = next((p for p in products if p["name"] == item["name"]), None)
        if product and product["bondruck"]:
            print_receipt(club_name, product["name"], product["price"])

    if total_price < 0:
        change = total_price
    else:
        change = given_amount - total_price
        if change < 0:
            return jsonify({"error": "Erhaltener Betrag ist zu gering."}), 400

    conn = sqlite3.connect('cash_register.db')
    cursor = conn.cursor()
    checkout_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO checkouts (checkout_datetime, user) VALUES (?, ?)', (checkout_datetime, user))
    checkout_id = cursor.lastrowid

    for item in items:
        cursor.execute('INSERT INTO purchased_items (checkout_id, item_name, item_price) VALUES (?, ?, ?)',
                       (checkout_id, item['name'], item['price']))
    conn.commit()
    conn.close()

    return jsonify({"change": change, "total_price": total_price, "items": items, "given_amount": given_amount})

if __name__ == "__main__":
    socketio.run(host='0.0.0.0', port=5000)
