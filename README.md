# Cash Register Web App für Raspberry Pi

Dies ist eine einfache Web-App für ein Kassensystem, das auf einem Raspberry Pi betrieben wird und über Nginx und Flask bereitgestellt wird. Das System speichert Checkout-Daten in einer SQLite-Datenbank und kann über ein mobiles Gerät als Website bedient werden.

## Voraussetzungen
- **Raspberry Pi** mit Raspberry Pi OS
- **Nginx** als Webserver
- **Flask** für die Webanwendung
- **SQLite** für die Datenbank

## Hardware
- **Raspberry Pi**: Ein Raspberry Pi 3 oder neuer mit Raspberry Pi OS.
- **Netzwerkzugang**: Der Raspberry Pi sollte über das Netzwerk zugänglich sein.

## Installation

### 1. Repository klonen
Klonen Sie das Repository auf Ihren Raspberry Pi:
```bash
git clone https://github.com/username/cash_register_web.git
cd cash_register_web

