from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime
import serial
import sqlite3
import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import threading
import json
GPIO.setwarnings(False)

app = Flask(__name__)

# Konfiguration laden
with open('config.json') as config_file:
    config = json.load(config_file)

# Zugriff auf die Konfiguration
club_name = config["club_name"]
products = config["products"]
users = config["users"]

# Initialisiere das serielle Interface beim Start der App
try:
    ser = serial.Serial('/dev/ttyUSB0', 38400, timeout=1, dsrdtr=True)
    print("Serielles Interface erfolgreich geöffnet.")
except serial.SerialException as e:
    ser = None
    print(f"Fehler beim Öffnen des seriellen Interfaces: {e}")

# Initialisiere den NFC-Reader
reader = SimpleMFRC522()

current_user = None
active_nfc_id = None
timer = None


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


@app.route('/')
def index():
    return render_template('index.html', products=products, users=users, current_user=current_user)

# Funktion zum Ausführen des Bondrucks auf der seriellen Konsole
def print_receipt(club_name, product_name, price):
    if ser is not None and ser.is_open:
        try:
            ser.write(b'\x1B\x45\x01')  # ESC E 1 (Fettdruck aktivieren)
            ser.write(b'\x1B\x61\x01')  # ESC a 1 (zentrierte Ausrichtung)
            ser.write(f"{club_name}\n".encode('ascii'))
            ser.write(b'\x1B\x45\x00')  # ESC E 0 (Fettdruck deaktivieren)
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


def read_nfc():
    global active_nfc_id, timer
    while True:
        try:
            #print("Warte auf NFC-Tag...")  # Informiere, dass auf ein Tag gewartet wird

            start_time = time.time()  # Starte den Timer
            id, text = reader.read()  # Blockiert, bis ein Tag gelesen wird

            #print(f"NFC-Tag erkannt: {id}")
            if id:
                # Setze die aktive NFC-ID
                active_nfc_id = str(id)
                #print(f"Aktive NFC-ID gesetzt: {active_nfc_id}")

                # Benutzersuche basierend auf der NFC-ID
                user_found = next((user for user in users if user["nfc_id"] == active_nfc_id), None)
                if user_found:
                    global current_user
                    current_user = user_found["name"]  # Setze den aktuellen Benutzer auf den gefundenen Namen
                    #print(f"{current_user} aktiviert.")
                else:
                    #print("Unbekannter Benutzer.")
                    current_user = None

                # Timer zurücksetzen, wenn eine ID gelesen wird
                if timer:
                    timer.cancel()
                timer = threading.Timer(2.0, reset_active_nfc_id)  # Setze den Timer auf 2 Sekunden
                timer.start()  # Starte den Timer

            else:
                print("Kein Tag erkannt.")

        except Exception as e:
            GPIO.cleanup()
            print(f"Fehler beim Lesen des NFC-Tags: {e}")


def reset_active_nfc_id():
    global active_nfc_id
    active_nfc_id = None
    #print("Aktive NFC-ID wurde auf None gesetzt.")


# Starte den NFC-Lesethread
nfc_thread = threading.Thread(target=read_nfc, daemon=True)
nfc_thread.start()


@app.route('/active_nfc', methods=['GET'])
def get_active_nfc():
    return jsonify({"current_user": active_nfc_id})


@app.route('/users', methods=['GET'])
def get_users():
    return jsonify(users)


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
    app.run(host='0.0.0.0', port=5000)
