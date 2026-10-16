/**
 * MugiManager - Frontend Controller
 * Planificador de viajes, red de transporte, avisos y tarjeta MUGI.
 * Proyecto independiente, no oficial.
 */

// URL del backend (vacía = mismo servidor). La define js/config.js.
const API_BASE = (window.MUGI_CONFIG && window.MUGI_CONFIG.apiBase) || "";

// Global State
let currentUser = null; // { token, email, full_name, card }
let currentCardNumber = null;
let currentCardData = null;
let allStopsList = [];
let allLinesList = [];
let currentFilterOperator = "";
let currentFilterMode = "";

document.addEventListener("DOMContentLoaded", () => {
    if ("serviceWorker" in navigator && location.protocol === "https:") {
        navigator.serviceWorker.register("sw.js").catch(e => console.warn("Service worker:", e));
    }
    initTabs();
    initAuthAndCard();
    restoreOrInitSession();
    loadLines();
    loadStopsCatalog();
    loadIncidents("all");
    loadScrapedData();
    initScrapingEvents();
    initPlannerEvents();
    initMLEvents();
    runCustomMLAnalysis();
});

// --- AUTENTICACIÓN (CORREO ELECTRÓNICO Y CONTRASEÑA) ---
function initAuthAndCard() {
    renderHeaderAuth();

    // Tab buttons in modal
    document.querySelectorAll(".auth-tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-auth-tab");
            switchAuthTab(target);
        });
    });

    // Login submit button
    document.getElementById("btn-submit-login")?.addEventListener("click", () => {
        const email = document.getElementById("input-login-email").value;
        const pass = document.getElementById("input-login-password").value;
        handleLogin(email, pass);
    });

    // Enter key in login inputs
    document.getElementById("input-login-password")?.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            const email = document.getElementById("input-login-email").value;
            const pass = document.getElementById("input-login-password").value;
            handleLogin(email, pass);
        }
    });

    // Register submit button
    document.getElementById("btn-submit-register")?.addEventListener("click", handleRegister);

    // Open auth modal buttons (cabecera y aviso de Mi Tarjeta)
    document.getElementById("btn-open-auth-modal")?.addEventListener("click", () => {
        switchAuthTab("auth-login-pane");
        openModal("modal-auth");
    });
    document.getElementById("btn-gate-login")?.addEventListener("click", () => {
        switchAuthTab("auth-login-pane");
        openModal("modal-auth");
    });
    document.getElementById("btn-gate-register")?.addEventListener("click", () => {
        switchAuthTab("auth-register-pane");
        openModal("modal-auth");
    });

    // Card inputs with auto-formatting in 3-3-3-1 MUGI format (XXX XXX XXX X)
    ["input-card-search", "input-adjust-card-num", "input-reg-card"].forEach(id => {
        const inputEl = document.getElementById(id);
        if (inputEl) {
            inputEl.addEventListener("input", (e) => {
                const raw = e.target.value.replace(/\D/g, "").slice(0, 10);
                if (raw.length > 0) {
                    let formatted = "";
                    for (let i = 0; i < raw.length; i++) {
                        if (i === 3 || i === 6 || i === 9) formatted += " ";
                        formatted += raw[i];
                    }
                    e.target.value = formatted;
                }
            });
        }
    });

    // Flip card button (Anverso / Reverso)
    document.getElementById("btn-flip-card")?.addEventListener("click", () => {
        const flipEl = document.getElementById("mugi-card-flip");
        if (flipEl) flipEl.classList.toggle("is-flipped");
    });

    // Simulate trip modal
    document.getElementById("btn-open-simulate")?.addEventListener("click", () => openModal("modal-simulate"));
    document.getElementById("btn-confirm-simulate")?.addEventListener("click", handleSimulateTrip);
}

function switchAuthTab(targetPaneId) {
    document.querySelectorAll(".auth-tab-btn").forEach(b => {
        b.classList.toggle("active", b.getAttribute("data-auth-tab") === targetPaneId);
    });
    document.querySelectorAll(".auth-sub-pane").forEach(p => {
        p.style.display = (p.id === targetPaneId) ? "block" : "none";
    });
}

function renderHeaderAuth() {
    updateCardAccess();
    const box = document.getElementById("header-auth-box");
    const indicator = document.getElementById("user-session-indicator");
    if (!box) return;

    if (currentUser) {
        const rawName = (currentUser.full_name || currentUser.email || "Usuario").trim();
        const parts = rawName.split(/\s+/);
        const initials = parts.length >= 2 
            ? (parts[0][0] + parts[1][0]).toUpperCase() 
            : rawName.slice(0, 2).toUpperCase();
        const shortName = parts.length >= 2 ? `${parts[0]} ${parts[1]}` : parts[0];

        box.innerHTML = `
            <div class="header-user-capsule" title="${rawName} (${currentUser.email})">
                <div class="header-avatar">${initials}</div>
                <span class="header-user-name">${shortName}</span>
                <button id="btn-header-logout" class="header-logout-btn" title="Cerrar Sesión">
                    <svg class="svg-icon" style="width: 0.85em; height: 0.85em;"><use href="#icon-close"></use></svg>
                    <span>Salir</span>
                </button>
            </div>
        `;
        if (indicator) {
            indicator.innerHTML = `
                <span style="color: var(--mugi-green); font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
                    <svg class="svg-icon" style="width: 0.9em; height: 0.9em;"><use href="#icon-check"></use></svg>
                    <span>Sesión activa:</span>
                </span>
                <span style="font-weight: 600;">${currentUser.email}</span>
            `;
        }
        document.getElementById("btn-header-logout")?.addEventListener("click", handleLogout);
    } else {
        box.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <button id="btn-header-login" class="header-login-btn">
                    <svg class="svg-icon" style="width: 0.9em; height: 0.9em;"><use href="#icon-lock"></use></svg>
                    <span>Acceder</span>
                </button>
                <button id="btn-header-register" class="header-reg-btn">
                    <span>Registro</span>
                </button>
            </div>
        `;
        if (indicator) {
            indicator.innerHTML = `
                <span style="color: #64748b;">(Sin iniciar sesión)</span>
            `;
        }
        document.getElementById("btn-header-login")?.addEventListener("click", () => {
            switchAuthTab("auth-login-pane");
            openModal("modal-auth");
        });
        document.getElementById("btn-header-register")?.addEventListener("click", () => {
            switchAuthTab("auth-register-pane");
            openModal("modal-auth");
        });
    }
}

async function handleLogin(email, password) {
    const cleanEmail = (email || "").trim();
    const cleanPass = (password || "").trim();
    const errAlert = document.getElementById("login-error-alert");
    if (errAlert) {
        errAlert.style.display = "none";
        errAlert.innerHTML = "";
    }

    if (!cleanEmail || !cleanPass) {
        if (errAlert) {
            errAlert.innerHTML = "Por favor introduce tu correo electrónico y tu contraseña.";
            errAlert.style.display = "block";
        } else {
            alert("Por favor introduce tu correo electrónico y tu contraseña.");
        }
        return;
    }

    const submitBtn = document.getElementById("btn-submit-login");
    const originalText = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <svg class="svg-icon" style="animation: spin 1s infinite;"><use href="#icon-refresh"></use></svg>
            <span>Conectando con Gune Pribatua MUGI...</span>
        `;
    }

    try {
        const res = await fetch(API_BASE + "/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: cleanEmail, password: cleanPass })
        });
        const data = await res.json();
        if (!res.ok) {
            const errorMsg = data.detail || "Correo o contraseña no válidos en el portal de MUGI.";
            if (errAlert) {
                errAlert.innerHTML = `
                    <div style="display: flex; gap: 8px; align-items: flex-start;">
                        <svg class="svg-icon" style="color: #dc2626; flex-shrink: 0; margin-top: 2px;"><use href="#icon-close"></use></svg>
                        <div>
                            <strong>No se pudo acceder:</strong><br>${errorMsg}
                        </div>
                    </div>
                `;
                errAlert.style.display = "block";
            } else {
                alert(errorMsg);
            }
            return;
        }

        currentUser = data;
        localStorage.setItem("mugimanager_auth_token", data.token);
        localStorage.setItem("mugimanager_user_email", data.email);
        renderHeaderAuth();

        if (data.card) {
            currentCardNumber = data.card.card_number;
            currentCardData = data.card;
            renderCardDetails(data.card);
        }

        closeModal("modal-auth");
        alert(`¡Bienvenido/a, ${data.full_name}!\nSesión iniciada.\nSaldo disponible: ${data.card ? data.card.balance.toFixed(2) : 0.00}€`);
    } catch (e) {
        console.error(e);
        if (errAlert) {
            errAlert.innerHTML = "Error de red al conectar con el servidor local o el portal de MUGI.";
            errAlert.style.display = "block";
        } else {
            alert("Error de conexión al iniciar sesión.");
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
}

async function handleRegister() {
    const email = document.getElementById("input-reg-email").value.trim();
    const password = document.getElementById("input-reg-pass").value.trim();
    const fullName = document.getElementById("input-reg-name").value.trim();
    const cardNumber = document.getElementById("input-reg-card").value.trim();
    const balance = parseFloat(document.getElementById("input-reg-balance").value);
    const trips = parseInt(document.getElementById("input-reg-trips").value) || 0;
    const cardType = document.getElementById("select-reg-type").value;

    if (!email || !email.includes("@")) {
        alert("Por favor introduce una dirección de correo electrónico válida.");
        return;
    }
    if (!password || password.length < 4) {
        alert("La contraseña debe tener al menos 4 caracteres.");
        return;
    }
    if (!cardNumber || cardNumber.length < 4) {
        alert("Introduce el número de tu tarjeta MUGI.");
        return;
    }
    if (isNaN(balance) || balance < 0) {
        alert("Introduce tu saldo real actual en euros (ej: 4.50).");
        return;
    }

    try {
        const res = await fetch(API_BASE + "/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: email,
                password: password,
                full_name: fullName,
                card_number: cardNumber,
                initial_balance: balance,
                monthly_trips: trips,
                card_type: cardType
            })
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Error al registrar la cuenta.");
            return;
        }

        currentUser = data;
        localStorage.setItem("mugimanager_auth_token", data.token);
        localStorage.setItem("mugimanager_user_email", data.email);
        renderHeaderAuth();

        if (data.card) {
            currentCardNumber = data.card.card_number;
            currentCardData = data.card;
            renderCardDetails(data.card);
        }

        closeModal("modal-auth");
        alert(`¡Cuenta MUGI creada con éxito!\nCorreo: ${data.email}\nTarjeta vinculada: ${data.card.card_number}\nSaldo real exacto: ${data.card.balance.toFixed(2)}€`);
    } catch (e) {
        console.error(e);
        alert("Error al conectar con el servidor para registrar la cuenta.");
    }
}

