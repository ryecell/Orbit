import { useState, useRef, useEffect } from "react";
import {
  Home, FolderOpen, Plus, Users, User, Search, Bell, Camera, Calendar as CalendarIcon,
  ChevronLeft, ChevronRight, CheckSquare, Square, Clock, MapPin, TrendingUp, Sparkles,
  Send, X, Check, ArrowLeft, Shield, Zap, Star, Atom, Sigma, Wrench, FileText,
  Wifi, Mic, ListTodo, BarChart3, ChevronDown, AlertCircle, Loader2,
  Leaf, Paperclip, Lock, LayoutGrid, Layers, Orbit as OrbitIcon, LogOut, Mail, KeyRound
} from "lucide-react";
import { api } from "./api.js";

/* ---------------------------------- THEME ---------------------------------- */

const T = {
  bg: "#F4F1FB",
  panel: "#FFFFFF",
  ink: "#1B1533",
  inkSoft: "#6F6885",
  inkFaint: "#A29BB8",
  line: "#E9E4F7",
  primary: "#5B3FE0",
  primaryDark: "#3F2AA8",
  primarySoft: "#EEEAFC",
  sidebar: "#160F2B",
  sidebarSoft: "#2A2049",
  danger: "#E2456B",
};

const FOLDER_META = {
  "Biology": { color: "#0E9F6E", icon: Leaf },
  "Math 21": { color: "#5B3FE0", icon: Sigma },
  "Physics": { color: "#E2456B", icon: Atom },
  "Group Project": { color: "#A855F7", icon: Users },
  "Workshops": { color: "#D68A0C", icon: Wrench },
  "Personal": { color: "#0891B2", icon: User },
};
const FOLDER_NAMES = Object.keys(FOLDER_META);
const DEMO_GROUP_ID = "study-group-1";

// Calendar/insights have no backend model yet, so these stay illustrative.
const weeklyStudy = [
  { day: "Mon", hours: 1.5 }, { day: "Tue", hours: 2.2 }, { day: "Wed", hours: 1.8 },
  { day: "Thu", hours: 3.1 }, { day: "Fri", hours: 2.4 }, { day: "Sat", hours: 2.0 }, { day: "Sun", hours: 1.5 },
];
const MAY_EVENTS = {
  7: [{ t: "Math 21 Quiz", time: "10:00 – 11:00 AM", color: T.primary }],
  15: [
    { t: "Math 21 Quiz", time: "10:00 – 11:00 AM", color: T.primary },
    { t: "Group Meeting", time: "2:00 – 3:00 PM", color: "#A855F7" },
    { t: "Physics Lab", time: "4:00 – 5:30 PM", color: T.danger },
  ],
  20: [{ t: "Group Project Report Due", time: "11:59 PM", color: "#D68A0C" }],
};

/* ------------------------------- UTILITIES ---------------------------------- */

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result.split(",")[1]);
    r.onerror = () => reject(new Error("Could not read file"));
    r.readAsDataURL(file);
  });
}

function matchFolder(name) {
  if (!name) return "Personal";
  const hit = FOLDER_NAMES.find(
    (f) => f.toLowerCase() === String(name).toLowerCase() || String(name).toLowerCase().includes(f.toLowerCase())
  );
  return hit || "Personal";
}

/* ------------------------------ SMALL PIECES --------------------------------- */

function ProgressRing({ pct, size = 84, stroke = 9, color = T.primary }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size / 2} cy={size / 2} r={r} stroke={T.line} strokeWidth={stroke} fill="none" />
      <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none"
        strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c} strokeLinecap="round" />
    </svg>
  );
}

function Chip({ children, onRemove, color }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 10px", borderRadius: 999,
      fontSize: 12.5, fontWeight: 600, background: color ? `${color}1A` : T.primarySoft,
      color: color || T.primary, border: `1px solid ${color ? color + "33" : "#DCD3F8"}`,
    }}>
      {children}
      {onRemove && <X size={12} style={{ cursor: "pointer" }} onClick={onRemove} />}
    </span>
  );
}

function TopBar({ title, onBack, right }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {onBack && <button onClick={onBack} style={iconBtnStyle}><ArrowLeft size={18} color={T.ink} /></button>}
        <h1 style={{ fontSize: 19, fontWeight: 800, color: T.ink, margin: 0, letterSpacing: -0.3 }}>{title}</h1>
      </div>
      <div style={{ display: "flex", gap: 8 }}>{right}</div>
    </div>
  );
}

function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", background: "#FCEAEE", border: "1px solid #F3C6D1", borderRadius: 12, padding: 12, fontSize: 12.5, color: "#A5223F" }}>
      <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
      {message}
    </div>
  );
}

function CenterSpinner({ label }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "60px 20px", color: T.inkSoft }}>
      <Loader2 size={22} color={T.primary} style={{ animation: "spin 1s linear infinite" }} />
      <span style={{ fontSize: 13 }}>{label}</span>
    </div>
  );
}

const iconBtnStyle = { width: 36, height: 36, borderRadius: 12, border: `1px solid ${T.line}`, background: T.panel, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" };
const screenBox = { padding: "0 20px 100px", display: "flex", flexDirection: "column", gap: 14 };
const rowCardStyle = { display: "flex", alignItems: "center", gap: 12, background: T.panel, border: `1px solid ${T.line}`, borderRadius: 14, padding: "13px 14px" };
const iconTileStyle = { width: 38, height: 38, borderRadius: 11, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 };
const primaryBtn = { display: "flex", alignItems: "center", justifyContent: "center", gap: 8, background: T.primary, color: "#fff", border: "none", borderRadius: 13, padding: "13px 16px", fontWeight: 700, fontSize: 14.5, cursor: "pointer" };
const secondaryBtn = { display: "flex", alignItems: "center", justifyContent: "center", gap: 8, background: T.panel, color: T.ink, border: `1px solid ${T.line}`, borderRadius: 13, padding: "13px 16px", fontWeight: 700, fontSize: 14, cursor: "pointer" };
const inputStyle = { width: "100%", border: `1px solid ${T.line}`, borderRadius: 12, padding: "12px 14px", fontSize: 14, color: T.ink, background: T.panel, boxSizing: "border-box" };
const selectStyle = { ...inputStyle, appearance: "none", cursor: "pointer" };

function PriorityTag({ p }) {
  const colors = { High: T.danger, Medium: "#D68A0C", Low: "#0E9F6E" };
  const c = colors[p] || T.inkFaint;
  return <span style={{ fontSize: 11, fontWeight: 700, color: c, background: `${c}15`, padding: "3px 8px", borderRadius: 8 }}>{p}</span>;
}
function FieldLabel({ children, icon: Icon }) {
  return <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5, fontWeight: 700, color: T.inkSoft, marginBottom: 8 }}>{Icon && <Icon size={13} />}{children}</div>;
}
function QuickAction({ icon: Icon, label, onClick }) {
  return (
    <div onClick={onClick} style={{ cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 7, background: T.panel, border: `1px solid ${T.line}`, borderRadius: 14, padding: "14px 0" }}>
      <div style={{ width: 38, height: 38, borderRadius: 12, background: T.primarySoft, display: "flex", alignItems: "center", justifyContent: "center" }}><Icon size={18} color={T.primary} /></div>
      <span style={{ fontSize: 11.5, fontWeight: 600, color: T.inkSoft }}>{label}</span>
    </div>
  );
}

