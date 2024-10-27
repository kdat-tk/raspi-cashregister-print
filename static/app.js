$(document).ready(function() {
    $("#checkoutBtn").click(function() {
        let total_price = parseFloat($("#total_price").text());
        let given_amount = parseFloat(prompt("Geben Sie den erhaltenen Betrag ein:"));
        let items = [];  // Hier wird eine Items-Liste übergeben

        $.ajax({
            url: "/checkout",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ total_price, items, given_amount }),
            success: function(response) {
                alert(`Rückgeld: ${response.change} €`);
            },
            error: function(response) {
                alert(response.responseJSON.error);
            }
        });
    });
});

