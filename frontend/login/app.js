const errorBox = document.getElementById("errorBox");
const params = new URLSearchParams(window.location.search);
const error = params.get("error");

if (error) {
  errorBox.hidden = false;
  errorBox.textContent = error;
}
