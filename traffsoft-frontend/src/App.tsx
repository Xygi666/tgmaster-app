import React, { useState, useEffect, useCallback } from "react";

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

interface AudienceSource {
  id: number;
  type: string;
  username: string | null;
  external_id: string | null;
  title: string | null;
  description: string | null;
  member_count: number | null;
  is_verified: boolean;
  is_private: boolean;
  last_parsed_at: string | null;
  parse_errors: number;
  created_at: string;
}

interface SourceStats {
  source_id: number;
  total_members: number;
  new_members_today: number;
  active_last_day: number;
  active_last_week: number;
  active_last_month: number;
  long_ago: number;
  hidden: number;
  bots: number;
  with_usernames: number;
  with_phones: number;
  with_bio: number;
  with_photos: number;
  languages: Record<string, number>;
  countries: Record<string, number>;
}

interface ParseJob {
  id: number;
  source_id: number;
  source_title: string | null;
  mode: string;
  status: string;
  processed_items: number;
  new_members: number;
  created_at: string;
  finished_at: string | null;
}

interface ParseJobProgress {
  id: number;
  status: string;
  processed_items: number;
  new_members: number;
  skipped_members: number;
  total_items: number | null;
  error_message: string | null;
}

interface AudienceMember {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  bio: string | null;
  lang_code: string | null;
  country_code: string | null;
  is_bot: boolean;
  is_verified: boolean;
  is_deleted: boolean;
  has_photo: boolean;
  has_phone: boolean;
  last_seen_bucket: string;
  last_seen_at: string | null;
  sources_count: number;
  sources: string[] | null;
  created_at: string;
}

interface AnalyticsOverview {
  total_sources: number;
  total_members: number;
  members_with_usernames: number;
  members_with_phones: number;
  members_with_bio: number;
  active_last_week: number;
  active_last_month: number;
  bots_count: number;
  unique_languages: number;
  top_sources: { Title: string; members: number }[];
  top_languages: Record<string, number>[];
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
    | "addSource"
    | "createParseJob"
    | "sourceStats"
    | "exportMembers"
  >(null);

  const [masslookingMode, setMasslookingMode] = useState<"safe" | "balanced" | "aggressive">("balanced");

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | AccountStatus>("all");
  const [groupFilter, setGroupFilter] = useState<string>("all");

  const [newAccPhone, setNewAccPhone] = useState("");
  const [newAccName, setNewAccName] = useState("");
  const [newAccProxy, setNewAccProxy] = useState("");
  const [newAccGroup, setNewAccGroup] = useState("");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [authMessage, setAuthMessage] = useState<string | null>(null);

  const loadAccounts = async () => {
    setAccountsLoading(true);
    setAccountsError(null);
    try {
      const url = new URL("/api/v1/accounts/", API_BASE);
      if (statusFilter !== "all") url.searchParams.set("status", statusFilter);
      if (groupFilter !== "all" && groupFilter !== "") url.searchParams.set("group", groupFilter);
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error("Ошибка загрузки аккаунтов");
      setAccounts(await res.json());
    } catch (e: any) {
      setAccountsError(e.message);
    } finally {
      setAccountsLoading(false);
    }
  };

  useEffect(() => { loadAccounts(); }, [statusFilter, groupFilter]);

