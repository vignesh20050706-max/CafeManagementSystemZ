/**
 * Cart Page
 * ==========
 * Renders the shopping cart from localStorage, handles quantity changes,
 * item removal, clearing, and the Phase 5 order-flow transition.
 *
 * Flow:
 *   Cart -> PROCEED -> Delivery Options -> Submit -> Checkout
 *
 * Existing order_type localStorage key is preserved so the current
 * checkout/payment backend continues to receive the same value.
 */
(function () {
  "use strict";

  var CART_KEY = "cart";
  var ORDER_TYPE_KEY = "order_type";

  function formatRs(amount) {
    var num = parseFloat(amount);
    if (isNaN(num)) return "Rs.0";
    return "Rs." + num;
  }

  function getCart() {
    try {
      return JSON.parse(localStorage.getItem(CART_KEY)) || [];
    } catch (_) {
      return [];
    }
  }

  function saveCart(cart) {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    dispatchCartEvent();
  }

  function dispatchCartEvent() {
    try {
      window.dispatchEvent(new CustomEvent("cartUpdated"));
    } catch (_) {}
  }

  function escapeHTML(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str == null ? "" : String(str)));
    return div.innerHTML;
  }

  function getItemCount(cart) {
    var count = 0;

    for (var i = 0; i < cart.length; i++) {
      count += Number(cart[i].quantity) || 0;
    }

    return count;
  }

  function getTotal(cart) {
    var total = 0;

    for (var i = 0; i < cart.length; i++) {
      total += (Number(cart[i].price) || 0) * (Number(cart[i].quantity) || 0);
    }

    return total;
  }

  function buildCartItemHTML(item, index) {
    var quantity = Number(item.quantity) || 0;
    var price = Number(item.price) || 0;
    var subtotal = price * quantity;

    return (
      "" +
      '<div class="cart-item"' +
      ' data-cart-item-id="' +
      escapeHTML(item.menu_item_id) +
      '">' +
      '<div class="cart-item-info">' +
      '<div class="cart-item-number">' +
      escapeHTML(item.item_number || "") +
      "</div>" +
      '<div class="cart-item-name">' +
      escapeHTML(item.name) +
      "</div>" +
      '<div class="cart-item-price">' +
      formatRs(price) +
      "</div>" +
      "</div>" +
      '<div class="qty-control">' +
      "<button " +
      'class="qty-btn cart-qty-dec" ' +
      'data-id="' +
      escapeHTML(item.menu_item_id) +
      '" ' +
      'type="button" ' +
      'aria-label="Decrease quantity">' +
      "-" +
      "</button>" +
      '<span class="qty-val">' +
      quantity +
      "</span>" +
      "<button " +
      'class="qty-btn cart-qty-inc" ' +
      'data-id="' +
      escapeHTML(item.menu_item_id) +
      '" ' +
      'type="button" ' +
      'aria-label="Increase quantity">' +
      "+" +
      "</button>" +
      "</div>" +
      '<div class="cart-item-subtotal">' +
      formatRs(subtotal) +
      "</div>" +
      "<button " +
      'class="cart-remove" ' +
      'data-id="' +
      escapeHTML(item.menu_item_id) +
      '" ' +
      'type="button" ' +
      'title="Remove item" ' +
      'aria-label="Remove item">' +
      "&#10005;" +
      "</button>" +
      "</div>"
    );
  }

  function buildCartHTML(cart) {
    var html = "";
    var total = getTotal(cart);
    var itemCount = getItemCount(cart);

    for (var i = 0; i < cart.length; i++) {
      html += buildCartItemHTML(cart[i], i);
    }

    html +=
      "" +
      '<div class="cart-summary">' +
      '<div class="cart-summary-row">' +
      "<span>" +
      itemCount +
      (itemCount === 1 ? " item" : " items") +
      "</span>" +
      "<span>" +
      formatRs(total) +
      "</span>" +
      "</div>" +
      '<div class="cart-summary-row total">' +
      "<span>Total</span>" +
      "<span>" +
      formatRs(total) +
      "</span>" +
      "</div>" +
      "</div>";

    html +=
      "" +
      '<div class="d-grid gap-2 p-3">' +
      "<button " +
      'class="btn btn-outline-secondary py-2" ' +
      'id="clear-cart-btn" ' +
      'type="button" ' +
      'style="border-radius:10px;font-size:.88rem;">' +
      "Clear Cart" +
      "</button>" +
      "</div>";

    return html;
  }

  function updateBottomBar(cart) {
    var bar = document.getElementById("cart-bottom-bar");
    var countEl = document.getElementById("cart-bottom-count");
    var totalEl = document.getElementById("cart-bottom-total");

    if (!bar) return;

    if (!cart.length) {
      bar.style.display = "none";
      document.body.classList.remove("has-cart-bottom-bar");
      return;
    }

    var count = getItemCount(cart);
    var total = getTotal(cart);

    if (countEl) {
      countEl.textContent = count + (count === 1 ? " item" : " items");
    }

    if (totalEl) {
      totalEl.textContent = formatRs(total);
    }

    bar.style.display = "";
    document.body.classList.add("has-cart-bottom-bar");
  }

  function renderCart() {
    var cart = getCart();

    var contentEl = document.getElementById("cart-content");

    var emptyEl = document.getElementById("cart-empty");

    if (!contentEl || !emptyEl) return;

    if (cart.length === 0) {
      contentEl.style.display = "none";
      contentEl.innerHTML = "";

      emptyEl.style.display = "";

      updateBottomBar([]);

      return;
    }

    contentEl.style.display = "";
    emptyEl.style.display = "none";

    contentEl.innerHTML = buildCartHTML(cart);

    updateBottomBar(cart);
  }

  function clearCart() {
    if (!confirm("Clear all items from your cart?")) {
      return;
    }

    saveCart([]);

    renderCart();
  }

  function openDeliveryOptions() {
    var cart = getCart();

    if (!cart.length) {
      renderCart();
      return;
    }

    var modalEl = document.getElementById("deliveryOptionsModal");

    /*
     * If Bootstrap's modal isn't available,
     * preserve the existing checkout flow.
     */
    if (!modalEl || !window.bootstrap || !bootstrap.Modal) {
      window.location.href = "/checkout";
      return;
    }

    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);

    modal.show();
  }

  function selectDeliveryOption(button) {
    var buttons = document.querySelectorAll(".delivery-option");

    for (var i = 0; i < buttons.length; i++) {
      buttons[i].classList.remove("selected");

      var radio = buttons[i].querySelector(".delivery-radio");

      if (radio) {
        radio.checked = false;
      }
    }

    button.classList.add("selected");

    var selectedRadio = button.querySelector(".delivery-radio");

    if (selectedRadio) {
      selectedRadio.checked = true;
    }
  }

  function submitDeliveryOption() {
    var selected = document.querySelector(
      ".delivery-option.selected .delivery-radio",
    );

    if (!selected) {
      alert("Please choose your preferred order method.");

      return;
    }

    /*
     * Keep the existing order_type key.
     * The checkout/payment backend already uses
     * this value, so we don't change the backend contract.
     */
    localStorage.setItem(ORDER_TYPE_KEY, selected.value);

    var modalEl = document.getElementById("deliveryOptionsModal");

    if (modalEl && window.bootstrap && bootstrap.Modal) {
      var modal = bootstrap.Modal.getOrCreateInstance(modalEl);

      modal.hide();
    }

    window.location.href = "/checkout";
  }

  function initEventDelegation() {
    var contentEl = document.getElementById("cart-content");

    if (!contentEl) return;

    contentEl.addEventListener("click", function (e) {
      var target = e.target;

      /*
       * INCREASE QUANTITY
       */
      if (target.classList.contains("cart-qty-inc")) {
        e.preventDefault();

        var incId = parseInt(target.getAttribute("data-id"), 10);

        if (isNaN(incId)) return;

        var cart = getCart();

        for (var i = 0; i < cart.length; i++) {
          if (Number(cart[i].menu_item_id) === incId) {
            cart[i].quantity = (Number(cart[i].quantity) || 0) + 1;

            break;
          }
        }

        saveCart(cart);

        renderCart();

        return;
      }

      /*
       * DECREASE QUANTITY
       */
      if (target.classList.contains("cart-qty-dec")) {
        e.preventDefault();

        var decId = parseInt(target.getAttribute("data-id"), 10);

        if (isNaN(decId)) return;

        var decCart = getCart();

        for (var j = 0; j < decCart.length; j++) {
          if (Number(decCart[j].menu_item_id) === decId) {
            decCart[j].quantity = (Number(decCart[j].quantity) || 0) - 1;

            if (decCart[j].quantity <= 0) {
              decCart.splice(j, 1);
            }

            break;
          }
        }

        saveCart(decCart);

        renderCart();

        return;
      }

      /*
       * REMOVE ITEM
       */
      if (
        target.classList.contains("cart-remove") ||
        target.closest(".cart-remove")
      ) {
        e.preventDefault();

        var removeBtn = target.classList.contains("cart-remove")
          ? target
          : target.closest(".cart-remove");

        var removeId = parseInt(removeBtn.getAttribute("data-id"), 10);

        if (isNaN(removeId)) return;

        var removeCart = getCart();

        for (var k = 0; k < removeCart.length; k++) {
          if (Number(removeCart[k].menu_item_id) === removeId) {
            removeCart.splice(k, 1);

            break;
          }
        }

        saveCart(removeCart);

        renderCart();

        return;
      }

      /*
       * CLEAR CART
       */
      if (target.id === "clear-cart-btn" || target.closest("#clear-cart-btn")) {
        e.preventDefault();

        clearCart();
      }
    });
  }

  function initDeliveryEvents() {
    var optionButtons = document.querySelectorAll(".delivery-option");

    for (var i = 0; i < optionButtons.length; i++) {
      optionButtons[i].addEventListener("click", function () {
        selectDeliveryOption(this);
      });
    }

    var proceedBtn = document.getElementById("proceed-order-btn");

    if (proceedBtn) {
      proceedBtn.addEventListener("click", openDeliveryOptions);
    }

    var submitBtn = document.getElementById("delivery-submit");

    if (submitBtn) {
      submitBtn.addEventListener("click", submitDeliveryOption);
    }
  }

  function init() {
    renderCart();

    initEventDelegation();

    initDeliveryEvents();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