async function handleLogout() {
    const token = localStorage.getItem("mugimanager_auth_token");
    if (token) {
        try {
            await fetch(`${API_BASE}/api/auth/logout?token=${token}`, { method: "POST" });
        } catch (e) {
            console.error(e);
        }
    }
    localStorage.removeItem("mugimanager_auth_token");
    localStorage.removeItem("mugimanager_user_email");
    currentUser = null;
    currentCardData = null;
    currentCardNumber = null;
    renderHeaderAuth();
    alert("Has cerrado sesión. Puedes volver a iniciar sesión con tu correo y contraseña.");
}

async function restoreOrInitSession() {
    // Limpia restos de versiones anteriores que guardaban la tarjeta sin sesión
    try {
        localStorage.removeItem("mugimanager_saved_card");
        localStorage.removeItem("mugimanager_card_number");
    } catch (e) {}

    const token = localStorage.getItem("mugimanager_auth_token");
    if (token) {
        try {
            const res = await fetch(`${API_BASE}/api/auth/me?token=${encodeURIComponent(token)}`);
            if (res.ok) {
                const data = await res.json();
                currentUser = data;
                if (data.card) {
                    currentCardNumber = data.card.card_number;
                    currentCardData = data.card;
                    renderCardDetails(data.card);
                }
            } else {
                localStorage.removeItem("mugimanager_auth_token");
                localStorage.removeItem("mugimanager_user_email");
            }
        } catch (e) {
            console.error("Session restore error:", e);
        }
    }
    renderHeaderAuth();
}

function authQuery() {
    const token = localStorage.getItem("mugimanager_auth_token") || "";
    return `?token=${encodeURIComponent(token)}`;
}

// Muestra la tarjeta solo con sesión iniciada; si no, el aviso para entrar
function updateCardAccess() {
    const gate = document.getElementById("card-login-gate");
    const area = document.getElementById("card-area");
    const hasCard = Boolean(currentUser && currentCardData);
    if (gate) gate.style.display = hasCard ? "none" : "block";
    if (area) area.style.display = hasCard ? "block" : "none";
}