  const handleCreateAccount = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/accounts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: newAccPhone, display_name: newAccName, status: "active",
          proxy: newAccProxy || null, group_name: newAccGroup || null,
          tasks_per_day: 0, tasks_limit: 500,
        }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      setNewAccPhone(""); setNewAccName(""); setNewAccProxy(""); setNewAccGroup("");
      setActiveModal(null); loadAccounts();
    } catch (e: any) { alert(e.message); }
  };

  const handleDeleteAccount = async (id: number) => {
    if (!confirm("Удалить аккаунт?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/accounts/${id}`, { method: "DELETE" });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      loadAccounts();
    } catch (e: any) { alert(e.message); }
  };

  const handleRegister = async () => {
    setAuthMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      setAuthMessage("Регистрация успешна");
    } catch (e: any) { setAuthMessage(e.message); }
  };

  const handleLogin = async () => {
    setAuthMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      const data = await res.json();
      setToken(data.access_token);
      setAuthMessage("Логин успешен");
    } catch (e: any) { setAuthMessage(e.message); }
  };

  return (
    <div className="container">
      <aside className="sidebar">
        <div className="logo">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
          </svg>
          TraffSoft
        </div>
        <nav>
          <NavItem label="Дашборд" icon={<HomeIcon />} active={activeSection === "dashboard"} onClick={() => setActiveSection("dashboard")} />
          <NavItem label="Аккаунты" icon={<UsersIcon />} active={activeSection === "accounts"} onClick={() => setActiveSection("accounts")} />
          <NavItem label="Масслукинг" icon={<EyeIcon />} active={activeSection === "masslooking"} onClick={() => setActiveSection("masslooking")} />
          <NavItem label="Инвайтинг" icon={<UserAddIcon />} active={activeSection === "inviting"} onClick={() => setActiveSection("inviting")} />
          <NavItem label="Тегер" icon={<TagIcon />} active={activeSection === "tagging"} onClick={() => setActiveSection("tagging")} />
          <NavItem label="Парсинг" icon={<DatabaseIcon />} active={activeSection === "parsing"} onClick={() => setActiveSection("parsing")} />
          <NavItem label="Настройки" icon={<SettingsIcon />} active={activeSection === "settings"} onClick={() => setActiveSection("settings")} />
        </nav>
      </aside>

      <main className="main-content">
        {activeSection === "dashboard" && <DashboardSection />}
        {activeSection === "accounts" && (
          <AccountsSection accounts={accounts} loading={accountsLoading} error={accountsError}
            statusFilter={statusFilter} setStatusFilter={setStatusFilter}
            groupFilter={groupFilter} setGroupFilter={setGroupFilter}
            onOpenAddAccount={() => setActiveModal("addAccount")}
            onDeleteAccount={handleDeleteAccount} />
        )}
        {activeSection === "masslooking" && <MasslookingSection onOpenCreate={() => setActiveModal("createMasslooking")} />}
        {activeSection === "inviting" && <InvitingSection onOpenCreate={() => setActiveModal("createInviting")} />}
        {activeSection === "tagging" && <TaggingSection onOpenCreate={() => setActiveModal("createTagging")} />}
        {activeSection === "parsing" && <ParsingSection onOpenAddSource={() => setActiveModal("addSource")} onOpenCreateJob={() => setActiveModal("createParseJob")} onOpenStats={(id) => { (window as any).__statsSourceId = id; setActiveModal("sourceStats"); }} />}
        {activeSection === "settings" && (
          <SettingsSection email={email} setEmail={setEmail} password={password} setPassword={setPassword}
            token={token} authMessage={authMessage} onRegister={handleRegister} onLogin={handleLogin} />
        )}
      </main>

      {activeModal === "addAccount" && (
        <Modal title="Добавить аккаунт" onClose={() => setActiveModal(null)}>
          <div className="form-group"><label className="form-label">Номер телефона</label>
            <input className="form-input" type="tel" placeholder="+7 999 123-45-67" value={newAccPhone} onChange={(e) => setNewAccPhone(e.target.value)} /></div>
          <div className="form-group"><label className="form-label">Отображаемое имя</label>
            <input className="form-input" type="text" placeholder="Alex_Marketing" value={newAccName} onChange={(e) => setNewAccName(e.target.value)} /></div>
          <div className="form-group"><label className="form-label">Прокси (опционально)</label>
            <input className="form-input" type="text" placeholder="host:port:login:password" value={newAccProxy} onChange={(e) => setNewAccProxy(e.target.value)} /></div>
          <div className="form-group"><label className="form-label">Группа (опционально)</label>
            <input className="form-input" type="text" placeholder="Группа 1" value={newAccGroup} onChange={(e) => setNewAccGroup(e.target.value)} /></div>
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={() => setActiveModal(null)}>Отмена</button>
            <button className="btn btn-primary" onClick={handleCreateAccount}>Добавить</button>
          </div>
        </Modal>
      )}

      {activeModal === "createMasslooking" && <MasslookingModal masslookingMode={masslookingMode} setMasslookingMode={setMasslookingMode} onClose={() => setActiveModal(null)} />}
      {activeModal === "createInviting" && <InvitingModal onClose={() => setActiveModal(null)} />}
      {activeModal === "createTagging" && <TaggingModal onClose={() => setActiveModal(null)} />}
      {activeModal === "addSource" && <AddSourceModal onClose={() => setActiveModal(null)} />}
      {activeModal === "createParseJob" && <CreateParseJobModal onClose={() => setActiveModal(null)} />}
      {activeModal === "sourceStats" && <SourceStatsModal sourceId={(window as any).__statsSourceId} onClose={() => setActiveModal(null)} />}
      {activeModal === "exportMembers" && <ExportModal onClose={() => setActiveModal(null)} />}
    </div>
  );
};

const NavItem: React.FC<{ label: string; icon: React.ReactNode; active: boolean; onClick: () => void }> = ({ label, icon, active, onClick }) => (
  <div className={`nav-item ${active ? "active" : ""}`} onClick={onClick}>{icon}{label}</div>
);

