$(document).ready(function() {
    let cart = [];
    let totalPrice = 0;

    // Produkt hinzufügen
    $(".product-btn").click(function() {
        let itemName = $(this).data("name");
        let itemPrice = parseFloat($(this).data("price")).toFixed(2);

        cart.unshift({ name: itemName, price: itemPrice });
        totalPrice += parseFloat(itemPrice);
        updateCart();
    });

    // Geldschein-Button hinzufügen
    $(".note-btn").click(function() {
        let amount = parseFloat($(this).data("amount"));
        let currentAmount = parseFloat($("#given_amount").val()) || 0;
        $("#given_amount").val((currentAmount + amount).toFixed(2));
    });

    // Checkout
    $("#checkoutBtn").click(function() {
        let givenAmount = parseFloat($("#given_amount").val());

        if (isNaN(givenAmount) || givenAmount < totalPrice) {
            alert("Bitte geben Sie einen gültigen Betrag ein.");
            return;
        }

        // Daten an den Server senden und Rückgeld anzeigen
        $.ajax({
            url: "/checkout",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ total_price: totalPrice, items: cart, given_amount: givenAmount }),
            success: function(response) {
                showPopup(response.change.toFixed(2));
                resetCart();
            },
            error: function(response) {
                alert(response.responseJSON.error);
            }
        });
    });

    // Reset
    $("#resetBtn").click(function() {
        resetCart();
    });

    // Letzter Artikel löschen
    $("#removeLastBtn").click(function() {
        if (cart.length > 0) {
            let lastItem = cart.shift();
            totalPrice -= parseFloat(lastItem.price);
            updateCart();
        }
    });

    // Warenkorb aktualisieren
    function updateCart() {
        let cartHtml = cart.map(item => `${item.name} - ${parseFloat(item.price).toFixed(2)} €`).join("<br>");
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
});
