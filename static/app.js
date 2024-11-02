$(document).ready(function() {
    let cart = [];
    let totalPrice = 0;
    let currentUser = null;
    let currentUserNfcId = null; // Globale Variable für die aktuelle NFC-ID

    // Funktion, um die Benutzer vom Backend abzurufen
    function fetchUsers() {
        fetch('/users') // Angenommener Endpoint zum Abrufen der Benutzer
            .then(response => response.json())
            .then(data => {
                // Dynamisch Benutzer-Buttons erstellen
                const userSelection = $('#user-selection');
                userSelection.empty(); // Leere die bestehende Auswahl
                data.forEach(user => {
                    userSelection.append(`
                        <button class="user-btn" data-nfc-id="${user.nfc_id}">
                            ${user.name}
                        </button>
                    `);
                });
            })
            .catch(error => {
                console.error('Fehler beim Abrufen der Benutzer:', error);
            });
    }

    // Funktion, um die NFC-ID vom Backend abzurufen
    function fetchActiveNfc() {
        fetch('/active_nfc')
            .then(response => response.json())
            .then(data => {
                if (data.current_user) {
                    // Überprüfe, ob sich die NFC-ID geändert hat
                    if (data.current_user !== currentUserNfcId) {
                        // Neue NFC-ID erkannt
                        currentUserNfcId = data.current_user; // Setze die neue NFC-ID
                        handleNfcTagRead(currentUserNfcId); // Aktiviere den Benutzer
                    } else {
                        // NFC-ID hat sich nicht geändert, nur die Buttons aktivieren
                        enableCashRegisterButtons(); // Buttons aktivieren
                    }
                } else {
                    // Wenn keine NFC-ID erkannt wurde
                    console.log("Keine NFC-ID erkannt.");
                    disableCashRegisterButtons(); // Deaktiviere alle Kassen-Buttons
                }
            })
            .catch(error => {
                console.error('Fehler beim Abrufen der aktiven NFC:', error);
            });
    }

    // Funktion, die aufgerufen wird, wenn ein NFC-Tag gelesen wird
    function handleNfcTagRead(nfcId) {
        // Deaktiviere alle Benutzer-Buttons
        $(".user-btn").removeClass("active");

        // Aktiviere den entsprechenden Benutzer-Button basierend auf der NFC-ID
        const button = $(`.user-btn[data-nfc-id="${nfcId}"]`);
        if (button.length) {
            button.addClass("active"); // Aktiviere den Button für den aktuellen Benutzer
            currentUser = button.data("user"); // Setze den aktuellen Benutzer basierend auf dem Button
            enableCashRegisterButtons(); // Aktiviere die Kassen-Buttons
            resetCart(); // Setze den Warenkorb zurück
        } else {
            // Wenn der Benutzer nicht existiert, setze die Transaktion zurück
            console.log("Unbekannter Benutzer. Transaktion zurücksetzen.");
            resetCart(); // Setze die Transaktion zurück
        }
    }

    // Funktion, um alle Benutzer zu deaktivieren
    function disableAllUsers() {
        $(".user-btn").removeClass("active"); // Alle Benutzerbuttons deaktivieren
        disableCashRegisterButtons(); // Kassen-Buttons deaktivieren
    }

    // Initialisiere die Anwendung
    function initializeApp() {
        disableCashRegisterButtons(); // Deaktiviere alle Kassen-Buttons beim Start
        fetchUsers(); // (Optional) Benutzer beim Start abrufen
    }

    // Benutzer-Auswahl
    $(document).on('click', '.user-btn', function() {
        $(".user-btn").removeClass("active");
        $(this).addClass("active");
        currentUser = $(this).data("user");

        enableCashRegisterButtons();
        resetCart();
    });

    // Logout-Button
    $("#logoutBtn").click(function() {
        $(".user-btn").removeClass("active");
        currentUser = null;
        disableCashRegisterButtons();
        resetCart();
    });

    // Produkt hinzufügen
    $(".product-btn").click(function() {
        if (!currentUser) return;

        let itemName = $(this).data("name");
        let itemPrice = parseFloat($(this).data("price")).toFixed(2);

        cart.unshift({ name: itemName, price: itemPrice });
        totalPrice += parseFloat(itemPrice);
        updateCart();
    });

    // Geldschein-Button hinzufügen
    $(".note-btn").click(function() {
        if (!currentUser) return;

        let amount = parseFloat($(this).data("amount"));
        let currentAmount = parseFloat($("#given_amount").val()) || 0;
        $("#given_amount").val((currentAmount + amount).toFixed(2));
    });

    // Checkout
    $("#checkoutBtn").click(function() {
        if (!currentUser) return;

        let givenAmount = parseFloat($("#given_amount").val());

        // Überprüfen, ob ein negativer Gesamtbetrag vorliegt
        if (totalPrice < 0) {
            // Bei negativem Gesamtbetrag wird kein Rückgeld benötigt
            performCheckout(givenAmount, totalPrice);
        } else {
            // Normaler Checkout mit Rückgeldprüfung
            if (isNaN(givenAmount) || givenAmount < totalPrice) {
                alert("Bitte geben Sie einen gültigen Betrag ein.");
                return;
            }
            performCheckout(givenAmount, totalPrice - givenAmount);
        }
    });

    // Funktion für den Checkout-Prozess
    function performCheckout(givenAmount, change) {
        $.ajax({
            url: "/checkout",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ total_price: totalPrice, items: cart, given_amount: givenAmount, user: currentUser }),
            success: function(response) {
                showPopup(change.toFixed(2));
                resetCart();
            },
            error: function(response) {
                alert(response.responseJSON.error);
            }
        });
    }

    // Reset
    $("#resetBtn").click(resetCart);

    // Letzter Artikel löschen
    $("#removeLastBtn").click(function() {
        if (cart.length > 0 && currentUser) {
            let lastItem = cart.shift();
            totalPrice -= parseFloat(lastItem.price);
            updateCart();
        }
    });

    // Rückgeldbetrag zurücksetzen
    $("#clearAmountBtn").click(function() {
        $("#given_amount").val("0.00");
    });

    // Warenkorb aktualisieren
    function updateCart() {
        let cartHtml = cart.map(item => `${item.name} | ${parseFloat(item.price).toFixed(2)} €`).join("<br>");
        $("#cart-items").html(cartHtml);
        $("#total_price").text(totalPrice.toFixed(2));
    }

    // Warenkorb zurücksetzen
    function resetCart() {
        cart = [];
        totalPrice = 0;
        updateCart();
        $("#given_amount").val("");
    }

    // Popup anzeigen
    function showPopup(change) {
        $("#change-amount").text(change);
        $("#change-popup").fadeIn();
    }

    // Popup schließen
    $("#close-popup").click(function() {
        $("#change-popup").fadeOut();
    });

    // Kassen-Buttons aktivieren
    function enableCashRegisterButtons() {
        $(".product-btn, .note-btn, #checkoutBtn, .remove-last-btn, #resetBtn").prop("disabled", false).css("opacity", 1);
    }

    // Kassen-Buttons deaktivieren
    function disableCashRegisterButtons() {
        $(".product-btn, .note-btn, #checkoutBtn, .remove-last-btn, #resetBtn").prop("disabled", true).css("opacity", 0.5);
    }

    // Starte die Abfrage der aktiven NFC-ID alle 2 Sekunden
    setInterval(fetchActiveNfc, 2000);

    // Initialisiere die Anwendung
    initializeApp(); // Setze beim Laden der Seite die Anwendung in den Ausgangszustand
});