const DashboardSection: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`).then(r => r.json()).then(d => setBackendStatus(d.status)).catch(() => setBackendStatus("error"));
    fetch(`${API_BASE}/api/v1/audience/analytics/overview`).then(r => r.json()).then(setAnalytics).catch(() => {});
  }, []);

  return (
    <section className="section" id="dashboard">
      <div className="header">
        <h1>Дашборд</h1>
        {backendStatus && <span style={{ fontSize: 14, color: backendStatus === "ok" ? "#22c55e" : "#ef4444" }}>Backend: {backendStatus}</span>}
      </div>
      <div className="stats-grid">
        <div className="stat-card"><div className="stat-label">Источников</div><div className="stat-value">{analytics?.total_sources ?? "-"}</div></div>
        <div className="stat-card"><div className="stat-label">Участников</div><div className="stat-value">{analytics?.total_members?.toLocaleString() ?? "-"}</div><div className="stat-change positive">из парсинга</div></div>
        <div className="stat-card"><div className="stat-label">Активных (неделя)</div><div className="stat-value">{analytics?.active_last_week?.toLocaleString() ?? "-"}</div></div>
        <div className="stat-card"><div className="stat-label">С username</div><div className="stat-value">{analytics?.members_with_usernames?.toLocaleString() ?? "-"}</div></div>
      </div>
      {analytics && analytics.top_languages.length > 0 && (
        <div className="table-container">
          <div className="table-header"><div className="table-title">Языки аудитории</div></div>
          <div style={{ padding: "12px 20px", display: "flex", gap: 8, flexWrap: "wrap" }}>
            {analytics.top_languages.slice(0, 8).map(langObj => {
              const [lang, count] = Object.entries(langObj)[0];
              return <span key={lang} style={{ background: "#1e293b", padding: "4px 10px", borderRadius: 6, fontSize: 13 }}>{lang?.toUpperCase()}: {Number(count).toLocaleString()}</span>;
            })}
          </div>
        </div>
      )}
      <div className="table-container" style={{ marginTop: 16 }}>
        <div className="table-header"><div className="table-title">Топ источников по размеру</div></div>
        {analytics && analytics.top_sources.length > 0 ? (
          <table>
            <thead><tr><th>Название</th><th>Участников</th></tr></thead>
            <tbody>
              {analytics.top_sources.map((s, i) => <tr key={i}><td>{s.Title || "-"}</td><td>{(s.members as number).toLocaleString()}</td></tr>)}
            </tbody>
          </table>
        ) : <div style={{ padding: 20, color: "#94a3b8" }}>Пока нет данных — запустите парсинг</div>}
      </div>
    </section>
  );
};

const AccountsSection: React.FC<{
  accounts: Account[]; loading: boolean; error: string | null;
  statusFilter: "all" | AccountStatus; setStatusFilter: (s: "all" | AccountStatus) => void;
  groupFilter: string; setGroupFilter: (g: string) => void;
  onOpenAddAccount: () => void; onDeleteAccount: (id: number) => void;
}> = ({ accounts, loading, error, statusFilter, setStatusFilter, groupFilter, setGroupFilter, onOpenAddAccount, onDeleteAccount }) => {
  const statusLabel = (s: AccountStatus) => ({ active: "Активен", spam_block: "Спам-блок", banned: "Забанен" }[s] ?? s);
  const statusClass = (s: AccountStatus) => ({ active: "status-active", spam_block: "status-spam", banned: "status-banned" }[s] ?? "");
  const groups = Array.from(new Set(accounts.map(a => a.group_name).filter((g): g is string => !!g)));

  return (
    <section className="section" id="accounts">
      <div className="header"><h1>Управление аккаунтами</h1><button className="btn btn-primary" onClick={onOpenAddAccount}><PlusIcon /> Добавить аккаунт</button></div>
      <div className="filters">
        <select className="filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value as "all" | AccountStatus)}>
          <option value="all">Все статусы</option><option value="active">Активные</option><option value="spam_block">Спам-блок</option><option value="banned">Забанены</option>
        </select>
        <select className="filter-select" value={groupFilter} onChange={e => setGroupFilter(e.target.value)}>
          <option value="all">Все группы</option>{groups.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
      </div>
      <div className="table-container">
        <div className="table-header"><div className="table-title">Список аккаунтов ({accounts.length})</div></div>
        {loading ? <div style={{ padding: 20 }}>Загрузка...</div>
          : error ? <div style={{ padding: 20, color: "#ef4444" }}>{error}</div>
          : accounts.length === 0 ? <div style={{ padding: 20, color: "#94a3b8" }}>Аккаунтов пока нет</div>
          : <table><thead><tr><th>Телефон</th><th>Имя</th><th>Статус</th><th>Прокси</th><th>Задач/день</th><th>Группа</th><th>Действия</th></tr></thead>
            <tbody>{accounts.map(acc => (
              <tr key={acc.id}>
                <td>{acc.phone}</td><td>{acc.display_name}</td>
                <td><span className={`status-badge ${statusClass(acc.status)}`}>{statusLabel(acc.status)}</span></td>
                <td>{acc.proxy || "-"}</td><td>{acc.tasks_per_day}/{acc.tasks_limit}</td><td>{acc.group_name || "-"}</td>
                <td><button className="btn-icon" title="Удалить" onClick={() => onDeleteAccount(acc.id)}>🗑️</button></td>
              </tr>
            ))}</tbody></table>}
      </div>
    </section>
  );
};

function ParsingSection({ onOpenAddSource, onOpenCreateJob, onOpenStats }: { onOpenAddSource: () => void; onOpenCreateJob: () => void; onOpenStats: (id: number) => void }) {
  const [tab, setTab] = useState<"sources" | "jobs" | "members" | "analytics">("sources");
  const [sources, setSources] = useState<AudienceSource[]>([]);
  const [jobs, setJobs] = useState<ParseJob[]>([]);
  const [members, setMembers] = useState<AudienceMember[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [memberFilters, setMemberFilters] = useState({ has_username: undefined as boolean | undefined, lang_codes: "", activity: "" });
  const [deleteLoading, setDeleteLoading] = useState<number | null>(null);
  const [selectedJobs, setSelectedJobs] = useState<Set<number>>(new Set());
  const [jobsStatusFilter, setJobsStatusFilter] = useState<string>("all");

  const loadSources = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/sources`);
      if (res.ok) setSources(await res.json());
    } finally { setLoading(false); }
  }, []);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/parse-jobs`);
      if (res.ok) setJobs(await res.json());
    } finally { setLoading(false); }
  }, []);

  const loadMembers = useCallback(async () => {
    setLoading(true);
    try {
      const filters: any = { limit: 50 };
      if (memberFilters.has_username !== undefined) filters.has_username = memberFilters.has_username;
      if (memberFilters.lang_codes) filters.lang_codes = memberFilters.lang_codes.split(",").map(s => s.trim()).filter(Boolean);
      if (memberFilters.activity) filters.activity = memberFilters.activity.split(",").map(s => s.trim()).filter(Boolean);
      const res = await fetch(`${API_BASE}/api/v1/audience/members`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(filters),
      });
      if (res.ok) setMembers(await res.json());
    } finally { setLoading(false); }
  }, [memberFilters]);

  const loadAnalytics = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/analytics/overview`);
      if (res.ok) setAnalytics(await res.json());
    } catch {}
  }, []);

  useEffect(() => { if (tab === "sources") loadSources(); }, [tab, loadSources]);
  useEffect(() => { if (tab === "jobs") loadJobs(); }, [tab, loadJobs]);
  useEffect(() => { if (tab === "members") loadMembers(); }, [tab, loadMembers]);
  useEffect(() => { if (tab === "analytics") loadAnalytics(); }, [tab, loadAnalytics]);

  useEffect(() => {
    if (tab === "jobs") {
      const interval = setInterval(() => {
        const running = jobs.some(j => j.status === "running" || j.status === "pending");
        if (running) loadJobs();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [tab, jobs, loadJobs]);

  const handleDeleteSource = async (id: number) => {
    if (!confirm("Удалить источник и все собранные данные?")) return;
    setDeleteLoading(id);
    try {
      await fetch(`${API_BASE}/api/v1/audience/sources/${id}`, { method: "DELETE" });
      loadSources();
    } catch {} finally { setDeleteLoading(null); }
  };

  const handleDeleteJob = async (id: number) => {
    if (!confirm("Удалить задачу?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/parse-jobs/${id}`, { method: "DELETE" });
      if (res.ok) { setSelectedJobs(s => { const n = new Set(s); n.delete(id); return n; }); loadJobs(); }
    } catch {}
  };

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedJobs);
    if (ids.length === 0) { alert("Выберите задачи"); return; }
    if (!confirm(`Удалить ${ids.length} задач?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/parse-jobs/bulk-delete`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_ids: ids }),
      });
      if (res.ok) { setSelectedJobs(new Set()); loadJobs(); }
    } catch {}
  };

  const handleBulkDeleteByStatus = async (status: string) => {
    const matching = jobs.filter(j => j.status === status);
    if (matching.length === 0) { alert(`Нет задач со статусом "${status}"`); return; }
    if (!confirm(`Удалить ${matching.length} задач со статусом "${status}"?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/parse-jobs/bulk-delete`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (res.ok) { setSelectedJobs(new Set()); loadJobs(); }
    } catch {}
  };

  const toggleJobSelect = (id: number) => {
    setSelectedJobs(s => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  };

  const toggleAllJobs = () => {
    const filtered = jobsStatusFilter === "all" ? jobs : jobs.filter(j => j.status === jobsStatusFilter);
    if (selectedJobs.size === filtered.length) setSelectedJobs(new Set());
    else setSelectedJobs(new Set(filtered.map(j => j.id)));
  };

  const handleExport = async (format: string) => {
    const filters: any = { limit: 10000 };
    if (memberFilters.has_username !== undefined) filters.has_username = memberFilters.has_username;
    if (memberFilters.lang_codes) filters.lang_codes = memberFilters.lang_codes.split(",").map(s => s.trim()).filter(Boolean);
    if (memberFilters.activity) filters.activity = memberFilters.activity.split(",").map(s => s.trim()).filter(Boolean);
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/members/export`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filters, format }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a"); a.href = url;
        a.download = `audience_export.${format === "phones" ? "txt" : format === "txt" ? "txt" : format}`;
        a.click(); URL.revokeObjectURL(url);
      }
    } catch (e) { alert("Ошибка экспорта"); }
  };

  const statusBadge = (s: string) => {
    const map: Record<string, string> = { pending: "status-pending", running: "status-active", completed: "status-active", failed: "status-banned", paused: "status-spam", cancelled: "status-banned" };
    const labels: Record<string, string> = { pending: "В очереди", running: "Выполняется", completed: "Завершён", failed: "Ошибка", paused: "Приостановлен", cancelled: "Отменён" };
    return <span className={`status-badge ${map[s] || ""}`}>{labels[s] || s}</span>;
  };

  return (
    <section className="section" id="parsing">
      <div className="header"><h1>Парсинг аудитории</h1><button className="btn btn-primary" onClick={onOpenAddSource}><PlusIcon /> Добавить источник</button></div>

      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {(["sources", "jobs", "members", "analytics"] as const).map(t => (
          <button key={t} className={`btn ${tab === t ? "btn-primary" : "btn-secondary"}`} onClick={() => setTab(t)} style={{ padding: "6px 16px", fontSize: 13 }}>
            {{ sources: "Источники", jobs: "Задачи", members: "Участники", analytics: "Аналитика" }[t]}
            {t === "sources" && sources.length > 0 && <span style={{ marginLeft: 6, background: "#1e293b", padding: "1px 6px", borderRadius: 10, fontSize: 11 }}>{sources.length}</span>}
            {t === "jobs" && jobs.filter(j => j.status === "running" || j.status === "pending").length > 0 && <span style={{ marginLeft: 6, background: "#22c55e", padding: "1px 6px", borderRadius: 10, fontSize: 11 }}>{jobs.filter(j => j.status === "running" || j.status === "pending").length}</span>}
          </button>
        ))}
      </div>

      {tab === "sources" && (
        <div className="table-container">
          <div className="table-header"><div className="table-title">Источники ({sources.length})</div></div>
          {loading ? <div style={{ padding: 20 }}>Загрузка...</div>
          : sources.length === 0 ? <div style={{ padding: 20, color: "#94a3b8" }}>
            Нет источников. Добавьте канал или группу через кнопку "Добавить источник".
          </div>
          : <table><thead><tr><th>Название</th><th>Username</th><th>Тип</th><th>Парсилось</th><th>Проверен</th><th>Последний парсинг</th><th>Ошибки</th><th>Действия</th></tr></thead>
            <tbody>{sources.map(s => (
              <tr key={s.id}>
                <td><strong>{s.title || "-"}</strong></td>
                <td style={{ color: "#60a5fa" }}>{s.username || "-"}</td>
                <td>{s.type === "telegram_channel" ? "Канал" : s.type === "telegram_group" ? "Группа" : s.type}</td>
                <td>{s.member_count?.toLocaleString() ?? "-"}</td>
                <td>{s.is_verified ? "✅" : "❌"}</td>
                <td>{s.last_parsed_at ? new Date(s.last_parsed_at).toLocaleString() : "Никогда"}</td>
                <td>{s.parse_errors > 0 ? <span style={{ color: "#ef4444" }}>{s.parse_errors}</span> : "0"}</td>
                <td>
                  <div className="action-buttons">
                    <button className="btn-icon" title="Статистика" onClick={() => onOpenStats(s.id)}>📊</button>
                    <button className="btn-icon" title="Создать парсинг" onClick={onOpenCreateJob}>▶️</button>
                    <button className="btn-icon" title="Удалить" onClick={() => handleDeleteSource(s.id)} disabled={deleteLoading === s.id}>🗑️</button>
                  </div>
                </td>
              </tr>
            ))}</tbody></table>}
        </div>
      )}

      {tab === "jobs" && (
        <div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              {(["all", "completed", "failed", "running", "pending", "cancelled"] as const).map(s => {
                const count = s === "all" ? jobs.length : jobs.filter(j => j.status === s).length;
                return (
                  <button key={s} className={`btn ${jobsStatusFilter === s ? "btn-primary" : "btn-secondary"}`}
                    onClick={() => setJobsStatusFilter(s)} style={{ fontSize: 12, padding: "4px 10px" }}>
                    {s === "all" ? `Все (${jobs.length})` : `${s} (${count})`}
                  </button>
                );
              })}
            </div>
            <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
              {selectedJobs.size > 0 && (
                <button className="btn btn-secondary" onClick={handleBulkDelete} style={{ fontSize: 12, padding: "4px 10px", color: "#ef4444" }}>
                  Удалить выбранные ({selectedJobs.size})
                </button>
              )}
              <button className="btn btn-secondary" onClick={() => handleBulkDeleteByStatus("failed")} style={{ fontSize: 12, padding: "4px 10px" }}>
                Удалить ошибки
              </button>
              <button className="btn btn-secondary" onClick={() => handleBulkDeleteByStatus("completed")} style={{ fontSize: 12, padding: "4px 10px" }}>
                Удалить завершённые
              </button>
              <button className="btn btn-primary" onClick={onOpenCreateJob} style={{ fontSize: 13, padding: "6px 12px" }}><PlusIcon /> Новая задача</button>
            </div>
          </div>
          <div className="table-container">
            <div className="table-header"><div className="table-title">
              Задачи парсинга
              {(jobsStatusFilter !== "all" || selectedJobs.size > 0) && (
                <span style={{ fontSize: 13, color: "#94a3b8", marginLeft: 8 }}>
                  ({jobsStatusFilter === "all" ? jobs.length : jobs.filter(j => j.status === jobsStatusFilter).length})
                </span>
              )}
            </div></div>
            {loading ? <div style={{ padding: 20 }}>Загрузка...</div>
            : (jobsStatusFilter === "all" ? jobs : jobs.filter(j => j.status === jobsStatusFilter)).length === 0
              ? <div style={{ padding: 20, color: "#94a3b8" }}>Нет задач с таким статусом.</div>
              : <table><thead><tr>
                <th style={{ width: 40 }}>
                  <input type="checkbox" checked={selectedJobs.size > 0 && selectedJobs.size === (jobsStatusFilter === "all" ? jobs : jobs.filter(j => j.status === jobsStatusFilter)).length}
                    onChange={toggleAllJobs} />
                </th>
                <th>ID</th><th>Источник</th><th>Режим</th><th>Статус</th><th>Обработано</th><th>Новых</th><th>Создана</th><th>Завершена</th><th style={{ width: 60 }}>Удалить</th>
              </tr></thead>
                <tbody>{(jobsStatusFilter === "all" ? jobs : jobs.filter(j => j.status === jobsStatusFilter)).map(j => (
                  <tr key={j.id} style={{ opacity: selectedJobs.has(j.id) ? 1 : undefined }}>
                    <td><input type="checkbox" checked={selectedJobs.has(j.id)} onChange={() => toggleJobSelect(j.id)} /></td>
                    <td>#{j.id}</td><td>{j.source_title || `#${j.source_id}`}</td>
                    <td><span style={{ fontSize: 12, background: "#1e293b", padding: "2px 6px", borderRadius: 4 }}>{j.mode}</span></td>
                    <td>{statusBadge(j.status)}</td>
                    <td>{j.processed_items.toLocaleString()}</td><td>{j.new_members.toLocaleString()}</td>
                    <td style={{ fontSize: 12 }}>{new Date(j.created_at).toLocaleString()}</td>
                    <td style={{ fontSize: 12 }}>{j.finished_at ? new Date(j.finished_at).toLocaleString() : "-"}</td>
                    <td><button className="btn-icon" title="Удалить" onClick={() => handleDeleteJob(j.id)}>🗑️</button></td>
                  </tr>
                ))}</tbody></table>}
          </div>
        </div>
      )}

      {tab === "members" && (
        <>
          <div className="filters" style={{ marginBottom: 12 }}>
            <select className="filter-select" value={String(memberFilters.has_username)} onChange={e => setMemberFilters(f => ({ ...f, has_username: e.target.value === "true" ? true : e.target.value === "false" ? false : undefined }))}>
              <option value="">Все</option><option value="true">С username</option><option value="false">Без username</option>
            </select>
            <input className="filter-select" placeholder="Языки: ru, en, uk" value={memberFilters.lang_codes} onChange={e => setMemberFilters(f => ({ ...f, lang_codes: e.target.value }))} style={{ maxWidth: 200 }} />
            <input className="filter-select" placeholder="Активность: online, day, week" value={memberFilters.activity} onChange={e => setMemberFilters(f => ({ ...f, activity: e.target.value }))} style={{ maxWidth: 220 }} />
            <button className="btn btn-secondary" onClick={loadMembers} style={{ fontSize: 13 }}>Фильтровать</button>
            <button className="btn btn-secondary" onClick={() => handleExport("csv")} style={{ fontSize: 13 }}>Export CSV</button>
            <button className="btn btn-secondary" onClick={() => handleExport("txt")} style={{ fontSize: 13 }}>Export @usernames</button>
          </div>
          <div className="table-container">
            <div className="table-header"><div className="table-title">Участники ({members.length})</div></div>
            {loading ? <div style={{ padding: 20 }}>Загрузка...</div>
            : members.length === 0 ? <div style={{ padding: 20, color: "#94a3b8" }}>Нет участников. Запустите парсинг источника.</div>
            : <table><thead><tr><th>@username</th><th>Имя</th><th>Язык</th><th>Бот</th><th>Активность</th><th>Источников</th></tr></thead>
              <tbody>{members.map(m => (
                <tr key={m.id}>
                  <td style={{ color: "#60a5fa" }}>{m.username ? `@${m.username}` : m.phone || "-"}</td>
                  <td>{[m.first_name, m.last_name].filter(Boolean).join(" ") || "-"}</td>
                  <td>{m.lang_code?.toUpperCase() || "-"}</td>
                  <td>{m.is_bot ? "🤖" : ""}</td>
                  <td>{m.last_seen_bucket}</td>
                  <td>{m.sources_count}</td>
                </tr>
              ))}</tbody></table>}
          </div>
        </>
      )}

      {tab === "analytics" && (
        analytics ? (
          <>
            <div className="stats-grid">
              <div className="stat-card"><div className="stat-label">Всего источников</div><div className="stat-value">{analytics.total_sources}</div></div>
              <div className="stat-card"><div className="stat-label">Всего участников</div><div className="stat-value">{analytics.total_members.toLocaleString()}</div></div>
              <div className="stat-card"><div className="stat-label">Активных (7 дн)</div><div className="stat-value">{analytics.active_last_week.toLocaleString()}</div></div>
              <div className="stat-card"><div className="stat-label">Активных (30 дн)</div><div className="stat-value">{analytics.active_last_month.toLocaleString()}</div></div>
              <div className="stat-card"><div className="stat-label">С username</div><div className="stat-value">{analytics.members_with_usernames.toLocaleString()}</div></div>
              <div className="stat-card"><div className="stat-label">С телефоном</div><div className="stat-value">{analytics.members_with_phones.toLocaleString()}</div></div>
              <div className="stat-card"><div className="stat-label">С био</div><div className="stat-value">{analytics.members_with_bio.toLocaleString()}</div></div>
              <div className="stat-card"><div className="stat-label">Боты</div><div className="stat-value">{analytics.bots_count.toLocaleString()}</div></div>
            </div>
            {analytics.top_languages.length > 0 && (
              <div className="table-container" style={{ marginTop: 16 }}>
                <div className="table-header"><div className="table-title">Языки</div></div>
                <div style={{ padding: "12px 20px" }}>
                  {analytics.top_languages.slice(0, 15).map(langObj => {
                    const [lang, count] = Object.entries(langObj)[0];
                    const max = analytics.top_languages[0] ? Object.values(analytics.top_languages[0])[0] as number : 1;
                    const pct = Math.round((Number(count) / max) * 100);
                    return (
                      <div key={lang} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                        <span style={{ width: 40, fontSize: 13, color: "#94a3b8" }}>{String(lang).toUpperCase()}</span>
                        <div style={{ flex: 1, background: "#1e293b", borderRadius: 4, height: 8 }}>
                          <div style={{ width: `${pct}%`, background: "#3b82f6", borderRadius: 4, height: 8 }} />
                        </div>
                        <span style={{ fontSize: 13, color: "#94a3b8", width: 60, textAlign: "right" }}>{Number(count).toLocaleString()}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        ) : <div style={{ padding: 20, color: "#94a3b8" }}>Загрузка аналитики...</div>
      )}
    </section>
  );
}

const AddSourceModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [link, setLink] = useState("");
  const [type, setType] = useState<"telegram_group" | "telegram_channel">("telegram_group");
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!link.trim()) { setError("Введите ссылку или username"); return; }
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/sources`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, link: link.trim(), title: title.trim() || undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ошибка");
      onClose();
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Modal title="Добавить источник" onClose={onClose}>
      <div className="form-group"><label className="form-label">Тип</label>
        <select className="form-select" value={type} onChange={e => setType(e.target.value as any)}>
          <option value="telegram_group">Группа</option><option value="telegram_channel">Канал</option>
        </select>
      </div>
      <div className="form-group"><label className="form-label">Ссылка или username</label>
        <input className="form-input" placeholder="@channel_name или https://t.me/channel_name" value={link} onChange={e => setLink(e.target.value)} />
        <div className="help-text">Можно указать @username, ссылку или просто название (без @)</div>
      </div>
      <div className="form-group"><label className="form-label">Название (опционально)</label>
        <input className="form-input" placeholder="Мой канал" value={title} onChange={e => setTitle(e.target.value)} />
      </div>
      {error && <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 8 }}>{error}</div>}
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Отмена</button>
        <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}>{loading ? "Добавляю..." : "Добавить"}</button>
      </div>
    </Modal>
  );
};

const CreateParseJobModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [sources, setSources] = useState<AudienceSource[]>([]);
  const [sourceId, setSourceId] = useState<number | "">("");
  const [mode, setMode] = useState("members_full");
  const [limit, setLimit] = useState("");
  const [delayMs, setDelayMs] = useState("500");
  const [skipBots, setSkipBots] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/audience/sources`).then(r => r.json()).then(setSources).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    if (!sourceId) { setError("Выберите источник"); return; }
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/audience/parse-jobs`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_id: Number(sourceId),
          mode,
          limit_members: limit ? Number(limit) : null,
          delay_ms: Number(delayMs),
          skip_bots: skipBots,
          skip_deleted: true,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ошибка");
      onClose();
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Modal title="Создать задачу парсинга" onClose={onClose}>
      <div className="form-group"><label className="form-label">Источник</label>
        <select className="form-select" value={String(sourceId)} onChange={e => setSourceId(e.target.value ? Number(e.target.value) : "")}>
          <option value="">-- Выберите источник --</option>
          {sources.map(s => <option key={s.id} value={String(s.id)}>{s.title || s.username || `#${s.id}`}</option>)}
        </select>
        {sources.length === 0 && <div className="help-text">Сначала добавьте источник</div>}
      </div>
      <div className="form-group"><label className="form-label">Режим</label>
        <select className="form-select" value={mode} onChange={e => setMode(e.target.value)}>
          <option value="members_full">Полный (username, имя, телефон, био, язык, страна)</option>
          <option value="members_lite">Облегчённый (username, имя, язык)</option>
          <option value="members_active">Только активные (онлайн/день/неделя)</option>
          <option value="admins">Администраторы</option>
        </select>
      </div>
      <div className="form-group"><label className="form-label">Лимит участников</label>
        <input className="form-input" type="number" placeholder="Без лимита" value={limit} onChange={e => setLimit(e.target.value)} />
        <div className="help-text">0 или пусто = без ограничения</div>
      </div>
      <div className="form-group"><label className="form-label">Задержка между запросами (мс)</label>
        <input className="form-input" type="number" value={delayMs} onChange={e => setDelayMs(e.target.value)} />
        <div className="help-text">100-10000 мс. Больше = меньше риск блокировки</div>
      </div>
      <div className="form-group">
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input type="checkbox" checked={skipBots} onChange={e => setSkipBots(e.target.checked)} />
          Пропускать ботов
        </label>
      </div>
      {error && <div style={{ color: "#ef4444", fontSize: 13, marginBottom: 8 }}>{error}</div>}
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Отмена</button>
        <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}>{loading ? "Запуск..." : "Запустить парсинг"}</button>
      </div>
    </Modal>
  );
};