async function loadMugiCard(cardNumber) {
    const loadingElem = document.getElementById("mugi-loading");
    if (loadingElem) loadingElem.style.display = "block";

    const cleanNum = (cardNumber || "").replace(/\D/g, "").trim();
    if (!cleanNum) {
        alert("Por favor escribe el número de tu tarjeta MUGI (10 dígitos).");
        if (loadingElem) loadingElem.style.display = "none";
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/mugi/card/${cleanNum}${authQuery()}`);
        const data = await res.json();

        currentCardNumber = data.card_number;
        currentCardData = data;
        if (!res.ok) {
            alert(data.detail || "No se pudo cargar la tarjeta.");
            return;
        }
        renderCardDetails(data);

        // If card has 0 balance or is new, invite user to calibrate real balance
        if (data.balance === 0.0) {
            const promptBal = prompt(`Tarjeta MUGI ${formatMugiCardNumber(cleanNum)} cargada.\nIntroduce tu saldo real actual en euros (ej: 14.50):`, "10.00");
            if (promptBal !== null) {
                const balFloat = parseFloat(promptBal.replace(",", "."));
                if (!isNaN(balFloat) && balFloat >= 0) {
                    await calibrateAndSaveCard(cleanNum, balFloat);
                }
            }
        }
    } catch (e) {
        console.error("Error loading card:", e);
    } finally {
        if (loadingElem) loadingElem.style.display = "none";
    }
}

async function handleQuickSaveBalance() {
    const inp = document.getElementById("quick-input-balance");
    if (!inp) return;
    const val = parseFloat(inp.value.replace(",", "."));
    if (isNaN(val) || val < 0) {
        alert("Por favor introduce un saldo válido en euros (ej: 14.50).");
        return;
    }

    const cardNum = currentCardNumber || (currentCardData ? currentCardData.card_number : null);
    if (!cardNum) return;
    await calibrateAndSaveCard(cardNum, val);
}

async function calibrateAndSaveCard(cardNumber, balance) {
    const cleanNum = cardNumber.replace(/\D/g, "").trim();
    const btn = document.getElementById("btn-quick-save-balance");
    const origHtml = btn ? btn.innerHTML : "";
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span>Guardando...</span>`;
    }

    try {
        const res = await fetch(`${API_BASE}/api/mugi/card/calibrate${authQuery()}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                card_number: cleanNum,
                balance: balance,
                holder_name: currentCardData ? currentCardData.holder_name : "Titular MUGI",
                monthly_trips: currentCardData ? currentCardData.monthly_trips : 0,
                card_type: currentCardData ? currentCardData.card_type : "MUGI Ordinaria (Arrunta)"
            })
        });
        const data = await res.json();
        if (res.ok && data.card) {
            currentCardData = data.card;
            currentCardNumber = data.card.card_number;
            renderCardDetails(data.card);
            alert(`¡Saldo real calibrado con éxito!\nTu tarjeta MUGI ${formatMugiCardNumber(cleanNum)} ahora tiene: ${data.card.balance.toFixed(2)}€`);
        } else {
            alert(data.detail || "Error al calibrar saldo.");
        }
    } catch (e) {
        console.error(e);
        alert("Error de conexión al actualizar el saldo de la tarjeta.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}

function openAdjustModal() {
    const cardNumInput = document.getElementById("input-adjust-card-num");
    const holderInput = document.getElementById("input-adjust-holder-name");
    const typeSelect = document.getElementById("select-adjust-card-type");
    const balanceInput = document.getElementById("input-adjust-balance-val");
    const tripsInput = document.getElementById("input-adjust-trips-val");

    if (currentCardData) {
        if (cardNumInput) cardNumInput.value = formatMugiCardNumber(currentCardData.card_number);
        if (holderInput) holderInput.value = currentCardData.holder_name || "Titular MUGI";
        if (typeSelect && currentCardData.card_type) typeSelect.value = currentCardData.card_type;
        if (balanceInput) balanceInput.value = currentCardData.balance.toFixed(2);
        if (tripsInput) tripsInput.value = currentCardData.monthly_trips || 0;
    } else {
        if (cardNumInput) cardNumInput.value = "";
        if (holderInput) holderInput.value = "";
        if (balanceInput) balanceInput.value = "";
        if (tripsInput) tripsInput.value = "0";
    }
    openModal("modal-adjust-balance");
}

async function submitAdjustBalance() {
    const cardNumRaw = document.getElementById("input-adjust-card-num")?.value || "";
    const holderName = document.getElementById("input-adjust-holder-name")?.value.trim() || "Titular MUGI";
    const cardType = document.getElementById("select-adjust-card-type")?.value || "MUGI Ordinaria (Arrunta)";
    const balance = parseFloat(document.getElementById("input-adjust-balance-val").value);
    const trips = parseInt(document.getElementById("input-adjust-trips-val").value) || 0;

    const cleanNum = cardNumRaw.replace(/\D/g, "") || currentCardNumber;
    if (!cleanNum) return;

    if (isNaN(balance) || balance < 0) {
        alert("Por favor introduce un saldo válido en euros.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/mugi/card/calibrate${authQuery()}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                card_number: cleanNum,
                balance: balance,
                monthly_trips: trips,
                holder_name: holderName,
                card_type: cardType
            })
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Error al actualizar saldo.");
            return;
        }

        currentCardData = data.card;
        currentCardNumber = data.card.card_number;
        closeModal("modal-adjust-balance");
        renderCardDetails(currentCardData);
        alert(`¡Datos y saldo real de tarjeta MUGI actualizados con éxito!\nNúmero: ${formatMugiCardNumber(cleanNum)}\nTitular: ${holderName}\nSaldo exacto: ${currentCardData.balance.toFixed(2)}€`);
    } catch (e) {
        console.error(e);
        alert("Error al actualizar datos de la tarjeta.");
    }
}

const USER_SILHOUETTE_SVG = `
  <svg viewBox="0 0 74 94" width="74" height="94" style="display: block;">
    <defs>
      <linearGradient id="userAvatarBg" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#ffffff"/>
        <stop offset="100%" stop-color="#f1f5f9"/>
      </linearGradient>
      <linearGradient id="userAvatarBody" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#94a3b8"/>
        <stop offset="100%" stop-color="#64748b"/>
      </linearGradient>
    </defs>
    <rect width="74" height="94" fill="url(#userAvatarBg)"/>
    <rect x="2.5" y="2.5" width="69" height="89" rx="2" fill="none" stroke="#cbd5e1" stroke-width="0.8" stroke-dasharray="3 3"/>
    <circle cx="37" cy="36" r="14" fill="url(#userAvatarBody)"/>
    <path d="M 14,84 C 14,64 24,56 32,56 L 42,56 C 50,56 60,64 60,84 Z" fill="url(#userAvatarBody)"/>
  </svg>
`;

function renderCardDetails(card) {
    if (!card) return;
    const formattedNum = formatMugiCardNumber(card.card_number);

    // Front of official MUGI card
    const cardNumEl = document.getElementById("card-display-number");
    const barcodeNumEl = document.getElementById("card-back-barcode-num");

    // Split holder name into First Name and Surnames
    const fullName = (card.holder_name || "").trim();
    const displayNum = formattedNum;
    if (cardNumEl) cardNumEl.textContent = displayNum;
    if (barcodeNumEl) barcodeNumEl.textContent = displayNum;

    const fnEl = document.getElementById("card-display-firstname");
    const snEl = document.getElementById("card-display-surnames");

    // Toggle anonymous card style
    const frontCardEl = document.querySelector(".mugi-card-front");
    const backCardEl = document.querySelector(".mugi-card-back");
    const photoBoxEl = document.querySelector(".mugi-official-photo-box");
    const isAnon = (card.card_type || "").toLowerCase().includes("anónima") || (card.card_type || "").toLowerCase().includes("anonima");

    if (frontCardEl) frontCardEl.classList.toggle("is-anon", isAnon);
    if (backCardEl) backCardEl.classList.toggle("is-anon", isAnon);
    if (photoBoxEl) {
        photoBoxEl.style.display = isAnon ? "none" : "flex";
        if (!isAnon) {
            photoBoxEl.innerHTML = USER_SILHOUETTE_SVG;
        }
    }

    if (isAnon) {
        if (snEl) snEl.textContent = "TXARTEL ANONIMOA";
        if (fnEl) fnEl.textContent = "TARJETA ANÓNIMA";
    } else if (!fullName) {
        if (snEl) snEl.textContent = "";
        if (fnEl) fnEl.textContent = "";
    } else if (fullName.includes(",")) {
        const splitComma = fullName.split(",");
        if (snEl) snEl.textContent = splitComma[0].trim();
        if (fnEl) fnEl.textContent = splitComma.slice(1).join(" ").trim();
    } else {
        const parts = fullName.split(/\s+/);
        if (parts.length >= 3) {
            if (snEl) snEl.textContent = parts.slice(1).join(" ");
            if (fnEl) fnEl.textContent = parts[0];
        } else if (parts.length === 2) {
            if (snEl) snEl.textContent = parts[1];
            if (fnEl) fnEl.textContent = parts[0];
        } else {
            if (snEl) snEl.textContent = fullName;
            if (fnEl) fnEl.textContent = "";
        }
    }

    // Colectivo code letter (Only shown on Colectivos card, empty on Ordinaria)
    const colectivoElem = document.getElementById("card-display-colectivo");
    if (colectivoElem) {
        if (!fullName) {
            colectivoElem.textContent = "";
        } else {
            const typeStr = (card.card_type || "").toLowerCase();
            if (typeStr.includes("gaztea")) colectivoElem.textContent = "G";
            else if (typeStr.includes("berezia") || typeStr.includes("familia")) colectivoElem.textContent = "A";
            else if (typeStr.includes("jubilatua") || typeStr.includes("nagusia")) colectivoElem.textContent = "J";
            else if (typeStr.includes("colectivo")) colectivoElem.textContent = "A";
            else colectivoElem.textContent = "";
        }
    }

    const typeEl = document.getElementById("card-display-type");
    if (typeEl) typeEl.textContent = card.card_type || "MUGI Ordinaria";

    // Technical info
    if (document.getElementById("card-email-info")) {
        document.getElementById("card-email-info").textContent = card.user_email || (currentUser ? currentUser.email : "--");
    }
    if (document.getElementById("card-holder-name-info")) {
        document.getElementById("card-holder-name-info").textContent = card.holder_name || "--";
    }
    if (document.getElementById("card-expiry-info")) {
        document.getElementById("card-expiry-info").textContent = card.expiry_date || "--";
    }
    if (document.getElementById("card-last-use-info")) {
        document.getElementById("card-last-use-info").textContent = card.last_use || "--";
    }
    if (document.getElementById("card-status-info")) {
        document.getElementById("card-status-info").innerHTML = `
            <svg class="svg-icon" style="width: 1em; height: 1em; color: var(--mugi-green);"><use href="#icon-check"></use></svg>
            <span style="color: var(--mugi-green); font-weight: 700;">${card.status || "Activa"}</span>
        `;
    }
    if (document.getElementById("card-bonus-info")) {
        document.getElementById("card-bonus-info").textContent = card.bonus_percentage > 0 ? `+${card.bonus_percentage}% por colectivo` : "Estándar";
    }

    // Balance & Info Box
    const numBalance = typeof card.balance === "number" ? card.balance : parseFloat(card.balance) || 0.0;
    if (document.getElementById("card-balance-val")) {
        document.getElementById("card-balance-val").textContent = numBalance.toFixed(2);
    }
    const quickInp = document.getElementById("quick-input-balance");
    if (quickInp) {
        quickInp.value = numBalance.toFixed(2);
    }
    if (document.getElementById("card-monthly-trips")) {
        document.getElementById("card-monthly-trips").textContent = card.monthly_trips || 0;
    }

    // Tier Info
    const tier = card.tier_info;
    if (tier) {
        document.getElementById("tier-name").textContent = tier.tier_name;
        document.getElementById("tier-discount").textContent = `${tier.discount_percentage}% de descuento ATTG`;
        document.getElementById("tier-progress-fill").style.width = `${tier.progress_percentage}%`;
        
        if (tier.trips_to_next_tier > 0) {
            document.getElementById("tier-next-msg").textContent = `Faltan ${tier.trips_to_next_tier} viajes para acceder a ${tier.next_tier_name}.`;
        } else {
            document.getElementById("tier-next-msg").textContent = `¡Has alcanzado la máxima bonificación ATTG del 90%!`;
        }
    }

    // Movements Table
    renderMovementsTable(card.history || []);
    updateCardAccess();
}

function renderMovementsTable(history) {
    const tbody = document.getElementById("card-movements-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!history.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 18px;">Sin movimientos registrados este mes.</td></tr>`;
        return;
    }

    history.forEach(mov => {
        const tr = document.createElement("tr");
        const isPositive = mov.cost > 0;
        const costStr = isPositive ? `+${mov.cost.toFixed(2)}€` : `${mov.cost.toFixed(2)}€`;
        const costColor = isPositive ? "#059669" : (mov.cost === 0 ? "#0284c7" : "#1e293b");

        tr.innerHTML = `
            <td><strong>${mov.date}</strong></td>
            <td><span class="op-badge ${getOperatorClass(mov.operator)}">${mov.operator}</span></td>
            <td><strong>${mov.line}</strong> <div style="font-size: 0.78rem; color: var(--text-muted);">${mov.stop}</div></td>
            <td>${mov.type}</td>
            <td style="color: #64748b; font-size: 0.8rem;">${mov.discount_applied}</td>
            <td style="font-weight: 700; color: ${costColor};">${costStr}</td>
            <td style="font-weight: 600;">${mov.balance_after.toFixed(2)}€</td>
        `;
        tbody.appendChild(tr);
    });
}

function updateRechargeSummary(amount) {
    const bonusText = document.getElementById("recharge-bonus-calc");
    if (!bonusText) return;
    const bonusPct = currentCardData ? (currentCardData.bonus_percentage || 0) : 0;
    const extra = (amount * bonusPct / 100).toFixed(2);
    const totalCredit = (amount + parseFloat(extra)).toFixed(2);
    bonusText.innerHTML = `Total a ingresar en tarjeta: <strong>${totalCredit}€</strong> (Importe: ${amount.toFixed(2)}€ ${bonusPct > 0 ? `+ Bonificación colectiva: ${extra}€` : ''})`;
}

async function handleRecharge() {
    const amount = parseFloat(document.getElementById("input-recharge-amount").value);
    const method = document.getElementById("select-recharge-method").value;
    if (!amount || amount < 5) {
        alert("El importe mínimo de recarga es 5.00€.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/mugi/recharge${authQuery()}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                card_number: currentCardNumber,
                amount: amount,
                payment_method: method
            })
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Error en la recarga.");
            return;
        }

        closeModal("modal-recharge");
        alert(`¡Recarga efectuada con éxito!\nJustificante: ${data.transaction_id}\nNuevo saldo: ${data.new_balance.toFixed(2)}€`);
        loadMugiCard(currentCardNumber);
    } catch (e) {
        console.error(e);
        alert("Error de conexión al procesar la recarga.");
    }
}

