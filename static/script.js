document.addEventListener("DOMContentLoaded", () => {

  if (window.lucide) lucide.createIcons();

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // ============ МОДАЛКА АВТОРИЗАЦИИ ============
  const authModal = document.getElementById("authModal");
  const openAuthBtn = document.getElementById("openAuthBtn");
  const joinSquadBtn = document.getElementById("joinSquadBtn");
  const closeAuthBtn = document.getElementById("closeAuthBtn");

  function openModal() { if (authModal) authModal.classList.add("active"); }
  function closeModal() { if (authModal) authModal.classList.remove("active"); }

  if (openAuthBtn) openAuthBtn.addEventListener("click", openModal);
  if (closeAuthBtn) closeAuthBtn.addEventListener("click", closeModal);

  if (joinSquadBtn) {
    joinSquadBtn.addEventListener("click", () => {
      const target = document.getElementById("joinSection");
      if (target) target.scrollIntoView({ behavior: "smooth" });
    });
  }

  if (authModal) {
    authModal.addEventListener("click", (e) => {
      if (e.target === authModal) closeModal();
    });
  }

  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      tab.classList.add("active");
      const form = document.getElementById(target + "Form");
      if (form) form.classList.add("active");
    });
  });

  window.togglePass = function (btn) {
    const input = btn.parentElement.querySelector("input");
    input.type = input.type === "password" ? "text" : "password";
  };

  // ============ РЕГИСТРАЦИЯ ============
  const registerForm = document.getElementById("registerForm");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = document.getElementById("registerError");
      err.textContent = "";
      try {
        const res = await fetch("/api/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: registerForm.username.value.trim(),
            password: registerForm.password.value,
          }),
        });
        const json = await res.json();
        if (!res.ok) { err.textContent = json.error || "Ошибка"; return; }

        err.style.color = "#2a8";
        err.textContent = "Аккаунт создан! Теперь войди.";
        registerForm.reset();

        setTimeout(() => {
          const loginTab = document.querySelector('.tab[data-tab="login"]');
          if (loginTab) loginTab.click();
          setTimeout(() => {
            err.textContent = "";
            err.style.color = "";
          }, 3000);
        }, 800);

      } catch (ex) {
        err.textContent = "Сервер не отвечает";
      }
    });
  }

  // ============ ВХОД ============
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = document.getElementById("loginError");
      err.textContent = "";
      try {
        const res = await fetch("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: loginForm.username.value.trim(),
            password: loginForm.password.value,
          }),
        });
        const json = await res.json();
        if (!res.ok) { err.textContent = json.error || "Ошибка"; return; }
        window.location.href = "/profile";
      } catch (ex) {
        err.textContent = "Сервер не отвечает";
      }
    });
  }

  // ============ ПРОФИЛЬ ============
  const profileCard = document.getElementById("profileCard");
  if (profileCard) {
    let userData = null;
    let editMode = false;

    async function loadProfile() {
      const res = await fetch("/api/profile");
      if (!res.ok) return (window.location.href = "/");
      const data = await res.json();
      userData = data.user;
      renderProfile();
    }

    function renderProfile() {
      const u = userData;
      if (editMode) {
        profileCard.innerHTML = `
          <h1 class="profile-name">Редактирование профиля</h1>
          <div style="margin-top:20px">
            <label style="font-weight:600;font-size:14px;display:block;margin-bottom:6px">Никнейм</label>
            <input id="nickname" value="${escapeHtml(u.nickname)}"
              style="width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;margin-bottom:14px">

            <label style="font-weight:600;font-size:14px;display:block;margin-bottom:6px">Аватар</label>
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px">
              <div class="avatar" id="avatarPreview" style="margin:0">
                ${u.avatar ? `<img src="${escapeHtml(u.avatar)}" alt="">` : '<i data-lucide="user"></i>'}
              </div>
              <div>
                <label for="avatarFile" class="btn" style="cursor:pointer;display:inline-flex;align-items:center;gap:6px">
                  <i data-lucide="upload"></i> Выбрать файл
                </label>
                <input type="file" id="avatarFile" accept="image/*" style="display:none">
                <p class="muted" style="font-size:12px;margin-top:6px">PNG, JPG, GIF, WEBP. До 5 МБ.</p>
              </div>
            </div>

            <label style="font-weight:600;font-size:14px;display:block;margin-bottom:6px">О себе</label>
            <textarea id="about" rows="4" placeholder="Расскажи о себе..."
              style="width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;margin-bottom:16px">${escapeHtml(u.about)}</textarea>

            <div class="btn-row-left">
              <button class="btn primary" id="saveProfileBtn">Сохранить</button>
              <button class="btn" id="cancelEditBtn">Отмена</button>
            </div>
          </div>
        `;

        if (window.lucide) lucide.createIcons();

        const fileInput = document.getElementById("avatarFile");
        const preview = document.getElementById("avatarPreview");
        fileInput.addEventListener("change", async () => {
          const file = fileInput.files[0];
          if (!file) return;
          if (file.size > 5 * 1024 * 1024) {
            alert("Файл больше 5 МБ");
            return;
          }
          const formData = new FormData();
          formData.append("file", file);
          const res = await fetch("/api/upload-avatar", { method: "POST", body: formData });
          const json = await res.json();
          if (!res.ok) { alert(json.error || "Ошибка загрузки"); return; }
          userData.avatar = json.url;
          preview.innerHTML = `<img src="${json.url}" alt="">`;
        });

        document.getElementById("saveProfileBtn").addEventListener("click", saveProfile);
        document.getElementById("cancelEditBtn").addEventListener("click", () => {
          editMode = false; renderProfile();
        });
      } else {
        profileCard.innerHTML = `
          <div class="avatar">${u.avatar ? `<img src="${escapeHtml(u.avatar)}" alt="">` : '<i data-lucide="user"></i>'}</div>
          <h1 class="profile-name">${escapeHtml(u.nickname)}</h1>
          <p class="profile-handle">@${escapeHtml(u.username)}</p>
          <span class="role">${escapeHtml(u.role)}</span>
          <p class="profile-about">${escapeHtml(u.about) || "Пока нет описания..."}</p>
          <p class="profile-meta">Баланс: ${u.balance || 0} АР</p>
          <p class="profile-meta">В скваде с: ${new Date(u.created_at).toLocaleDateString("ru")}</p>
          <div class="btn-row-left">
            <button class="btn primary" id="editProfileBtn">Редактировать</button>
          </div>
        `;
        if (window.lucide) lucide.createIcons();
        document.getElementById("editProfileBtn").addEventListener("click", () => {
          editMode = true; renderProfile();
        });
      }
    }

    async function saveProfile() {
      const data = {
        nickname: document.getElementById("nickname").value,
        about: document.getElementById("about").value,
        avatar: userData.avatar || "",
      };
      const res = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        userData = { ...userData, nickname: data.nickname, about: data.about };
        editMode = false;
        renderProfile();
      }
    }

    loadProfile();
  }

  // ============ ВЫХОД ============
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      await fetch("/api/logout", { method: "POST" });
      window.location.href = "/";
    });
  }

  // ============ БУРГЕР-МЕНЮ ============
  const burger = document.querySelector(".burger");
  const sideMenu = document.getElementById("sideMenu");
  const sideMenuOverlay = document.getElementById("sideMenuOverlay");
  const closeSideMenu = document.getElementById("closeSideMenu");

  if (burger && sideMenu) {
    burger.addEventListener("click", () => {
      sideMenu.classList.add("active");
      if (sideMenuOverlay) sideMenuOverlay.classList.add("active");
    });
  }
  if (closeSideMenu && sideMenu) {
    closeSideMenu.addEventListener("click", () => {
      sideMenu.classList.remove("active");
      if (sideMenuOverlay) sideMenuOverlay.classList.remove("active");
    });
  }
  if (sideMenuOverlay) {
    sideMenuOverlay.addEventListener("click", () => {
      if (sideMenu) sideMenu.classList.remove("active");
      sideMenuOverlay.classList.remove("active");
    });
  }

  // ============ АНИМАЦИЯ ============
  const joinSection = document.getElementById("joinSection");
  if (joinSection) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add("visible");
      });
    }, { threshold: 0.15 });
    observer.observe(joinSection);
  }

  // ============ ТОРГОВЛЯ ============
  const productsBody = document.getElementById("productsBody");
  const purchasesBody = document.getElementById("purchasesBody");
  if (productsBody) {
    let allProducts = [];
    let allPurchases = [];
    let currentFilter = "active";
    let currentSort = "default";
    let searchQuery = { id: "", player: "", item: "" };
    let currentPage = "products";
    let currentBuyProductId = null;

    async function loadProducts() {
      const res = await fetch("/api/products");
      const data = await res.json();
      allProducts = data.products || [];
      renderProducts();
    }

    async function loadPurchases() {
      const res = await fetch("/api/purchases");
      const data = await res.json();
      allPurchases = data.purchases || [];
      renderPurchases();
    }

    function renderProducts() {
      let list = [...allProducts];
      if (currentFilter === "active") list = list.filter(p => p.status === "active");
      if (searchQuery.id) list = list.filter(p => String(p.id).includes(searchQuery.id));
      if (searchQuery.player)
        list = list.filter(p => (p.nickname || p.username || "").toLowerCase().includes(searchQuery.player.toLowerCase()));
      if (searchQuery.item)
        list = list.filter(p => (p.item || "").toLowerCase().includes(searchQuery.item.toLowerCase()));
      if (currentSort === "asc") list.sort((a, b) => a.price - b.price);
      if (currentSort === "desc") list.sort((a, b) => b.price - a.price);

      if (!list.length) {
        productsBody.innerHTML = `<tr><td colspan="7" class="empty-row">Список товаров пустой</td></tr>`;
        return;
      }

      productsBody.innerHTML = list.map(p => `
        <tr>
          <td>
            <div class="seller-cell">
              <div class="seller-avatar">${p.avatar ? `<img src="${escapeHtml(p.avatar)}">` : '<i data-lucide="user"></i>'}</div>
              <div>
                <div class="seller-name">${escapeHtml(p.nickname || p.username)}</div>
                <div class="seller-role">${p.description ? escapeHtml(p.description) : "Продавец"}</div>
              </div>
            </div>
          </td>
          <td>${escapeHtml(p.item)}</td>
          <td>${p.quantity} * ${p.per_slot || 1} ${escapeHtml(p.measure)}</td>
          <td>${p.price} AP</td>
          <td>${escapeHtml(p.shop || "—")}</td>
          <td>${new Date(p.updated_at || p.created_at).toLocaleDateString("ru")}</td>
          <td>
            <button class="icon-btn" title="Купить" data-buy="${p.id}">
              <i data-lucide="shopping-cart"></i>
            </button>
            <button class="icon-btn" title="Удалить" data-del="${p.id}">
              <i data-lucide="trash-2"></i>
            </button>
          </td>
        </tr>
      `).join("");

      if (window.lucide) lucide.createIcons();

      productsBody.querySelectorAll("[data-buy]").forEach(btn => {
        btn.addEventListener("click", () => {
          const p = allProducts.find(x => String(x.id) === btn.dataset.buy);
          if (!p) return;
          currentBuyProductId = p.id;
          const totalLabel = document.getElementById("buyProductTotal");
          if (totalLabel) {
            totalLabel.textContent = `Цена: ${p.price} AP за ${p.per_slot || 1} ${p.measure}`;
          }
          document.getElementById("buyProductModal").classList.add("active");
        });
      });

      productsBody.querySelectorAll("[data-del]").forEach(btn => {
        btn.addEventListener("click", async () => {
          if (!confirm("Удалить товар?")) return;
          await fetch(`/api/products/${btn.dataset.del}`, { method: "DELETE" });
          loadProducts();
        });
      });
    }

    function renderPurchases() {
      if (!purchasesBody) return;
      let list = [...allPurchases];
      if (!list.length) {
        purchasesBody.innerHTML = `<tr><td colspan="7" class="empty-row">Список покупок пустой</td></tr>`;
        return;
      }

      purchasesBody.innerHTML = list.map(p => `
        <tr>
          <td>
            <div class="seller-cell">
              <div class="seller-avatar">${p.buyer_avatar ? `<img src="${escapeHtml(p.buyer_avatar)}">` : '<i data-lucide="user"></i>'}</div>
              <div>
                <div class="seller-name">${escapeHtml(p.buyer_nickname || p.buyer_username)}</div>
                <div class="seller-role">Покупатель</div>
              </div>
            </div>
          </td>
          <td>
            <div class="seller-cell">
              <div class="seller-avatar">${p.seller_avatar ? `<img src="${escapeHtml(p.seller_avatar)}">` : '<i data-lucide="user"></i>'}</div>
              <div>
                <div class="seller-name">${escapeHtml(p.seller_nickname || p.seller_username)}</div>
                <div class="seller-role">Продавец</div>
              </div>
            </div>
          </td>
          <td>${escapeHtml(p.item)}</td>
          <td>${p.quantity} * ${p.per_slot || 1} ${escapeHtml(p.measure)}</td>
          <td>${p.total} AP</td>
          <td>${escapeHtml(p.shop || "—")}</td>
          <td>${new Date(p.created_at).toLocaleDateString("ru")}</td>
        </tr>
      `).join("");

      if (window.lucide) lucide.createIcons();
    }

    document.querySelectorAll(".tabline[data-page]").forEach(t => {
      t.addEventListener("click", () => {
        document.querySelectorAll(".tabline[data-page]").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        currentPage = t.dataset.page;
        document.getElementById("productsSection").style.display = currentPage === "products" ? "block" : "none";
        document.getElementById("purchasesSection").style.display = currentPage === "purchases" ? "block" : "none";
        document.getElementById("pageTitle").textContent = currentPage === "products" ? "Товары" : "Покупки";
        const createBtn = document.getElementById("openCreateProduct");
        if (createBtn) createBtn.style.display = currentPage === "products" ? "inline-flex" : "none";
        if (currentPage === "purchases") loadPurchases();
      });
    });

    document.querySelectorAll(".tabline[data-filter]").forEach(t => {
      t.addEventListener("click", () => {
        document.querySelectorAll(".tabline[data-filter]").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        currentFilter = t.dataset.filter || "active";
        renderProducts();
      });
    });

    const createProductModal = document.getElementById("createProductModal");
    const createProductForm = document.getElementById("createProductForm");
    const openCreateProduct = document.getElementById("openCreateProduct");
    const noShopsBlock = document.getElementById("noShopsBlock");
    const shopSelect = document.getElementById("shopSelect");

    async function loadMyShops() {
      try {
        const res = await fetch("/api/my-shops");
        if (!res.ok) return [];
        const data = await res.json();
        return data.shops || [];
      } catch { return []; }
    }

    if (openCreateProduct) {
      openCreateProduct.addEventListener("click", async () => {
        const shops = await loadMyShops();
        if (!shops.length) {
          if (noShopsBlock) noShopsBlock.style.display = "block";
          if (createProductForm) createProductForm.style.display = "none";
        } else {
          if (noShopsBlock) noShopsBlock.style.display = "none";
          if (createProductForm) createProductForm.style.display = "block";
          if (shopSelect) {
            shopSelect.innerHTML = `<option value="">Выбери магазин</option>` +
              shops.map(s => `<option value="${escapeHtml(s.title)}">${escapeHtml(s.title)} (${escapeHtml(s.map || "")} X:${s.x} Z:${s.z})</option>`).join("");
          }
        }
        if (createProductModal) createProductModal.classList.add("active");
        if (window.lucide) lucide.createIcons();
      });
    }

    document.querySelectorAll("[data-close]").forEach(btn => {
      btn.addEventListener("click", () => {
        const m = document.getElementById(btn.dataset.close);
        if (m) m.classList.remove("active");
      });
    });

    document.querySelectorAll(".switch-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".switch-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
      });
    });

    if (createProductForm) {
      createProductForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const err = document.getElementById("createProductError");
        err.textContent = "";
        const activeSwitch = document.querySelector(".switch-tab.active");
        const type = activeSwitch ? activeSwitch.dataset.type : "shop";
        const data = {
          type,
          shop: createProductForm.shop.value,
          item: createProductForm.item.value,
          description: createProductForm.description.value,
          quantity: createProductForm.quantity.value,
          per_slot: createProductForm.per_slot.value,
          measure: createProductForm.querySelector('input[name="measure"]:checked').value,
          price: createProductForm.price.value,
        };
        const res = await fetch("/api/products", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const json = await res.json();
        if (!res.ok) return (err.textContent = json.error || "Ошибка");
        createProductModal.classList.remove("active");
        createProductForm.reset();
        loadProducts();
      });
    }

    const buyProductModal = document.getElementById("buyProductModal");
    const buyProductForm = document.getElementById("buyProductForm");

    if (buyProductForm) {
      buyProductForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const err = document.getElementById("buyProductError");
        err.textContent = "";
        const data = {
          quantity: buyProductForm.quantity.value,
          map: buyProductForm.map.value,
        };
        const res = await fetch(`/api/products/${currentBuyProductId}/buy`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const json = await res.json();
        if (!res.ok) return (err.textContent = json.error || "Ошибка");
        buyProductModal.classList.remove("active");
        buyProductForm.reset();
        loadProducts();
      });
    }

    const searchModal = document.getElementById("searchModal");
    const openSearch = document.getElementById("openSearch");
    const applySearch = document.getElementById("applySearch");
    if (openSearch) openSearch.addEventListener("click", () => searchModal.classList.add("active"));
    if (applySearch) {
      applySearch.addEventListener("click", () => {
        searchQuery.id = document.getElementById("searchId").value;
        searchQuery.player = document.getElementById("searchPlayer").value;
        searchQuery.item = document.getElementById("searchItem").value;
        searchModal.classList.remove("active");
        renderProducts();
      });
    }

    const sortMenu = document.getElementById("sortMenu");
    const openSort = document.getElementById("openSort");
    if (openSort) openSort.addEventListener("click", () => sortMenu.classList.toggle("active"));
    document.querySelectorAll("#sortMenu button").forEach(b => {
      b.addEventListener("click", () => {
        currentSort = b.dataset.sort;
        sortMenu.classList.remove("active");
        renderProducts();
      });
    });

    loadProducts();
    loadPurchases();
  }
  // ============ НЕДВИЖИМОСТЬ ============
  const plotsBody = document.getElementById("plotsBody");
  if (plotsBody) {
    let allPlots = [];

    async function loadPlots() {
      const res = await fetch("/api/plots");
      const data = await res.json();
      allPlots = data.plots || [];
      renderPlots();
    }

    function renderPlots() {
      if (!allPlots.length) {
        plotsBody.innerHTML = `<tr><td colspan="7" class="empty-row">Список объектов пустой</td></tr>`;
        return;
      }
      plotsBody.innerHTML = allPlots.map(p => `
        <tr>
          <td>${escapeHtml(p.nickname || p.username)}</td>
          <td>${escapeHtml(p.title)}</td>
          <td>${escapeHtml(p.map || "—")}</td>
          <td>X: ${p.x}, Z: ${p.z}</td>
          <td>${p.price} AP</td>
          <td>${p.status === "rented" ? "Арендован" : "Свободен"}</td>
          <td>
            ${p.status === "free"
              ? `<button class="btn primary" data-rent="${p.id}" style="padding:6px 12px;font-size:13px">Арендовать</button>`
              : ""}
          </td>
        </tr>
      `).join("");

      plotsBody.querySelectorAll("[data-rent]").forEach(btn => {
        btn.addEventListener("click", async () => {
          const res = await fetch(`/api/plots/${btn.dataset.rent}/rent`, { method: "POST" });
          const json = await res.json();
          if (!res.ok) return alert(json.error || "Ошибка");
          loadPlots();
        });
      });
    }

    const createPlotModal = document.getElementById("createPlotModal");
    const createPlotForm = document.getElementById("createPlotForm");
    const openCreatePlot = document.getElementById("openCreatePlot");

    if (openCreatePlot) {
      openCreatePlot.addEventListener("click", () => createPlotModal.classList.add("active"));
    }

    document.querySelectorAll("[data-plot-type]").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll("[data-plot-type]").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        const label = document.getElementById("mapLabel");
        if (label) label.innerHTML = tab.dataset.plotType === "shop"
          ? 'Магазин <span class="req">*</span>'
          : 'Карта <span class="req">*</span>';
      });
    });

    if (createPlotForm) {
      createPlotForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const err = document.getElementById("createPlotError");
        err.textContent = "";
        const activeTab = document.querySelector("[data-plot-type].active");
        const kind = activeTab ? activeTab.dataset.plotType : "rent";
        const data = {
          map: createPlotForm.map.value,
          title: createPlotForm.title.value,
          x: createPlotForm.x.value,
          z: createPlotForm.z.value,
          price: createPlotForm.price.value,
          kind: kind,
        };
        const res = await fetch("/api/plots", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const json = await res.json();
        if (!res.ok) return (err.textContent = json.error || "Ошибка");
        createPlotModal.classList.remove("active");
        createPlotForm.reset();
        loadPlots();
      });
    }

    loadPlots();
  }

  // ============ ОБЩЕСТВЕННЫЕ МЕСТА ============
  const placesBody = document.getElementById("placesBody");
  if (placesBody) {
    let allPlaces = [];
    let currentFilter = "active";

    async function loadPlaces() {
      const res = await fetch("/api/places");
      const data = await res.json();
      allPlaces = data.places || [];
      renderPlaces();
    }

    function renderPlaces() {
      let list = [...allPlaces];
      if (currentFilter === "active") list = list.filter(p => p.title);

      if (!list.length) {
        placesBody.innerHTML = `<tr><td colspan="6" class="empty-row">Список мест пустой</td></tr>`;
        return;
      }

      placesBody.innerHTML = list.map(p => `
        <tr>
          <td>
            <div class="seller-cell">
              <div class="seller-avatar">
                ${p.avatar ? `<img src="${escapeHtml(p.avatar)}">` : '<i data-lucide="user"></i>'}
              </div>
              <div>
                <div class="seller-name">${escapeHtml(p.nickname || p.username)}</div>
                <div class="seller-role">Ответственный</div>
              </div>
            </div>
          </td>
          <td>${escapeHtml(p.title)}</td>
          <td>${p.x}</td>
          <td>${p.z}</td>
          <td>${new Date(p.created_at).toLocaleDateString("ru")}</td>
          <td>
            <button class="icon-btn" title="Удалить" data-del-place="${p.id}">
              <i data-lucide="trash-2"></i>
            </button>
          </td>
        </tr>
      `).join("");

      if (window.lucide) lucide.createIcons();

      placesBody.querySelectorAll("[data-del-place]").forEach(btn => {
        btn.addEventListener("click", async () => {
          if (!confirm("Удалить место?")) return;
          await fetch(`/api/places/${btn.dataset.delPlace}`, { method: "DELETE" });
          loadPlaces();
        });
      });
    }

    document.querySelectorAll(".tabline").forEach(t => {
      t.addEventListener("click", () => {
        document.querySelectorAll(".tabline").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        currentFilter = t.dataset.filter || "active";
        renderPlaces();
      });
    });

    const createPlaceModal = document.getElementById("createPlaceModal");
    const createPlaceForm = document.getElementById("createPlaceForm");
    const openCreatePlace = document.getElementById("openCreatePlace");

    if (openCreatePlace) {
      openCreatePlace.addEventListener("click", () => createPlaceModal.classList.add("active"));
    }

    document.querySelectorAll("[data-close]").forEach(btn => {
      btn.addEventListener("click", () => {
        const m = document.getElementById(btn.dataset.close);
        if (m) m.classList.remove("active");
      });
    });

    if (createPlaceForm) {
      createPlaceForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const err = document.getElementById("createPlaceError");
        err.textContent = "";
        const data = {
          title: createPlaceForm.title.value,
          x: createPlaceForm.x.value,
          z: createPlaceForm.z.value,
        };
        const res = await fetch("/api/places", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const json = await res.json();
        if (!res.ok) return (err.textContent = json.error || "Ошибка");
        createPlaceModal.classList.remove("active");
        createPlaceForm.reset();
        loadPlaces();
      });
    }

    loadPlaces();
  }

  // ============ УВЕДОМЛЕНИЯ ============
  const openNotifications = document.getElementById("openNotifications");
  if (openNotifications) {
    openNotifications.addEventListener("click", () => {
      alert("Уведомлений пока нет");
    });
  }

});
  // ============ АДМИНКА ============
  const adminUsersBody = document.getElementById("adminUsersBody");
  if (adminUsersBody) {
    let adminUserIdForPassword = null;
    let adminUserIdForBalance = null;

    async function loadAdminUsers() {
      const res = await fetch("/api/admin/users");
      if (!res.ok) return;
      const data = await res.json();
      const users = data.users || [];
      if (!users.length) {
        adminUsersBody.innerHTML = `<tr><td colspan="6" class="empty-row">Пусто</td></tr>`;
        return;
      }
      adminUsersBody.innerHTML = users.map(u => `
        <tr>
          <td>${u.id}</td>
          <td>
            <div class="seller-cell">
              <div class="seller-avatar">${u.avatar ? `<img src="${escapeHtml(u.avatar)}">` : '<i data-lucide="user"></i>'}</div>
              <div>
                <div class="seller-name">${escapeHtml(u.nickname || u.username)}</div>
                <div class="seller-role">@${escapeHtml(u.username)}</div>
              </div>
            </div>
          </td>
          <td>${escapeHtml(u.role || "—")}</td>
          <td>${u.balance || 0} АР</td>
          <td>${u.is_banned ? '<span style="color:#d33">Забанен</span>' : '<span style="color:#2a8">Активен</span>'}</td>
          <td>
            <button class="icon-btn" title="Сменить пароль" data-pwd="${u.id}"><i data-lucide="key"></i></button>
            <button class="icon-btn" title="Баланс" data-bal="${u.id}"><i data-lucide="coins"></i></button>
            <button class="icon-btn" title="${u.is_banned ? 'Разбанить' : 'Забанить'}" data-ban="${u.id}" data-banstate="${u.is_banned}">
              <i data-lucide="shield-off"></i>
            </button>
            <button class="icon-btn" title="Удалить" data-deluser="${u.id}"><i data-lucide="trash-2"></i></button>
          </td>
        </tr>
      `).join("");
      if (window.lucide) lucide.createIcons();

      adminUsersBody.querySelectorAll("[data-pwd]").forEach(btn => {
        btn.addEventListener("click", () => {
          adminUserIdForPassword = btn.dataset.pwd;
          document.getElementById("adminPasswordModal").classList.add("active");
        });
      });
      adminUsersBody.querySelectorAll("[data-bal]").forEach(btn => {
        btn.addEventListener("click", () => {
          adminUserIdForBalance = btn.dataset.bal;
          document.getElementById("adminBalanceModal").classList.add("active");
        });
      });
      adminUsersBody.querySelectorAll("[data-ban]").forEach(btn => {
        btn.addEventListener("click", async () => {
          const isBanned = btn.dataset.banstate === "true";
          if (!confirm(isBanned ? "Разбанить?" : "Забанить?")) return;
          await fetch(`/api/admin/users/${btn.dataset.ban}/ban`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ban: !isBanned }),
          });
          loadAdminUsers();
        });
      });
      adminUsersBody.querySelectorAll("[data-deluser]").forEach(btn => {
        btn.addEventListener("click", async () => {
          if (!confirm("Удалить пользователя?")) return;
          await fetch(`/api/admin/users/${btn.dataset.deluser}`, { method: "DELETE" });
          loadAdminUsers();
        });
      });
    }

    document.getElementById("adminPasswordForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = document.getElementById("adminPasswordError");
      err.textContent = "";
      const pass = e.target.password.value;
      const res = await fetch(`/api/admin/users/${adminUserIdForPassword}/password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: pass }),
      });
      const json = await res.json();
      if (!res.ok) return (err.textContent = json.error || "Ошибка");
      document.getElementById("adminPasswordModal").classList.remove("active");
      e.target.reset();
      alert("Пароль изменён");
    });

    document.getElementById("adminBalanceForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = document.getElementById("adminBalanceError");
      err.textContent = "";
      const amount = e.target.amount.value;
      const res = await fetch(`/api/admin/users/${adminUserIdForBalance}/balance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: amount }),
      });
      const json = await res.json();
      if (!res.ok) return (err.textContent = json.error || "Ошибка");
      document.getElementById("adminBalanceModal").classList.remove("active");
      e.target.reset();
      loadAdminUsers();
    });

    document.querySelectorAll("[data-close]").forEach(btn => {
      btn.addEventListener("click", () => {
        const m = document.getElementById(btn.dataset.close);
        if (m) m.classList.remove("active");
      });
    });

    // Вкладки админки
    document.querySelectorAll("[data-atab]").forEach(t => {
      t.addEventListener("click", () => {
        document.querySelectorAll("[data-atab]").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        const tab = t.dataset.atab;
        document.getElementById("adminUsersSection").style.display = tab === "users" ? "block" : "none";
        document.getElementById("adminProductsSection").style.display = tab === "products" ? "block" : "none";
        document.getElementById("adminPlotsSection").style.display = tab === "plots" ? "block" : "none";
        document.getElementById("adminPlacesSection").style.display = tab === "places" ? "block" : "none";
        if (tab === "products") loadAdminProducts();
        if (tab === "plots") loadAdminPlots();
        if (tab === "places") loadAdminPlaces();
      });
    });

    async function loadAdminProducts() {
      const res = await fetch("/api/products");
      const data = await res.json();
      const list = data.products || [];
      const body = document.getElementById("adminProductsBody");
      if (!list.length) { body.innerHTML = `<tr><td colspan="6" class="empty-row">Пусто</td></tr>`; return; }
      body.innerHTML = list.map(p => `
        <tr>
          <td>${p.id}</td>
          <td>${escapeHtml(p.nickname || p.username)}</td>
          <td>${escapeHtml(p.item)}</td>
          <td>${p.price} AP</td>
          <td>${p.quantity} * ${p.per_slot || 1}</td>
          <td><button class="icon-btn" data-deladminprod="${p.id}"><i data-lucide="trash-2"></i></button></td>
        </tr>
      `).join("");
      if (window.lucide) lucide.createIcons();
      body.querySelectorAll("[data-deladminprod]").forEach(b => {
        b.addEventListener("click", async () => {
          if (!confirm("Удалить товар?")) return;
          await fetch(`/api/admin/products/${b.dataset.deladminprod}`, { method: "DELETE" });
          loadAdminProducts();
        });
      });
    }

    async function loadAdminPlots() {
      const res = await fetch("/api/plots");
      const data = await res.json();
      const list = data.plots || [];
      const body = document.getElementById("adminPlotsBody");
      if (!list.length) { body.innerHTML = `<tr><td colspan="6" class="empty-row">Пусто</td></tr>`; return; }
      body.innerHTML = list.map(p => `
        <tr>
          <td>${p.id}</td>
          <td>${escapeHtml(p.nickname || p.username)}</td>
          <td>${escapeHtml(p.title)}</td>
          <td>${p.kind === "shop" ? "Магазин" : "Аренда"}</td>
          <td>${p.price} AP</td>
          <td><button class="icon-btn" data-deladminplot="${p.id}"><i data-lucide="trash-2"></i></button></td>
        </tr>
      `).join("");
      if (window.lucide) lucide.createIcons();
      body.querySelectorAll("[data-deladminplot]").forEach(b => {
        b.addEventListener("click", async () => {
          if (!confirm("Удалить объект?")) return;
          await fetch(`/api/admin/plots/${b.dataset.deladminplot}`, { method: "DELETE" });
          loadAdminPlots();
        });
      });
    }

    async function loadAdminPlaces() {
      const res = await fetch("/api/places");
      const data = await res.json();
      const list = data.places || [];
      const body = document.getElementById("adminPlacesBody");
      if (!list.length) { body.innerHTML = `<tr><td colspan="6" class="empty-row">Пусто</td></tr>`; return; }
      body.innerHTML = list.map(p => `
        <tr>
          <td>${p.id}</td>
          <td>${escapeHtml(p.nickname || p.username)}</td>
          <td>${escapeHtml(p.title)}</td>
          <td>${p.x}</td>
          <td>${p.z}</td>
          <td><button class="icon-btn" data-deladminplace="${p.id}"><i data-lucide="trash-2"></i></button></td>
        </tr>
      `).join("");
      if (window.lucide) lucide.createIcons();
      body.querySelectorAll("[data-deladminplace]").forEach(b => {
        b.addEventListener("click", async () => {
          if (!confirm("Удалить место?")) return;
          await fetch(`/api/admin/places/${b.dataset.deladminplace}`, { method: "DELETE" });
          loadAdminPlaces();
        });
      });
    }

    const reloadBtn = document.getElementById("reloadAdmin");
    if (reloadBtn) reloadBtn.addEventListener("click", loadAdminUsers);

    loadAdminUsers();
  }
