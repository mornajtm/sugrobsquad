// ============ МОДАЛКА ============
const authModal = document.getElementById("authModal");
const openAuthBtn = document.getElementById("openAuthBtn");
const startPlayBtn = document.getElementById("startPlayBtn");
const closeAuthBtn = document.getElementById("closeAuthBtn");

function openModal() { if (authModal) authModal.classList.add("active"); }
function closeModal() { if (authModal) authModal.classList.remove("active"); }

if (openAuthBtn) openAuthBtn.addEventListener("click", openModal);
if (startPlayBtn) startPlayBtn.addEventListener("click", openModal);
if (closeAuthBtn) closeAuthBtn.addEventListener("click", closeModal);

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
    document.getElementById(target + "Form").classList.add("active");
  });
});

function togglePass(btn) {
  const input = btn.parentElement.querySelector("input");
  input.type = input.type === "password" ? "text" : "password";
}

function copyIP() {
  navigator.clipboard.writeText("sugrob.squad");
  alert("IP скопирован: sugrob.squad");
}

// ============ РЕГИСТРАЦИЯ ============
const registerForm = document.getElementById("registerForm");
if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = document.getElementById("registerError");
    err.textContent = "";
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: registerForm.username.value,
        password: registerForm.password.value,
      }),
    });
    const json = await res.json();
    if (!res.ok) return (err.textContent = json.error);
    window.location.href = "/profile";
  });
}

// ============ ВХОД ============
const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = document.getElementById("loginError");
    err.textContent = "";
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: loginForm.username.value,
        password: loginForm.password.value,
      }),
    });
    const json = await res.json();
    if (!res.ok) return (err.textContent = json.error);
    window.location.href = "/profile";
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
        <h1 class="profile-name">Редактирование</h1>
        <div style="margin-top:20px">
          <input id="nickname" placeholder="Никнейм" value="${escapeHtml(u.nickname)}"
            style="width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;margin-bottom:12px">
          <input id="avatar" placeholder="Ссылка на аватар" value="${escapeHtml(u.avatar)}"
            style="width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;margin-bottom:12px">
          <textarea id="about" placeholder="О себе" rows="4"
            style="width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;margin-bottom:12px">${escapeHtml(u.about)}</textarea>
          <div class="btn-row-left">
            <button class="btn primary" onclick="saveProfile()">Сохранить</button>
            <button class="btn" onclick="cancelEdit()">Отмена</button>
          </div>
        </div>
      `;
    } else {
      profileCard.innerHTML = `
        <div class="avatar">${u.avatar ? `<img src="${escapeHtml(u.avatar)}" alt="">` : "🎮"}</div>
        <h1 class="profile-name">${escapeHtml(u.nickname)}</h1>
        <p class="profile-handle">@${escapeHtml(u.username)}</p>
        <span class="role">${escapeHtml(u.role)}</span>
        <p class="profile-about">${escapeHtml(u.about) || "Пока нет описания..."}</p>
        <p class="profile-meta">
          В скваде с: ${new Date(u.created_at).toLocaleDateString("ru")}
        </p>
        <div class="btn-row-left">
          <button class="btn primary" onclick="startEdit()">Редактировать</button>
        </div>
      `;
    }
  }

  window.startEdit = () => { editMode = true; renderProfile(); };
  window.cancelEdit = () => { editMode = false; renderProfile(); };

  window.saveProfile = async () => {
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
  };

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

// ============ УТИЛИТА ============
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