async function handleSimulateTrip() {
    const op = document.getElementById("sim-operator").value;
    const line = document.getElementById("sim-line").value;
    const stopPair = document.getElementById("sim-stoppair").value;
    const isTransfer = document.getElementById("sim-is-transfer").checked;

    try {
        const res = await fetch(`${API_BASE}/api/mugi/simulate-trip${authQuery()}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                card_number: currentCardNumber,
                operator: op,
                line: line,
                stop_pair: stopPair,
                is_transfer: isTransfer
            })
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Error al simular viaje.");
            return;
        }

        closeModal("modal-simulate");
        const msg = isTransfer 
            ? `¡Transbordo validado con Tarifa MUGI!\nCoste: 0.00€ (Bonificación ATTG 100% activa)\nSaldo restante: ${data.new_balance.toFixed(2)}€`
            : `¡Viaje registrado!\nCoste descontado: ${data.cost.toFixed(2)}€\nTotal viajes del mes: ${data.monthly_trips}\nNuevo saldo: ${data.new_balance.toFixed(2)}€`;
        alert(msg);
        loadMugiCard(currentCardNumber);
    } catch (e) {
        console.error(e);
        alert("Error de conexión al registrar viaje.");
    }
}

// --- TABS SYSTEM ---
function initTabs() {
    const tabButtons = document.querySelectorAll(".main-nav .nav-tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");
            switchTab(targetId);
        });
    });
}

function switchTab(targetId) {
    document.querySelectorAll(".main-nav .nav-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

    const activeBtn = document.querySelector(`.main-nav .nav-tab-btn[data-tab="${targetId}"]`);
    const activePane = document.getElementById(targetId);

    if (activeBtn) activeBtn.classList.add("active");
    if (activePane) activePane.classList.add("active");

    if (targetId === "tab-ml") {
        const resultBox = document.getElementById("ml-analysis-result");
        if (!resultBox || !resultBox.innerHTML.trim() || resultBox.innerHTML.includes("Renderizado dinámicamente")) {
            runCustomMLAnalysis();
        }
    }
}

// --- RED INTEGRAL (TRENES Y BUSES TODO EN UNO) ---
async function loadLines(operator = "", mode = "") {
    currentFilterOperator = operator;
    currentFilterMode = mode;

    let url = API_BASE + "/api/transport/lines";
    const params = [];
    if (operator) params.push(`operator=${encodeURIComponent(operator)}`);
    if (mode) params.push(`mode=${encodeURIComponent(mode)}`);
    if (params.length) url += `?${params.join("&")}`;

    try {
        const res = await fetch(url);
        allLinesList = await res.json();
        renderLinesGrid(allLinesList);
    } catch (e) {
        console.error("Error loading lines:", e);
    }
}

let gipuzkoaMap = null;
let mapMarkers = [];

function switchTransportView(view) {
    const btnLines = document.getElementById("btn-view-lines");
    const btnMap = document.getElementById("btn-view-map");
    const mapPanel = document.getElementById("transport-map-panel");

    if (view === "map") {
        btnLines?.classList.remove("active");
        btnMap?.classList.add("active");
        if (mapPanel) {
            mapPanel.style.display = "block";
            initGipuzkoaMap();
            setTimeout(() => {
                gipuzkoaMap?.invalidateSize();
            }, 250);
        }
    } else {
        btnMap?.classList.remove("active");
        btnLines?.classList.add("active");
        if (mapPanel) {
            mapPanel.style.display = "none";
        }
    }
}

function initGipuzkoaMap() {
    const mapContainer = document.getElementById("gipuzkoa-transport-map");
    if (!mapContainer || gipuzkoaMap) return;

    if (typeof L === "undefined") {
        console.warn("Leaflet library is still loading");
        return;
    }

    gipuzkoaMap = L.map("gipuzkoa-transport-map", {
        scrollWheelZoom: false
    }).setView([43.3183, -1.9812], 12);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Red MUGI Gipuzkoa',
        maxZoom: 18
    }).addTo(gipuzkoaMap);

    populateMapMarkers();
}

function populateMapMarkers() {
    if (!gipuzkoaMap || !allStopsList || !allStopsList.length) return;

    mapMarkers.forEach(m => gipuzkoaMap.removeLayer(m));
    mapMarkers = [];

    allStopsList.forEach(stop => {
        if (!stop.lat || !stop.lng) return;

        let markerColor = "#009fe3";
        if (stop.operators.includes("euskotren")) markerColor = "#005baa";
        else if (stop.operators.includes("renfe")) markerColor = "#990033";
        else if (stop.operators.includes("lurraldebus")) markerColor = "#007a3d";
        else if (stop.operators.includes("dbus")) markerColor = "#0082c9";
        else if (stop.operators.includes("metrobilbao")) markerColor = "#e2231a";
        else if (stop.operators.includes("bizkaibus")) markerColor = "#5f8f1f";

        const customIcon = L.divIcon({
            className: "custom-map-pin",
            html: `<div style="background-color: ${markerColor}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid #ffffff; box-shadow: 0 1px 5px rgba(0,0,0,0.4);"></div>`,
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });

        const marker = L.marker([stop.lat, stop.lng], { icon: customIcon }).addTo(gipuzkoaMap);

        const linesBadges = (stop.lines || []).map(l => `
            <span style="background: ${getOperatorBorderColor(l.operator_id)}; color: #fff; font-size: 0.7rem; font-weight: 700; padding: 1px 5px; border-radius: 3px;">${l.code}</span>
        `).join(" ");

        const addressText = stop.address ? `${stop.address} (${stop.municipality || 'Gipuzkoa'})` : (stop.municipality || 'Gipuzkoa');
        const mapsUrl = stop.maps_url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(stop.name + ' Gipuzkoa')}`;
        const dirUrl = stop.maps_dir_url || `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(stop.name + ' Gipuzkoa')}`;

        const popupContent = `
            <div style="font-family: inherit; font-size: 0.85rem; min-width: 210px;">
                <strong style="color: #0f172a; font-size: 0.95rem;">${stop.name}</strong>
                ${stop.is_transfer_hub ? '<div style="color: #1d4ed8; font-weight: 800; font-size: 0.7rem; margin-top: 2px;">NODO INTERMODAL</div>' : ''}
                <div style="color: #475569; font-size: 0.78rem; margin: 4px 0;">${addressText}</div>
                <div style="margin: 6px 0;">${linesBadges}</div>
                <div style="margin-top: 8px; display: flex; gap: 6px;">
                    <a href="${mapsUrl}" target="_blank" rel="noopener noreferrer" style="background: #00a859; color: #fff; text-decoration: none; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">Google Maps</a>
                    <a href="${dirUrl}" target="_blank" rel="noopener noreferrer" style="background: #009fe3; color: #fff; text-decoration: none; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">Cómo llegar</a>
                </div>
            </div>
        `;
        marker.bindPopup(popupContent);
        mapMarkers.push(marker);
    });
}

function focusStopOnMap(lat, lng, name) {
    switchTransportView("map");
    setTimeout(() => {
        if (gipuzkoaMap) {
            gipuzkoaMap.setView([lat, lng], 15);
            const marker = mapMarkers.find(m => {
                const pos = m.getLatLng();
                return Math.abs(pos.lat - lat) < 0.0001 && Math.abs(pos.lng - lng) < 0.0001;
            });
            if (marker) marker.openPopup();
        }
        document.getElementById("transport-map-panel")?.scrollIntoView({ behavior: "smooth" });
    }, 250);
}

