/**
 * Cart Page
 * ==========
 * Renders the shopping cart from localStorage, handles quantity changes,
 * item removal, clearing, and navigation to checkout.
 *
 * Expected DOM containers (set by Jinja2 template):
 *   #cart-content   - where rendered cart items are injected
 *   #cart-empty     - empty-cart message (shown/hidden by JS)
 *
 * NOTE: This file is loaded inside Jinja2 templates. Avoid double-curly-braces and percent-brace tags.
 *       Never write double curly braces or percent-brace tags here.
 */
(function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /*  Constants                                                          */
    /* ------------------------------------------------------------------ */
    var CART_KEY = 'cart';

    /* ------------------------------------------------------------------ */
    /*  Utility: format currency                                           */
    /* ------------------------------------------------------------------ */
    function formatRs(amount) {
        var num = parseFloat(amount);
        if (isNaN(num)) return 'Rs.0';
        return 'Rs.' + num;
    }

    /* ------------------------------------------------------------------ */
    /*  Cart helpers (localStorage)                                        */
    /* ------------------------------------------------------------------ */
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
            window.dispatchEvent(new CustomEvent('cartUpdated'));
        } catch (_) { /* noop */ }
    }

    /* ------------------------------------------------------------------ */
    /*  Build HTML for a single cart item row                              */
    /* ------------------------------------------------------------------ */
    function buildCartItemHTML(item, index) {
        var subtotal = item.price * item.quantity;

        return '' +
            '<div class="d-flex align-items-center gap-3 py-3' +
                (index > 0 ? ' border-top' : '') + '" style="border-color:var(--border);" ' +
                'data-cart-item-id="' + item.menu_item_id + '">' +
                '<!-- Item info -->' +
                '<div style="flex:1;min-width:0;">' +
                    '<div style="font-size:0.72rem;color:var(--muted);font-weight:600;">' +
                        escapeHTML(item.item_number || '') +
                    '</div>' +
                    '<div style="font-weight:600;font-size:0.92rem;color:var(--text);">' +
                        escapeHTML(item.name) +
                    '</div>' +
                    '<div style="font-size:0.85rem;color:var(--primary);font-weight:700;">' +
                        formatRs(item.price) +
                    '</div>' +
                '</div>' +
                '<!-- Qty controls -->' +
                '<div class="qty-control">' +
                    '<button class="qty-btn cart-qty-dec" data-id="' + item.menu_item_id + '" type="button">-</button>' +
                    '<span class="qty-val">' + item.quantity + '</span>' +
                    '<button class="qty-btn cart-qty-inc" data-id="' + item.menu_item_id + '" type="button">+</button>' +
                '</div>' +
                '<!-- Subtotal -->' +
                '<div style="min-width:70px;text-align:right;font-weight:700;font-size:0.95rem;color:var(--primary);">' +
                    formatRs(subtotal) +
                '</div>' +
                '<!-- Remove button -->' +
                '<button class="btn btn-sm btn-outline-danger cart-remove-btn" data-id="' + item.menu_item_id + '" ' +
                    'type="button" style="border-radius:8px;font-size:0.78rem;padding:0.25rem 0.5rem;" ' +
                    'title="Remove item">' +
                    '<span style="pointer-events:none;">&#10005;</span>' +
                '</button>' +
            '</div>';
    }

    /* ------------------------------------------------------------------ */
    /*  Build full cart HTML (items + summary + actions)                   */
    /* ------------------------------------------------------------------ */
    function buildCartHTML(cart) {
        var html = '';

        // Items
        for (var i = 0; i < cart.length; i++) {
            html += buildCartItemHTML(cart[i], i);
        }

        // Summary
        var total = 0;
        var itemCount = 0;
        for (var j = 0; j < cart.length; j++) {
            total += cart[j].price * cart[j].quantity;
            itemCount += cart[j].quantity;
        }

        html += '' +
            '<div style="border-top:1.5px solid var(--border);margin-top:0.5rem;padding-top:0.75rem;">' +
                '<div class="summary-row total" style="display:flex;justify-content:space-between;align-items:center;">' +
                    '<span>' + itemCount + (itemCount === 1 ? ' item' : ' items') + '</span>' +
                    '<span style="font-size:1.1rem;color:var(--primary);">' + formatRs(total) + '</span>' +
                '</div>' +
            '</div>';

        // Action buttons
        html += '' +
            '<div class="d-grid gap-2 mt-3">' +
                '<a href="/checkout" class="btn btn-primary py-2 fw-semibold" ' +
                    'style="border-radius:10px;font-size:0.95rem;">' +
                    'Proceed to Checkout' +
                '</a>' +
                '<button class="btn btn-outline-secondary py-2" id="clear-cart-btn" type="button" ' +
                    'style="border-radius:10px;font-size:0.88rem;">' +
                    'Clear Cart' +
                '</button>' +
            '</div>';

        return html;
    }

    /* ------------------------------------------------------------------ */
    /*  Render the entire cart view                                       */
    /* ------------------------------------------------------------------ */
    function renderCart() {
        var cart = getCart();
        var contentEl = document.getElementById('cart-content');
        var emptyEl   = document.getElementById('cart-empty');

        if (!contentEl || !emptyEl) return;

        if (cart.length === 0) {
            contentEl.style.display = 'none';
            emptyEl.style.display = '';
            return;
        }

        contentEl.style.display = '';
        emptyEl.style.display = 'none';
        contentEl.innerHTML = buildCartHTML(cart);
    }

    /* ------------------------------------------------------------------ */
    /*  Clear the entire cart                                              */
    /* ------------------------------------------------------------------ */
    function clearCart() {
        if (!confirm('Clear all items from your cart?')) return;
        saveCart([]);
        renderCart();
    }

    /* ------------------------------------------------------------------ */
    /*  Event delegation for cart interactions                            */
    /* ------------------------------------------------------------------ */
    function initEventDelegation() {
        var contentEl = document.getElementById('cart-content');
        if (!contentEl) return;

        contentEl.addEventListener('click', function (e) {
            var target = e.target;

            // --- Increment ---
            if (target.classList.contains('cart-qty-inc')) {
                e.preventDefault();
                var incId = parseInt(target.getAttribute('data-id'), 10);
                if (isNaN(incId)) return;

                var cart = getCart();
                for (var i = 0; i < cart.length; i++) {
                    if (cart[i].menu_item_id === incId) {
                        cart[i].quantity += 1;
                        break;
                    }
                }
                saveCart(cart);
                renderCart();
                return;
            }

            // --- Decrement ---
            if (target.classList.contains('cart-qty-dec')) {
                e.preventDefault();
                var decId = parseInt(target.getAttribute('data-id'), 10);
                if (isNaN(decId)) return;

                var decCart = getCart();
                for (var j = 0; j < decCart.length; j++) {
                    if (decCart[j].menu_item_id === decId) {
                        decCart[j].quantity -= 1;
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

            // --- Remove ---
            if (target.classList.contains('cart-remove-btn') || target.closest('.cart-remove-btn')) {
                e.preventDefault();
                var btn = target.classList.contains('cart-remove-btn') ? target : target.closest('.cart-remove-btn');
                var removeId = parseInt(btn.getAttribute('data-id'), 10);
                if (isNaN(removeId)) return;

                var rmCart = getCart();
                for (var k = 0; k < rmCart.length; k++) {
                    if (rmCart[k].menu_item_id === removeId) {
                        rmCart.splice(k, 1);
                        break;
                    }
                }
                saveCart(rmCart);
                renderCart();
                return;
            }

            // --- Clear cart ---
            if (target.id === 'clear-cart-btn' || target.closest('#clear-cart-btn')) {
                e.preventDefault();
                clearCart();
                return;
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /*  HTML escape to prevent XSS in item names                          */
    /* ------------------------------------------------------------------ */
    function escapeHTML(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    /* ------------------------------------------------------------------ */
    /*  Initialise on DOM ready                                           */
    /* ------------------------------------------------------------------ */
    function init() {
        renderCart();
        initEventDelegation();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
