// to set time for flashed messages in 'layout.html'
var flash_div = document.getElementById("flash_div");
if (flash_div) {
	setTimeout(function () {
		flash_div.style.display = "none";
	}, 7000); // Hide the div after 7 seconds
}

// for clickable table rows
document.addEventListener("DOMContentLoaded", function () {
    const rows = document.querySelectorAll(".clickable-row");
    rows.forEach(row => {
        row.addEventListener("click", () => {
            const href = row.getAttribute("data-href");
            if (href) {
                window.location.href = href;
            }
        });
    });
});