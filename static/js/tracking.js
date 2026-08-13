document.addEventListener("DOMContentLoaded", function () {
  "use strict";

  // Get order ID from /track/<order_id>
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const orderId = pathParts[pathParts.length - 1];

  if (!orderId) {
    console.error("Tracking: Order ID not found.");
    return;
  }

  let lastStatus = "{{ order.status }}";
  let lastRefundStatus = null;
  let lastRejectionReason = null;

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value || "";
    return div.innerHTML;
  }

  function updateRejectionBanner(order) {
    const banner = document.getElementById("rejection-banner");
    const reasonElement = document.getElementById("rejection-reason");
    const refundElement = document.getElementById("refund-status");

    if (!banner || !reasonElement || !refundElement) {
      return;
    }

    if (order.status !== "rejected") {
      banner.classList.add("d-none");
      return;
    }

    const reason =
      order.rejection_reason || "Your order could not be processed.";

    let refundMessage = "";

    switch (order.refund_status) {
      case "refunded":
      case "success":
        refundMessage =
          "Your payment has been refunded to the original payment method.";
        break;

      case "pending":
      case "processing":
        refundMessage = "Your refund is being processed.";
        break;

      case "refund_failed":
      case "failed":
        refundMessage =
          "We could not complete the refund automatically. Please contact the cafe.";
        break;

      default:
        refundMessage = "No payment refund is required.";
    }

    reasonElement.innerHTML = escapeHtml(reason);
    refundElement.innerHTML = escapeHtml(refundMessage);

    banner.classList.remove("d-none");
  }

  function updateStatus(order) {
    const badge = document.getElementById("status-badge");

    if (!badge) {
      return;
    }

    const status = order.status || "";

    badge.textContent = status
      .replace(/_/g, " ")
      .replace(/\b\w/g, function (char) {
        return char.toUpperCase();
      });

    badge.className = "status-badge status-" + status;

    updateStepper(status);
  }

  function updateStepper(status) {
    const steps = ["received", "accepted", "preparing", "ready", "delivered"];

    const stepper = document.getElementById("stepper");
    const fill = document.getElementById("stepper-fill");

    if (!stepper) {
      return;
    }

    const stepElements = stepper.querySelectorAll(".step");

    if (status === "rejected") {
      stepElements.forEach(function (step) {
        step.classList.remove("active", "done");
      });

      const rejectedStep = stepper.querySelector('[data-step="received"]');

      if (rejectedStep) {
        rejectedStep.classList.add("rejected");
      }

      if (fill) {
        fill.style.width = "0%";
      }

      return;
    }

    const currentIndex = steps.indexOf(status);

    stepElements.forEach(function (step, index) {
      step.classList.remove("active", "done", "rejected");

      if (index < currentIndex) {
        step.classList.add("done");
      } else if (index === currentIndex) {
        step.classList.add("active");
      }
    });

    if (fill && currentIndex >= 0) {
      const percentage = (currentIndex / (steps.length - 1)) * 100;

      fill.style.width = percentage + "%";
    }
  }

  function showStatusMessage(message) {
    if (typeof window.showToast === "function") {
      window.showToast(message, "info");
    }
  }

  function checkForChanges(order) {
    if (lastStatus !== null && lastStatus !== order.status) {
      const messages = {
        accepted: "Your order has been accepted by the cafe.",

        preparing: "Your order is now being prepared.",

        ready: "Your order is ready.",

        delivered: "Your order has been delivered.",

        rejected: "Your order has been rejected by the cafe.",
      };

      if (messages[order.status]) {
        showStatusMessage(messages[order.status]);
      }
    }

    if (
      lastRefundStatus !== null &&
      lastRefundStatus !== order.refund_status &&
      order.refund_status === "refunded"
    ) {
      showStatusMessage("Your payment has been refunded.");
    }

    lastStatus = order.status || null;
    lastRefundStatus = order.refund_status || null;
    lastRejectionReason = order.rejection_reason || null;
  }

  function fetchOrderStatus() {
    fetch("/api/orders/" + encodeURIComponent(orderId), {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) {
            throw new Error(data.error || "Unable to load order status.");
          }

          return data;
        });
      })
      .then(function (order) {
        checkForChanges(order);
        updateStatus(order);
        updateRejectionBanner(order);
      })
      .catch(function (error) {
        console.error("Tracking update failed:", error);
      });
  }

  // Initial update
  fetchOrderStatus();

  // Check for Admin status changes every 5 seconds
  setInterval(fetchOrderStatus, 5000);
});