/* --------------------------------- AUTH SCREEN --------------------------------- */

function AuthScreen({ onAuthed }) {
  const [mode, setMode] = useState("login"); // login | register | forgot
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [forgotSent, setForgotSent] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (mode === "forgot") {
      try {
        await api.forgotPassword({ username });
        setForgotSent(true);
      } catch (err) {
        // Still show the generic success state — the backend already
        // returns a generic message either way, so a thrown error here
        // is a genuine network/server problem, worth surfacing distinctly.
        setError(err.message || "Something went wrong. Is the backend running?");
      } finally {
        setLoading(false);
      }
      return;
    }

    try {
      const payload = mode === "login" ? { username, password } : { username, password, ...(name.trim() && { name: name.trim() }) };
      const data = mode === "login" ? await api.login(payload) : await api.register(payload);
      api.setToken(data.access_token);
      onAuthed(data.user);
    } catch (err) {
      setError(err.message || "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  function switchMode(next) {
    setMode(next);
    setError("");
    setForgotSent(false);
  }

  return (
    <div style={{ minHeight: "640px", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 28px", maxWidth: 420, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "center", marginBottom: 30 }}>
        <div style={{ width: 42, height: 42, borderRadius: 12, background: T.primary, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <OrbitIcon size={22} color="#fff" />
        </div>
        <span style={{ fontWeight: 800, fontSize: 22, color: T.ink, letterSpacing: -0.4 }}>ORBIT</span>
      </div>

      <h2 style={{ textAlign: "center", fontSize: 17, fontWeight: 700, color: T.ink, margin: "0 0 4px" }}>
        {mode === "login" ? "Welcome back" : mode === "register" ? "Create your account" : "Reset your password"}
      </h2>
      <p style={{ textAlign: "center", fontSize: 12.5, color: T.inkFaint, margin: "0 0 22px" }}>
        {mode === "login" ? "Sign in to access your archive" : mode === "register" ? "Just a username and a password to start — add an email later if you want" : "Enter your username and we'll email a reset link if one's linked to your account"}
      </p>

      {mode === "forgot" && forgotSent ? (
        <div style={{ textAlign: "center" }}>
          <div style={{ background: T.primarySoft, border: `1px solid #DCD3F8`, borderRadius: 14, padding: "16px 18px", fontSize: 13.5, color: T.ink, lineHeight: 1.6 }}>
            If <strong>{username}</strong> has an email on file, a reset link is on its way there.
          </div>
          <span onClick={() => switchMode("login")} style={{ display: "inline-block", marginTop: 18, color: T.primary, fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
            Back to sign in
          </span>
        </div>
      ) : (
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <FieldLabel icon={User}>Username</FieldLabel>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={inputStyle}
              placeholder="alexm"
              autoCapitalize="none"
              autoCorrect="off"
            />
          </div>

          {mode === "register" && (
            <div>
              <FieldLabel icon={User}>Full name <span style={{ fontWeight: 500, color: T.inkFaint }}>(optional)</span></FieldLabel>
              <input value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} placeholder="Alex Morgan" />
            </div>
          )}

          {mode !== "forgot" && (
            <div>
              <FieldLabel icon={KeyRound}>Password</FieldLabel>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} style={inputStyle} placeholder="At least 8 characters" />
            </div>
          )}

          {mode === "login" && (
            <span onClick={() => switchMode("forgot")} style={{ alignSelf: "flex-end", fontSize: 12.5, color: T.inkSoft, cursor: "pointer", marginTop: -4 }}>
              Forgot password?
            </span>
          )}

          <ErrorBanner message={error} />

          <button type="submit" disabled={loading} style={{ ...primaryBtn, opacity: loading ? 0.6 : 1, marginTop: 6 }}>
            {loading ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : (mode === "login" ? "Sign in" : mode === "register" ? "Create account" : "Send reset link")}
          </button>
        </form>
      )}

      {!(mode === "forgot" && forgotSent) && (
        <div style={{ textAlign: "center", marginTop: 18, fontSize: 13, color: T.inkSoft }}>
          {mode === "forgot" ? (
            <span onClick={() => switchMode("login")} style={{ color: T.primary, fontWeight: 700, cursor: "pointer" }}>Back to sign in</span>
          ) : (
            <>
              {mode === "login" ? "New to Orbit?" : "Already have an account?"}{" "}
              <span onClick={() => switchMode(mode === "login" ? "register" : "login")} style={{ color: T.primary, fontWeight: 700, cursor: "pointer" }}>
                {mode === "login" ? "Create an account" : "Sign in"}
              </span>
            </>
          )}
        </div>
      )}

      <div style={{ textAlign: "center", marginTop: 26, fontSize: 11, color: T.inkFaint }}>
        Connecting to <code>{api.base}</code>
      </div>
    </div>
  );
}

function ResetPasswordScreen({ token, onDone }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setLoading(true);
    try {
      await api.resetPassword({ token, new_password: password });
      setDone(true);
    } catch (err) {
      setError(err.message || "This reset link may have expired. Request a new one.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "640px", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 28px", maxWidth: 420, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "center", marginBottom: 30 }}>
        <div style={{ width: 42, height: 42, borderRadius: 12, background: T.primary, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <OrbitIcon size={22} color="#fff" />
        </div>
        <span style={{ fontWeight: 800, fontSize: 22, color: T.ink, letterSpacing: -0.4 }}>ORBIT</span>
      </div>

      {done ? (
        <div style={{ textAlign: "center" }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, color: T.ink, margin: "0 0 8px" }}>Password updated</h2>
          <p style={{ fontSize: 13.5, color: T.inkSoft, marginBottom: 20 }}>Sign in with your new password.</p>
          <button onClick={onDone} style={primaryBtn}>Go to sign in</button>
        </div>
      ) : (
        <>
          <h2 style={{ textAlign: "center", fontSize: 17, fontWeight: 700, color: T.ink, margin: "0 0 4px" }}>Choose a new password</h2>
          <p style={{ textAlign: "center", fontSize: 12.5, color: T.inkFaint, margin: "0 0 22px" }}>Must be at least 8 characters, with a letter and a number</p>
          <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <FieldLabel icon={KeyRound}>New password</FieldLabel>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} style={inputStyle} placeholder="At least 8 characters" />
            </div>
            <div>
              <FieldLabel icon={KeyRound}>Confirm password</FieldLabel>
              <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} style={inputStyle} placeholder="Type it again" />
            </div>
            <ErrorBanner message={error} />
            <button type="submit" disabled={loading} style={{ ...primaryBtn, opacity: loading ? 0.6 : 1, marginTop: 6 }}>
              {loading ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : "Update password"}
            </button>
          </form>
        </>
      )}
    </div>
  );
}

function VerifyPendingScreen({ user, onVerified, onLogout }) {
  const [resendState, setResendState] = useState("idle"); // idle | sending | sent
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");

  // Poll in the background so the screen advances on its own the moment the
  // person clicks the link in their email — no manual "I've verified" click
  // needed, though we still offer one below in case polling is slow/blocked.
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const fresh = await api.me();
        if (fresh.is_verified) onVerified(fresh);
      } catch {
        // Ignore transient errors during polling — the manual check button
        // and the next tick will retry.
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [onVerified]);

  async function checkNow() {
    setChecking(true);
    setError("");
    try {
      const fresh = await api.me();
      if (fresh.is_verified) {
        onVerified(fresh);
      } else {
        setError("Not verified yet — click the link in the email first, then try again.");
      }
    } catch (err) {
      setError(err.message || "Couldn't check verification status.");
    } finally {
      setChecking(false);
    }
  }

  async function resend() {
    setResendState("sending");
    setError("");
    try {
      await api.resendVerification();
      setResendState("sent");
    } catch (err) {
      setError(err.message || "Couldn't resend the email.");
      setResendState("idle");
    }
  }

  return (
    <div style={{ minHeight: "640px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "0 28px", maxWidth: 420, margin: "0 auto", textAlign: "center" }}>
      <div style={{ width: 64, height: 64, borderRadius: 18, background: T.primarySoft, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 22 }}>
        <Mail size={28} color={T.primary} />
      </div>

      <h2 style={{ fontSize: 18, fontWeight: 800, color: T.ink, margin: "0 0 8px" }}>Check your email</h2>
      <p style={{ fontSize: 13.5, color: T.inkSoft, lineHeight: 1.6, margin: "0 0 4px" }}>
        We sent a confirmation link to
      </p>
      <p style={{ fontSize: 14, fontWeight: 700, color: T.ink, margin: "0 0 22px" }}>{user.email}</p>

      <div style={{ display: "flex", alignItems: "center", gap: 10, color: T.inkFaint, fontSize: 12.5, marginBottom: 26 }}>
        <Loader2 size={15} style={{ animation: "spin 1s linear infinite" }} />
        Waiting for confirmation…
      </div>

      {error && <div style={{ width: "100%", marginBottom: 14 }}><ErrorBanner message={error} /></div>}

      <button onClick={checkNow} disabled={checking} style={{ ...primaryBtn, width: "100%", opacity: checking ? 0.6 : 1 }}>
        {checking ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : "I've verified — check now"}
      </button>

      <button onClick={resend} disabled={resendState === "sending"} style={{ ...secondaryBtn, width: "100%", marginTop: 10, opacity: resendState === "sending" ? 0.6 : 1 }}>
        {resendState === "sending" ? "Sending…" : resendState === "sent" ? "Email sent again ✓" : "Resend confirmation email"}
      </button>

      <span onClick={onLogout} style={{ marginTop: 22, fontSize: 12.5, color: T.inkFaint, cursor: "pointer", textDecoration: "underline" }}>
        Sign out
      </span>

      <div style={{ marginTop: 26, fontSize: 11, color: T.inkFaint }}>
        Connecting to <code>{api.base}</code>
      </div>
    </div>
  );
}

/* --------------------------------- SCREENS ------------------------------------ */

function HomeScreen({ folders, tasks, go, user }) {
  const recentEntries = FOLDER_NAMES.map((f) => folders[f]).filter((f) => f && f.items.length)
    .sort((a, b) => (a.items[0]?.created_at < b.items[0]?.created_at ? 1 : -1)).slice(0, 4);

  return (
    <div>
      <div style={{ padding: "18px 20px 0", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 800, color: T.ink, letterSpacing: -0.4 }}>Good morning, {(user.name || user.username).split(" ")[0]} 👋</div>
          <div style={{ color: T.inkSoft, fontSize: 14, marginTop: 2 }}>Stay productive today.</div>
        </div>
        <button onClick={() => go("reminders")} style={{ ...iconBtnStyle, position: "relative" }}>
          <Bell size={17} color={T.ink} />
        </button>
      </div>

      <div style={{ padding: "16px 20px 0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, background: T.panel, border: `1px solid ${T.line}`, borderRadius: 14, padding: "11px 14px" }}>
          <Search size={16} color={T.inkFaint} />
          <span style={{ color: T.inkFaint, fontSize: 14 }}>Search anything…</span>
        </div>
      </div>

      <div style={{ padding: "20px 20px 0" }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft, marginBottom: 10 }}>Quick actions</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          <QuickAction icon={Camera} label="Camera" onClick={() => go("capture")} />
          <QuickAction icon={ListTodo} label="To-Do" onClick={() => go("todo")} />
          <QuickAction icon={CalendarIcon} label="Calendar" onClick={() => go("calendar")} />
          <QuickAction icon={BarChart3} label="Insights" onClick={() => go("insights")} />
        </div>
      </div>

      <div style={screenBox}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft }}>Recent folders</div>
          <span onClick={() => go("archive")} style={{ fontSize: 12.5, fontWeight: 700, color: T.primary, cursor: "pointer" }}>See all</span>
        </div>
        {recentEntries.length === 0 && <div style={{ fontSize: 13, color: T.inkFaint }}>Nothing captured yet — try the camera above.</div>}
        {recentEntries.map((f) => {
          const meta = FOLDER_META[f.name] || FOLDER_META.Personal;
          const Icon = meta.icon;
          return (
            <div key={f.id} onClick={() => go("folder", f.name)} style={rowCardStyle}>
              <div style={{ ...iconTileStyle, background: `${meta.color}1A`, color: meta.color }}><Icon size={18} /></div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14.5, color: T.ink }}>{f.name}</div>
                <div style={{ fontSize: 12.5, color: T.inkFaint }}>{f.items.length} items</div>
              </div>
            </div>
          );
        })}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft }}>Tasks</div>
          <span onClick={() => go("todo")} style={{ fontSize: 12.5, fontWeight: 700, color: T.primary, cursor: "pointer" }}>See all</span>
        </div>
        {tasks.length === 0 && <div style={{ fontSize: 13, color: T.inkFaint }}>No tasks yet.</div>}
        {tasks.slice(0, 2).map((t) => (
          <div key={t.id} style={rowCardStyle}>
            {t.done ? <CheckSquare size={19} color={T.primary} /> : <Square size={19} color={T.inkFaint} />}
            <div style={{ flex: 1, fontSize: 14, color: t.done ? T.inkFaint : T.ink, textDecoration: t.done ? "line-through" : "none" }}>{t.text}</div>
            <PriorityTag p={t.priority} />
          </div>
        ))}
      </div>
    </div>
  );
}