function renderLinesGrid(lines) {
    const container = document.getElementById("lines-container");
    const counterBadge = document.getElementById("lines-counter-badge");
    if (!container) return;
    container.innerHTML = "";

    if (counterBadge) {
        counterBadge.textContent = `${lines.length} líneas mostradas`;
    }

    if (!lines.length) {
        container.innerHTML = `<p style="color: var(--text-muted); padding: 24px; text-align: center; grid-column: 1 / -1;">No se encontraron líneas con los filtros seleccionados.</p>`;
        return;
    }

    lines.forEach(line => {
        const card = document.createElement("div");
        card.className = "line-item-card";
        const opColor = getOperatorBorderColor(line.operator_id);
        card.style.setProperty("--op", opColor);
        const isTrain = isRailOperator(line.operator_id);

        const mapsRouteUrl = line.maps_route_url || `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(line.origin + ' Gipuzkoa')}&destination=${encodeURIComponent(line.destination + ' Gipuzkoa')}`;

        card.innerHTML = `
            <div class="line-card-top">
                <span class="line-badge-lg">${line.code}</span>
                <div class="line-card-heading">
                    <strong class="line-card-title">${line.name}</strong>
                    <span class="line-card-op">
                        <svg class="svg-icon"><use href="#${isTrain ? "icon-train" : "icon-bus"}"></use></svg>
                        ${line.operator_name} · ${line.mode}
                    </span>
                </div>
            </div>

            <div class="line-route-terminal" title="Trayecto entre cabeceras">
                <div class="terminal-stop"><i></i><span>${line.origin}</span></div>
                <div class="terminal-stop is-end"><i></i><span>${line.destination}</span></div>
            </div>

            <div class="line-card-meta">
                <span class="meta-chip">
                    <svg class="svg-icon"><use href="#icon-clock"></use></svg>
                    <span>${line.frequency}</span>
                </span>
                <span class="meta-chip">
                    <svg class="svg-icon"><use href="#icon-info"></use></svg>
                    <span>${line.hours}</span>
                </span>
                <span class="meta-chip">
                    <svg class="svg-icon"><use href="#icon-pin"></use></svg>
                    <span>${line.stops.length} paradas</span>
                </span>
            </div>

            <div class="line-card-footer">
                <a href="${mapsRouteUrl}" target="_blank" rel="noopener noreferrer" class="btn-maps-link" title="Ver trayecto en Google Maps">
                    <svg class="svg-icon"><use href="#icon-globe"></use></svg>
                    <span>Maps</span>
                </a>
                <button class="btn-line-detail" onclick="viewLineDetail('${line.id}')">
                    <span>Ver recorrido</span>
                    <svg class="svg-icon"><use href="#icon-arrow-right"></use></svg>
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

async function viewLineDetail(lineId) {
    try {
        const res = await fetch(`${API_BASE}/api/transport/lines/${lineId}`);
        const line = await res.json();
        const opColor = getOperatorBorderColor(line.operator_id);
        
        document.getElementById("modal-line-title").innerHTML = `
            <span class="line-badge-lg" style="background-color: ${opColor};">${line.code}</span>
            <span>${line.name}</span>
        `;
        document.getElementById("modal-line-meta").innerHTML = `
            Operador: <strong>${line.operator_name}</strong> | Frecuencia: <strong>${line.frequency}</strong> | Horario: ${line.hours} | ${line.stops.length} paradas
        `;

        const mapsBtn = document.getElementById("modal-line-maps-btn");
        if (mapsBtn) {
            mapsBtn.href = line.maps_route_url || `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(line.origin + ' Gipuzkoa')}&destination=${encodeURIComponent(line.destination + ' Gipuzkoa')}`;
        }

        const stopsList = document.getElementById("modal-line-stops");
        stopsList.innerHTML = "";
        
        const stopsDetails = line.stops_detail || line.stops.map(s => ({ name: s, address: `Parada ${s}`, municipality: "Gipuzkoa" }));

        stopsDetails.forEach((stop, idx) => {
            const isOrigin = idx === 0;
            const isDest = idx === stopsDetails.length - 1;
            const li = document.createElement("li");
            li.className = "timeline-item";

            const nodeClass = isOrigin ? "timeline-node origin" : (isDest ? "timeline-node destination" : "timeline-node");
            const addressText = stop.address ? `${stop.address} · ${stop.municipality || 'Gipuzkoa'}` : (stop.municipality || 'Gipuzkoa');
            const mapsUrl = stop.maps_url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(stop.name + ' Gipuzkoa')}`;
            const dirUrl = stop.maps_dir_url || `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(stop.name + ' Gipuzkoa')}`;

            const connectionsHtml = (stop.connecting_lines && stop.connecting_lines.length)
                ? `<div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">
                     <span>Enlaces:</span> ${stop.connecting_lines.slice(0, 5).map(c => `<span style="background: #e2e8f0; color: #1e293b; padding: 1px 5px; border-radius: 3px; font-weight: 700; margin-left: 2px;">${c}</span>`).join("")}
                   </div>`
                : '';

            li.innerHTML = `
                <div class="${nodeClass}" title="Parada ${idx + 1}"></div>
                <div class="timeline-content">
                    <div style="flex: 1; min-width: 220px;">
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <span class="timeline-stop-name">${idx + 1}. ${stop.name}</span>
                            ${isOrigin ? '<span style="font-size: 0.7rem; background: #e6f5ed; color: #007a3d; padding: 2px 7px; border-radius: 4px; font-weight: 800;">CABECERA INICIAL</span>' : ''}
                            ${isDest ? '<span style="font-size: 0.7rem; background: #fae6ec; color: #990033; padding: 2px 7px; border-radius: 4px; font-weight: 800;">CABECERA FINAL</span>' : ''}
                        </div>
                        <div class="timeline-stop-address">
                            <svg class="svg-icon" style="width: 0.85em; height: 0.85em; color: var(--mugi-cyan);"><use href="#icon-globe"></use></svg>
                            <span>${addressText}</span>
                        </div>
                        ${connectionsHtml}
                    </div>
                    <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                        <a href="${mapsUrl}" target="_blank" rel="noopener noreferrer" class="btn-maps-link" title="Ver en Google Maps">
                            <svg class="svg-icon" style="width: 0.85em; height: 0.85em;"><use href="#icon-globe"></use></svg>
                            <span>Google Maps</span>
                        </a>
                        <a href="${dirUrl}" target="_blank" rel="noopener noreferrer" class="btn-dir-link" title="Cómo llegar a esta parada">
                            <svg class="svg-icon" style="width: 0.85em; height: 0.85em;"><use href="#icon-transfer"></use></svg>
                            <span>Cómo llegar</span>
                        </a>
                    </div>
                </div>
            `;
            stopsList.appendChild(li);
        });

        openModal("modal-line-detail");
    } catch (e) {
        console.error(e);
    }
}

async function loadStopsCatalog() {
    try {
        const res = await fetch(API_BASE + "/api/transport/stops");
        allStopsList = await res.json();
        populateStopSelects(allStopsList);

        document.getElementById("input-stop-search")?.addEventListener("input", (e) => {
            const q = e.target.value.toLowerCase().trim();
            renderStopsResults(allStopsList.filter(s => 
                s.name.toLowerCase().includes(q) || 
                (s.address && s.address.toLowerCase().includes(q)) ||
                (s.municipality && s.municipality.toLowerCase().includes(q))
            ));
        });

        renderStopsResults(allStopsList);
        
        if (gipuzkoaMap) {
            populateMapMarkers();
        }
    } catch (e) {
        console.error(e);
    }
}

