document.addEventListener("DOMContentLoaded", () => {
  // Estimate order total from the selected service and quantity.
  const serviceSelect = document.getElementById("serviceSelect");
  const quantityInput = document.getElementById("quantityInput");
  const estimatedTotal = document.getElementById("estimatedTotal");

  function updateEstimate() {
    if (!serviceSelect || !quantityInput || !estimatedTotal) return;
    const option = serviceSelect.options[serviceSelect.selectedIndex];
    const price = Number(option?.dataset?.price || 0);
    const quantity = Math.max(0, Number(quantityInput.value || 0));
    estimatedTotal.textContent = new Intl.NumberFormat("en-IN", {
      style: "currency", currency: "INR"
    }).format(price * quantity);
  }

  serviceSelect?.addEventListener("change", updateEstimate);
  quantityInput?.addEventListener("input", updateEstimate);
  updateEstimate();

  // Confirm destructive actions.
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm || "Are you sure?")) {
        event.preventDefault();
      }
    });
  });

  // Bootstrap client-side validation.
  document.querySelectorAll(".needs-validation").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  });
});
