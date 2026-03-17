import React, { useState, useEffect } from "react";

type SectionId =
  | "dashboard"
  | "accounts"
  | "masslooking"
  | "inviting"
  | "tagging"
  | "parsing"
  | "settings";

type AccountStatus = "active" | "spam_block" | "banned";

interface Account {
  id: number;
  phone: string;
  display_name: string;
  status: AccountStatus;
  proxy: string | null;
  group_name: string | null;
  tasks_per_day: number;
  tasks_limit: number;
  last_activity_at: string;
  created_at: string;
}

const API_BASE = "http://127.0.0.1:8000";

const App: React.FC = () => {
  const [activeSection, setActiveSection] = useState<SectionId>("dashboard");
  const [activeModal, setActiveModal] = useState<
    | null
    | "addAccount"
    | "createMasslooking"
    | "createInviting"
    | "createTagging"
    | "createParsing"
  >(null);

  const [masslookingMode, setMasslookingMode] = useState<"safe" | "balanced" | "aggressive">(
    "balanced",
  );

  // состояние аккаунтов
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [accountsError, setAccountsError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<"all" | AccountStatus>("all");
  const [groupFilter, setGroupFilter] = useState<string>("all");

  // поля модалки "Добавить аккаунт"
  const [newAccPhone, setNewAccPhone] = useState("");
  const [newAccName, setNewAccName] = useState("");
  const [newAccProxy, setNewAccProxy] = useState("");
  const [newAccGroup, setNewAccGroup] = useState("");

  // auth состояние для SettingsSection
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [authMessage, setAuthMessage] = useState<string | null>(null);

  // загрузка аккаунтов
  const loadAccounts = async () => {
    setAccountsLoading(true);
    setAccountsError(null);
    try {
      const url = new URL("/api/v1/accounts/", API_BASE);
      if (statusFilter !== "all") {
        url.searchParams.set("status", statusFilter);
      }
      if (groupFilter !== "all" && groupFilter !== "") {
        url.searchParams.set("group", groupFilter);
      }

      const res = await fetch(url.toString());
      if (!res.ok) {
        throw new Error("Ошибка загрузки аккаунтов");
      }
      const data = (await res.json()) as Account[];
      setAccounts(data);
    } catch (e: any) {
      setAccountsError(e.message || "Ошибка загрузки аккаунтов");
    } finally {
      setAccountsLoading(false);
    }
  };

  useEffect(() => {
    loadAccounts();
  }, [statusFilter, groupFilter]);

  const handleCreateAccount = async () => {
    try {
      const payload = {
        phone: newAccPhone,
        display_name: newAccName,
        status: "active",
        proxy: newAccProxy || null,
        group_name: newAccGroup || null,
        tasks_per_day: 0,
        tasks_limit: 500,
      };
      const res = await fetch(`${API_BASE}/api/v1/accounts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Ошибка создания аккаунта");
      }
      setNewAccPhone("");
      setNewAccName("");
      setNewAccProxy("");
      setNewAccGroup("");
      setActiveModal(null);
      await loadAccounts();
    } catch (e: any) {
      alert(e.message || "Ошибка создания аккаунта");
    }
  };

  const handleDeleteAccount = async (id: number) => {
    if (!window.confirm("Удалить аккаунт?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/accounts/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Ошибка удаления аккаунта");
      }
      await loadAccounts();
    } catch (e: any) {
      alert(e.message || "Ошибка удаления аккаунта");
    }
  };

  const handleRegister = async () => {
    setAuthMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Ошибка регистрации");
      }
      setAuthMessage("Регистрация успешна");
    } catch (e: any) {
      setAuthMessage(e.message || "Ошибка регистрации");
    }
  };

  const handleLogin = async () => {
    setAuthMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Ошибка логина");
      }
      const data = await res.json();
      setToken(data.access_token);
      setAuthMessage("Логин успешен, токен получен");
    } catch (e: any) {
      setAuthMessage(e.message || "Ошибка логина");
    }
  };

  return (
    <div className="container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
          </svg>
          TraffSoft
        </div>
        <nav>
          <NavItem
            label="Дашборд"
            icon={
              <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                />
              </svg>
            }
            active={activeSection === "dashboard"}
            onClick={() => setActiveSection("dashboard")}
          />
          <NavItem
            label="Аккаунты"
            icon={
              <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                />
              </svg>
            }
            active={activeSection === "accounts"}
            onClick={() => setActiveSection("accounts")}
          />
          <NavItem
            label="Масслукинг"
            icon={
              <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            }
            active={activeSection === "masslooking"}
            onClick={() => setActiveSection("masslooking")}
          />
          <NavItem
            label="Инвайтинг"
            icon={
              <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                />
              </svg>
            }
            active={activeSection === "inviting"}
            onClick={() => setActiveSection("inviting")}
          />
          <NavItem
            label="Тегер"
            icon={
              <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                />
              </svg>
            }
            active={activeSection === "tagging"}
            onClick={() => setActiveSection("tagging")}
          />
          <NavItem
            label="Парсинг"
            icon={
              <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
                />
              </svg>
            }
            active={activeSection === "parsing"}
            onClick={() => setActiveSection("parsing")}
          />
          <NavItem
            label="Настройки"
            icon={
              <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c-.94 1.543.826 3.31 2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            }
            active={activeSection === "settings"}
            onClick={() => setActiveSection("settings")}
          />
        </nav>
      </aside>

      {/* Main content */}
      <main className="main-content">
        {activeSection === "dashboard" && <DashboardSection />}
        {activeSection === "accounts" && (
          <AccountsSection
            accounts={accounts}
            loading={accountsLoading}
            error={accountsError}
            statusFilter={statusFilter}
            setStatusFilter={setStatusFilter}
            groupFilter={groupFilter}
            setGroupFilter={setGroupFilter}
            onOpenAddAccount={() => setActiveModal("addAccount")}
            onDeleteAccount={handleDeleteAccount}
          />
        )}
        {activeSection === "masslooking" && (
          <MasslookingSection onOpenCreate={() => setActiveModal("createMasslooking")} />
        )}
        {activeSection === "inviting" && (
          <InvitingSection onOpenCreate={() => setActiveModal("createInviting")} />
        )}
        {activeSection === "tagging" && (
          <TaggingSection onOpenCreate={() => setActiveModal("createTagging")} />
        )}
        {activeSection === "parsing" && (
          <ParsingSection onOpenCreate={() => setActiveModal("createParsing")} />
        )}
        {activeSection === "settings" && (
          <SettingsSection
            email={email}
            setEmail={setEmail}
            password={password}
            setPassword={setPassword}
            token={token}
            authMessage={authMessage}
            onRegister={handleRegister}
            onLogin={handleLogin}
          />
        )}
      </main>

      {/* Modals */}
      {activeModal === "addAccount" && (
        <Modal title="Добавить аккаунт" onClose={() => setActiveModal(null)}>
          <div className="form-group">
            <label className="form-label">Номер телефона</label>
            <input
              className="form-input"
              type="tel"
              placeholder="+7 999 123-45-67"
              value={newAccPhone}
              onChange={(e) => setNewAccPhone(e.target.value)}
            />
            <div className="help-text">Формат: +7 или +380 с кодом страны</div>
          </div>
          <div className="form-group">
            <label className="form-label">Отображаемое имя</label>
            <input
              className="form-input"
              type="text"
              placeholder="Alex_Marketing"
              value={newAccName}
              onChange={(e) => setNewAccName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Прокси (опционально)</label>
            <input
              className="form-input"
              type="text"
              placeholder="host:port:login:password"
              value={newAccProxy}
              onChange={(e) => setNewAccProxy(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Группа (опционально)</label>
            <input
              className="form-input"
              type="text"
              placeholder="Группа 1"
              value={newAccGroup}
              onChange={(e) => setNewAccGroup(e.target.value)}
            />
          </div>
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={() => setActiveModal(null)}>
              Отмена
            </button>
            <button className="btn btn-primary" onClick={handleCreateAccount}>
              Добавить
            </button>
          </div>
        </Modal>
      )}

      {/* Остальные модалки оставляем как были */}
      {activeModal === "createMasslooking" && (
        <Modal title="Создать задачу масслукинга" onClose={() => setActiveModal(null)}>
          {/* ... тело модалки без изменений ... */}
          <div className="form-group">
            <label className="form-label">Название задачи</label>
            <input className="form-input" type="text" placeholder="Криптоканалы масслукинг" />
          </div>
          <div className="form-group">
            <label className="form-label">Целевые источники</label>
            <textarea
              className="form-textarea"
              placeholder="@channel1&#10;@channel2&#10;@channel3"
            />
            <div className="help-text">По одному username или ссылке на строку</div>
          </div>
          <div className="form-group">
            <label className="form-label">Выберите аккаунты</label>
            <select className="form-select" multiple style={{ height: 120 }}>
              <option>+7 999 123-45-67 (Alex_Marketing)</option>
              <option>+7 999 234-56-78 (Maria_SMM)</option>
              <option>+7 999 345-67-89 (Ivan_Traffic)</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Режим работы</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="mode"
                  value="safe"
                  checked={masslookingMode === "safe"}
                  onChange={() => setMasslookingMode("safe")}
                />
                <span>Safe (200-500/день)</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="mode"
                  value="balanced"
                  checked={masslookingMode === "balanced"}
                  onChange={() => setMasslookingMode("balanced")}
                />
                <span>Balanced (1000-2000/день)</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="mode"
                  value="aggressive"
                  checked={masslookingMode === "aggressive"}
                  onChange={() => setMasslookingMode("aggressive")}
                />
                <span>Aggressive (3000+/день)</span>
              </label>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Лимит просмотров</label>
            <input className="form-input" type="number" defaultValue={2000} />
          </div>
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={() => setActiveModal(null)}>
              Отмена
            </button>
            <button
              className="btn btn-primary"
              onClick={() => {
                alert("Задача масслукинга будет создана через API /api/v1/masslooking/tasks");
                setActiveModal(null);
              }}
            >
              Создать
            </button>
          </div>
        </Modal>
      )}

      {activeModal === "createInviting" && (
        <Modal title="Создать задачу инвайтинга" onClose={() => setActiveModal(null)}>
          {/* тело как было, опускаю для краткости */}
          <div className="form-group">
            <label className="form-label">Название задачи</label>
            <input className="form-input" type="text" placeholder="Целевая группа #1" />
          </div>
          {/* ... остальные поля ... */}
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={() => setActiveModal(null)}>
              Отмена
            </button>
            <button
              className="btn btn-primary"
              onClick={() => {
                alert("Задача инвайтинга будет создана через API /api/v1/inviting/tasks");
                setActiveModal(null);
              }}
            >
              Создать
            </button>
          </div>
        </Modal>
      )}

      {activeModal === "createTagging" && (
        <Modal title="Создать задачу тегера" onClose={() => setActiveModal(null)}>
          {/* тело как было */}
          <div className="form-group">
            <label className="form-label">Название задачи</label>
            <input className="form-input" type="text" placeholder="Отметки в сторис" />
          </div>
          {/* ... */}
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={() => setActiveModal(null)}>
              Отмена
            </button>
            <button
              className="btn btn-primary"
              onClick={() => {
                alert("Задача тегера будет создана через API /api/v1/tagging/tasks");
                setActiveModal(null);
              }}
            >
              Создать
            </button>
          </div>
        </Modal>
      )}

      {activeModal === "createParsing" && (
        <Modal title="Создать парсинг" onClose={() => setActiveModal(null)}>
          {/* тело как было */}
          <div className="form-group">
            <label className="form-label">Название задачи</label>
            <input className="form-input" type="text" placeholder="Парсинг конкурентов" />
          </div>
          {/* ... */}
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={() => setActiveModal(null)}>
              Отмена
            </button>
            <button
              className="btn btn-primary"
              onClick={() => {
                alert("Задача парсинга будет создана через API /api/v1/parsing/tasks");
                setActiveModal(null);
              }}
            >
              Создать
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
};

const NavItem: React.FC<{
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}> = ({ label, icon, active, onClick }) => (
  <div className={`nav-item ${active ? "active" : ""}`} onClick={onClick}>
    {icon}
    {label}
  </div>
);

const DashboardSection: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then((data) => setBackendStatus(data.status))
      .catch(() => setBackendStatus("error"));
  }, []);

  return (
    <section className="section active" id="dashboard">
      <div className="header">
        <h1>Дашборд</h1>
        {backendStatus && (
          <span
            style={{
              fontSize: 14,
              marginRight: 12,
              color: backendStatus === "ok" ? "#22c55e" : "#ef4444",
            }}
          >
            Backend: {backendStatus}
          </span>
        )}
        <button className="btn btn-primary">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          Создать задачу
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Активных аккаунтов</div>
          <div className="stat-value">24</div>
          <div className="stat-change positive">+3 за сегодня</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Задач в работе</div>
          <div className="stat-value">8</div>
          <div className="stat-change positive">2 завершено</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Просмотров сегодня</div>
          <div className="stat-value">3,247</div>
          <div className="stat-change positive">+18%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Инвайтов сегодня</div>
          <div className="stat-value">156</div>
          <div className="stat-change negative">-5%</div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <div className="table-title">Активные задачи</div>
        </div>
        <div style={{ padding: 20 }}>
          <TaskItem
            name="Масслукинг - Криптоканалы"
            status="Активна"
            statusClass="status-active"
            stats={["Просмотров: 847 / 2000", "Аккаунтов: 5", "Режим: Balanced"]}
            progress={42}
          />
          <TaskItem
            name="Инвайтинг - Целевая группа #1"
            status="Активна"
            statusClass="status-active"
            stats={["Приглашено: 82 / 200", "Аккаунтов: 3", "Режим: Теневой"]}
            progress={41}
          />
          <TaskItem
            name="Парсинг - Конкуренты"
            status="В очереди"
            statusClass="status-pending"
            stats={["Собрано: 0 / 1000", "Источников: 3"]}
            progress={0}
          />
        </div>
      </div>
    </section>
  );
};

const TaskItem: React.FC<{
  name: string;
  status: string;
  statusClass: string;
  stats: string[];
  progress: number;
}> = ({ name, status, statusClass, stats, progress }) => (
  <div className="task-item">
    <div className="task-header">
      <div className="task-name">{name}</div>
      <span className={`status-badge ${statusClass}`}>{status}</span>
    </div>
    <div className="task-stats">
      {stats.map((s) => (
        <span key={s}>{s}</span>
      ))}
    </div>
    <div className="progress-bar">
      <div className="progress-fill" style={{ width: `${progress}%` }} />
    </div>
  </div>
);

const AccountsSection: React.FC<{
  accounts: Account[];
  loading: boolean;
  error: string | null;
  statusFilter: "all" | AccountStatus;
  setStatusFilter: (s: "all" | AccountStatus) => void;
  groupFilter: string;
  setGroupFilter: (g: string) => void;
  onOpenAddAccount: () => void;
  onDeleteAccount: (id: number) => void;
}> = ({
  accounts,
  loading,
  error,
  statusFilter,
  setStatusFilter,
  groupFilter,
  setGroupFilter,
  onOpenAddAccount,
  onDeleteAccount,
}) => {
  const statusLabel = (s: AccountStatus): string => {
    if (s === "active") return "Активен";
    if (s === "spam_block") return "Спам-блок";
    if (s === "banned") return "Забанен";
    return s;
  };

  const statusClass = (s: AccountStatus): string => {
    if (s === "active") return "status-active";
    if (s === "spam_block") return "status-spam";
    if (s === "banned") return "status-banned";
    return "";
  };

  const groups = Array.from(
    new Set(accounts.map((a) => a.group_name).filter((g): g is string => !!g)),
  );

  return (
    <section className="section" id="accounts">
      <div className="header">
        <h1>Управление аккаунтами</h1>
        <button className="btn btn-primary" onClick={onOpenAddAccount}>
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          Добавить аккаунт
        </button>
      </div>

      <div className="filters">
        <select
          className="filter-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as "all" | AccountStatus)}
        >
          <option value="all">Все статусы</option>
          <option value="active">Активные</option>
          <option value="spam_block">Спам-блок</option>
          <option value="banned">Забанены</option>
        </select>
        <select
          className="filter-select"
          value={groupFilter}
          onChange={(e) => setGroupFilter(e.target.value)}
        >
          <option value="all">Все группы</option>
          {groups.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </div>

      <div className="table-container">
        <div className="table-header">
          <div className="table-title">Список аккаунтов ({accounts.length})</div>
        </div>
        {loading ? (
          <div style={{ padding: 20 }}>Загрузка...</div>
        ) : error ? (
          <div style={{ padding: 20, color: "#ef4444" }}>{error}</div>
        ) : accounts.length === 0 ? (
          <div style={{ padding: 20, color: "#94a3b8" }}>Аккаунтов пока нет</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Телефон</th>
                <th>Имя</th>
                <th>Статус</th>
                <th>Прокси</th>
                <th>Задач/день</th>
                <th>Последняя активность</th>
                <th>Группа</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((acc) => (
                <tr key={acc.id}>
                  <td>{acc.phone}</td>
                  <td>{acc.display_name}</td>
                  <td>
                    <span className={`status-badge ${statusClass(acc.status)}`}>
                      {statusLabel(acc.status)}
                    </span>
                  </td>
                  <td>{acc.proxy || "-"}</td>
                  <td>
                    {acc.tasks_per_day} / {acc.tasks_limit}
                  </td>
                  <td>{new Date(acc.last_activity_at).toLocaleString()}</td>
                  <td>{acc.group_name || "-"}</td>
                  <td>
                    <div className="action-buttons">
                      <button className="btn-icon" title="Удалить" onClick={() => onDeleteAccount(acc.id)}>
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
};

const MasslookingSection: React.FC<{ onOpenCreate: () => void }> = ({ onOpenCreate }) => (
  <section className="section" id="masslooking">
    <div className="header">
      <h1>Масслукинг</h1>
      <button className="btn btn-primary" onClick={onOpenCreate}>
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
        </svg>
        Создать задачу
      </button>
    </div>

    <div className="table-container">
      <div className="table-header">
        <div className="table-title">Задачи масслукинга</div>
      </div>
      <div style={{ padding: 20, color: "#94a3b8" }}>Пока пусто — задачи будут позже.</div>
    </div>
  </section>
);

const InvitingSection: React.FC<{ onOpenCreate: () => void }> = ({ onOpenCreate }) => (
  <section className="section" id="inviting">
    <div className="header">
      <h1>Инвайтинг</h1>
      <button className="btn btn-primary" onClick={onOpenCreate}>
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
        </svg>
        Создать задачу
      </button>
    </div>

    <div className="table-container">
      <div className="table-header">
        <div className="table-title">Задачи инвайтинга</div>
      </div>
      <div style={{ padding: 20, color: "#94a3b8" }}>Пока пусто — задачи будут позже.</div>
    </div>
  </section>
);

const TaggingSection: React.FC<{ onOpenCreate: () => void }> = ({ onOpenCreate }) => (
  <section className="section" id="tagging">
    <div className="header">
      <h1>Отметки и тегер</h1>
      <button className="btn btn-primary" onClick={onOpenCreate}>
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
        </svg>
        Создать задачу
      </button>
    </div>

    <div className="empty-state">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
        />
      </svg>
      <h3>Нет активных задач</h3>
      <p>Создайте задачу для отметок в историях или тегера в чатах</p>
    </div>
  </section>
);

const ParsingSection: React.FC<{ onOpenCreate: () => void }> = ({ onOpenCreate }) => (
  <section className="section" id="parsing">
    <div className="header">
      <h1>Парсинг аудитории</h1>
      <button className="btn btn-primary" onClick={onOpenCreate}>
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
        </svg>
        Создать парсинг
      </button>
    </div>

    <div className="table-container">
      <div className="table-header">
        <div className="table-title">Задачи парсинга</div>
      </div>
      <div style={{ padding: 20, color: "#94a3b8" }}>Пока пусто — задачи будут позже.</div>
    </div>
  </section>
);

const SettingsSection: React.FC<{
  email: string;
  setEmail: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  token: string | null;
  authMessage: string | null;
  onRegister: () => void;
  onLogin: () => void;
}> = ({ email, setEmail, password, setPassword, token, authMessage, onRegister, onLogin }) => (
  <section className="section" id="settings">
    <div className="header">
      <h1>Настройки</h1>
    </div>

    <div className="table-container" style={{ marginBottom: 20 }}>
      <div className="table-header">
        <div className="table-title">Авторизация (backend)</div>
      </div>
      <div style={{ padding: 24 }}>
        <div className="form-group">
          <label className="form-label">Email</label>
          <input
            className="form-input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@example.com"
            style={{ maxWidth: 300 }}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Пароль</label>
          <input
            className="form-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            style={{ maxWidth: 300 }}
          />
        </div>
        <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
          <button className="btn btn-secondary" onClick={onRegister}>
            Регистрация
          </button>
          <button className="btn btn-primary" onClick={onLogin}>
            Логин
          </button>
        </div>
        {authMessage && (
          <div
            style={{
              fontSize: 14,
              color: authMessage.includes("успеш") ? "#22c55e" : "#ef4444",
            }}
          >
            {authMessage}
          </div>
        )}
        {token && (
          <div style={{ marginTop: 8, fontSize: 12, color: "#94a3b8" }}>
            Токен (обрезан): {token.slice(0, 20)}...
          </div>
        )}
      </div>
    </div>

    <div className="table-container">
      <div className="table-header">
        <div className="table-title">Пользователи</div>
        <button className="btn btn-secondary">Добавить пользователя</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Роль</th>
            <th>Аккаунтов</th>
            <th>Последний вход</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>admin@traffsoft.com</td>
            <td>Admin</td>
            <td>24</td>
            <td>Сейчас</td>
            <td>
              <div className="action-buttons">
                <button className="btn-icon">✏️</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div className="table-container" style={{ marginTop: 20 }}>
      <div className="table-header">
        <div className="table-title">Лимиты и безопасность</div>
      </div>
      <div style={{ padding: 24 }}>
        <div className="form-group">
          <label className="form-label">Лимит просмотров на аккаунт в день</label>
          <input className="form-input" type="number" defaultValue={500} style={{ maxWidth: 200 }} />
        </div>
        <div className="form-group">
          <label className="form-label">Лимит инвайтов на аккаунт в день</label>
          <input className="form-input" type="number" defaultValue={50} style={{ maxWidth: 200 }} />
        </div>
        <div className="form-group">
          <label className="form-label">Задержка между действиями (мс)</label>
          <input className="form-input" type="number" defaultValue={2000} style={{ maxWidth: 200 }} />
        </div>
        <button
          className="btn btn-primary"
          onClick={() => alert("Сохранение лимитов будет реализовано через API /api/v1/settings")}
        >
          Сохранить настройки
        </button>
      </div>
    </div>
  </section>
);

const Modal: React.FC<{ title: string; onClose: () => void; children: React.ReactNode }> = ({
  title,
  onClose,
  children,
}) => (
  <div className="modal active" onClick={(e) => e.target === e.currentTarget && onClose()}>
    <div className="modal-content">
      <div className="modal-header">
        <h2 className="modal-title">{title}</h2>
        <button className="modal-close" onClick={onClose}>
          ×
        </button>
      </div>
      <div className="modal-body">{children}</div>
    </div>
  </div>
);

export default App;