function ArchiveScreen({ folders, go }) {
  return (
    <div>
      <TopBar title="My Archive" />
      <div style={screenBox}>
        {FOLDER_NAMES.map((name) => {
          const folder = folders[name];
          if (!folder) return null;
          const meta = FOLDER_META[name];
          const Icon = meta.icon;
          return (
            <div key={folder.id} onClick={() => go("folder", name)} style={{ ...rowCardStyle, cursor: "pointer" }}>
              <div style={{ ...iconTileStyle, background: `${meta.color}1A`, color: meta.color }}><Icon size={18} /></div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14.5, color: T.ink }}>{name}</div>
                <div style={{ fontSize: 12.5, color: T.inkFaint }}>{folder.items.length} items</div>
              </div>
              <ChevronRight size={17} color={T.inkFaint} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FolderDetailScreen({ name, folder, go, back, onDeleteItem }) {
  const meta = FOLDER_META[name] || FOLDER_META.Personal;
  const Icon = meta.icon;
  const items = folder ? folder.items : [];
  return (
    <div>
      <TopBar title={name} onBack={back} />
      <div style={screenBox}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: -4 }}>
          <div style={{ ...iconTileStyle, background: `${meta.color}1A`, color: meta.color }}><Icon size={18} /></div>
          <div style={{ fontSize: 13, color: T.inkSoft }}>{items.length} items in this folder</div>
        </div>
        {items.length === 0 && <div style={{ textAlign: "center", padding: "40px 10px", color: T.inkFaint, fontSize: 13.5 }}>Nothing here yet. Capture a photo or note to add your first item.</div>}
        {items.map((it) => (
          <div key={it.id} style={{ ...rowCardStyle, alignItems: "flex-start", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
              <div style={{ fontWeight: 700, fontSize: 14.5, color: T.ink }}>{it.title}</div>
              <X size={15} color={T.inkFaint} style={{ cursor: "pointer" }} onClick={() => onDeleteItem(it.id)} />
            </div>
            {it.summary && <div style={{ fontSize: 12.5, color: T.inkSoft }}>{it.summary}</div>}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {it.tags.map((tg) => <Chip key={tg} color={meta.color}>{tg}</Chip>)}
            </div>
          </div>
        ))}
        <button onClick={() => go("capture")} style={{ ...primaryBtn, marginTop: 6 }}><Plus size={16} /> Add to {name}</button>
      </div>
    </div>
  );
}

function CaptureScreen({ back, onSave, folders }) {
  const inputRef = useRef(null);
  const [image, setImage] = useState(null);
  const [mediaType, setMediaType] = useState("image/jpeg");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [folder, setFolder] = useState("Personal");
  const [tags, setTags] = useState([]);
  const [summary, setSummary] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setMediaType(file.type || "image/jpeg");
    setStatus("loading");
    setError("");
    try {
      const b64 = await fileToBase64(file);
      setImage(b64);
      const result = await api.ai.analyze({ image_base64: b64, media_type: file.type || "image/jpeg", candidate_folders: FOLDER_NAMES });
      setTitle(result.title || "Untitled note");
      setFolder(matchFolder(result.folder));
      setTags(Array.isArray(result.tags) ? result.tags.slice(0, 5) : []);
      setSummary(result.summary || "");
      setStatus("ready");
    } catch (err) {
      setError(err.message || "Couldn't analyze this image automatically. You can still fill in the details yourself.");
      setStatus("error");
    }
  }

  function addTag() {
    const v = tagInput.trim().toLowerCase();
    if (v && !tags.includes(v)) setTags([...tags, v]);
    setTagInput("");
  }

  async function save() {
    if (!title.trim()) return;
    const targetFolder = folders[folder];
    if (!targetFolder) { setError(`Folder "${folder}" wasn't found on the server.`); return; }
    setSaving(true);
    setError("");
    try {
      await onSave(targetFolder.id, folder, { title: title.trim(), summary, tags });
    } catch (err) {
      setError(err.message || "Couldn't save this item.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <TopBar title="Add to Archive" onBack={back} />
      <div style={screenBox}>
        {!image && (
          <div onClick={() => inputRef.current?.click()} style={{ border: `2px dashed ${T.line}`, borderRadius: 18, padding: "44px 16px", textAlign: "center", cursor: "pointer", background: T.panel }}>
            <div style={{ width: 52, height: 52, borderRadius: 16, background: T.primarySoft, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 14px" }}>
              <Camera size={24} color={T.primary} />
            </div>
            <div style={{ fontWeight: 700, color: T.ink, fontSize: 15 }}>Capture or upload a photo</div>
            <div style={{ fontSize: 12.5, color: T.inkFaint, marginTop: 4 }}>Sent to your Orbit backend, which asks Claude to read it</div>
          </div>
        )}
        <input ref={inputRef} type="file" accept="image/*" capture="environment" onChange={handleFile} style={{ display: "none" }} />

        {image && (
          <div style={{ borderRadius: 16, overflow: "hidden", border: `1px solid ${T.line}` }}>
            <img src={`data:${mediaType};base64,${image}`} alt="Captured" style={{ width: "100%", display: "block", maxHeight: 220, objectFit: "cover" }} />
          </div>
        )}

        {status === "loading" && (
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: T.inkSoft, fontSize: 13.5, padding: "6px 2px" }}>
            <Loader2 size={16} color={T.primary} style={{ animation: "spin 1s linear infinite" }} /> Analyzing image with AI…
          </div>
        )}

        <ErrorBanner message={status === "error" ? error : (error && status === "ready" ? error : "")} />

        {(status === "ready" || status === "error") && image && (
          <>
            {status === "ready" && (
              <div>
                <FieldLabel icon={Sparkles}>AI suggestions</FieldLabel>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{tags.map((tg) => <Chip key={tg}>{tg}</Chip>)}</div>
                {summary && <div style={{ fontSize: 12.5, color: T.inkSoft, marginTop: 8, lineHeight: 1.5 }}>{summary}</div>}
              </div>
            )}

            <div>
              <FieldLabel>Add to folder</FieldLabel>
              <div style={{ position: "relative" }}>
                <select value={folder} onChange={(e) => setFolder(e.target.value)} style={selectStyle}>
                  {FOLDER_NAMES.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
                <ChevronDown size={16} color={T.inkFaint} style={{ position: "absolute", right: 14, top: 14, pointerEvents: "none" }} />
              </div>
            </div>

            <div>
              <FieldLabel>Title</FieldLabel>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Give it a title" style={inputStyle} />
            </div>

            <div>
              <FieldLabel>Tags</FieldLabel>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                {tags.map((tg) => <Chip key={tg} onRemove={() => setTags(tags.filter((x) => x !== tg))}>{tg}</Chip>)}
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <input value={tagInput} onChange={(e) => setTagInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addTag()} placeholder="Add a tag" style={inputStyle} />
                <button onClick={addTag} style={{ ...secondaryBtn, padding: "0 16px" }}>Add</button>
              </div>
            </div>

            <button onClick={save} disabled={!title.trim() || saving} style={{ ...primaryBtn, opacity: title.trim() && !saving ? 1 : 0.5 }}>
              {saving ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : <><Check size={16} /> Save to Archive</>}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function CalendarScreen({ back }) {
  const [selected, setSelected] = useState(15);
  const cells = [...Array(4).fill(null), ...Array.from({ length: 31 }, (_, i) => i + 1)];
  const events = MAY_EVENTS[selected] || [];
  return (
    <div>
      <TopBar title="May 2025" onBack={back} />
      <div style={screenBox}>
        <div style={{ background: T.panel, border: `1px solid ${T.line}`, borderRadius: 16, padding: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 4, marginBottom: 6 }}>
            {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => <div key={i} style={{ textAlign: "center", fontSize: 11, fontWeight: 700, color: T.inkFaint }}>{d}</div>)}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 4 }}>
            {cells.map((d, i) => {
              const hasEvent = d && MAY_EVENTS[d];
              const isSel = d === selected;
              return (
                <div key={i} onClick={() => d && setSelected(d)} style={{ aspectRatio: "1", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 10, fontSize: 12.5, fontWeight: isSel ? 800 : 500, cursor: d ? "pointer" : "default", background: isSel ? T.primary : "transparent", color: isSel ? "#fff" : d ? T.ink : "transparent", position: "relative" }}>
                  {d}
                  {hasEvent && !isSel && <span style={{ position: "absolute", bottom: 3, width: 4, height: 4, borderRadius: 99, background: T.primary }} />}
                </div>
              );
            })}
          </div>
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft, marginTop: 6 }}>May {selected}, 2025</div>
        {events.length === 0 && <div style={{ fontSize: 13, color: T.inkFaint, padding: "10px 0" }}>No events scheduled.</div>}
        {events.map((ev, i) => (
          <div key={i} style={rowCardStyle}>
            <div style={{ width: 4, height: 34, borderRadius: 4, background: ev.color }} />
            <div style={{ flex: 1 }}><div style={{ fontWeight: 700, fontSize: 14, color: T.ink }}>{ev.t}</div><div style={{ fontSize: 12, color: T.inkFaint }}>{ev.time}</div></div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TodoScreen({ tasks, back, onToggle, onAdd }) {
  const [filter, setFilter] = useState("All");
  const [draft, setDraft] = useState("");
  const filtered = tasks.filter((t) => filter === "All" || (filter === "Completed" ? t.done : !t.done));

  async function addTask() {
    if (!draft.trim()) return;
    await onAdd(draft.trim());
    setDraft("");
  }

  return (
    <div>
      <TopBar title="My Tasks" onBack={back} />
      <div style={screenBox}>
        <div style={{ display: "flex", gap: 8 }}>
          {["All", "Active", "Completed"].map((f) => (
            <button key={f} onClick={() => setFilter(f)} style={{ border: `1px solid ${filter === f ? T.ink : T.line}`, borderRadius: 999, padding: "7px 14px", fontSize: 12.5, fontWeight: 700, cursor: "pointer", background: filter === f ? T.ink : T.panel, color: filter === f ? "#fff" : T.inkSoft }}>{f}</button>
          ))}
        </div>
        {filtered.map((t) => (
          <div key={t.id} style={rowCardStyle} onClick={() => onToggle(t)}>
            <div style={{ cursor: "pointer" }}>{t.done ? <CheckSquare size={19} color={T.primary} /> : <Square size={19} color={T.inkFaint} />}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: t.done ? T.inkFaint : T.ink, textDecoration: t.done ? "line-through" : "none" }}>{t.text}</div>
            </div>
            <PriorityTag p={t.priority} />
          </div>
        ))}
        <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
          <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addTask()} placeholder="Add a task…" style={inputStyle} />
          <button onClick={addTask} style={{ ...primaryBtn, padding: "0 18px" }}><Plus size={16} /></button>
        </div>
      </div>
    </div>
  );
}

function GroupScreen({ back, user }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [connected, setConnected] = useState(false);
  const [authFailed, setAuthFailed] = useState(false);
  const wsRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    api.groups.messages(DEMO_GROUP_ID).then((history) => { if (!cancelled) setMessages(history || []); }).catch(() => {});

    const ws = new WebSocket(api.wsURL(DEMO_GROUP_ID));
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = (evt) => {
      setConnected(false);
      // 4401 is the code the backend sends when the token is missing/invalid.
      if (evt.code === 4401) setAuthFailed(true);
    };
    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      setMessages((prev) => [...prev, msg]);
    };
    return () => { cancelled = true; ws.close(); };
  }, []);

  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight); }, [messages]);

  function send() {
    if (!draft.trim() || !wsRef.current || wsRef.current.readyState !== 1) return;
    // sender_name is no longer sent — the backend derives it from the
    // authenticated connection so a message can't be posted as someone else.
    wsRef.current.send(JSON.stringify({ text: draft.trim() }));
    setDraft("");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <TopBar title="Study Group" onBack={back} right={<span style={{ fontSize: 11, fontWeight: 700, color: connected ? "#0E9F6E" : T.inkFaint, alignSelf: "center" }}>{connected ? "● live" : "connecting…"}</span>} />
      {authFailed && <div style={{ margin: "0 20px 10px" }}><ErrorBanner message="Your session couldn't be verified for chat. Try signing out and back in." /></div>}
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "0 20px", display: "flex", flexDirection: "column", gap: 10 }}>
        {messages.map((m) => {
          const mine = m.sender_name === user.name;
          return (
            <div key={m.id} style={{ alignSelf: mine ? "flex-end" : "flex-start", maxWidth: "78%" }}>
              {!mine && <div style={{ fontSize: 11, fontWeight: 700, color: T.primary, marginBottom: 2 }}>{m.sender_name}</div>}
              <div style={{ background: mine ? T.primary : T.panel, color: mine ? "#fff" : T.ink, border: mine ? "none" : `1px solid ${T.line}`, borderRadius: 14, padding: "10px 13px", fontSize: 13.5 }}>{m.text}</div>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 8, padding: "12px 20px 90px", alignItems: "center" }}>
        <Paperclip size={17} color={T.inkFaint} />
        <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Type a message…" style={inputStyle} />
        <button onClick={send} style={{ ...iconBtnStyle, background: T.primary, border: "none" }}><Send size={15} color="#fff" /></button>
      </div>
    </div>
  );
}

function InsightsScreen({ back, tasks }) {
  const done = tasks.filter((t) => t.done).length;
  const pct = tasks.length ? Math.round((done / tasks.length) * 100) : 0;
  const maxHours = Math.max(...weeklyStudy.map((d) => d.hours));
  return (
    <div>
      <TopBar title="Insights" onBack={back} />
      <div style={screenBox}>
        <div style={{ display: "flex", gap: 12 }}>
          <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "center", flex: 1, gap: 6, padding: "16px 10px" }}>
            <div style={{ position: "relative" }}>
              <ProgressRing pct={pct} />
              <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 16, color: T.ink }}>{pct}%</div>
            </div>
            <div style={{ fontSize: 12, color: T.inkSoft, fontWeight: 600 }}>{done} of {tasks.length} tasks</div>
          </div>
          <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "flex-start", flex: 1, gap: 6, padding: "16px 14px", justifyContent: "center" }}>
            <TrendingUp size={18} color="#0E9F6E" />
            <div style={{ fontSize: 20, fontWeight: 800, color: T.ink }}>14h 30m</div>
            <div style={{ fontSize: 11.5, color: "#0E9F6E", fontWeight: 700 }}>Sample data</div>
          </div>
        </div>
        <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "stretch", gap: 14, padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft }}>Study time this week</div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 100 }}>
            {weeklyStudy.map((d) => (
              <div key={d.day} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <div style={{ width: "100%", borderRadius: 6, background: T.primary, height: `${(d.hours / maxHours) * 80}px`, opacity: 0.85 }} />
                <div style={{ fontSize: 10.5, color: T.inkFaint, fontWeight: 600 }}>{d.day}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function RemindersScreen({ back, reminders, onAdd }) {
  const kindIcon = { time: Clock, location: MapPin, inactivity: Bell };
  const [draft, setDraft] = useState("");

  async function addReminder() {
    if (!draft.trim()) return;
    await onAdd(draft.trim());
    setDraft("");
  }

  return (
    <div>
      <TopBar title="Reminders" onBack={back} />
      <div style={screenBox}>
        {reminders.length === 0 && <div style={{ fontSize: 13, color: T.inkFaint }}>No reminders yet.</div>}
        {reminders.map((r) => {
          const Icon = kindIcon[r.kind] || Bell;
          return (
            <div key={r.id} style={rowCardStyle}>
              <div style={{ ...iconTileStyle, background: T.primarySoft, color: T.primary }}><Icon size={17} /></div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 13.5, color: T.ink }}>{r.title}</div>
                <div style={{ fontSize: 11.5, color: T.inkFaint }}>{r.detail}</div>
              </div>
            </div>
          );
        })}
        <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
          <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addReminder()} placeholder="New reminder…" style={inputStyle} />
          <button onClick={addReminder} style={{ ...primaryBtn, padding: "0 18px" }}><Plus size={16} /></button>
        </div>
      </div>
    </div>
  );
}

