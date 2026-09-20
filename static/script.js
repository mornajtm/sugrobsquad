document.addEventListener("DOMContentLoaded", () => {

  // ============ МОДАЛКА ============
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

  // ============ ВКЛАДКИ ВХОД / РЕГИСТРАЦИЯ ============
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

  // ============ ПОКАЗ ПАРОЛЯ ============
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
        window.location.href = "/profile";
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

            <label style="font-weight:600;font-size:14px;display:block;margin-bottom:6px">Ссылка на аватар</label>
            <input id="avatar" placeholder="https://..." value="${escapeHtml(u.avatar)}"
              style="width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;margin-bottom:14px">

            <label style="font-weight:600;font-size:14px;display:block;margin-bottom:6px">О себе</label>
            <textarea id="about" rows="4" placeholder="Расскажи о себе..."
              style="width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;margin-bottom:16px">${escapeHtml(u.about)}</textarea>

            <div class="btn-row-left">
              <button class="btn primary" id="saveProfileBtn">Сохранить</button>
              <button class="btn" id="cancelEditBtn">Отмена</button>
            </div>
          </div>
        `;
        document.getElementById("saveProfileBtn").addEventListener("click", saveProfile);
        document.getElementById("cancelEditBtn").addEventListener("click", () => {
          editMode = false; renderProfile();
        });
      } else {
        profileCard.innerHTML = `
          <div class="avatar">${u.avatar ? `<img src="${escapeHtml(u.avatar)}" alt="">` : "🎮"}</div>
          <h1 class="profile-name">${escapeHtml(u.nickname)}</h1>
          <p class="profile-handle">@${escapeHtml(u.username)}</p>
          <span class="role">${escapeHtml(u.role)}</span>
          <p class="profile-about">${escapeHtml(u.about) || "Пока нет описания..."}</p>
          <p class="profile-meta">В скваде с: ${new Date(u.created_at).toLocaleDateString("ru")}</p>
          <div class="btn-row-left">
            <button class="btn primary" id="editProfileBtn">Редактировать</button>
          </div>
        `;
        document.getElementById("editProfileBtn").addEventListener("click", () => {
          editMode = true; renderProfile();
        });
      }
    }

    async function saveProfile() {
      const data = {
        nickname: document.getElementById("nickname").value,
        avatar: document.getElementById("avatar").value,
        about: document.getElementById("about").value,
      };
      const res = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        userData = { ...userData, ...data };
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
      sideMenu.classList.remove("active");
      sideMenuOverlay.classList.remove("active");
    });
  }

  // ============ АНИМАЦИЯ ПОЯВЛЕНИЯ ============
  const joinSection = document.getElementById("joinSection");
  if (joinSection) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) entry.target.classList.add("visible");
      });
    }, { threshold: 0.15 });
    observer.observe(joinSection);
  }

  // ============ УТИЛИТА ============
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

});
  // ============ ТОРГОВЛЯ ============
  const productsBody = document.getElementById("productsBody");
  if (productsBody) {
    let allProducts = [];
    let currentFilter = "active";
    let currentSort = "default";
    let searchQuery = { id: "", player: "", item: "" };

    async function loadProducts() {
      const res = await fetch("/api/products");
      const data = await res.json();
      allProducts = data.products || [];
      renderProducts();
    }

    function renderProducts() {
      let list = [...allProducts];

      if (currentFilter === "active") list = list.filter(p => p.status === "active");
      if (currentFilter === "mine") list = list.filter(p => p.is_mine);

      if (searchQuery.id) list = list.filter(p => String(p.id).includes(searchQuery.id));
      if (searchQuery.player) list = list.filter(p => (p.nickname || p.username || "").toLowerCase().includes(searchQuery.player.toLowerCase()));
      if (searchQuery.item) list = list.filter(p => (p.item || "").toLowerCase().includes(searchQuery.item.toLowerCase()));

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
              <div class="seller-avatar">${p.avatar ? `<img src="${escapeHtml(p.avatar)}">` : "🎮"}</div>
              <div>
                <div class="seller-name">${escapeHtml(p.nickname || p.username)}</div>
                <div class="seller-role">Продавец</div>
              </div>
            </div>
          </td>
          <td>${escapeHtml(p.item)}</td>
          <td>${p.quantity} * 1 ${escapeHtml(p.measure)}</td>
          <td>${p.price} AP</td>
          <td>${escapeHtml(p.shop || "—")}</td>
          <td>${new Date(p.created_at).toLocaleDateString("ru")}</td>
          <td><button class="icon-btn" title="Удалить" data-del="${p.id}">🗑</button></td>
        </tr>
      `).join("");

      productsBody.querySelectorAll("[data-del]").forEach(btn => {
        btn.addEventListener("click", async () => {
          if (!confirm("Удалить товар?")) return;
          await fetch(`/api/products/${btn.dataset.del}`, { method: "DELETE" });
          loadProducts();
        });
      });
    }

    document.querySelectorAll(".tabline").forEach(t => {
      t.addEventListener("click", () => {
        document.querySelectorAll(".tabline").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        currentFilter = t.dataset.filter;
        renderProducts();
      });
    });

    // Модалка создания товара
    const createProductModal = document.getElementById("createProductModal");
    const createProductForm = document.getElementById("createProductForm");
    const openCreateProduct = document.getElementById("openCreateProduct");

    if (openCreateProduct) {
      openCreateProduct.addEventListener("click", () => {
        createProductModal.classList.add("active");
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
        const label = document.getElementById("shopLabel");
        if (label) label.textContent = tab.dataset.type === "rent" ? "Аренда *" : "Магазин *";
      });
    });

    if (createProductForm) {
      createProductForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const err = document.getElementById("createProductError");
        err.textContent = "";
        const type = document.querySelector(".switch-tab.active")?.dataset.type || "shop";
        const data = {
          type,
          shop: createProductForm.shop.value,
          item: createProductForm.item.value,
          description: createProductForm.description.value,
          quantity: createProductForm.quantity.value,
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

    // Поиск
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

    // Сортировка
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
        plotsBody.innerHTML = `<tr><td colspan="7" class="empty-row">Список участков пустой</td></tr>