function renderStopsResults(stops) {
    const container = document.getElementById("stops-search-results");
    const counterBadge = document.getElementById("stops-counter-badge");
    if (!container) return;
    container.innerHTML = "";

    if (counterBadge) {
        counterBadge.textContent = `${stops.length} paradas encontradas`;
    }

    if (!stops.length) {
        container.innerHTML = `<p style="color: var(--text-muted); padding: 18px; text-align: center;">No se encontraron paradas coincidentes con ese término de búsqueda.</p>`;
        return;
    }

    stops.slice(0, 25).forEach(s => {
        const div = document.createElement("div");
        div.className = "stop-card-item";

        const linesBadges = (s.lines || []).map(l => `
            <span class="stop-line-chip" style="background: ${getOperatorBorderColor(l.operator_id)};" title="${l.operator_name}: ${l.name}">${l.code}</span>
        `).join("");

        const addressText = s.address ? `${s.address} · ${s.municipality || 'Gipuzkoa'}` : (s.municipality || 'Gipuzkoa');
        const mapsUrl = s.maps_url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(s.name + ' Gipuzkoa')}`;
        const dirUrl = s.maps_dir_url || `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(s.name + ' Gipuzkoa')}`;

        div.innerHTML = `
            <div style="flex: 1; min-width: 250px;">
                <div class="stop-title-row">
                    <span class="stop-name">${s.name}</span>
                    ${s.is_transfer_hub ? '<span class="stop-hub-badge">NODO INTERMODAL</span>' : ''}
                    <span class="stop-muni-badge">${s.municipality || 'Gipuzkoa'}</span>
                </div>
                <div class="stop-address">
                    <svg class="svg-icon"><use href="#icon-pin"></use></svg>
                    <span>${addressText}</span>
                </div>
                <div class="stop-lines-row">
                    ${linesBadges}
                </div>
            </div>

            <div class="stop-actions-row">
                <a href="${mapsUrl}" target="_blank" rel="noopener noreferrer" class="btn-maps-link" title="Ver ubicación en Google Maps">
                    <svg class="svg-icon"><use href="#icon-globe"></use></svg>
                    <span>Maps</span>
                </a>
                <a href="${dirUrl}" target="_blank" rel="noopener noreferrer" class="btn-dir-link" title="Cómo llegar desde tu ubicación">
                    <svg class="svg-icon"><use href="#icon-walk"></use></svg>
                    <span>Cómo llegar</span>
                </a>
                ${s.lat && s.lng ? `
                <button class="btn-dir-link" onclick="focusStopOnMap(${s.lat}, ${s.lng}, '${s.name.replace(/'/g, "\\'")}')" title="Centrar parada en el mapa interactivo">
                    <svg class="svg-icon"><use href="#icon-pin"></use></svg>
                    <span>Mapa</span>
                </button>` : ''}
                <span class="stop-plan-group">
                    <button onclick="setPlannerFrom('${s.name.replace(/'/g, "\\'")}')" title="Usar como origen">Origen</button>
                    <button onclick="setPlannerTo('${s.name.replace(/'/g, "\\'")}')" title="Usar como destino">Destino</button>
                </span>
            </div>
        `;
        container.appendChild(div);
    });
}

function populateStopSelects(stops) {
    const origSelect = document.getElementById("select-planner-origin");
    const destSelect = document.getElementById("select-planner-destination");
    if (!origSelect || !destSelect) return;

    origSelect.innerHTML = `<option value="">-- Selecciona parada de origen --</option>`;
    destSelect.innerHTML = `<option value="">-- Selecciona parada de destino --</option>`;

    stops.forEach(s => {
        const hubSuffix = s.is_transfer_hub ? " [Nodo Intermodal]" : "";
        const opt1 = document.createElement("option");
        opt1.value = s.name;
        opt1.textContent = `${s.name}${hubSuffix}`;
        origSelect.appendChild(opt1);

        const opt2 = document.createElement("option");
        opt2.value = s.name;
        opt2.textContent = `${s.name}${hubSuffix}`;
        destSelect.appendChild(opt2);
    });
}

function setPlannerFrom(stopName) {
    switchTab("tab-planificador");
    document.getElementById("select-planner-origin").value = stopName;
}

function setPlannerTo(stopName) {
    switchTab("tab-planificador");
    document.getElementById("select-planner-destination").value = stopName;
}

// --- PLANIFICADOR DE TRANSBORDOS ---
function initPlannerEvents() {
    document.getElementById("btn-run-planner")?.addEventListener("click", runJourneyPlanner);

    document.getElementById("btn-swap-planner")?.addEventListener("click", () => {
        const origSelect = document.getElementById("select-planner-origin");
        const destSelect = document.getElementById("select-planner-destination");
        [origSelect.value, destSelect.value] = [destSelect.value, origSelect.value];
    });

    document.querySelectorAll(".btn-preset-route").forEach(btn => {
        btn.addEventListener("click", () => {
            const orig = btn.getAttribute("data-orig");
            const dest = btn.getAttribute("data-dest");
            document.getElementById("select-planner-origin").value = orig;
            document.getElementById("select-planner-destination").value = dest;
            runJourneyPlanner();
        });
    });
}

async function runJourneyPlanner() {
    const orig = document.getElementById("select-planner-origin").value;
    const dest = document.getElementById("select-planner-destination").value;
    const resultsContainer = document.getElementById("planner-results");

    if (!orig || !dest) {
        alert("Selecciona tanto la parada de origen como la de destino.");
        return;
    }

    if (orig === dest) {
        alert("El origen y el destino deben ser paradas diferentes.");
        return;
    }

    resultsContainer.innerHTML = `
        <div class="empty-state">
            <svg class="svg-icon" style="animation: spin 1s linear infinite;"><use href="#icon-refresh"></use></svg>
            <strong>Calculando rutas…</strong>
            <span>Buscando conexiones directas y transbordos con bonificación MUGI.</span>
        </div>`;

    try {
        const res = await fetch(API_BASE + "/api/transport/route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ origin: orig, destination: dest })
        });
        const data = await res.json();
        renderPlannerRoutes(data);
    } catch (e) {
        console.error(e);
        resultsContainer.innerHTML = `<div style="color: #b91c1c; padding: 16px;">Error al calcular la ruta.</div>`;
    }
}

function renderPlannerRoutes(data) {
    const container = document.getElementById("planner-results");
    container.innerHTML = "";

    if (!data.found || !data.routes.length) {
        container.innerHTML = `
            <div class="empty-state is-error">
                <svg class="svg-icon"><use href="#icon-alert"></use></svg>
                <strong>No hay conexión directa ni con un transbordo entre ${data.origin} y ${data.destination}</strong>
                <span>Prueba con un nodo intermodal cercano como Donostia Atotxa, Donostia Amara o Herrera.</span>
            </div>
        `;
        return;
    }

    const fastest = Math.min(...data.routes.map(r => r.total_duration_min));

    data.routes.forEach((route, rIdx) => {
        const card = document.createElement("div");
        card.className = "route-card";

        const isTransfer = route.num_transfers > 0;
        const isFastest = route.total_duration_min === fastest;
        const typeBadge = isTransfer
            ? `<span class="route-type-badge is-transfer">${route.type}</span>`
            : `<span class="route-type-badge is-direct">Servicio directo</span>`;

        // Resumen compacto de la ruta: chips de líneas y enlaces a pie
        const summaryChips = route.segments.map(seg => {
            if (seg.type === "transit") {
                const isTrain = isRailOperator(seg.operator_id);
                return `<span class="route-chip" style="--op: ${getOperatorBorderColor(seg.operator_id)};">
                            <svg class="svg-icon"><use href="#${isTrain ? "icon-train" : "icon-bus"}"></use></svg>${seg.line_code}
                        </span>`;
            }
            return `<span class="route-chip is-walk"><svg class="svg-icon"><use href="#icon-walk"></use></svg>${seg.duration_min}'</span>`;
        }).join(`<svg class="svg-icon route-chip-sep"><use href="#icon-arrow-right"></use></svg>`);

        let segmentsHtml = "";
        route.segments.forEach(seg => {
            if (seg.type === "transit") {
                const opColor = getOperatorBorderColor(seg.operator_id);
                const isTrain = isRailOperator(seg.operator_id);
                const iconId = isTrain ? "icon-train" : "icon-bus";
                segmentsHtml += `
                    <div class="timeline-step" style="--op: ${opColor};">
                        <div class="timeline-dot">
                            <svg class="svg-icon"><use href="#${iconId}"></use></svg>
                        </div>
                        <div class="segment-body">
                            <div class="segment-head">
                                <span class="line-code-badge">${seg.line_code}</span>
                                <strong>${seg.line_name}</strong>
                                <span class="op-badge ${getOperatorClass(seg.operator_id)}">${seg.operator_name}</span>
                            </div>
                            <div class="segment-stops">
                                <span>${seg.from_stop}</span>
                                <svg class="svg-icon"><use href="#icon-arrow-right"></use></svg>
                                <span>${seg.to_stop}</span>
                            </div>
                            <div class="segment-meta">
                                <span>${seg.duration_min} min</span>
                                <span>${seg.stops_count} ${seg.stops_count === 1 ? "parada" : "paradas"}</span>
                                <span>${seg.frequency}</span>
                            </div>
                        </div>
                    </div>
                `;
            } else if (seg.type === "walk_transfer") {
                segmentsHtml += `
                    <div class="timeline-step is-walk">
                        <div class="timeline-dot walk">
                            <svg class="svg-icon"><use href="#icon-walk"></use></svg>
                        </div>
                        <div class="segment-walk">
                            <strong>${seg.from_stop === seg.to_stop ? `Transbordo · ${seg.duration_min} min` : `A pie · ${seg.duration_min} min`}</strong>
                            ${seg.from_stop === seg.to_stop ? `en ${seg.from_stop}` : `de ${seg.from_stop} a ${seg.to_stop}`}
                            <div>${seg.note}</div>
                        </div>
                    </div>
                `;
            }
        });

        segmentsHtml += `
            <div class="timeline-step is-end">
                <div class="timeline-dot end">
                    <svg class="svg-icon"><use href="#icon-pin"></use></svg>
                </div>
                <div class="segment-arrival">Llegada a <strong>${data.destination}</strong></div>
            </div>
        `;

        const fares = route.fare_breakdown;

        card.innerHTML = `
            <div class="route-header">
                <div class="route-header-main">
                    <div class="route-badges">
                        <span class="route-option">Opción ${rIdx + 1}</span>
                        ${typeBadge}
                        ${isFastest ? '<span class="route-type-badge is-fastest">Más rápida</span>' : ''}
                    </div>
                    <div class="route-summary">${summaryChips}</div>
                </div>
                <div class="route-duration">
                    <span class="route-duration-val">${route.total_duration_min}<small>min</small></span>
                    <span class="route-duration-label">${isTransfer ? `${route.num_transfers} transbordo${route.num_transfers > 1 ? "s" : ""}` : "Sin transbordos"}</span>
                </div>
            </div>

            <div class="timeline">
                ${segmentsHtml}
            </div>

            <div class="fare-panel">
                <div class="fare-panel-head">
                    <strong>Precio con tarjeta MUGI</strong>
                    <span class="mugi-discount-pill">${fares.transfer_rule}</span>
                </div>
                <div class="fare-grid">
                    <div class="fare-tile is-cash">
                        <span>Billete ocasional</span>
                        <strong>${fares.single_cash_ticket}</strong>
                    </div>
                    <div class="fare-tile">
                        <span>Tramo 1 · 1-20 viajes</span>
                        <strong>${fares.mugi_tramo_1}</strong>
                    </div>
                    <div class="fare-tile">
                        <span>Tramo 2 · 21-50 viajes</span>
                        <strong>${fares.mugi_tramo_2}</strong>
                    </div>
                    <div class="fare-tile is-best">
                        <span>Tramo 3 · 51+ viajes</span>
                        <strong>${fares.mugi_tramo_3}</strong>
                    </div>
                </div>
            </div>
        `;

        container.appendChild(card);
    });
}

