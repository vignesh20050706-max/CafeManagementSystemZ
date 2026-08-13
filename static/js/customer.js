/**
 * Customer Menu Page
 * ==================
 * Category filtering, search, quantity controls, add-to-cart via localStorage.
 *
 * Expects the following data attributes on menu cards (set by Jinja2 template):
 *   data-item-id       - MenuItem.id (database primary key)
 *   data-item-name     - MenuItem.name
 *   data-item-price    - MenuItem.price
 *   data-item-number   - MenuItem.item_number
 *   data-category-id   - MenuCategory.id the item belongs to
 *
 * Qty wrappers inside each card should have data-item-id matching their card.
 *
 * Sticky cart bar (id="sticky-cart-bar") visibility is driven by cart contents.
 * Dispatches a 'cartUpdated' CustomEvent so the navbar badge stays in sync.
 *
 * NOTE: This file is loaded inside Jinja2 templates. Avoid double-curly-braces and percent-brace tags.
 *       Never write double curly braces or percent-brace tags here.
 */
(function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /*  Constants                                                          */
    /* ------------------------------------------------------------------ */
    var CART_KEY      = 'cart';
    var ORDER_TYPE_KEY = 'order_type';

    /* ------------------------------------------------------------------ */
    /*  Utility: format currency — "Rs.150" (no decimal for whole nums)  */
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

    function findCartItem(id) {
        var cart = getCart();
        for (var i = 0; i < cart.length; i++) {
            if (cart[i].menu_item_id === id) return cart[i];
        }
        return null;
    }

    function updateItemQty(id, delta) {
        var cart = getCart();
        for (var i = 0; i < cart.length; i++) {
            if (cart[i].menu_item_id === id) {
                cart[i].quantity += delta;
                if (cart[i].quantity <= 0) {
                    cart.splice(i, 1);
                }
                saveCart(cart);
                return cart;
            }
        }
        return cart;
    }

    function addToCart(id, name, price, itemNumber) {
        var cart = getCart();
        var existing = false;
        for (var i = 0; i < cart.length; i++) {
            if (cart[i].menu_item_id === id) {
                cart[i].quantity += 1;
                existing = true;
                break;
            }
        }
        if (!existing) {
            cart.push({
                menu_item_id: id,
                name: name,
                price: parseFloat(price),
                quantity: 1,
                item_number: itemNumber
            });
        }
        saveCart(cart);
        return cart;
    }

    function getCartCount() {
        var cart = getCart();
        var count = 0;
        for (var i = 0; i < cart.length; i++) {
            count += cart[i].quantity;
        }
        return count;
    }

    function getCartTotal() {
        var cart = getCart();
        var total = 0;
        for (var i = 0; i < cart.length; i++) {
            total += cart[i].price * cart[i].quantity;
        }
        return total;
    }

    function dispatchCartEvent() {
        try {
            window.dispatchEvent(new CustomEvent('cartUpdated'));
        } catch (_) { /* noop */ }
    }

    /* ------------------------------------------------------------------ */
    /*  Toast notification (brief "Added to cart" message)                  */
    /* ------------------------------------------------------------------ */
    function showToast(message) {
        var existing = document.getElementById('cart-toast');
        if (existing) existing.remove();

        var toast = document.createElement('div');
        toast.id = 'cart-toast';
        toast.textContent = message;
        toast.style.cssText =
            'position:fixed;bottom:120px;left:50%;transform:translateX(-50%);' +
            'background:#333;color:#fff;padding:0.45rem 1.1rem;border-radius:8px;' +
            'font-size:0.82rem;font-weight:600;z-index:1060;opacity:0;' +
            'transition:opacity 0.25s;pointer-events:none;white-space:nowrap;';

        document.body.appendChild(toast);

        requestAnimationFrame(function () {
            toast.style.opacity = '1';
        });
        setTimeout(function () {
            toast.style.opacity = '0';
            setTimeout(function () { toast.remove(); }, 300);
        }, 1400);
    }

    /* ------------------------------------------------------------------ */
    /*  Render quantity controls for every available item                 */
    /* ------------------------------------------------------------------ */
    function renderQtyControls() {
        var wrappers = document.querySelectorAll('.qty-wrapper');
        for (var w = 0; w < wrappers.length; w++) {
            (function (wrapper) {
                var itemId = parseInt(wrapper.getAttribute('data-item-id'), 10);
                if (isNaN(itemId)) return;

                var card = wrapper.closest('.menu-card');
                if (!card) return;

                var name  = card.getAttribute('data-item-name')  || '';
                var price = card.getAttribute('data-item-price')  || '0';
                var num   = card.getAttribute('data-item-number') || '';

                var item = findCartItem(itemId);
                var qty  = item ? item.quantity : 0;

                wrapper.innerHTML = buildQtyHTML(itemId, qty);
            })(wrappers[w]);
        }
    }

    function buildQtyHTML(itemId, qty) {
        if (qty > 0) {
            return '' +
                '<div class="qty-control">' +
                    '<button class="qty-btn qty-dec" data-id="' + itemId + '" type="button">-</button>' +
                    '<span class="qty-val">' + qty + '</span>' +
                    '<button class="qty-btn qty-inc" data-id="' + itemId + '" type="button">+</button>' +
                '</div>';
        }
        return '<button class="add-btn add-to-cart" data-id="' + itemId + '" type="button">+</button>';
    }

    /* ------------------------------------------------------------------ */
    /*  Sticky cart bar                                                    */
    /* ------------------------------------------------------------------ */
    function updateStickyBar() {
        var bar   = document.getElementById('sticky-cart-bar');
        var info  = document.getElementById('sticky-cart-info');
        var total = document.getElementById('sticky-cart-total');

        if (!bar) return;

        var count = getCartCount();
        var totalAmount = getCartTotal();

        if (count > 0) {
            bar.classList.remove('hidden');
            if (info)  info.textContent  = count + (count === 1 ? ' item' : ' items');
            if (total) total.textContent = formatRs(totalAmount);
        } else {
            bar.classList.add('hidden');
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Category filter pills                                              */
    /* ------------------------------------------------------------------ */
    function initCategoryFilter() {
        var pills = document.querySelectorAll('.cat-pill');
        var cards = document.querySelectorAll('.menu-card');

        if (!pills.length || !cards.length) return;

        for (var p = 0; p < pills.length; p++) {
            (function (pill) {
                pill.addEventListener('click', function (e) {
                    e.preventDefault();

                    // Remove active from all pills
                    for (var i = 0; i < pills.length; i++) {
                        pills[i].classList.remove('active');
                    }
                    pill.classList.add('active');

                    var cat = pill.getAttribute('data-category');

                    for (var c = 0; c < cards.length; c++) {
                        if (cat === 'all' || cards[c].getAttribute('data-category-id') === cat) {
                            cards[c].style.display = '';
                        } else {
                            cards[c].style.display = 'none';
                        }
                    }
                });
            })(pills[p]);
        }

        // Activate pill from URL param ?category=<id>
        var params = new URLSearchParams(window.location.search);
        var catParam = params.get('category');
        if (catParam) {
            for (var j = 0; j < pills.length; j++) {
                pills[j].classList.remove('active');
                if (pills[j].getAttribute('data-category') === catParam) {
                    pills[j].classList.add('active');
                }
            }
            for (var k = 0; k < cards.length; k++) {
                if (cards[k].getAttribute('data-category-id') === catParam) {
                    cards[k].style.display = '';
                } else {
                    cards[k].style.display = 'none';
                }
            }
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Search / text filter                                               */
    /* ------------------------------------------------------------------ */
    function initSearch() {
        var searchInput = document.getElementById('menu-search');
        if (!searchInput) return;

        var cards = document.querySelectorAll('.menu-card');

        searchInput.addEventListener('input', function () {
            var query = this.value.toLowerCase().trim();

            for (var i = 0; i < cards.length; i++) {
                if (!query) {
                    cards[i].style.display = '';
                    continue;
                }
                var name  = (cards[i].getAttribute('data-item-name')  || '').toLowerCase();
                var num   = (cards[i].getAttribute('data-item-number') || '').toLowerCase();
                var desc  = '';
                var descEl = cards[i].querySelector('.item-desc');
                if (descEl) desc = descEl.textContent.toLowerCase();

                if (name.indexOf(query) !== -1 || num.indexOf(query) !== -1 || desc.indexOf(query) !== -1) {
                    cards[i].style.display = '';
                } else {
                    cards[i].style.display = 'none';
                }
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /*  Event delegation for qty buttons & add buttons                     */
    /* ------------------------------------------------------------------ */
    function initEventDelegation() {
        document.addEventListener('click', function (e) {
            var target = e.target;

            // --- Add to cart (+) button ---
            if (target.classList.contains('add-to-cart')) {
                e.preventDefault();
                var id = parseInt(target.getAttribute('data-id'), 10);
                if (isNaN(id)) return;

                var card = target.closest('.menu-card');
                if (!card) return;

                var name = card.getAttribute('data-item-name')  || '';
                var price = card.getAttribute('data-item-price') || '0';
                var num  = card.getAttribute('data-item-number') || '';

                addToCart(id, name, price, num);
                refreshUI();
                showToast('Added to cart');
                return;
            }

            // --- Quantity increment (+) ---
            if (target.classList.contains('qty-inc')) {
                e.preventDefault();
                var incId = parseInt(target.getAttribute('data-id'), 10);
                if (isNaN(incId)) return;

                var incCard = target.closest('.menu-card');
                if (!incCard) return;

                addToCart(
                    incId,
                    incCard.getAttribute('data-item-name')  || '',
                    incCard.getAttribute('data-item-price') || '0',
                    incCard.getAttribute('data-item-number') || ''
                );
                refreshUI();
                return;
            }

            // --- Quantity decrement (-) ---
            if (target.classList.contains('qty-dec')) {
                e.preventDefault();
                var decId = parseInt(target.getAttribute('data-id'), 10);
                if (isNaN(decId)) return;

                updateItemQty(decId, -1);
                refreshUI();
                return;
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /*  Refresh all dynamic UI elements                                    */
    /* ------------------------------------------------------------------ */
    function refreshUI() {
        renderQtyControls();
        updateStickyBar();
    }

    /* ------------------------------------------------------------------ */
    /*  Initialise on DOM ready                                           */
    /* ------------------------------------------------------------------ */
    function init() {
        renderQtyControls();
        updateStickyBar();
        initCategoryFilter();
        initSearch();
        initEventDelegation();

        // Add body class for sticky-cart spacing
        var body = document.querySelector('body');
        if (body) body.classList.add('has-sticky-cart');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
