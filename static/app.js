$(document).ready(function() {
    let cart = [];
    let totalPrice = 0;
    let currentUser = null;

    // Benutzer-Auswahl
    $(".user-btn").click(function() {
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

    // Initial deaktivierte Kassen-Buttons
    disableCashRegisterButtons();
});