// --- INCIDENCIAS Y MACHINE LEARNING ---
async function loadIncidents(zone = "all") {
    const listContainer = document.getElementById("incidents-list-container");
    if (!listContainer) return;
    listContainer.innerHTML = `<p style="color: var(--text-muted); padding: 14px;">Consultando estado de la red e incidencias activas...</p>`;

    try {
        const url = zone === "all" ? API_BASE + "/api/incidents" : `${API_BASE}/api/incidents?zone=${encodeURIComponent(zone)}`;
        const res = await fetch(url);
        const data = await res.json();

        const mlMetrics = data.ml_status;
        if (mlMetrics) {
            const accElem = document.getElementById("ml-metrics-accuracy");
            if (accElem) accElem.textContent = `${mlMetrics.severity_accuracy}%`;
            const catElem = document.getElementById("ml-metrics-cat-acc");
            if (catElem) catElem.textContent = `${mlMetrics.category_accuracy || 93.3}%`;
            const samplesElem = document.getElementById("ml-metrics-samples");
            if (samplesElem) samplesElem.textContent = mlMetrics.sample_count;
            const trainedElem = document.getElementById("ml-metrics-trained-at");
            if (trainedElem) trainedElem.textContent = mlMetrics.trained_at;
        }

        renderIncidentsList(data.incidents || []);
    } catch (e) {
        console.error(e);
        listContainer.innerHTML = `<p style="color: #b91c1c; padding: 14px;">Error al obtener incidencias.</p>`;
    }
}

function renderIncidentsList(incidents) {
    const container = document.getElementById("incidents-list-container");
    const mlFeedContainer = document.getElementById("ml-incidents-feed-container");

    const renderTo = (target) => {
        if (!target) return;
        target.innerHTML = "";

        if (!incidents.length) {
            target.innerHTML = `
                <div class="empty-state is-ok">
                    <svg class="svg-icon"><use href="#icon-check"></use></svg>
                    <strong>Sin incidencias activas en esta comarca</strong>
                    <span>Trenes y autobuses circulan con normalidad.</span>
                </div>
            `;
            return;
        }

        incidents.forEach(inc => {
            const card = document.createElement("div");
            card.className = "incident-card";
            const ml = inc.ml_analysis || {};
            const sevMeta = ml.severity_meta || { bg: "#fef9c3", text: "#854d0e", border: "#eab308", label: "Media" };
            card.style.setProperty("--sev", sevMeta.border || sevMeta.text);

            card.innerHTML = `
                <div class="incident-header">
                    <div class="incident-tags">
                        <span class="incident-severity-badge" style="background-color: ${sevMeta.bg}; color: ${sevMeta.text};">
                            <i class="sev-dot" style="--dot: ${sevMeta.border || sevMeta.text};"></i>${sevMeta.label}
                        </span>
                        <span class="op-badge ${getOperatorClass(inc.operator)}">${inc.operator}</span>
                        <span class="incident-zone">
                            <svg class="svg-icon"><use href="#icon-pin"></use></svg>${inc.zone}
                        </span>
                    </div>
                    <div class="incident-time">
                        <span>${inc.created_at}</span>
                        <span>${inc.source}</span>
                    </div>
                </div>

                <h3 class="incident-title">${inc.title}</h3>
                <p class="incident-text">${inc.text}</p>

                <div class="incident-stats">
                    <div><span>Categoría</span><strong>${ml.predicted_category || 'General'}</strong></div>
                    <div><span>Demora estimada</span><strong class="is-delay">+${ml.estimated_delay_min || 0} min</strong></div>
                    <div><span>Confianza</span><strong>${ml.confidence_percentage || 95}%</strong></div>
                </div>

                <div class="incident-mitigation-box">
                    <svg class="svg-icon"><use href="#icon-transfer"></use></svg>
                    <div>
                        <strong>Alternativa recomendada</strong>
                        <span>${ml.recommended_alternative || 'Consulte desvíos alternativos.'}</span>
                    </div>
                </div>
            `;

            target.appendChild(card);
        });
    };

    renderTo(container);
    renderTo(mlFeedContainer);
}

function initMLEvents() {
    document.querySelectorAll(".btn-zone-filter").forEach(btn => {
        btn.addEventListener("click", () => {
            const zone = btn.getAttribute("data-zone");
            document.querySelectorAll(".btn-zone-filter").forEach(b => {
                b.classList.toggle("active", b.getAttribute("data-zone") === zone);
            });
            loadIncidents(zone);
        });
    });

    document.getElementById("btn-analyze-ml")?.addEventListener("click", runCustomMLAnalysis);

    document.getElementById("btn-clear-ml-text")?.addEventListener("click", () => {
        const textarea = document.getElementById("input-custom-alert");
        if (textarea) {
            textarea.value = "";
            textarea.focus();
        }
    });

    document.querySelectorAll(".ml-preset-chip").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".ml-preset-chip").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const txt = btn.getAttribute("data-text");
            const textarea = document.getElementById("input-custom-alert");
            if (textarea) textarea.value = txt;
            runCustomMLAnalysis();
        });
    });

    document.getElementById("btn-retrain-ml")?.addEventListener("click", async () => {
        const btn = document.getElementById("btn-retrain-ml");
        const origContent = btn ? btn.innerHTML : "";
        if (btn) {
            btn.innerHTML = `<svg class="svg-icon" style="animation: spin 1s linear infinite;"><use href="#icon-refresh"></use></svg><span>Re-entrenando...</span>`;
            btn.disabled = true;
        }
        try {
            const res = await fetch(API_BASE + "/api/incidents/train", { method: "POST" });
            const data = await res.json();
            alert(`Modelo de Machine Learning re-entrenado con éxito.\nMuestras analizadas: ${data.metrics.sample_count}\nPrecisión Severidad: ${data.metrics.severity_accuracy}%\nPrecisión Categorías: ${data.metrics.category_accuracy || 93.3}%`);
            loadIncidents("all");
        } catch (e) {
            console.error(e);
            alert("Error al re-entrenar el modelo de Machine Learning.");
        } finally {
            if (btn) {
                btn.innerHTML = origContent;
                btn.disabled = false;
            }
        }
    });
}