const SourceStatsModal: React.FC<{ sourceId: number; onClose: () => void }> = ({ sourceId, onClose }) => {
  const [stats, setStats] = useState<SourceStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/audience/sources/${sourceId}/stats`)
      .then(r => r.json())
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sourceId]);

  if (loading) return <Modal title="Статистика источника" onClose={onClose}><div style={{ padding: 20 }}>Загрузка...</div></Modal>;

  if (!stats) return <Modal title="Статистика источника" onClose={onClose}><div style={{ padding: 20, color: "#ef4444" }}>Ошибка загрузки</div></Modal>;

  const total = stats.total_members || 1;
  return (
    <Modal title={`Статистика источника #${sourceId}`} onClose={onClose}>
      <div className="stats-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 16 }}>
        <div className="stat-card"><div className="stat-label">Всего</div><div className="stat-value">{stats.total_members.toLocaleString()}</div></div>
        <div className="stat-card"><div className="stat-label">Активных (день)</div><div className="stat-value">{stats.active_last_day.toLocaleString()}</div></div>
        <div className="stat-card"><div className="stat-label">Активных (нед)</div><div className="stat-value">{stats.active_last_week.toLocaleString()}</div></div>
        <div className="stat-card"><div className="stat-label">Боты</div><div className="stat-value">{stats.bots}</div></div>
        <div className="stat-card"><div className="stat-label">С username</div><div className="stat-value">{stats.with_usernames}</div></div>
        <div className="stat-card"><div className="stat-label">С телефоном</div><div className="stat-value">{stats.with_phones}</div></div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ background: "#0f172a", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 8 }}>Языки</div>
          {Object.entries(stats.languages).slice(0, 6).map(([lang, count]) => (
            <div key={lang} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
              <span>{lang?.toUpperCase()}</span><span style={{ color: "#94a3b8" }}>{Number(count).toLocaleString()}</span>
            </div>
          ))}
          {Object.keys(stats.languages).length === 0 && <div style={{ color: "#94a3b8", fontSize: 13 }}>Нет данных</div>}
        </div>
        <div style={{ background: "#0f172a", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 8 }}>Активность</div>
          {[
            ["Онлайн / день", stats.active_last_day],
            ["Неделя", stats.active_last_week - stats.active_last_day],
            ["Месяц", stats.active_last_month - stats.active_last_week],
            ["Давно", stats.long_ago],
            ["Скрыто", stats.hidden],
          ].map(([label, count]) => (
            <div key={String(label)} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
              <span>{String(label)}</span><span style={{ color: "#94a3b8" }}>{Number(count).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
};

const ExportModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [format, setFormat] = useState("csv");
  return (
    <Modal title="Экспорт участников" onClose={onClose}>
      <div className="form-group"><label className="form-label">Формат</label>
        <select className="form-select" value={format} onChange={e => setFormat(e.target.value)}>
          <option value="csv">CSV (Excel)</option><option value="txt">TXT (@usernames)</option>
          <option value="phones">TXT (телефоны)</option><option value="json">JSON</option>
        </select>
      </div>
      <div className="modal-footer">
        <button className="btn btn-secondary" onClick={onClose}>Отмена</button>
        <button className="btn btn-primary" onClick={onClose}>Экспорт (через фильтры)</button>
      </div>
    </Modal>
  );
};

const MasslookingSection: React.FC<{ onOpenCreate: () => void }> = ({ onOpenCreate }) => (
  <section className="section" id="masslooking">
    <div className="header"><h1>Масслукинг</h1><button className="btn btn-primary" onClick={onOpenCreate}><PlusIcon /> Создать задачу</button></div>
    <div className="table-container"><div className="table-header"><div className="table-title">Задачи масслукинга</div></div>
      <div style={{ padding: 20, color: "#94a3b8" }}>Задачи масслукинга появятся после настройки модуля.</div></div>
  </section>
);

const InvitingSection: React.FC<{ onOpenCreate: () => void }> = ({ onOpenCreate }) => (
  <section className="section" id="inviting">
    <div className="header"><h1>Инвайтинг</h1><button className="btn btn-primary" onClick={onOpenCreate}><PlusIcon /> Создать задачу</button></div>
    <div className="table-container"><div className="table-header"><div className="table-title">Задачи инвайтинга</div></div>
      <div style={{ padding: 20, color: "#94a3b8" }}>Задачи инвайтинга появятся после настройки модуля.</div></div>
  </section>
);

const TaggingSection: React.FC<{ onOpenCreate: () => void }> = ({ onOpenCreate }) => (
  <section className="section" id="tagging">
    <div className="header"><h1>Отметки и тегер</h1><button className="btn btn-primary" onClick={onOpenCreate}><PlusIcon /> Создать задачу</button></div>
    <div className="empty-state"><TagIcon /><h3>Нет активных задач</h3><p>Модуль тегера в разработке</p></div>
  </section>
);

const SettingsSection: React.FC<{ email, setEmail, password, setPassword, token, authMessage, onRegister, onLogin }> =
  ({ email, setEmail, password, setPassword, token, authMessage, onRegister, onLogin }) => (
    <section className="section" id="settings">
      <div className="header"><h1>Настройки</h1></div>
      <div className="table-container" style={{ marginBottom: 20 }}>
        <div className="table-header"><div className="table-title">Авторизация (backend)</div></div>
        <div style={{ padding: 24 }}>
          <div className="form-group"><label className="form-label">Email</label>
            <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="user@example.com" style={{ maxWidth: 300 }} /></div>
          <div className="form-group"><label className="form-label">Пароль</label>
            <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} style={{ maxWidth: 300 }} /></div>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <button className="btn btn-secondary" onClick={onRegister}>Регистрация</button>
            <button className="btn btn-primary" onClick={onLogin}>Логин</button>
          </div>
          {authMessage && <div style={{ fontSize: 14, color: authMessage.includes("успех") ? "#22c55e" : "#ef4444" }}>{authMessage}</div>}
          {token && <div style={{ marginTop: 8, fontSize: 12, color: "#94a3b8" }}>Токен: {token.slice(0, 20)}...</div>}
        </div>
      </div>
      <div className="table-container">
        <div className="table-header"><div className="table-title">Лимиты и безопасность</div></div>
        <div style={{ padding: 24 }}>
          <div className="form-group"><label className="form-label">Задержка между действиями (мс)</label>
            <input className="form-input" type="number" defaultValue={500} style={{ maxWidth: 200 }} /></div>
          <button className="btn btn-primary" onClick={() => alert("Сохранение лимитов будет реализовано через API /api/v1/settings")}>Сохранить</button>
        </div>
      </div>
    </section>
  );

const MasslookingModal: React.FC<{ masslookingMode: "safe" | "balanced" | "aggressive"; setMasslookingMode: (m: "safe" | "balanced" | "aggressive") => void; onClose: () => void }> =
  ({ masslookingMode, setMasslookingMode, onClose }) => (
    <Modal title="Создать задачу масслукинга" onClose={onClose}>
      <div className="form-group"><label className="form-label">Режим работы</label>
        <div className="radio-group">
          <label className="radio-label"><input type="radio" name="mlmode" value="safe" checked={masslookingMode === "safe"} onChange={() => setMasslookingMode("safe")} /><span>Safe (200-500/день)</span></label>
          <label className="radio-label"><input type="radio" name="mlmode" value="balanced" checked={masslookingMode === "balanced"} onChange={() => setMasslookingMode("balanced")} /><span>Balanced (1000-2000/день)</span></label>
          <label className="radio-label"><input type="radio" name="mlmode" value="aggressive" checked={masslookingMode === "aggressive"} onChange={() => setMasslookingMode("aggressive")} /><span>Aggressive (3000+/день)</span></label>
        </div>
      </div>
      <div className="modal-footer"><button className="btn btn-secondary" onClick={onClose}>Отмена</button>
        <button className="btn btn-primary" onClick={() => { alert("Модуль масслукинга в разработке"); onClose(); }}>Создать</button>
      </div>
    </Modal>
  );

const InvitingModal: React.FC<{ onClose: () => void }> = ({ onClose }) => (
  <Modal title="Создать задачу инвайтинга" onClose={onClose}>
    <div style={{ padding: 8, color: "#94a3b8" }}>Модуль инвайтинга в разработке. Выберите источник и целевую группу после реализации.</div>
    <div className="modal-footer"><button className="btn btn-secondary" onClick={onClose}>Закрыть</button></div>
  </Modal>
);

const TaggingModal: React.FC<{ onClose: () => void }> = ({ onClose }) => (
  <Modal title="Создать задачу тегера" onClose={onClose}>
    <div style={{ padding: 8, color: "#94a3b8" }}>Модуль тегера в разработке.</div>
    <div className="modal-footer"><button className="btn btn-secondary" onClick={onClose}>Закрыть</button></div>
  </Modal>
);

const Modal: React.FC<{ title: string; onClose: () => void; children: React.ReactNode }> = ({ title, onClose, children }) => (
  <div className="modal active" onClick={e => e.target === e.currentTarget && onClose()}>
    <div className="modal-content">
      <div className="modal-header"><h2 className="modal-title">{title}</h2><button className="modal-close" onClick={onClose}>×</button></div>
      <div className="modal-body">{children}</div>
    </div>
  </div>
);

const PlusIcon = () => <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ marginRight: 6 }}><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>;
const HomeIcon = () => <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>;
const UsersIcon = () => <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>;
const EyeIcon = () => <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>;
const UserAddIcon = () => <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" /></svg>;
const TagIcon = () => <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>;
const DatabaseIcon = () => <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" /></svg>;
const SettingsIcon = () => <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c-.94 1.543.826 3.31 2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>;

export default App;
