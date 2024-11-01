from flask import Flask, render_template, request, jsonify
from datetime import datetime
import serial
import sqlite3

app = Flask(__name__)

# Initialisiere das serielle Interface beim Start der App
try:
    ser = serial.Serial('/dev/ttyUSB2', 38400, timeout=1, dsrdtr=True)
    print("Serielles Interface erfolgreich geöffnet.")
except serial.SerialException as e:
    ser = None
    print(f"Fehler beim Öffnen des seriellen Interfaces: {e}")


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

users = ["Admin", "Bedienung1", "Bedienung2", "Bedienung3", "Bedienung4"]


@app.route('/')
def index():
    return render_template('index.html', products=products, users=users)


# Funktion zum Ausführen des Bondrucks auf der seriellen Konsole
def print_receipt(club_name, product_name, price):
    if ser is not None and ser.is_open:
        try:
            # Abstand einfügen
            ser.write(b'\n')

            # Vereinsname zentriert drucken
            ser.write(b'\x1B\x61\x01')  # ESC a 1 (zentrierte Ausrichtung)
            ser.write(f"{club_name}\n".encode('ascii'))

            # Ausrichtung auf linksbündig zurücksetzen
            ser.write(b'\x1B\x61\x00')  # ESC a 0 (linksbündige Ausrichtung)

            # Abstand einfügen
            ser.write(b'\n')

            # Produktname in doppelter Schriftgröße und zentriert drucken
            ser.write(b'\x1D\x21\x11')  # GS ! 17 (doppelte Höhe und Breite)
            ser.write(f"{product_name}\n".encode('ascii'))
            ser.write(b'\x1D\x21\x00')  # GS ! 0 (Standardgröße)

            # Preis rechtsbündig drucken
            ser.write(f"{price:>9.2f} EUR\n".encode('ascii'))

            # Abstand einfügen
            ser.write(b'\n')

            # "Vielen Dank!" zentriert drucken
            ser.write(b'\x1B\x61\x01')  # ESC a 1 (zentrierte Ausrichtung)
            ser.write("Vielen Dank!\n".encode('ascii'))

            # Ausrichtung auf linksbündig zurücksetzen
            ser.write(b'\x1B\x61\x00')  # ESC a 0 (linksbündige Ausrichtung)

            # ESC/POS-Befehl zum Abschneiden des Bons
            ser.write(b'\x1Bm')  # ESC m

            print(f"Bondruck gesendet:\n{club_name}\n{product_name}\n{price:>9.2f} EUR\nVielen Dank!")
        except serial.SerialException as e:
            print(f"Fehler beim Bondruck: {e}")
    else:
        print("Serielles Interface ist nicht geöffnet. Kein Bondruck möglich.")


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

    # Berechne das Rückgeld abhängig vom Gesamtbetrag
    if total_price < 0:
        change = total_price  # Negativer Gesamtbetrag wird als Rückgeld angezeigt
    else:
        change = given_amount - total_price
        if change < 0:
            return jsonify({"error": "Erhaltener Betrag ist zu gering."}), 400

    # Checkout in der Datenbank speichern
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