function ProfileScreen({ back, user, onLogout, onUserUpdate }) {
  const [emailInput, setEmailInput] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState("");

  async function linkEmail(e) {
    e.preventDefault();
    setLinking(true);
    setLinkError("");
    try {
      const updated = await api.linkEmail({ email: emailInput.trim() });
      onUserUpdate(updated);
      // Note: this immediately routes to the "check your email" screen at
      // the App level, since that screen triggers whenever a linked email
      // isn't verified yet — same behavior as a fresh signup with an email.
    } catch (err) {
      setLinkError(err.message || "Couldn't link that email.");
    } finally {
      setLinking(false);
    }
  }

  const premium = [
    { icon: Mic, title: "Voice Commands", desc: "\u201cArchive this under Biology.\u201d" },
    { icon: LayoutGrid, title: "Home Screen Widgets", desc: "Quick access to tasks, events, recent captures" },
    { icon: Wifi, title: "Offline Mode", desc: "Capture and browse without a connection, auto-syncs later" },
    { icon: Layers, title: "Cross-Platform Sync", desc: "Works seamlessly on mobile, tablet, and web" },
    { icon: Shield, title: "Advanced Privacy", desc: "Biometric lock and per-folder permissions" },
  ];
  return (
    <div>
      <TopBar title="Profile" onBack={back} />
      <div style={screenBox}>
        <div style={{ ...rowCardStyle, gap: 14 }}>
          <div style={{ width: 50, height: 50, borderRadius: 999, background: T.primarySoft, display: "flex", alignItems: "center", justifyContent: "center", color: T.primary, fontWeight: 800, fontSize: 18 }}>{(user.name || user.username)[0].toUpperCase()}</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15.5, color: T.ink }}>{user.name || user.username}</div>
            <div style={{ fontSize: 12.5, color: T.inkFaint }}>@{user.username}</div>
          </div>
        </div>

        {user.email ? (
          <div style={rowCardStyle}>
            <Mail size={17} color={T.inkSoft} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13.5, color: T.ink }}>{user.email}</div>
              <div style={{ fontSize: 11.5, color: user.is_verified ? "#0E9F6E" : T.inkFaint }}>{user.is_verified ? "Verified" : "Verification pending"}</div>
            </div>
          </div>
        ) : (
          <form onSubmit={linkEmail} style={{ ...rowCardStyle, flexDirection: "column", alignItems: "stretch", gap: 10 }}>
            <FieldLabel icon={Mail}>Add an email (optional)</FieldLabel>
            <div style={{ fontSize: 12, color: T.inkFaint, marginTop: -6 }}>Lets you recover your account if you forget your password.</div>
            <input type="email" value={emailInput} onChange={(e) => setEmailInput(e.target.value)} placeholder="you@school.edu" style={inputStyle} />
            {linkError && <ErrorBanner message={linkError} />}
            <button type="submit" disabled={linking || !emailInput.trim()} style={{ ...secondaryBtn, opacity: linking || !emailInput.trim() ? 0.6 : 1 }}>
              {linking ? <Loader2 size={15} style={{ animation: "spin 1s linear infinite" }} /> : "Link email"}
            </button>
          </form>
        )}

        <div onClick={onLogout} style={{ ...rowCardStyle, cursor: "pointer" }}>
          <LogOut size={17} color={T.danger} />
          <div style={{ fontSize: 13.5, color: T.danger, fontWeight: 700 }}>Sign out</div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 700, color: T.inkSoft, marginTop: 10 }}>
          <Zap size={14} color={T.primary} /> Premium — coming soon
        </div>
        {premium.map((p) => (
          <div key={p.title} style={{ ...rowCardStyle, opacity: 0.9 }}>
            <div style={{ ...iconTileStyle, background: T.primarySoft, color: T.primary }}><p.icon size={17} /></div>
            <div style={{ flex: 1 }}><div style={{ fontWeight: 700, fontSize: 13.5, color: T.ink }}>{p.title}</div><div style={{ fontSize: 11.5, color: T.inkFaint }}>{p.desc}</div></div>
            <span style={{ fontSize: 10.5, fontWeight: 700, color: T.primary, background: T.primarySoft, padding: "3px 8px", borderRadius: 7 }}>SOON</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* --------------------------------- NAV SHELL ----------------------------------- */

const NAV_ITEMS = [
  { key: "home", label: "Home", icon: Home }, { key: "archive", label: "Archive", icon: FolderOpen },
  { key: "calendar", label: "Calendar", icon: CalendarIcon }, { key: "todo", label: "Tasks", icon: ListTodo },
  { key: "group", label: "Groups", icon: Users }, { key: "insights", label: "Insights", icon: BarChart3 },
  { key: "reminders", label: "Reminders", icon: Bell }, { key: "profile", label: "Profile", icon: User },
];
const MOBILE_NAV = [
  { key: "home", icon: Home, label: "Home" }, { key: "archive", icon: FolderOpen, label: "Archive" },
  { key: "capture", icon: Plus, label: "" }, { key: "group", icon: Users, label: "Groups" },
  { key: "profile", icon: User, label: "Profile" },
];

function MainShell({ user, onLogout, onUserUpdate }) {
  const [screen, setScreen] = useState("home");
  const [activeFolder, setActiveFolder] = useState(null);
  const [folders, setFolders] = useState({});
  const [tasks, setTasks] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.folders.list(), api.tasks.list(), api.reminders.list()])
      .then(([f, t, r]) => {
        if (cancelled) return;
        const byName = {};
        f.forEach((folder) => { byName[folder.name] = folder; });
        setFolders(byName);
        setTasks(t);
        setReminders(r);
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []);

  function go(target, param) {
    if (target === "folder") setActiveFolder(param);
    setScreen(target);
  }

  async function saveItem(folderId, folderName, payload) {
    const item = await api.folders.addItem(folderId, payload);
    setFolders((prev) => ({ ...prev, [folderName]: { ...prev[folderName], items: [item, ...prev[folderName].items] } }));
    setActiveFolder(folderName);
    setScreen("folder");
  }

  async function deleteItem(itemId) {
    await api.items.delete(itemId);
    setFolders((prev) => ({ ...prev, [activeFolder]: { ...prev[activeFolder], items: prev[activeFolder].items.filter((i) => i.id !== itemId) } }));
  }

  async function toggleTask(task) {
    const updated = await api.tasks.update(task.id, { done: !task.done });
    setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
  }

  async function addTask(text) {
    const created = await api.tasks.create({ text, priority: "Medium", due_date: "" });
    setTasks((prev) => [created, ...prev]);
  }

  async function addReminder(title) {
    const created = await api.reminders.create({ title, detail: "", kind: "time" });
    setReminders((prev) => [created, ...prev]);
  }

  function renderScreen() {
    if (loading) return <CenterSpinner label="Loading your archive…" />;
    if (error) return <div style={{ padding: 20 }}><ErrorBanner message={error} /></div>;

    switch (screen) {
      case "home": return <HomeScreen folders={folders} tasks={tasks} go={go} user={user} />;
      case "archive": return <ArchiveScreen folders={folders} go={go} />;
      case "folder": return <FolderDetailScreen name={activeFolder} folder={folders[activeFolder]} go={go} back={() => setScreen("archive")} onDeleteItem={deleteItem} />;
      case "capture": return <CaptureScreen back={() => setScreen("home")} onSave={saveItem} folders={folders} />;
      case "calendar": return <CalendarScreen back={() => setScreen("home")} />;
      case "todo": return <TodoScreen tasks={tasks} back={() => setScreen("home")} onToggle={toggleTask} onAdd={addTask} />;
      case "group": return <GroupScreen back={() => setScreen("home")} user={user} />;
      case "insights": return <InsightsScreen back={() => setScreen("home")} tasks={tasks} />;
      case "reminders": return <RemindersScreen back={() => setScreen("home")} reminders={reminders} onAdd={addReminder} />;
      case "profile": return <ProfileScreen back={() => setScreen("home")} user={user} onLogout={onLogout} onUserUpdate={onUserUpdate} />;
      default: return null;
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "640px", background: T.bg, fontFamily: "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif" }}>
      <div className="orbit-sidebar" style={{ width: 220, background: T.sidebar, padding: "22px 14px", flexShrink: 0, display: "none" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "0 8px 26px" }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: T.primary, display: "flex", alignItems: "center", justifyContent: "center" }}><OrbitIcon size={16} color="#fff" /></div>
          <span style={{ color: "#fff", fontWeight: 800, fontSize: 16, letterSpacing: -0.3 }}>ORBIT</span>
        </div>
        {NAV_ITEMS.map((n) => (
          <div key={n.key} onClick={() => go(n.key)} style={{ display: "flex", alignItems: "center", gap: 11, padding: "10px 12px", borderRadius: 11, cursor: "pointer", marginBottom: 3, background: screen === n.key ? T.sidebarSoft : "transparent", color: screen === n.key ? "#fff" : "#9188AD" }}>
            <n.icon size={16} /><span style={{ fontSize: 13.5, fontWeight: 600 }}>{n.label}</span>
          </div>
        ))}
        <div onClick={() => go("capture")} style={{ ...primaryBtn, marginTop: 18, width: "100%", boxSizing: "border-box" }}><Camera size={15} /> New capture</div>
      </div>

      <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
        <div className="orbit-frame" style={{ width: "100%", maxWidth: 420, background: T.bg, position: "relative", minHeight: "640px" }}>
          {renderScreen()}
          <div className="orbit-bottomnav" style={{ position: "fixed", bottom: 0, left: 0, right: 0, maxWidth: 420, margin: "0 auto", background: T.panel, borderTop: `1px solid ${T.line}`, padding: "10px 22px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            {MOBILE_NAV.map((n) => n.key === "capture" ? (
              <div key={n.key} onClick={() => go(n.key)} style={{ width: 46, height: 46, borderRadius: 999, background: T.primary, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", marginTop: -18, boxShadow: "0 6px 14px rgba(91,63,224,0.35)" }}>
                <Plus size={20} color="#fff" />
              </div>
            ) : (
              <div key={n.key} onClick={() => go(n.key)} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, cursor: "pointer", minWidth: 44 }}>
                <n.icon size={19} color={screen === n.key ? T.primary : T.inkFaint} />
                <span style={{ fontSize: 10, fontWeight: 700, color: screen === n.key ? T.primary : T.inkFaint }}>{n.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @media (min-width: 860px) {
          .orbit-sidebar { display: block !important; }
          .orbit-bottomnav { display: none !important; }
          .orbit-frame { max-width: 480px !important; border-left: 1px solid ${T.line}; border-right: 1px solid ${T.line}; }
        }
      `}</style>
    </div>
  );
}

/* ----------------------------------- APP --------------------------------------- */

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [resetToken, setResetToken] = useState(() => new URLSearchParams(window.location.search).get("resetToken"));

  useEffect(() => {
    const token = api.getToken();
    if (!token) { setChecking(false); return; }
    api.me().then(setUser).catch(() => api.clearToken()).finally(() => setChecking(false));
  }, []);

  function handleLogout() {
    api.logout().catch(() => {}).finally(() => {
      api.clearToken();
      setUser(null);
    });
  }

  function clearResetToken() {
    setResetToken(null);
    // Drop ?resetToken=... from the address bar without a full reload, so
    // refreshing afterward doesn't re-trigger the reset screen.
    window.history.replaceState({}, "", window.location.pathname);
  }

  // Checked before auth state on purpose — someone clicking a reset link
  // isn't necessarily logged in, and shouldn't need to be.
  if (resetToken) return <ResetPasswordScreen token={resetToken} onDone={clearResetToken} />;
  if (checking) return <CenterSpinner label="Checking your session…" />;
  if (!user) return <AuthScreen onAuthed={setUser} />;
  // Only gate on verification if there's actually an email pending
  // verification — accounts with no email at all skip this entirely.
  if (user.email && !user.is_verified) return <VerifyPendingScreen user={user} onVerified={setUser} onLogout={handleLogout} />;
  return <MainShell user={user} onLogout={handleLogout} onUserUpdate={setUser} />;
}
