/**
 * Checkout Page
 * ==============
 * Renders order summary from localStorage, validates the customer form,
 * initiates Razorpay payment, and verifies the transaction.
 *
 * Expected DOM elements:
 *   #checkout-summary
 *   #checkout-form
 *   #pay-btn
 *   #pay-amount
 *   #checkout-empty
 *   .validation-msg
 *   #err-name
 *   #err-mobile
 *   #err-terms
 *   #err-refund
 *   #cust-whatsapp
 *   #chk-whatsapp-same
 */

(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Constants                                                          */
  /* ------------------------------------------------------------------ */

  var CART_KEY = "cart";
  var ORDER_TYPE_KEY = "order_type";

  /* ------------------------------------------------------------------ */
  /* Utility: format currency                                           */
  /* ------------------------------------------------------------------ */

  function formatRs(amount) {
    var num = parseFloat(amount);

    if (isNaN(num)) {
      return "Rs.0";
    }

    return "Rs." + num;
  }

  /* ------------------------------------------------------------------ */
  /* Cart helpers                                                       */
  /* ------------------------------------------------------------------ */

  function getCart() {
    try {
      return JSON.parse(localStorage.getItem(CART_KEY)) || [];
    } catch (_) {
      return [];
    }
  }

  function getOrderType() {
    return localStorage.getItem(ORDER_TYPE_KEY) || "takeaway";
  }

  function clearCart() {
    localStorage.removeItem(CART_KEY);

    try {
      window.dispatchEvent(new CustomEvent("cartUpdated"));
    } catch (_) {
      /* noop */
    }
  }

  /* ------------------------------------------------------------------ */
  /* HTML escape                                                        */
  /* ------------------------------------------------------------------ */

  function escapeHTML(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  /* ------------------------------------------------------------------ */
  /* Render order summary                                               */
  /* ------------------------------------------------------------------ */

  function renderOrderSummary(cart) {
    var container = document.getElementById("checkout-summary");
    var payAmount = document.getElementById("pay-amount");

    if (!container) {
      return;
    }

    var html = "";
    var total = 0;

    for (var i = 0; i < cart.length; i++) {
      var item = cart[i];
      var subtotal = item.price * item.quantity;

      total += subtotal;

      html +=
        '<div class="summary-row">' +
        "<span>" +
        escapeHTML(item.name) +
        ' <small style="color:var(--muted);"> x' +
        item.quantity +
        "</small>" +
        "</span>" +
        '<span class="fw-semibold">' +
        formatRs(subtotal) +
        "</span>" +
        "</div>";
    }

    html +=
      '<div class="summary-row total">' +
      "<span>Total</span>" +
      "<span>" +
      formatRs(total) +
      "</span>" +
      "</div>";

    container.innerHTML = html;

    if (payAmount) {
      payAmount.textContent = formatRs(total);
    }
  }

  /* ------------------------------------------------------------------ */
  /* Show / hide empty state                                            */
  /* ------------------------------------------------------------------ */

  function showEmptyState() {
    var formEl = document.getElementById("checkout-form");
    var emptyEl = document.getElementById("checkout-empty");
    var summarySection = document.querySelector(".checkout-section");

    if (formEl) {
      formEl.closest(".checkout-section").style.display = "none";
    }

    if (summarySection) {
      summarySection.style.display = "none";
    }

    if (emptyEl) {
      emptyEl.classList.remove("d-none");
      emptyEl.style.display = "";
    }
  }

  /* ------------------------------------------------------------------ */
  /* Form validation helpers                                            */
  /* ------------------------------------------------------------------ */

  function showError(id, show) {
    var el = document.getElementById(id);

    if (!el) {
      return;
    }

    el.style.display = show ? "block" : "none";
  }

  function setFieldError(input, hasError) {
    if (!input) {
      return;
    }

    if (hasError) {
      input.classList.add("is-invalid");
      input.classList.remove("is-valid");
    } else {
      input.classList.remove("is-invalid");
      input.classList.add("is-valid");
    }
  }

  function clearAllErrors() {
    var msgs = document.querySelectorAll(".validation-msg");

    for (var i = 0; i < msgs.length; i++) {
      msgs[i].style.display = "none";
    }

    var invalids = document.querySelectorAll(".is-invalid");

    for (var j = 0; j < invalids.length; j++) {
      invalids[j].classList.remove("is-invalid");
    }
  }

  function validateForm() {
    var valid = true;

    var nameInput = document.getElementById("cust-name");
    var mobileInput = document.getElementById("cust-mobile");
    var emailInput = document.getElementById("cust-email");
    var termsChk = document.getElementById("chk-terms");
    var refundChk = document.getElementById("chk-refund");

    /* Name */

    var name = nameInput ? nameInput.value.trim() : "";

    if (!name || name.length < 2) {
      showError("err-name", true);
      setFieldError(nameInput, true);
      valid = false;
    } else {
      showError("err-name", false);
      setFieldError(nameInput, false);
    }

    /* Mobile */

    var mobile = mobileInput ? mobileInput.value.trim() : "";
    var mobileRegex = /^[0-9]{10}$/;

    if (!mobileRegex.test(mobile)) {
      showError("err-mobile", true);
      setFieldError(mobileInput, true);
      valid = false;
    } else {
      showError("err-mobile", false);
      setFieldError(mobileInput, false);
    }

    /* WhatsApp — must be exactly 10 digits */

    var whatsappInput = document.getElementById("cust-whatsapp");
    var whatsappSameChk = document.getElementById("chk-whatsapp-same");

    var whatsapp = whatsappInput ? whatsappInput.value.trim() : "";

    /*
     * If "same as mobile" is checked,
     * use the mobile number as WhatsApp.
     */
    if (whatsappSameChk && whatsappSameChk.checked) {
      whatsapp = mobile;
    }

    var whatsappRegex = /^[0-9]{10}$/;

    if (!whatsappRegex.test(whatsapp)) {
      if (whatsappInput) {
        setFieldError(whatsappInput, true);
      }

      valid = false;
    } else {
      if (whatsappInput) {
        setFieldError(whatsappInput, false);
      }
    }

    /* Email */

    var email = emailInput ? emailInput.value.trim() : "";

    if (email) {
      var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      if (!emailRegex.test(email)) {
        setFieldError(emailInput, true);
        valid = false;
      } else {
        setFieldError(emailInput, false);
      }
    }

    /* Terms checkbox */

    if (termsChk && !termsChk.checked) {
      showError("err-terms", true);
      valid = false;
    } else {
      showError("err-terms", false);
    }

    /* Refund checkbox */

    if (refundChk && !refundChk.checked) {
      showError("err-refund", true);
      valid = false;
    } else {
      showError("err-refund", false);
    }

    return valid;
  }

  /* ------------------------------------------------------------------ */
  /* Build payment request                                              */
  /* ------------------------------------------------------------------ */

  function buildPaymentPayload() {
    var cart = getCart();
    var cartItems = [];

    for (var i = 0; i < cart.length; i++) {
      cartItems.push({
        menu_item_id: cart[i].menu_item_id,
        quantity: cart[i].quantity,
        name: cart[i].name,
      });
    }

    var payload = {
      cart_items: cartItems,
      name: document.getElementById("cust-name").value.trim(),
      mobile: document.getElementById("cust-mobile").value.trim(),
      order_type: getOrderType(),
    };

    var emailInput = document.getElementById("cust-email");

    if (emailInput) {
      var email = emailInput.value.trim();

      if (email) {
        payload.email = email;
      }
    }

    /* -------------------------------------------------------------- */
    /* WhatsApp                                                        */
    /* -------------------------------------------------------------- */

    var whatsappInput = document.getElementById("cust-whatsapp");
    var whatsappSameChk = document.getElementById("chk-whatsapp-same");

    var whatsapp = whatsappInput ? whatsappInput.value.trim() : "";

    /*
     * If the customer selected:
     * "WhatsApp number is the same as mobile number"
     *
     * Always use the current mobile number.
     */
    if (whatsappSameChk && whatsappSameChk.checked) {
      whatsapp = document.getElementById("cust-mobile").value.trim();
    }

    if (whatsapp) {
      payload.whatsapp_number = whatsapp;
    }

    /* Special instructions */

    var instructionsInput = document.getElementById("cust-instructions");

    if (instructionsInput) {
      var instructions = instructionsInput.value.trim();

      if (instructions) {
        payload.special_instructions = instructions;
      }
    }

    return payload;
  }

  /* ------------------------------------------------------------------ */
  /* Payment button loading state                                       */
  /* ------------------------------------------------------------------ */

  function setPayLoading(loading) {
    var btn = document.getElementById("pay-btn");

    if (!btn) {
      return;
    }

    if (loading) {
      btn.disabled = true;
      btn.dataset.originalText = btn.innerHTML;

      btn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" ' +
        'role="status" aria-hidden="true"></span>Processing...';
    } else {
      btn.disabled = false;

      if (btn.dataset.originalText) {
        btn.innerHTML = btn.dataset.originalText;
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* Display error                                                      */
  /* ------------------------------------------------------------------ */

  function showFormError(message) {
    var alertEl = document.getElementById("checkout-form-error");

    if (!alertEl) {
      var formSection = document.getElementById("checkout-form");

      if (!formSection) {
        return;
      }

      var parent = formSection.closest(".checkout-section");

      if (!parent) {
        return;
      }

      alertEl = document.createElement("div");

      alertEl.id = "checkout-form-error";
      alertEl.className = "alert alert-danger py-2 px-3 small mb-3";
      alertEl.style.display = "none";

      parent.insertBefore(alertEl, parent.firstChild);
    }

    alertEl.textContent = message;
    alertEl.style.display = "";

    setTimeout(function () {
      alertEl.style.display = "none";
    }, 6000);
  }

  /* ------------------------------------------------------------------ */
  /* Load Razorpay                                                      */
  /* ------------------------------------------------------------------ */

  function loadRazorpayScript() {
    return new Promise(function (resolve, reject) {
      if (window.Razorpay) {
        resolve();
        return;
      }

      var script = document.createElement("script");

      script.src = "https://checkout.razorpay.com/v1/checkout.js";

      script.async = true;

      script.onload = resolve;

      script.onerror = function () {
        reject(new Error("Failed to load payment gateway."));
      };

      document.head.appendChild(script);
    });
  }

  /* ------------------------------------------------------------------ */
  /* Create payment order                                               */
  /* ------------------------------------------------------------------ */

  function createPaymentOrder() {
    var payload = buildPaymentPayload();

    return fetch("/api/payment/create", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          throw new Error(
            data.error || "Payment initiation failed. Please try again.",
          );
        }

        return data;
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Open Razorpay                                                      */
  /* ------------------------------------------------------------------ */

  function openRazorpayCheckout(rzpData, customerInfo) {
    return new Promise(function (resolve, reject) {
      var options = {
        key: rzpData.key,

        amount: rzpData.amount,

        currency: rzpData.currency,

        name: "Cafe Order",

        description: "Order #" + rzpData.order_id,

        order_id: rzpData.razorpay_order_id,

        handler: function (response) {
          resolve(response);
        },

        prefill: {
          name: customerInfo.name,

          contact: customerInfo.mobile,
        },

        theme: {
          color: "#7C3F2C",
        },

        modal: {
          ondismiss: function () {
            setPayLoading(false);
          },
        },
      };

      if (customerInfo.email) {
        options.prefill.email = customerInfo.email;
      }

      try {
        var rzpInstance = new Razorpay(options);

        rzpInstance.on("payment.failed", function (resp) {
          setPayLoading(false);

          showFormError(
            "Payment failed: " + (resp.error.description || "Unknown error"),
          );
        });

        rzpInstance.open();
      } catch (err) {
        setPayLoading(false);

        reject(new Error("Could not open payment gateway."));
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Verify payment                                                     */
  /* ------------------------------------------------------------------ */

  function verifyPayment(paymentResponse) {
    return fetch("/api/payment/verify", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        razorpay_order_id: paymentResponse.razorpay_order_id,

        razorpay_payment_id: paymentResponse.razorpay_payment_id,

        razorpay_signature: paymentResponse.razorpay_signature,
      }),
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          throw new Error(data.error || "Payment verification failed.");
        }

        return data;
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Handle form submission                                             */
  /* ------------------------------------------------------------------ */

  function handleFormSubmit(e) {
    e.preventDefault();

    clearAllErrors();

    if (!validateForm()) {
      var firstErr = document.querySelector(".is-invalid");

      if (firstErr) {
        firstErr.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }

      return;
    }

    setPayLoading(true);

    var customerInfo = {
      name: document.getElementById("cust-name").value.trim(),

      mobile: document.getElementById("cust-mobile").value.trim(),

      email: document.getElementById("cust-email").value.trim(),
    };

    createPaymentOrder()
      .then(function (rzpData) {
        return loadRazorpayScript().then(function () {
          return rzpData;
        });
      })

      .then(function (rzpData) {
        return openRazorpayCheckout(rzpData, customerInfo);
      })

      .then(function (paymentResponse) {
        return verifyPayment(paymentResponse);
      })

      .then(function (verifyResult) {
        var orderId = verifyResult.order_id;

        if (!orderId) {
          throw new Error("Order was created but no order ID was returned.");
        }

        clearCart();

        /*
         * Customer waits here while
         * cafe accepts/rejects the order.
         */
        window.location.href = "/track/" + encodeURIComponent(orderId);
      })

      .catch(function (err) {
        setPayLoading(false);

        showFormError(err.message || "Something went wrong. Please try again.");
      });
  }

  /* ------------------------------------------------------------------ */
  /* Real-time field validation                                         */
  /* ------------------------------------------------------------------ */

  function initLiveValidation() {
    var nameInput = document.getElementById("cust-name");

    var mobileInput = document.getElementById("cust-mobile");

    var emailInput = document.getElementById("cust-email");

    /*
     * WhatsApp controls
     */
    var whatsappInput = document.getElementById("cust-whatsapp");

    var whatsappSameChk = document.getElementById("chk-whatsapp-same");

    /* Name */

    if (nameInput) {
      nameInput.addEventListener("input", function () {
        if (this.value.trim().length >= 2) {
          showError("err-name", false);

          setFieldError(this, false);
        }
      });
    }

    /* Mobile */

    if (mobileInput) {
      mobileInput.addEventListener("input", function () {
        /*
         * Keep WhatsApp synchronized
         * with mobile while checkbox is checked.
         */
        if (whatsappSameChk && whatsappSameChk.checked && whatsappInput) {
          whatsappInput.value = this.value.trim();
        }

        if (/^[0-9]{10}$/.test(this.value.trim())) {
          showError("err-mobile", false);

          setFieldError(this, false);
        }
      });
    }

    /* WhatsApp checkbox */

    if (whatsappSameChk && whatsappInput && mobileInput) {
      whatsappSameChk.addEventListener("change", function () {
        if (this.checked) {
          /*
           * Copy mobile number immediately.
           */
          whatsappInput.value = mobileInput.value.trim();

          /*
           * Prevent editing while linked.
           */
          whatsappInput.disabled = true;
        } else {
          /*
           * Allow a separate WhatsApp number.
           */
          whatsappInput.disabled = false;
        }
      });
    }

    /* Email */

    if (emailInput) {
      emailInput.addEventListener("input", function () {
        var val = this.value.trim();

        if (!val || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
          setFieldError(this, false);
        }
      });
    }

    /* Terms */

    var termsChk = document.getElementById("chk-terms");

    if (termsChk) {
      termsChk.addEventListener("change", function () {
        if (this.checked) {
          showError("err-terms", false);
        }
      });
    }

    /* Refund */

    var refundChk = document.getElementById("chk-refund");

    if (refundChk) {
      refundChk.addEventListener("change", function () {
        if (this.checked) {
          showError("err-refund", false);
        }
      });
    }
  }

  /* ------------------------------------------------------------------ */
  /* Initialise                                                         */
  /* ------------------------------------------------------------------ */

  function init() {
    var cart = getCart();

    if (!cart || cart.length === 0) {
      showEmptyState();

      return;
    }

    renderOrderSummary(cart);

    var form = document.getElementById("checkout-form");

    if (form) {
      form.addEventListener("submit", handleFormSubmit);
    }

    initLiveValidation();
  }

  /* ------------------------------------------------------------------ */
  /* Start                                                              */
  /* ------------------------------------------------------------------ */

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
