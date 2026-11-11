// main.js - Повний скрипт сайту MONO.DROP
document.addEventListener("DOMContentLoaded", () => {
    // =========================================================================
    // 1. Універсальні допоміжні функції для модалок та сайдбару
    // =========================================================================
    function openModal(modalEl) {
        if (!modalEl) return;
        modalEl.classList.add("open", "active", "is-open");
        modalEl.style.display = "flex";
        document.body.style.overflow = "hidden";
    }

    function closeModal(modalEl) {
        if (!modalEl) return;
        modalEl.classList.remove("open", "active", "is-open");
        modalEl.style.display = "none";
        syncBodyOverflow();
    }

    function closeAllModals() {
        const modals = document.querySelectorAll(
            ".modal-backdrop, .modal-overlay, #productDetailsModal, #addProductModal, #infoModal"
        );
        modals.forEach((m) => {
            m.classList.remove("open", "active", "is-open");
            m.style.display = "none";
        });
        syncBodyOverflow();
    }

    function openSidebar() {
        const sidebar = document.getElementById("leftSidebar");
        const overlay = document.getElementById("sidebarOverlay") || document.getElementById("sidebarBackdrop");
        if (sidebar) sidebar.classList.add("open", "active");
        if (overlay) {
            overlay.classList.add("open", "active");
            overlay.style.display = "block";
        }
        document.body.style.overflow = "hidden";
    }

    function closeSidebar() {
        const sidebar = document.getElementById("leftSidebar");
        const overlay = document.getElementById("sidebarOverlay") || document.getElementById("sidebarBackdrop");
        if (sidebar) sidebar.classList.remove("open", "active");
        if (overlay) {
            overlay.classList.remove("open", "active");
            overlay.style.display = "none";
        }
        syncBodyOverflow();
    }

    function syncBodyOverflow() {
        const anyModalOpen = document.querySelector(
            ".modal-backdrop.open, .modal-backdrop.active, .modal-backdrop.is-open, .modal-overlay.open, .modal-overlay.active, #productDetailsModal.open, #addProductModal.open, #infoModal.open"
        );
        const sidebarOpen = document.querySelector("#leftSidebar.open, #leftSidebar.active");
        if (!anyModalOpen && !sidebarOpen) {
            document.body.style.overflow = "";
        }
    }

    // =========================================================================
    // 2. Елементи пошуку та категорій
    // =========================================================================
    const searchInput = document.getElementById("searchInput");
    const categoryButtons = document.querySelectorAll(".category-card");
    const productsGrid = document.getElementById("productsGrid");
    const noResults = document.getElementById("noResults");
    const resetFiltersBtn = document.getElementById("resetFiltersBtn");

    let currentCategory = "all";

    function getCards() {
        return document.querySelectorAll(".yt-card");
    }

    function applyFilters() {
        const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
        let visibleCount = 0;
        const cards = getCards();

        cards.forEach((card) => {
            const title = (card.getAttribute("data-title") || "").toLowerCase();
            const category = (card.getAttribute("data-category") || "").toLowerCase();
            const categoryName = (card.getAttribute("data-category-name") || "").toLowerCase();

            const matchesCategory = (currentCategory === "all" || category === currentCategory);
            const matchesSearch = (!query || title.includes(query) || categoryName.includes(query));

            if (matchesCategory && matchesSearch) {
                const wasHidden = card.classList.contains("is-hidden");
                card.classList.remove("is-hidden");

                if (wasHidden) {
                    card.classList.remove("fade-in");
                    void card.offsetWidth;
                    card.classList.add("fade-in");
                }
                visibleCount++;
            } else {
                card.classList.add("is-hidden");
                card.classList.remove("fade-in");
            }
        });

        if (noResults) {
            noResults.style.display = (visibleCount === 0) ? "flex" : "none";
        }
    }

    if (searchInput) {
        searchInput.addEventListener("input", applyFilters);
    }

    categoryButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const selectedCategory = button.getAttribute("data-category");
            if (!selectedCategory) return;

            categoryButtons.forEach((btn) => btn.classList.remove("active"));
            button.classList.add("active");

            currentCategory = selectedCategory;
            applyFilters();
        });
    });

    function resetAllFilters() {
        if (searchInput) {
            searchInput.value = "";
        }
        categoryButtons.forEach((btn) => btn.classList.remove("active"));
        const allBtn = document.querySelector('.category-card[data-category="all"]');
        if (allBtn) {
            allBtn.classList.add("active");
        }
        currentCategory = "all";
        applyFilters();
    }

    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener("click", () => {
            resetAllFilters();
            if (searchInput) {
                searchInput.focus();
            }
        });
    }

    // =========================================================================
    // 3. Інформаційне модальне вікно (#infoModal)
    // =========================================================================
    const infoModal = document.getElementById("infoModal");
    const infoModalTitle = document.getElementById("infoModalTitle");
    const infoModalBody = document.getElementById("infoModalBody");

    const INFO_CONTENT = {
        about: {
            title: "📦 Про товари та кастомні роботи",
            html: `
                <p>Ласкаво просимо до <strong>MONO.DROP</strong> — майстерні ексклюзивного кастому, освітлення та авторських речей.</p>
                <h4>⚡ Преміальні матеріали та ручна робота</h4>
                <p>Ми не займаємося масовим виробництвом. Кожен виріб збирається, тестується та пакується вручну нашими майстрами.</p>
                <ul>
                    <li><strong>Кастомні годинники:</strong> створюються на надійній базі оригінальних калібрів Seiko NH35/NH36, сапфірового скла та сталі 316L.</li>
                    <li><strong>Акумулятори та станції:</strong> безпечні елементи із захистом від короткого замикання та надшвидкою зарядкою PD 65-100W.</li>
                    <li><strong>Світильники:</strong> безпечний енергоефективний LED-неон на монолітному прозорому акрилі з терміном служби від 50 000 годин.</li>
                    <li><strong>Одяг:</strong> 100% надщільна бавовна з індивідуальною виваркою та стійким до прання шовкодруком.</li>
                </ul>
                <h4>🛡 Контроль якості</h4>
                <p>Перед відправкою кожен товар проходить 3-етапне тестування працездатності.</p>
            `
        },
        delivery: {
            title: "🚚 Оплата та доставка",
            html: `
                <p>Ми робимо процес замовлення швидким та прозорим.</p>
                <h4>📦 Доставка</h4>
                <ul>
                    <li>Відправка замовлень щодня перевізником <strong>Нова Пошта</strong> по всій Україні.</li>
                    <li>Швидка доставка: <strong>1–2 робочі дні</strong> у будь-яке відділення чи поштомат.</li>
                    <li>Відстеження посилки за номером ТТН одразу після відправки.</li>
                </ul>
                <h4>💳 Оплата</h4>
                <ul>
                    <li><strong>Післяплата (накладений платіж):</strong> оплачуйте замовлення тільки після огляду та перевірки у відділенні.</li>
                    <li><strong>Оплата на рахунок:</strong> безпечний безготівковий розрахунок на реквізити IBAN.</li>
                </ul>
                <h4>🤝 Гарантія та повернення</h4>
                <p>14 днів на повернення або обмін згідно із Законом України «Про захист прав споживачів».</p>
            `
        },
        socials: {
            title: "📱 Наші офіційні соцмережі",
            html: `
                <p>Підписуйтесь на наші ресурси, щоб дивитися бекстейдж збірок, дропи лімітованих робіт та брати участь у розіграшах!</p>
                <div class="info-social-links">
                    <a href="https://tiktok.com" target="_blank" rel="noopener noreferrer" class="social-link-btn">
                        <span>🎵</span>
                        <span>TikTok: @mono.drop (Відео та процеси кастому)</span>
                    </a>
                    <a href="https://t.me/maxpro13tv2" target="_blank" rel="noopener noreferrer" class="social-link-btn">
                        <span>✈️</span>
                        <span>Telegram: @maxpro13tv2 (Зв'язок та замовлення)</span>
                    </a>
                </div>
            `
        }
    };

    function openInfoModal(key) {
        if (!infoModal || !INFO_CONTENT[key]) return;
        const data = INFO_CONTENT[key];
        if (infoModalTitle) infoModalTitle.textContent = data.title;
        if (infoModalBody) infoModalBody.innerHTML = data.html;
        openModal(infoModal);
    }

    // =========================================================================
    // 4. Модальне вікно додавання товару (#addProductModal)
    // =========================================================================
    const addProductModal = document.getElementById("addProductModal");
    const addProductForm = document.getElementById("addProductForm");
    const submitAddProductBtn = document.getElementById("submitAddProductBtn");

    function createCardElement(product) {
        const article = document.createElement("article");
        article.className = "yt-card fade-in";
        article.setAttribute("data-id", product.id);
        article.setAttribute("data-title", product.title);
        article.setAttribute("data-price", product.price);
        article.setAttribute("data-thumbnail", product.thumbnail);
        article.setAttribute("data-description", product.description);
        article.setAttribute("data-category", product.category_id);
        article.setAttribute("data-category-name", product.category_name);

        article.innerHTML = `
            <div class="yt-thumbnail-wrapper">
                <img src="${product.thumbnail}" alt="${product.title}" loading="lazy" decoding="async" width="480" height="270" onerror="this.src='https://placehold.co/480x270/161616/ffffff?text=MONO.DROP'">
                <span class="yt-price-badge">${product.price} ₴</span>
            </div>
            <div class="yt-info">
                <div class="yt-avatar">${product.icon || "📦"}</div>
                <div class="yt-meta">
                    <h3 class="yt-title">${product.title}</h3>
                    <p class="yt-subtitle">${product.category_name} • ${product.badge}</p>
                </div>
            </div>
        `;

        return article;
    }

    if (addProductForm) {
        addProductForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const pin = document.getElementById("adminPin")?.value.trim() || "";
            const title = document.getElementById("newProductTitle")?.value.trim() || "";
            const category_id = document.getElementById("newProductCategory")?.value || "";
            const price = document.getElementById("newProductPrice")?.value || "";
            const badge = document.getElementById("newProductBadge")?.value.trim() || "";
            const thumbnail = document.getElementById("newProductThumbnail")?.value.trim() || "";
            const description = document.getElementById("newProductDescription")?.value.trim() || "";
            const specs_raw = document.getElementById("productSpecsInput")?.value.trim() || "";

            if (!pin || !title || !category_id || !price || !description) {
                alert("Будь ласка, заповніть усі обов'язкові поля, включаючи PIN-код!");
                return;
            }

            if (submitAddProductBtn) {
                submitAddProductBtn.disabled = true;
                submitAddProductBtn.textContent = "Публікація...";
            }

            try {
                const response = await fetch("/api/products/add", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        pin,
                        title,
                        category_id,
                        price: Number(price),
                        badge,
                        thumbnail,
                        description,
                        specs_raw
                    })
                });

                const data = await response.json();

                if (response.ok && data.status === "success" && data.product) {
                    addProductForm.reset();
                    closeModal(addProductModal);

                    if (Array.isArray(window.PRODUCTS_DATA)) {
                        window.PRODUCTS_DATA.unshift(data.product);
                    }

                    if (productsGrid) {
                        const newCard = createCardElement(data.product);
                        productsGrid.prepend(newCard);
                    }

                    resetAllFilters();
                } else {
                    alert(data.message || "Помилка при додаванні товару.");
                }
            } catch (err) {
                console.error("Помилка відправки форми товару:", err);
                alert("Не вдалося додати товар. Перевірте зв'язок із сервером.");
            } finally {
                if (submitAddProductBtn) {
                    submitAddProductBtn.disabled = false;
                    submitAddProductBtn.textContent = "ОПУБЛІКУВАТИ ТОВАР";
                }
            }
        });
    }

    // =========================================================================
    // 5. Повноцінне модальне вікно товару в стилі OLX (#productDetailsModal)
    // =========================================================================
    const productDetailsModal = document.getElementById("productDetailsModal");
    const olxProductImg = document.getElementById("olxProductImg");
    const olxCategoryBadge = document.getElementById("olxCategoryBadge");
    const olxSpecsSection = document.getElementById("olxSpecsSection");
    const olxSpecsTags = document.getElementById("olxSpecsTags");
    const olxDescription = document.getElementById("olxDescription");
    const olxProductIdLabel = document.getElementById("olxProductIdLabel");
    const olxViewsLabel = document.getElementById("olxViewsLabel");

    const olxCondition = document.getElementById("olxCondition");
    const olxTitle = document.getElementById("olxTitle");
    const olxPrice = document.getElementById("olxPrice");
    const showCheckoutFormBtn = document.getElementById("showCheckoutFormBtn");

    const olxCheckoutForm = document.getElementById("olxCheckoutForm");
    const olxOrderForm = document.getElementById("olxOrderForm");
    const olxOrderSuccess = document.getElementById("olxOrderSuccess");
    const olxSubmitOrder = document.getElementById("olxSubmitOrder");

    const olxHiddenId = document.getElementById("olxHiddenId");
    const olxHiddenTitle = document.getElementById("olxHiddenTitle");
    const olxHiddenPrice = document.getElementById("olxHiddenPrice");

    let olxCloseTimer = null;

    function openProductDetailsModal(productId, cardEl) {
        if (!productDetailsModal) return;

        if (olxCloseTimer) {
            clearTimeout(olxCloseTimer);
            olxCloseTimer = null;
        }

        const productsList = Array.isArray(window.PRODUCTS_DATA) ? window.PRODUCTS_DATA : [];
        let product = productsList.find(p => String(p.id) === String(productId));

        if (!product && cardEl) {
            product = {
                id: cardEl.getAttribute("data-id") || productId,
                title: cardEl.getAttribute("data-title") || "",
                price: Number(cardEl.getAttribute("data-price") || 0),
                thumbnail: cardEl.getAttribute("data-thumbnail") || "",
                description: cardEl.getAttribute("data-description") || "",
                category_name: cardEl.getAttribute("data-category-name") || "Товар",
                badge: "В наявності",
                condition: "Новий",
                specs: {}
            };
        }

        if (!product) return;

        // Фото та категорія: для локальних SVG (/static/img/...) підставляємо без змін, для Unsplash підвищуємо роздільну здатність
        if (olxProductImg) {
            let modalThumbnail = product.thumbnail || "/static/img/products/powerbank_65w.svg";
            if (modalThumbnail.includes("w=480")) {
                modalThumbnail = modalThumbnail.replace(/w=480/g, "w=750").replace(/q=60/g, "q=75");
            }
            olxProductImg.src = modalThumbnail;
            olxProductImg.alt = product.title || "Товар";
        }

        if (olxCategoryBadge) {
            const icon = product.icon || "";
            const catName = product.category_name || "";
            olxCategoryBadge.textContent = `${icon} ${catName}`.trim() || (product.badge || "В наявності");
        }

        // Характеристики (specs)
        if (olxSpecsSection && olxSpecsTags) {
            olxSpecsTags.innerHTML = "";
            const specs = product.specs || {};
            const specKeys = Object.keys(specs);

            if (specKeys.length === 0 && !product.condition) {
                olxSpecsSection.style.display = "none";
            } else {
                olxSpecsSection.style.display = "block";

                if (product.condition) {
                    const condPill = document.createElement("span");
                    condPill.className = "spec-pill";
                    condPill.innerHTML = `<span class="spec-key">Стан:</span> <span class="spec-val">${product.condition}</span>`;
                    olxSpecsTags.appendChild(condPill);
                }

                specKeys.forEach(k => {
                    const pill = document.createElement("span");
                    pill.className = "spec-pill";
                    pill.innerHTML = `<span class="spec-key">${k}:</span> <span class="spec-val">${specs[k]}</span>`;
                    olxSpecsTags.appendChild(pill);
                });
            }
        }

        // Опис товару
        if (olxDescription) {
            olxDescription.textContent = product.description || "Опис товару уточнюйте у продавця.";
        }

        // ID товару та перегляди
        if (olxProductIdLabel) {
            olxProductIdLabel.textContent = `ID товару: #${product.id}`;
        }
        if (olxViewsLabel) {
            const randomViews = Math.floor(Math.random() * (90 - 15 + 1)) + 15;
            olxViewsLabel.textContent = `👁 Переглядів сьогодні: ${randomViews}`;
        }

        // Права колонка
        if (olxCondition) {
            olxCondition.textContent = product.condition ? `${product.condition} • В наявності` : "В наявності";
        }
        if (olxTitle) {
            olxTitle.textContent = product.title || "";
        }
        if (olxPrice) {
            const priceNum = Number(product.price) || 0;
            olxPrice.textContent = `${priceNum.toLocaleString("uk-UA")} ₴`;
        }

        // Приховані поля форми замовлення
        if (olxHiddenId) olxHiddenId.value = product.id;
        if (olxHiddenTitle) olxHiddenTitle.value = product.title;
        if (olxHiddenPrice) olxHiddenPrice.value = product.price;

        // Оновлення динамічного посилання кнопки "Написати продавцю в Telegram"
        const sellerTgBtn = document.getElementById("olxSellerTgBtn") || document.querySelector(".olx-tg-btn");
        if (sellerTgBtn) {
            const productTitle = product.title || "Товар MONO.DROP";
            const productPrice = Number(product.price || 0).toLocaleString("uk-UA") + " грн";
            const prefilledText = encodeURIComponent(`Привіт! Мене цікавить товар: ${productTitle} (${productPrice})`);
            sellerTgBtn.href = `https://t.me/maxpro13tv2?text=${prefilledText}`;
        }

        // Скидання форми замовлення
        if (olxCheckoutForm) olxCheckoutForm.style.display = "none";
        if (olxOrderSuccess) olxOrderSuccess.style.display = "none";
        if (olxOrderForm) olxOrderForm.reset();

        if (showCheckoutFormBtn) {
            showCheckoutFormBtn.style.display = "block";
            showCheckoutFormBtn.textContent = "КУПИТИ З ДОСТАВКОЮ";
        }

        if (olxSubmitOrder) {
            olxSubmitOrder.disabled = false;
            olxSubmitOrder.textContent = "ПІДТВЕРДИТИ ЗАМОВЛЕННЯ";
        }

        openModal(productDetailsModal);
    }

    // Кнопка КУПИТИ З ДОСТАВКОЮ — розгортає компактну форму
    if (showCheckoutFormBtn && olxCheckoutForm) {
        showCheckoutFormBtn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            const isHidden = (olxCheckoutForm.style.display === "none" || !olxCheckoutForm.style.display);
            olxCheckoutForm.style.display = isHidden ? "block" : "none";
            if (isHidden) {
                showCheckoutFormBtn.textContent = "ЗГОРНУТИ ФОРМУ";
                const clientNameInput = document.getElementById("olxClientName");
                if (clientNameInput) clientNameInput.focus();
            } else {
                showCheckoutFormBtn.textContent = "КУПИТИ З ДОСТАВКОЮ";
            }
        });
    }

    // Безпечне екранування символів для Telegram HTML
    function escapeTgHtml(val) {
        if (val === null || val === undefined) return "";
        return String(val)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    // Відправка замовлення з форми: ОСНОВНИЙ запит напряму до Telegram Bot API
    if (olxOrderForm) {
        olxOrderForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const name = document.getElementById("olxClientName")?.value.trim() || "";
            const phone = document.getElementById("olxClientPhone")?.value.trim() || "";
            const telegram = document.getElementById("olxClientTelegram")?.value.trim() || "";
            const delivery = document.getElementById("olxClientDelivery")?.value.trim() || "";
            const payment_method = document.getElementById("olxPaymentMethod")?.value.trim() || "Накладений платіж";
            const comment = document.getElementById("olxClientComment")?.value.trim() || "";

            if (!name || !phone || !delivery) {
                alert("Будь ласка, заповніть обов'язкові поля: Ім'я, Номер телефону та Відділення доставки.");
                return;
            }

            const productId = olxHiddenId ? olxHiddenId.value : "";
            const productTitle = olxHiddenTitle?.value || olxTitle?.textContent || "Товар MONO.DROP";
            const productPrice = olxHiddenPrice?.value ? `${Number(olxHiddenPrice.value).toLocaleString('uk-UA')} грн` : (olxPrice?.textContent || "—");

            if (olxSubmitOrder) {
                olxSubmitOrder.disabled = true;
                olxSubmitOrder.textContent = "Відправка замовлення...";
            }

            // Формуємо повне структуроване HTML-повідомлення для Telegram
            const lines = [
                "📦 <b>НОВЕ ЗАМОВЛЕННЯ — MONO.DROP</b>",
                "━━━━━━━━━━━━━━━",
                `🛒 <b>Товар:</b> ${escapeTgHtml(productTitle)}${productId ? ` (ID: #${escapeTgHtml(productId)})` : ""}`,
                `💰 <b>Ціна:</b> ${escapeTgHtml(productPrice)}`,
                "━━━━━━━━━━━━━━━",
                `👤 <b>Ім'я та Прізвище:</b> ${escapeTgHtml(name)}`,
                `📞 <b>Телефон:</b> ${escapeTgHtml(phone)}`
            ];

            if (telegram) {
                lines.push(`✈️ <b>Telegram:</b> ${escapeTgHtml(telegram)}`);
            }

            lines.push(`🏙 <b>Місто / Доставка:</b> ${escapeTgHtml(delivery)}`);

            if (payment_method) {
                lines.push(`💳 <b>Оплата:</b> ${escapeTgHtml(payment_method)}`);
            }

            if (comment) {
                lines.push(`💬 <b>Коментар:</b> ${escapeTgHtml(comment)}`);
            }

            const orderTime = new Date().toLocaleString("uk-UA", { timeZone: "Europe/Kyiv" });
            lines.push(`🕒 <b>Час:</b> ${escapeTgHtml(orderTime)}`);

            // Зчитуємо всі інші можливі поля форми, щоб жодні дані не загубилися
            try {
                const formData = new FormData(olxOrderForm);
                const knownFields = new Set(["product_id", "product_title", "product_price", "name", "phone", "telegram", "delivery", "payment_method", "comment"]);
                const extraLines = [];
                for (const [k, v] of formData.entries()) {
                    if (!knownFields.has(k) && v && String(v).trim()) {
                        extraLines.push(`<b>${escapeTgHtml(k)}:</b> ${escapeTgHtml(String(v).trim())}`);
                    }
                }
                if (extraLines.length > 0) {
                    lines.push("━━━━━━━━━━━━━━━");
                    lines.push(...extraLines);
                }
            } catch (_) {}

            const messageText = lines.join("\n");

            const TG_BOT_TOKEN = "9159142714:AAE2L2ZICSLX4GdXIV_3DnSlYISYZ0SWBI8";
            const TG_CHAT_ID = "8737480622";
            const tgApiUrl = `https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage`;

            const payload = {
                product_id: productId,
                product_title: productTitle,
                product_price: olxHiddenPrice ? Number(olxHiddenPrice.value) : 0,
                name: name,
                phone: phone,
                telegram: telegram,
                delivery: delivery,
                payment_method: payment_method,
                comment: comment
            };

            let isSuccess = false;

            // 1. ОСНОВНА ДІЯ: прямий запит із браузера клієнта до Telegram Bot API
            try {
                const tgResponse = await fetch(tgApiUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        chat_id: TG_CHAT_ID,
                        parse_mode: "HTML",
                        text: messageText
                    })
                });

                const tgResult = await tgResponse.json();
                if (tgResponse.ok && tgResult.ok) {
                    isSuccess = true;
                } else {
                    console.warn("[Telegram Direct] Telegram API відповів:", tgResult);
                }
            } catch (tgError) {
                console.warn("[Telegram Direct] Помилка прямого виклику Telegram API:", tgError);
            }

            // 2. Фоновий виклик /api/order для бекапу (тихий, ніколи не ламає клієнт)
            fetch("/api/order", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(res => {
                if (res && res.status === "success") isSuccess = true;
            }).catch(() => {});

            if (isSuccess) {
                if (olxCheckoutForm) olxCheckoutForm.style.display = "none";
                if (showCheckoutFormBtn) showCheckoutFormBtn.style.display = "none";
                if (olxOrderSuccess) olxOrderSuccess.style.display = "block";
                if (olxOrderForm) olxOrderForm.reset();

                olxCloseTimer = setTimeout(() => {
                    closeModal(productDetailsModal);
                }, 2500);
            } else {
                // Якщо прямий запит був заблокований, робимо резервну спробу через бекенд
                try {
                    const fallbackResponse = await fetch("/api/order", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });
                    const fallbackResult = await fallbackResponse.json();
                    if (fallbackResponse.ok && fallbackResult.status === "success") {
                        if (olxCheckoutForm) olxCheckoutForm.style.display = "none";
                        if (showCheckoutFormBtn) showCheckoutFormBtn.style.display = "none";
                        if (olxOrderSuccess) olxOrderSuccess.style.display = "block";
                        if (olxOrderForm) olxOrderForm.reset();
                        olxCloseTimer = setTimeout(() => {
                            closeModal(productDetailsModal);
                        }, 2500);
                        return;
                    }
                } catch (_) {}

                // Якщо навіть резервна спроба не вдалась — дружньо пропонуємо перейти в Telegram
                alert("Замовлення не вдалося відправити автоматично. Будь ласка, зв'яжіться з продавцем напряму через кнопку 'Написати продавцю в Telegram'.");
            }

            if (olxSubmitOrder) {
                olxSubmitOrder.disabled = false;
                olxSubmitOrder.textContent = "ПІДТВЕРДИТИ ЗАМОВЛЕННЯ";
            }
        });
    }

    // =========================================================================
    // 6. НАДІЙНЕ ДЕЛЕГУВАННЯ КЛІКІВ (Event Delegation)
    // =========================================================================
    document.addEventListener("click", (e) => {
        // 1. Відкриття лівого меню: клік на #sidebarToggle
        const toggleBtn = e.target.closest("#sidebarToggle");
        if (toggleBtn) {
            e.preventDefault();
            e.stopPropagation();
            openSidebar();
            return;
        }

        // 2. Закриття лівого меню: клік на #closeSidebarBtn або #sidebarOverlay / #sidebarBackdrop
        if (
            e.target.closest("#closeSidebarBtn") ||
            e.target.closest("#sidebarOverlay") ||
            e.target.closest("#sidebarBackdrop")
        ) {
            e.preventDefault();
            closeSidebar();
            return;
        }

        // 3. Клік на «+ Додати роботу» виключно в лівому сайдбарі (#openAddProductBtn)
        const addBtn = e.target.closest("#openAddProductBtn");
        if (addBtn) {
            e.preventDefault();
            closeSidebar();
            openModal(addProductModal);
            setTimeout(() => {
                const firstInput = document.getElementById("adminPin") || document.getElementById("newProductTitle");
                if (firstInput) firstInput.focus();
            }, 150);
            return;
        }

        // 4. Клік по пунктах меню сайдбару (.sidebar-nav-item)
        const navItem = e.target.closest(".sidebar-nav-item");
        if (navItem) {
            e.preventDefault();
            const action = navItem.getAttribute("data-action");
            closeSidebar();
            if (action === "home") {
                resetAllFilters();
                window.scrollTo({ top: 0, behavior: "smooth" });
            } else if (INFO_CONTENT[action]) {
                openInfoModal(action);
            }
            return;
        }

        // 5. Закриття будь-якої модалки по кнопці закриття (.close-btn або .modal-close-btn)
        if (e.target.closest(".close-btn") || e.target.closest(".modal-close-btn")) {
            e.preventDefault();
            closeAllModals();
            return;
        }

        // 6. Закриття модалки при кліку на темний фон поза діалоговим вікном
        if (
            e.target.classList.contains("modal-backdrop") ||
            e.target.classList.contains("modal-overlay") ||
            e.target.id === "productDetailsModal" ||
            e.target.id === "addProductModal" ||
            e.target.id === "infoModal"
        ) {
            closeAllModals();
            return;
        }

        // 7. Клік на будь-яку картку товару (.yt-card)
        const cardEl = e.target.closest(".yt-card");
        if (cardEl) {
            const productId = cardEl.getAttribute("data-id");
            openProductDetailsModal(productId, cardEl);
            return;
        }
    });

    // =========================================================================
    // 7. Універсальна обробка гарячих клавіш (Escape, Ctrl + K)
    // =========================================================================
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeAllModals();
            closeSidebar();
        }

        if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K" || e.key === "л" || e.key === "Л")) {
            e.preventDefault();
            if (searchInput) {
                searchInput.scrollIntoView({ behavior: "smooth", block: "center" });
                searchInput.focus();
            }
        }
    });

    // Початкова фільтрація
    applyFilters();
});
