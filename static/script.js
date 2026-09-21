  // ============ АДМИНКА ============
  const adminUsersBody = document.getElementById("adminUsersBody");
  if (adminUsersBody) {
    let adminUserIdForPassword = null;
    let adminUserIdForBalance = null;

    async function loadAdminUsers() {
      const res = await fetch("/api/admin/users");
      if (!res.ok) {
        adminUsersBody.innerHTML = `<tr><td colspan="6" class="empty-row">Ошибка загрузки</td></tr>`;
        return;
      }
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

    const adminPasswordForm = document.getElementById("adminPasswordForm");
    if (adminPasswordForm) {
      adminPasswordForm.addEventListener("submit", async (e) => {
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
    }

    const adminBalanceForm = document.getElementById("adminBalanceForm");
    if (adminBalanceForm) {
      adminBalanceForm.addEventListener("submit", async (e) => {
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
    }

    document.querySelectorAll("[data-close]").forEach(btn => {
      btn.addEventListener("click", () => {
        const m = document.getElementById(btn.dataset.close);
        if (m) m.classList.remove("active");
      });
    });

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