async function runCustomMLAnalysis() {
    const textInput = document.getElementById("input-custom-alert");
    const text = textInput ? textInput.value.trim() : "";
    const resultBox = document.getElementById("ml-analysis-result");
    if (!resultBox) return;

    if (!text) {
        alert("Escribe o selecciona un texto de aviso para analizar.");
        return;
    }

    resultBox.style.display = "block";
    resultBox.innerHTML = `
        <div style="padding: 20px; color: var(--text-muted); display: flex; align-items: center; gap: 10px; background: #f8fafc; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); margin-top: 14px;">
            <svg class="svg-icon" style="animation: spin 1s linear infinite; color: var(--mugi-green);"><use href="#icon-refresh"></use></svg>
            <span>Procesando aviso con Vectorizador TF-IDF y Pipeline de Scikit-Learn...</span>
        </div>
    `;

    try {
        const res = await fetch(API_BASE + "/api/incidents/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
        const data = await res.json();
        renderMLAnalysisOutput(data);
    } catch (e) {
        console.error(e);
        resultBox.innerHTML = `<div style="color: #b91c1c; padding: 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: var(--radius-md); margin-top: 14px;">Error en la predicción ML.</div>`;
    }
}

function renderMLAnalysisOutput(data) {
    const resultBox = document.getElementById("ml-analysis-result");
    if (!resultBox) return;
    const sev = data.severity_meta || { bg: "#fef9c3", text: "#854d0e", border: "#eab308", label: "Media" };

    const termsBadges = (data.key_factors || []).map(t => `
        <span class="ml-keyword-tag">${t}</span>
    `).join(" ");

    const confidenceVal = data.confidence_percentage || 95;

    resultBox.innerHTML = `
        <div class="ml-result-card" style="--sev: ${sev.border || 'var(--mugi-green)'};">
            <div class="ml-result-header">
                <div class="ml-result-severity" style="background-color: ${sev.bg}; color: ${sev.text};">
                    <span class="ml-result-severity-label">Severidad predicha</span>
                    <strong><i class="sev-dot" style="--dot: ${sev.border || sev.text};"></i>${sev.label}</strong>
                </div>
                <div class="ml-result-delay">
                    <span>Demora estimada</span>
                    <strong>+${data.estimated_delay_min}<small>min</small></strong>
                </div>
            </div>

            <div class="ml-stat-grid">
                <div class="ml-stat-tile">
                    <div class="ml-stat-tile-label">Operador</div>
                    <div class="ml-stat-tile-value"><span class="op-badge ${getOperatorClass(data.predicted_operator)}">${data.predicted_operator}</span></div>
                </div>
                <div class="ml-stat-tile">
                    <div class="ml-stat-tile-label">Zona</div>
                    <div class="ml-stat-tile-value">${data.predicted_zone}</div>
                </div>
                <div class="ml-stat-tile">
                    <div class="ml-stat-tile-label">Categoría</div>
                    <div class="ml-stat-tile-value">${data.predicted_category}</div>
                </div>
                <div class="ml-stat-tile">
                    <div class="ml-stat-tile-label">Confianza</div>
                    <div class="ml-stat-tile-value">${confidenceVal}%</div>
                    <div class="ml-confidence-wrapper">
                        <div class="ml-confidence-bar" style="width: ${confidenceVal}%;"></div>
                    </div>
                </div>
            </div>

            <div class="ml-terms">
                <span class="ml-terms-label">Términos clave (TF-IDF)</span>
                <div class="ml-terms-list">
                  ${termsBadges || '<span style="color: #94a3b8; font-size: 0.8rem;">Vocabulario general de transporte</span>'}
                </div>
            </div>

            <div class="incident-mitigation-box">
                <svg class="svg-icon"><use href="#icon-transfer"></use></svg>
                <div>
                    <strong>Ruta alternativa recomendada</strong>
                    <span>${data.recommended_alternative}</span>
                </div>
            </div>
        </div>
    `;
}

// --- WEB SCRAPING EN VIVO DE MUGI.EUS ---
async function loadScrapedData() {
    const newsContainer = document.getElementById("mugi-scraped-news-container");
    const tariffsContainer = document.getElementById("mugi-scraped-tariffs-container");
    const timestampBadge = document.getElementById("scrape-timestamp-badge");

    try {
        // 1. Load Scraped News
        const resNews = await fetch(API_BASE + "/api/mugi/scraped-news");
        const dataNews = await resNews.json();

        if (timestampBadge && dataNews.last_updated) {
            timestampBadge.innerHTML = `
                <span style="display: inline-flex; align-items: center; gap: 4px;">
                    <svg class="svg-icon" style="width: 0.9em; height: 0.9em; color: var(--mugi-green);"><use href="#icon-check"></use></svg>
                    <span>Sincronizado: <strong>${dataNews.last_updated}</strong> (mugi.eus)</span>
                </span>
            `;
        }

        if (newsContainer) {
            newsContainer.innerHTML = "";
            const articles = dataNews.news || [];
            if (!articles.length) {
                newsContainer.innerHTML = `<p style="color: var(--text-muted); padding: 10px;">No se han recibido avisos en este ciclo de scraping.</p>`;
            } else {
                articles.forEach(art => {
                    const card = document.createElement("div");
                    card.className = "scraped-news-card";
                    card.innerHTML = `
                        <div>
                            <div class="news-card-meta">
                                <span class="scraped-badge">
                                    <svg class="svg-icon"><use href="#icon-globe"></use></svg>
                                    <span>${art.source}</span>
                                </span>
                                <span>${art.scraped_at || ''}</span>
                            </div>
                            <h4 class="news-card-title">${art.title}</h4>
                            <p class="news-card-summary">${art.summary}</p>
                        </div>
                        <a class="news-card-link" href="${art.url}" target="_blank" rel="noopener noreferrer">
                            <span>Leer en mugi.eus</span>
                            <svg class="svg-icon"><use href="#icon-external"></use></svg>
                        </a>
                    `;
                    newsContainer.appendChild(card);
                });
            }
        }

        // 2. Load Scraped Tariffs
        const resTariffs = await fetch(API_BASE + "/api/mugi/scraped-tariffs");
        const dataTariffs = await resTariffs.json();
        if (tariffsContainer && dataTariffs.tariffs) {
            tariffsContainer.innerHTML = "";
            dataTariffs.tariffs.forEach(tbl => {
                const wrapper = document.createElement("div");
                wrapper.className = "tariff-card";

                let thead = "";
                if (tbl.headers && tbl.headers.length) {
                    thead = `<thead><tr>${tbl.headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>`;
                }

                let tbody = "";
                if (tbl.rows && tbl.rows.length) {
                    tbody = `<tbody>${tbl.rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>`;
                }

                wrapper.innerHTML = `
                    <div class="tariff-card-title">${tbl.title || 'Tarifas y saltos MUGI'}</div>
                    <div class="tariff-card-scroll">
                        <table class="gov-table">
                            ${thead}
                            ${tbody}
                        </table>
                    </div>
                `;
                tariffsContainer.appendChild(wrapper);
            });
        }
    } catch (e) {
        console.error("Error loading scraped data:", e);
    }
}

function initScrapingEvents() {
    const handleSync = async (btn) => {
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `
            <svg class="svg-icon" style="animation: spin 1s infinite;"><use href="#icon-refresh"></use></svg>
            <span>Scrapeando mugi.eus...</span>
        `;

        try {
            const res = await fetch(API_BASE + "/api/mugi/sync-web", { method: "POST" });
            const data = await res.json();
            await loadScrapedData();
            alert(`¡Web scraping completado con éxito!\nSe han extraído ${data.news_scraped} comunicados y ${data.tariffs_scraped} tablas tarifarias directamente desde ${data.source_domain || 'mugi.eus'}.`);
        } catch (e) {
            console.error(e);
            alert("Error al ejecutar el scraping en tiempo real.");
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    };

    document.getElementById("btn-trigger-scrape")?.addEventListener("click", (e) => handleSync(e.currentTarget));
    document.getElementById("btn-sync-topbar")?.addEventListener("click", (e) => handleSync(e.currentTarget));
}

// --- UTILITIES ---
function formatMugiCardNumber(num) {
    if (!num) return "--- --- --- -";
    const clean = String(num).replace(/\D/g, "");
    if (clean.length === 10) {
        return `${clean.slice(0, 3)} ${clean.slice(3, 6)} ${clean.slice(6, 9)} ${clean.slice(9, 10)}`;
    }
    if (clean.length > 0) {
        let res = "";
        for (let i = 0; i < clean.length; i++) {
            if (i === 3 || i === 6 || i === 9) res += " ";
            res += clean[i];
        }
        return res;
    }
    return String(num);
}

function formatCardNumber(num) {
    return formatMugiCardNumber(num);
}

function getOperatorClass(op) {
    const lower = (op || "").toLowerCase();
    if (lower.includes("euskotren")) return "op-euskotren";
    if (lower.includes("renfe")) return "op-renfe";
    if (lower.includes("lurraldebus")) return "op-lurraldebus";
    if (lower.includes("dbus")) return "op-dbus";
    if (lower.includes("metro")) return "op-metrobilbao";
    if (lower.includes("bizkaibus")) return "op-bizkaibus";
    if (lower.includes("mugi") || lower.includes("pasarela") || lower.includes("recarga")) return "op-mugi";
    return "";
}

function getOperatorBorderColor(opId) {
    const lower = (opId || "").toLowerCase();
    if (lower.includes("euskotren")) return "#005baa";
    if (lower.includes("renfe")) return "#990033";
    if (lower.includes("lurraldebus")) return "#007a3d";
    if (lower.includes("dbus")) return "#0082c9";
    if (lower.includes("metro")) return "#e2231a";
    if (lower.includes("bizkaibus")) return "#5f8f1f";
    return "#0f2742";
}

function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = "flex";
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
}

function isRailOperator(opId) {
    return ["euskotren", "renfe", "metrobilbao"].includes(opId);
}
