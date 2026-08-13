/**
 * Admin Dashboard
 * =================
 * Live new-order notification using Server-Sent Events (SSE).
 *
 * New orders:
 *   1. Play the user's notification.mp3 sound.
 *   2. Remember the order ID so it does not ring again.
 *   3. Refresh the dashboard after the notification finishes.
 */

(function () {
  "use strict";

  /* ================================================================
       CONFIGURATION
    ================================================================ */

  var RETRY_BASE_DELAY = 3000;
  var RETRY_MAX_DELAY = 30000;
  var MAX_RETRIES = 10;

  var currentRetryDelay = RETRY_BASE_DELAY;
  var retryCount = 0;

  var eventSource = null;
  var reconnectTimeout = null;

  var isVisible = true;

  /* ================================================================
       NOTIFICATION AUDIO
    ================================================================ */

  var notificationAudio = null;
  var audioUnlocked = false;

  /*
   * Get the audio element that already exists in dashboard.html.
   *
   * dashboard.html contains:
   *
   * <audio id="newOrderSound">
   *     <source src="/static/audio/notification.mp3">
   * </audio>
   */
  function getNotificationAudio() {
    if (notificationAudio) {
      return notificationAudio;
    }

    notificationAudio = document.getElementById("newOrderSound");

    if (!notificationAudio) {
      console.warn("[admin.js] #newOrderSound was not found.");

      return null;
    }

    notificationAudio.preload = "auto";
    notificationAudio.volume = 1.0;

    return notificationAudio;
  }

  /*
   * Unlock the audio after the admin interacts with
   * the dashboard.
   *
   * This is necessary because browsers can block
   * autoplay when audio starts from an SSE event.
   */
  function unlockNotificationAudio() {
    var audio = getNotificationAudio();

    if (!audio || audioUnlocked) {
      return;
    }

    /*
     * Do not actually make an audible notification here.
     * We simply attempt to start the existing audio,
     * immediately pause it, and reset it.
     */
    audio.muted = true;
    audio.currentTime = 0;

    var promise = audio.play();

    if (promise !== undefined) {
      promise
        .then(function () {
          audio.pause();
          audio.currentTime = 0;
          audio.muted = false;

          audioUnlocked = true;

          console.info("[admin.js] Notification audio unlocked.");
        })
        .catch(function () {
          audio.muted = false;

          /*
           * The browser may require another
           * interaction. We will try again on
           * the next click/keydown.
           */
          console.info(
            "[admin.js] Waiting for user interaction to unlock notification audio.",
          );
        });
    } else {
      audio.muted = false;
      audioUnlocked = true;
    }
  }

  /*
   * Play the ACTUAL notification.mp3 supplied by the user.
   */
  function playNotificationSound() {
    var audio = getNotificationAudio();

    if (!audio) {
      return Promise.resolve(false);
    }

    try {
      audio.pause();
      audio.currentTime = 0;
      audio.volume = 1.0;
      audio.muted = false;

      var playPromise = audio.play();

      if (playPromise !== undefined) {
        return playPromise
          .then(function () {
            audioUnlocked = true;

            console.info("[admin.js] Notification sound playing.");

            return true;
          })
          .catch(function (error) {
            console.warn("[admin.js] Notification sound was blocked:", error);

            return false;
          });
      }

      return Promise.resolve(true);
    } catch (error) {
      console.warn("[admin.js] Notification sound error:", error);

      return Promise.resolve(false);
    }
  }

  /* ================================================================
       AUDIO USER-INTERACTION UNLOCK
    ================================================================ */

  function initializeAudioUnlock() {
    /*
     * The admin only needs to interact once with the
     * dashboard. After that the browser allows the
     * notification audio to play from SSE events.
     */
    document.addEventListener("click", unlockNotificationAudio, {
      passive: true,
    });

    document.addEventListener("keydown", unlockNotificationAudio, {
      passive: true,
    });

    document.addEventListener("touchstart", unlockNotificationAudio, {
      passive: true,
    });
  }

  /* ================================================================
       GET SSE URL
    ================================================================ */

  function getSSEUrl() {
    var body = document.querySelector("body");

    var baseUrl =
      body && body.dataset.sseUrl
        ? body.dataset.sseUrl
        : "/admin/api/orders/events";

    /*
     * Remember the last order that generated a
     * notification.
     */
    var lastId = null;

    try {
      lastId = sessionStorage.getItem("adminLastSeenOrderId");
    } catch (error) {
      console.warn("[admin.js] Could not access sessionStorage.");
    }

    if (lastId && /^\d+$/.test(lastId)) {
      return (
        baseUrl +
        (baseUrl.indexOf("?") >= 0 ? "&" : "?") +
        "last_id=" +
        encodeURIComponent(lastId)
      );
    }

    return baseUrl;
  }

  /* ================================================================
       CONNECT SSE
    ================================================================ */

  function connectSSE() {
    if (typeof EventSource === "undefined") {
      console.warn("[admin.js] EventSource is not supported.");

      return;
    }

    disconnectSSE();

    var url = getSSEUrl();

    console.info("[admin.js] Connecting to:", url);

    eventSource = new EventSource(url);

    eventSource.onopen = function () {
      currentRetryDelay = RETRY_BASE_DELAY;

      retryCount = 0;

      console.info("[admin.js] SSE connected.");
    };

    eventSource.onmessage = function (event) {
      handleSSEResponse(event.data);
    };

    eventSource.onerror = function () {
      console.warn("[admin.js] SSE connection error.");

      if (eventSource) {
        eventSource.close();
      }

      eventSource = null;

      scheduleReconnect();
    };
  }

  /* ================================================================
       HANDLE SSE MESSAGE
    ================================================================ */

  function handleSSEResponse(rawData) {
    if (!rawData) {
      return;
    }

    var data;

    try {
      data = JSON.parse(rawData);
    } catch (error) {
      console.warn("[admin.js] Invalid SSE JSON:", rawData);

      return;
    }

    console.info("[admin.js] SSE event received:", data);

    if (data.type === "new_order" && data.order) {
      onNewOrder(data.order);
    }
  }

  /* ================================================================
       NEW ORDER
    ================================================================ */

  function onNewOrder(order) {
    if (!order) {
      return;
    }

    var orderId = order.id || order.order_id;

    console.info("[admin.js] New order received:", order.order_id || order.id);

    /* ------------------------------------------------------------
           DUPLICATE PROTECTION
           ------------------------------------------------------------ */

    var alreadySeen = false;

    try {
      var lastSeen = sessionStorage.getItem("adminLastSeenOrderId");

      if (lastSeen && order.id && String(lastSeen) === String(order.id)) {
        alreadySeen = true;
      }

      /*
       * Store the ID immediately.
       *
       * This prevents the same order from
       * triggering another notification.
       */
      if (!alreadySeen && order.id) {
        sessionStorage.setItem("adminLastSeenOrderId", String(order.id));
      }
    } catch (error) {
      console.warn("[admin.js] Could not access sessionStorage:", error);
    }

    /* ------------------------------------------------------------
           IGNORE DUPLICATE
           ------------------------------------------------------------ */

    if (alreadySeen) {
      console.info("[admin.js] Duplicate order ignored:", orderId);

      return;
    }

    /* ------------------------------------------------------------
           PLAY USER'S ACTUAL SOUND
           ------------------------------------------------------------ */

    playNotificationSound()
      .then(function () {
        /*
         * Give the audio time to play.
         *
         * We wait for the actual audio to finish when
         * possible instead of blindly reloading after
         * 2.8 seconds.
         */
        var audio = getNotificationAudio();

        if (!audio) {
          scheduleReload(1000);
          return;
        }

        var reloadScheduled = false;

        function reloadDashboard() {
          if (reloadScheduled) {
            return;
          }

          reloadScheduled = true;

          window.location.reload();
        }

        /*
         * Reload after the audio ends.
         */
        audio.addEventListener("ended", reloadDashboard, { once: true });

        /*
         * Safety fallback.
         *
         * If the browser does not fire "ended",
         * refresh after 10 seconds.
         */
        setTimeout(reloadDashboard, 10000);
      })
      .catch(function () {
        /*
         * If sound cannot play, still update
         * the dashboard.
         */
        scheduleReload(1000);
      });
  }

  /* ================================================================
       PAGE RELOAD
    ================================================================ */

  function scheduleReload(delay) {
    setTimeout(function () {
      window.location.reload();
    }, delay || 1000);
  }

  /* ================================================================
       DISCONNECT SSE
    ================================================================ */

  function disconnectSSE() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);

      reconnectTimeout = null;
    }

    if (eventSource) {
      eventSource.close();

      eventSource = null;
    }
  }

  /* ================================================================
       RECONNECT
    ================================================================ */

  function scheduleReconnect() {
    retryCount++;

    if (retryCount > MAX_RETRIES) {
      console.warn("[admin.js] Maximum SSE retries reached.");

      return;
    }

    var jitter = Math.random() * 1000;

    var delay = Math.min(currentRetryDelay + jitter, RETRY_MAX_DELAY);

    console.info("[admin.js] Reconnecting in " + Math.round(delay) + "ms.");

    reconnectTimeout = setTimeout(function () {
      currentRetryDelay = Math.min(currentRetryDelay * 2, RETRY_MAX_DELAY);

      connectSSE();
    }, delay);
  }

  /* ================================================================
       PAGE VISIBILITY
    ================================================================ */

  function initVisibilityHandler() {
    window.addEventListener("beforeunload", function () {
      disconnectSSE();
    });

    document.addEventListener("visibilitychange", function () {
      isVisible = !document.hidden;

      if (isVisible) {
        connectSSE();

        /*
         * Do not immediately reload here.
         *
         * The SSE connection will detect genuinely
         * new orders using the saved last order ID.
         */
      } else {
        disconnectSSE();
      }
    });
  }

  /* ================================================================
       INITIALISE
    ================================================================ */

  function init() {
    var hasDashboard =
      document.getElementById("stepper-fill") ||
      document.querySelector(".admin-topbar");

    if (!hasDashboard) {
      return;
    }

    /*
     * Prepare the user's notification.mp3.
     */
    getNotificationAudio();

    /*
     * Allow browser audio after admin interaction.
     */
    initializeAudioUnlock();

    /*
     * Connect to live order events.
     */
    connectSSE();

    /*
     * Handle tab visibility/reconnection.
     */
    initVisibilityHandler();

    console.info("[admin.js] Admin notification system initialized.");
  }

  /* ================================================================
       START
    ================================================================ */

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
