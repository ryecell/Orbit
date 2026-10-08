import { useState, useRef, useEffect, useMemo } from "react";
import {
  Home, FolderOpen, Plus, Users, User, Search, Bell, Camera, Calendar as CalendarIcon,
  ChevronLeft, ChevronRight, CheckSquare, Square, Clock, MapPin, TrendingUp, Sparkles,
  Send, X, Check, ArrowLeft, Shield, Zap, Star, Atom, Sigma, Wrench, FileText,
  Wifi, Mic, ListTodo, BarChart3, ChevronDown, AlertCircle, Loader2,
  Leaf, Paperclip, Lock, LayoutGrid, Layers, LogOut, Mail, KeyRound, Download, Trash2, Copy, Share2,
  BookOpen, FlaskConical, Code, Calculator, Lightbulb, GraduationCap, Globe, Palette, Music, Heart, Briefcase,
  Pencil, ChevronUp
} from "lucide-react";
import { api } from "./api.js";

/* ---------------------------------- THEME ---------------------------------- */

const T = {
  bg: "#FFFFFF",            // white page background
  panel: "#F6FBF8",         // faint mint-white for cards — just enough to separate from bg
  ink: "#12241C",           // deep green-black text (not pure black — keeps the green identity)
  inkSoft: "#5C7568",       // muted green-gray secondary text
  inkFaint: "#9BB0A3",      // faint green-gray for placeholders
  line: "#E1ECE5",          // soft green-tinted border
  primary: "#50C878",       // emerald — buttons, active states, key accents
  primaryDark: "#2F9159",
  primarySoft: "rgba(80,200,120,0.14)",
  primaryGlow: "rgba(80,200,120,0.38)",  // for soft glow/fade effects around key elements
  sidebar: "#081C13",       // kept dark — a "night sky" strip against the white content
  sidebarSoft: "#12291B",
  danger: "#E2456B",        // kept distinct from the palette — errors should still read as errors
};

// A faint tileable sparkle texture — gold and spring-green flecks, visible
// but subtle against white. Same idea as the dark theme's starfield, just
// recalibrated so it reads as "glitter" rather than "dirty background."
// echoes the gold-flecked moodboard without needing an image asset.
const STARFIELD_BG = {
  backgroundImage: `
    radial-gradient(1.6px 1.6px at 20px 30px, rgba(212,175,55,0.5), transparent),
    radial-gradient(1.2px 1.2px at 70px 90px, rgba(212,175,55,0.32), transparent),
    radial-gradient(1.6px 1.6px at 140px 45px, rgba(212,175,55,0.38), transparent),
    radial-gradient(1.2px 1.2px at 100px 130px, rgba(80,200,120,0.28), transparent),
    radial-gradient(1.6px 1.6px at 170px 100px, rgba(212,175,55,0.3), transparent),
    radial-gradient(1.2px 1.2px at 40px 160px, rgba(80,200,120,0.22), transparent)
  `,
  backgroundRepeat: "repeat",
  backgroundSize: "200px 200px",
};

// True on desktop-width windows. Drives layouts that need different structure
// (not just different CSS), like the two-pane Groups workspace.
function useIsDesktop(breakpoint = 860) {
  const query = `(min-width: ${breakpoint}px)`;
  const [matches, setMatches] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = (e) => setMatches(e.matches);
    setMatches(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

function OrbitCatLogo({ size = 28, glow = true }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" style={glow ? { filter: "drop-shadow(0 0 10px rgba(80,200,120,0.45))" } : undefined}>
      <defs>
        <radialGradient id="orbitCatDome" cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#EAFBF1" />
          <stop offset="55%" stopColor="#8FE3B0" />
          <stop offset="100%" stopColor="#50C878" />
        </radialGradient>
      </defs>
      <ellipse cx="32" cy="43" rx="29" ry="9.5" stroke="#D4AF37" strokeWidth="1.4" opacity="0.35" transform="rotate(-6 32 43)" />
      <ellipse cx="32" cy="45" rx="21" ry="7.5" fill="#B8952B" />
      <ellipse cx="32" cy="42" rx="22" ry="7" fill="#D4AF37" />
      <circle cx="18" cy="43.5" r="1.6" fill="#EAF3EC" />
      <circle cx="32" cy="46" r="1.6" fill="#EAF3EC" />
      <circle cx="46" cy="43.5" r="1.6" fill="#EAF3EC" />
      <circle cx="32" cy="27" r="15" fill="url(#orbitCatDome)" stroke="#D4AF37" strokeWidth="1.2" />
      <path d="M21 18 L24 8 L29 17 Z" fill="#50C878" />
      <path d="M43 18 L40 8 L35 17 Z" fill="#50C878" />
      <circle cx="32" cy="29" r="11.5" fill="#6FDA9C" />
      <ellipse cx="27" cy="27.5" rx="1.9" ry="2.3" fill="#0A2617" />
      <ellipse cx="37" cy="27.5" rx="1.9" ry="2.3" fill="#0A2617" />
      <path d="M31 32 L33 32 L32 33.4 Z" fill="#0A2617" />
      <path d="M8 12 L9 15 L12 16 L9 17 L8 20 L7 17 L4 16 L7 15 Z" fill="#D4AF37" opacity="0.85" />
      <path d="M54 10 L54.8 12.3 L57 13 L54.8 13.7 L54 16 L53.2 13.7 L51 13 L53.2 12.3 Z" fill="#D4AF37" opacity="0.7" />
      <path d="M52 44 L52.6 45.8 L54.4 46.4 L52.6 47 L52 48.8 L51.4 47 L49.6 46.4 L51.4 45.8 Z" fill="#D4AF37" opacity="0.6" />
    </svg>
  );
}

const FOLDER_META = {
  "Biology": { color: "#00674F", icon: Leaf },
  "Math 21": { color: "#009B77", icon: Sigma },
  "Physics": { color: "#046307", icon: Atom },
  "Group Project": { color: "#D4AF37", icon: Users },
  "Workshops": { color: "#7FE0A8", icon: Wrench },
  "Personal": { color: "#2F9159", icon: User },
};

// Icons a person can pick for a folder. Keys are stored on the server — keep in
// sync with FOLDER_ICON_KEYS in schemas.py.
const FOLDER_ICONS = {
  folder: FolderOpen, leaf: Leaf, sigma: Sigma, atom: Atom, users: Users, wrench: Wrench, user: User,
  file: FileText, star: Star, sparkles: Sparkles, book: BookOpen, flask: FlaskConical, code: Code,
  calculator: Calculator, lightbulb: Lightbulb, graduation: GraduationCap, globe: Globe, palette: Palette,
  music: Music, heart: Heart, briefcase: Briefcase,
};
const FOLDER_COLORS = [
  "#00674F", "#009B77", "#2F9159", "#046307", "#D4AF37", "#D68A0C",
  "#E2456B", "#A855F7", "#5B3FE0", "#0891B2", "#7FE0A8", "#64748B",
];

// How a folder looks. Falls back to the old name-based lookup for any folder
// saved before icons existed.
function folderMeta(folder) {
  const legacy = (folder && FOLDER_META[folder.name]) || null;
  return {
    icon: (folder && FOLDER_ICONS[folder.icon]) || (legacy && legacy.icon) || FolderOpen,
    color: (folder && folder.color) || (legacy && legacy.color) || T.primary,
  };
}
const EVENT_COLORS = [T.primary, "#D4AF37", "#009B77", "#046307", "#00674F", "#7FE0A8"];

/* ------------------------------- UTILITIES ---------------------------------- */

function ymKey(date) { return `${date.getFullYear()}-${date.getMonth()}`; }
function dayKey(date) { return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`; }
function monthLabel(date) { return date.toLocaleDateString(undefined, { month: "long", year: "numeric" }); }
function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result.split(",")[1]);
    r.onerror = () => reject(new Error("Could not read file"));
    r.readAsDataURL(file);
  });
}

// Maps the AI's suggested folder onto one of the person's own folders.
function matchFolder(name, folderNames) {
  const fallback = folderNames.includes("Personal") ? "Personal" : folderNames[0] || "";
  if (!name) return fallback;
  const wanted = String(name).toLowerCase();
  const hit = folderNames.find((f) => f.toLowerCase() === wanted) || folderNames.find((f) => wanted.includes(f.toLowerCase()));
  return hit || fallback;
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
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, minHeight: "640px", background: T.bg, color: T.inkSoft, ...STARFIELD_BG, animation: "fadeIn 0.4s ease" }}>
      <Loader2 size={22} color={T.primary} style={{ animation: "spin 1s linear infinite" }} />
      <span style={{ fontSize: 13 }}>{label}</span>
    </div>
  );
}

const iconBtnStyle = { width: 36, height: 36, borderRadius: 12, border: `1px solid ${T.line}`, background: T.panel, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" };
const screenBox = { padding: "0 20px 100px", display: "flex", flexDirection: "column", gap: 14 };
const rowCardStyle = { display: "flex", alignItems: "center", gap: 12, background: `linear-gradient(180deg, ${T.panel}, #EFF7F1)`, border: `1px solid ${T.line}`, borderRadius: 14, padding: "13px 14px" };
const iconTileStyle = { width: 38, height: 38, borderRadius: 11, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 };
const primaryBtn = { display: "flex", alignItems: "center", justifyContent: "center", gap: 8, background: `linear-gradient(135deg, #6FDA9C, ${T.primary})`, color: "#fff", border: "none", borderRadius: 13, padding: "13px 16px", fontWeight: 700, fontSize: 14.5, cursor: "pointer", boxShadow: `0 4px 16px ${T.primaryGlow}` };
const secondaryBtn = { display: "flex", alignItems: "center", justifyContent: "center", gap: 8, background: T.panel, color: T.ink, border: `1px solid ${T.line}`, borderRadius: 13, padding: "13px 16px", fontWeight: 700, fontSize: 14, cursor: "pointer" };
const inputStyle = { width: "100%", border: `1px solid ${T.line}`, borderRadius: 12, padding: "12px 14px", fontSize: 14, color: T.ink, background: T.panel, boxSizing: "border-box" };
const selectStyle = { ...inputStyle, appearance: "none", cursor: "pointer" };

const PRIORITY_LEVELS = ["High", "Medium", "Low"]; // most urgent first
const PRIORITY_COLORS = { High: T.danger, Medium: "#D68A0C", Low: "#0E9F6E" };

// Three-way picker used when adding a task and when changing one.
function PriorityChips({ value, onChange, size = "md" }) {
  const small = size === "sm";
  return (
    <div role="radiogroup" aria-label="Priority" style={{ display: "flex", gap: 6 }}>
      {PRIORITY_LEVELS.map((level) => {
        const c = PRIORITY_COLORS[level];
        const active = value === level;
        return (
          <button
            key={level}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(level)}
            style={{
              cursor: "pointer", fontWeight: 700, borderRadius: 999,
              fontSize: small ? 11.5 : 12.5, padding: small ? "4px 10px" : "7px 14px",
              color: active ? "#fff" : c, background: active ? c : `${c}15`, border: `1px solid ${active ? c : `${c}55`}`,
            }}
          >{level}</button>
        );
      })}
    </div>
  );
}

function PriorityTag({ p }) {
  const colors = PRIORITY_COLORS;
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

const LEGAL_CONTENT = {
  terms: {
    title: "Terms of Service",
    body: `Last updated: October 4, 2026

By creating an account or using Orbit, you agree to these Terms.

# Eligibility
You must be at least 13 years old to use Orbit. If you are in the European Economic Area (EEA) or the United Kingdom, you must be at least 16. Orbit is not directed at children below these ages, and signup requires confirming you meet the minimum age.

# Your account
You're responsible for keeping your password secure and for activity under your account. An email address is optional at signup — without one, account recovery (e.g. a forgotten password) may not be possible.

# Your content
You keep ownership of what you create in Orbit. By uploading content, you grant us a limited license to store, process, and display it back to you — including sending images you upload to our AI provider (Anthropic) to generate suggested titles, tags, and summaries.

Don't upload anything that infringes someone else's rights, is illegal or abusive, or contains malware.

# AI features
Photo-tagging suggestions are AI-generated and may be inaccurate or incomplete. You're responsible for reviewing them before relying on them.

# Groups
Other members of a group you join can see messages you post there. We're not responsible for other users' conduct.

# Service availability
We aim to keep Orbit reliable, but don't guarantee uninterrupted access. Features marked "coming soon" aren't available yet and may change.

# Termination
You can stop using Orbit anytime, and you can delete your account from within the app at any time (Profile → Delete account). We may suspend accounts that violate these Terms.

# Disclaimers
The Service is provided "as is," without warranties of any kind, including that AI suggestions will be accurate.

# Limitation of liability
To the maximum extent permitted by law, we are not liable for indirect, incidental, or consequential damages arising from your use of the Service.

# Governing law
These Terms are governed by the laws of the Republic of the Philippines. Any dispute arising from these Terms or your use of Orbit is subject to the exclusive jurisdiction of the courts of the Republic of the Philippines.

# Changes
We may update these Terms; continued use after changes means you accept them.

# Contact
Questions? Reach us at ryecellz23@gmail.com.

This is a summary for in-app display. The full Terms of Service document governs.`,
  },
  privacy: {
    title: "Privacy Policy",
    body: `Last updated: October 4, 2026

This explains what Orbit collects and how we use it. The data controller for Orbit is the operator of this service, contactable at ryecellz23@gmail.com.

# What we collect
Account info: username (required), password (hashed, never stored in plain text), and full name and email (both optional). Your date of birth is checked at signup only to verify you meet the minimum age, and is not stored.

Your content: folders, archive items (including photos you upload), tasks, reminders, calendar events, study session logs, and group messages.

Technical data: IP address (for rate limiting, not tracking), basic server logs, and a single auth token in your browser's local storage to keep you signed in.

We don't use advertising cookies or third-party tracking scripts.

# How we use it
To provide the Service, process photos you upload for AI tagging, send account emails (verification, password reset) if you've linked an email, and prevent abuse.

# AI processing
Photos you upload through the capture feature are sent to Anthropic (Claude's maker) for analysis. Only images you actively upload are sent — nothing happens automatically in the background. We use Anthropic's Commercial Terms, which do not permit training on your data; Anthropic's own privacy terms govern their handling of the images.

# Subprocessors
We use the following third-party services to operate Orbit:

- Neon — PostgreSQL database hosting (all account and content data)
- Render — application hosting (all data processed by the API)
- Vercel — frontend static hosting (no user data)
- Anthropic — AI image analysis (images you actively upload)
- Resend — transactional email, if configured (your email address and the content of verification/reset emails)

# Data retention
Your account and content are retained while your account is active. When you delete your account, we immediately revoke all sessions, erase your content (folders, notes, tasks, reminders, events, study history) and anonymize your identifiers (username, email, name), then hard-delete the underlying record after a 30-day grace period, after which no personal data remains. Group messages you've posted remain visible to other group members, attributed to your display name — they are part of the group's shared history and are not removed by account deletion.

# Security
Passwords are hashed (bcrypt), sessions use signed tokens with expiration, and we rate-limit sensitive endpoints. No method is 100% secure.

# Your rights
Under the Philippine Data Privacy Act of 2012 (RA 10173) and, where applicable, the GDPR, you have the right to be informed about how your data is processed, to access your personal data, to correct inaccurate data, to erase or block your data, to object to processing, to data portability, and to file a complaint.

You can exercise access and portability yourself via Profile → Export my data, and erasure via Profile → Delete account. For anything else, contact us at ryecellz23@gmail.com. You may also file a complaint with the National Privacy Commission (privacy.gov.ph) or your local supervisory authority.

# Children's privacy
Orbit isn't directed at children under 13 (or 16 in the EEA/UK). Signup requires confirming you meet the minimum age. Contact us if you believe a child has created an account.

# Changes
We'll update the date above if this policy changes materially.

# Contact
ryecellz23@gmail.com

This is a summary for in-app display. The full Privacy Policy document governs.`,
  },
};

function renderLegalText(text) {
  return text.split("\n").map((line, i) => {
    if (line.startsWith("# ")) {
      return <div key={i} style={{ fontSize: 14, fontWeight: 800, color: T.ink, marginTop: 16, marginBottom: 4 }}>{line.slice(2)}</div>;
    }
    if (!line.trim()) return <div key={i} style={{ height: 4 }} />;
    return <div key={i} style={{ fontSize: 13, color: T.inkSoft, lineHeight: 1.6 }}>{line}</div>;
  });
}

function LegalModal({ type, onClose }) {
  const doc = LEGAL_CONTENT[type];
  if (!doc) return null;
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(8,28,19,0.6)", zIndex: 100, display: "flex", alignItems: "flex-end", justifyContent: "center" }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: T.panel, border: `1px solid ${T.line}`, borderRadius: "20px 20px 0 0", width: "100%", maxWidth: 420, maxHeight: "80vh", display: "flex", flexDirection: "column", ...STARFIELD_BG }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 20px 12px", borderBottom: `1px solid ${T.line}` }}>
          <span style={{ fontWeight: 800, fontSize: 16, color: T.ink }}>{doc.title}</span>
          <button onClick={onClose} style={iconBtnStyle}><X size={16} color={T.ink} /></button>
        </div>
        <div style={{ padding: "12px 20px 28px", overflowY: "auto" }}>{renderLegalText(doc.body)}</div>
      </div>
    </div>
  );
}

function AuthScreen({ onAuthed }) {
  const [mode, setMode] = useState("login"); // login | register | forgot
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [legalModal, setLegalModal] = useState(null); // null | "terms" | "privacy"
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
      const payload = mode === "login"
        ? { username, password }
        : { username, password, accept_terms: agreed, ...(name.trim() && { name: name.trim() }) };
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
    <div style={{ minHeight: "640px", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 28px", maxWidth: 420, margin: "0 auto", background: T.bg, ...STARFIELD_BG, animation: "fadeIn 0.4s ease" }}>
      {legalModal && <LegalModal type={legalModal} onClose={() => setLegalModal(null)} />}
      <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "center", marginBottom: 30 }}>
        <OrbitCatLogo size={46} />
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
            {mode === "register" && (
              <div style={{ fontSize: 11.5, color: T.inkFaint, marginTop: 6 }}>
                3–30 characters: letters, numbers, and . _ - only (no spaces)
              </div>
            )}
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

          {mode === "register" && (
            <label style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12, color: T.inkSoft, lineHeight: 1.5, cursor: "pointer" }}>
              <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} style={{ marginTop: 2, accentColor: T.primary }} />
              <span>
                I agree to the{" "}
                <span onClick={(e) => { e.preventDefault(); setLegalModal("terms"); }} style={{ color: T.primary, fontWeight: 700, cursor: "pointer" }}>Terms of Service</span>
                {" "}and{" "}
                <span onClick={(e) => { e.preventDefault(); setLegalModal("privacy"); }} style={{ color: T.primary, fontWeight: 700, cursor: "pointer" }}>Privacy Policy</span>
              </span>
            </label>
          )}

          {mode === "login" && (
            <span onClick={() => switchMode("forgot")} style={{ alignSelf: "flex-end", fontSize: 12.5, color: T.inkSoft, cursor: "pointer", marginTop: -4 }}>
              Forgot password?
            </span>
          )}

          <ErrorBanner message={error} />

          <button type="submit" disabled={loading || (mode === "register" && !agreed)} style={{ ...primaryBtn, opacity: loading || (mode === "register" && !agreed) ? 0.6 : 1, marginTop: 6 }}>
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

      <div style={{ textAlign: "center", marginTop: 18, fontSize: 11, color: T.inkFaint }}>
        <span onClick={() => setLegalModal("terms")} style={{ cursor: "pointer", textDecoration: "underline" }}>Terms</span>
        {" · "}
        <span onClick={() => setLegalModal("privacy")} style={{ cursor: "pointer", textDecoration: "underline" }}>Privacy</span>
      </div>

      <div style={{ textAlign: "center", marginTop: 10, fontSize: 11, color: T.inkFaint }}>
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
    <div style={{ minHeight: "640px", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 28px", maxWidth: 420, margin: "0 auto", background: T.bg, ...STARFIELD_BG, animation: "fadeIn 0.4s ease" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "center", marginBottom: 30 }}>
        <OrbitCatLogo size={46} />
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
    <div style={{ minHeight: "640px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "0 28px", maxWidth: 420, margin: "0 auto", textAlign: "center", background: T.bg, ...STARFIELD_BG, animation: "fadeIn 0.4s ease" }}>
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

function HomeScreen({ folderList, tasks, go, user }) {
  const recentEntries = folderList.filter((f) => f.items.length)
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

      <div className="orbit-cols" style={screenBox}>
       <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft }}>Recent folders</div>
          <span onClick={() => go("archive")} style={{ fontSize: 12.5, fontWeight: 700, color: T.primary, cursor: "pointer" }}>See all</span>
        </div>
        {recentEntries.length === 0 && <div style={{ fontSize: 13, color: T.inkFaint }}>Nothing captured yet — try the camera above.</div>}
        {recentEntries.map((f) => {
          const meta = folderMeta(f);
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

       </div>
       <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="orbit-tasks-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
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
    </div>
  );
}

// Create / edit / delete a folder. `folder` is null when creating.
function FolderEditorModal({ folder, onClose, onSave, onDelete }) {
  const isDesktop = useIsDesktop();
  const editing = !!folder;
  const initial = folderMeta(folder || {});
  const [name, setName] = useState(folder ? folder.name : "");
  const [color, setColor] = useState(folder ? initial.color : FOLDER_COLORS[0]);
  const [icon, setIcon] = useState(folder && folder.icon && FOLDER_ICONS[folder.icon] ? folder.icon : folder ? Object.keys(FOLDER_ICONS).find((k) => FOLDER_ICONS[k] === initial.icon) || "folder" : "folder");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const PreviewIcon = FOLDER_ICONS[icon] || FolderOpen;
  const itemCount = folder ? folder.items.length : 0;

  async function save() {
    const trimmed = name.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError("");
    try {
      await onSave({ name: trimmed, color, icon });
      onClose();
    } catch (err) {
      setError(err.message || "Couldn't save this folder.");
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError("");
    try {
      await onDelete();
      onClose();
    } catch (err) {
      setError(err.message || "Couldn't delete this folder.");
      setBusy(false);
    }
  }

  return (
    <div
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(8,28,19,0.6)", zIndex: 100, display: "flex", alignItems: isDesktop ? "center" : "flex-end", justifyContent: "center", padding: isDesktop ? 24 : 0 }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ background: T.panel, border: `1px solid ${T.line}`, borderRadius: isDesktop ? 20 : "20px 20px 0 0", width: "100%", maxWidth: 440, maxHeight: "90vh", overflowY: "auto", ...STARFIELD_BG }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 20px 12px", borderBottom: `1px solid ${T.line}` }}>
          <span style={{ fontWeight: 800, fontSize: 16, color: T.ink }}>{editing ? "Edit folder" : "New folder"}</span>
          <button onClick={onClose} style={iconBtnStyle} aria-label="Close"><X size={16} color={T.ink} /></button>
        </div>

        <div style={{ padding: "16px 20px 24px", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ ...rowCardStyle, gap: 12 }}>
            <div style={{ ...iconTileStyle, background: `${color}1A`, color }}><PreviewIcon size={18} /></div>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: name.trim() ? T.ink : T.inkFaint, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name.trim() || "Folder name"}</div>
          </div>

          <div>
            <FieldLabel>Name</FieldLabel>
            <input value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && save()} placeholder="e.g. Chemistry 101" maxLength={40} autoFocus style={{ ...inputStyle, marginTop: 6 }} />
          </div>

          <div>
            <FieldLabel>Color</FieldLabel>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 8 }}>
              {FOLDER_COLORS.map((c) => (
                <button key={c} type="button" onClick={() => setColor(c)} aria-label={`Color ${c}`} style={{ width: 30, height: 30, borderRadius: 999, background: c, cursor: "pointer", border: color === c ? `3px solid ${T.ink}` : "3px solid transparent", boxShadow: color === c ? `0 0 0 2px ${T.panel} inset` : "none", padding: 0 }} />
              ))}
            </div>
          </div>

          <div>
            <FieldLabel>Icon</FieldLabel>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 8, marginTop: 8 }}>
              {Object.entries(FOLDER_ICONS).map(([key, Ico]) => (
                <button key={key} type="button" onClick={() => setIcon(key)} aria-label={`Icon ${key}`} style={{ aspectRatio: "1", borderRadius: 10, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", background: icon === key ? `${color}1A` : T.panel, border: `1px solid ${icon === key ? color : T.line}`, color: icon === key ? color : T.inkSoft, padding: 0 }}>
                  <Ico size={17} />
                </button>
              ))}
            </div>
          </div>

          <ErrorBanner message={error} />

          <button onClick={save} disabled={busy || !name.trim()} style={{ ...primaryBtn, opacity: busy || !name.trim() ? 0.6 : 1 }}>
            {busy && !confirmDelete ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : editing ? "Save changes" : "Create folder"}
          </button>

          {editing && onDelete && (
            confirmDelete ? (
              <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "stretch", gap: 10, border: `1px solid ${T.danger}` }}>
                <div style={{ fontSize: 12.5, color: T.inkSoft, lineHeight: 1.5 }}>
                  Delete <strong>{folder.name}</strong>{itemCount > 0 ? <> and its {itemCount} item{itemCount === 1 ? "" : "s"}</> : null}? This can't be undone.
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                  <button type="button" disabled={busy} onClick={() => setConfirmDelete(false)} style={{ ...secondaryBtn, flex: 1 }}>Keep it</button>
                  <button type="button" disabled={busy} onClick={remove} style={{ ...secondaryBtn, flex: 1, background: T.danger, color: "#fff", border: "none" }}>
                    {busy ? <Loader2 size={15} style={{ animation: "spin 1s linear infinite" }} /> : "Delete"}
                  </button>
                </div>
              </div>
            ) : (
              <button type="button" onClick={() => setConfirmDelete(true)} style={{ ...secondaryBtn, color: T.danger }}><Trash2 size={15} /> Delete folder</button>
            )
          )}
        </div>
      </div>
    </div>
  );
}

function ArchiveScreen({ folderList, go, onCreate, onUpdate, onDelete, onMove }) {
  const [customizing, setCustomizing] = useState(false);
  const [modal, setModal] = useState(null); // null | { folder: Folder | null }

  return (
    <div>
      <TopBar
        title="My Archive"
        right={folderList.length > 0 && (
          <button
            onClick={() => setCustomizing((c) => !c)}
            aria-label={customizing ? "Done customizing" : "Customize folders"}
            title={customizing ? "Done" : "Customize folders"}
            style={{ ...iconBtnStyle, ...(customizing ? { background: T.primarySoft, border: `1px solid ${T.primary}` } : {}) }}
          >
            {customizing ? <Check size={16} color={T.primary} /> : <Pencil size={15} color={T.ink} />}
          </button>
        )}
      />
      {customizing && (
        <div style={{ padding: "0 20px 10px", fontSize: 12.5, color: T.inkSoft }}>
          Tap a folder to edit it, or use the arrows to change the order.
        </div>
      )}
      <div className="orbit-grid" style={{ ...screenBox, paddingBottom: 14 }}>
        {folderList.length === 0 && (
          <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "center", textAlign: "center", gap: 6, padding: "26px 16px" }}>
            <div style={{ ...iconTileStyle, background: T.primarySoft, color: T.primary }}><FolderOpen size={18} /></div>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: T.ink }}>No folders yet</div>
            <div style={{ fontSize: 12.5, color: T.inkFaint }}>Create a folder for each class or project to keep your notes sorted.</div>
          </div>
        )}
        {folderList.map((folder, i) => {
          const meta = folderMeta(folder);
          const Icon = meta.icon;
          return (
            <div key={folder.id} onClick={() => (customizing ? setModal({ folder }) : go("folder", folder.name))} style={{ ...rowCardStyle, cursor: "pointer" }}>
              <div style={{ ...iconTileStyle, background: `${meta.color}1A`, color: meta.color }}><Icon size={18} /></div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 14.5, color: T.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{folder.name}</div>
                <div style={{ fontSize: 12.5, color: T.inkFaint }}>{folder.items.length} item{folder.items.length === 1 ? "" : "s"}</div>
              </div>
              {customizing ? (
                <div style={{ display: "flex", gap: 6 }} onClick={(e) => e.stopPropagation()}>
                  <button disabled={i === 0} onClick={() => onMove(folder.id, -1)} aria-label="Move earlier" style={{ ...iconBtnStyle, width: 32, height: 32, opacity: i === 0 ? 0.35 : 1 }}><ChevronUp size={15} color={T.ink} /></button>
                  <button disabled={i === folderList.length - 1} onClick={() => onMove(folder.id, 1)} aria-label="Move later" style={{ ...iconBtnStyle, width: 32, height: 32, opacity: i === folderList.length - 1 ? 0.35 : 1 }}><ChevronDown size={15} color={T.ink} /></button>
                  <button onClick={() => setModal({ folder })} aria-label="Edit folder" style={{ ...iconBtnStyle, width: 32, height: 32 }}><Pencil size={14} color={T.ink} /></button>
                </div>
              ) : (
                <ChevronRight size={17} color={T.inkFaint} />
              )}
            </div>
          );
        })}
      </div>
      <div style={{ padding: "0 20px 100px" }}>
        <button onClick={() => setModal({ folder: null })} style={{ ...primaryBtn, width: "100%", boxSizing: "border-box" }}><Plus size={16} /> New folder</button>
      </div>
      {modal && (
        <FolderEditorModal
          folder={modal.folder}
          onClose={() => setModal(null)}
          onSave={(payload) => (modal.folder ? onUpdate(modal.folder.id, payload) : onCreate(payload))}
          onDelete={modal.folder ? () => onDelete(modal.folder.id) : null}
        />
      )}
    </div>
  );
}

function FolderDetailScreen({ name, folder, go, back, onDeleteItem, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const meta = folderMeta(folder || { name });
  const Icon = meta.icon;
  const items = folder ? folder.items : [];
  return (
    <div>
      <TopBar
        title={name}
        onBack={back}
        right={folder && <button onClick={() => setEditing(true)} aria-label="Edit folder" title="Edit folder" style={iconBtnStyle}><Pencil size={15} color={T.ink} /></button>}
      />
      <div style={screenBox}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: -4 }}>
          <div style={{ ...iconTileStyle, background: `${meta.color}1A`, color: meta.color }}><Icon size={18} /></div>
          <div style={{ fontSize: 13, color: T.inkSoft }}>{items.length} items in this folder</div>
        </div>
        {items.length === 0 && <div style={{ textAlign: "center", padding: "40px 10px", color: T.inkFaint, fontSize: 13.5 }}>Nothing here yet. Capture a photo or note to add your first item.</div>}
        <div className="orbit-grid" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
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
        </div>
        <button onClick={() => go("capture")} style={{ ...primaryBtn, marginTop: 6 }}><Plus size={16} /> Add to {name}</button>
      </div>
      {editing && folder && (
        <FolderEditorModal
          folder={folder}
          onClose={() => setEditing(false)}
          onSave={(payload) => onUpdate(folder.id, payload)}
          onDelete={async () => { await onDelete(folder.id); back(); }}
        />
      )}
    </div>
  );
}

function CaptureScreen({ back, onSave, folders }) {
  const folderNames = Object.keys(folders);
  const inputRef = useRef(null);
  const [image, setImage] = useState(null);
  const [mediaType, setMediaType] = useState("image/jpeg");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [folder, setFolder] = useState(folderNames.includes("Personal") ? "Personal" : folderNames[0] || "");
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
      const result = await api.ai.analyze({ image_base64: b64, media_type: file.type || "image/jpeg", candidate_folders: folderNames });
      setTitle(result.title || "Untitled note");
      setFolder(matchFolder(result.folder, folderNames));
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
    if (!targetFolder) { setError(folderNames.length ? `Folder "${folder}" wasn't found.` : "Create a folder in your Archive first, then come back to save this."); return; }
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
                  {folderNames.map((f) => <option key={f} value={f}>{f}</option>)}
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

function CalendarScreen({ back, events, onAddEvent, onDeleteEvent }) {
  const [month, setMonth] = useState(() => { const d = new Date(); d.setDate(1); return d; });
  const [selected, setSelected] = useState(() => new Date());
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const eventsByDay = {};
  events.forEach((ev) => {
    const k = dayKey(new Date(ev.start_time));
    (eventsByDay[k] = eventsByDay[k] || []).push(ev);
  });

  const firstOfMonth = new Date(month.getFullYear(), month.getMonth(), 1);
  const startOffset = firstOfMonth.getDay();
  const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const cells = [...Array(startOffset).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => new Date(month.getFullYear(), month.getMonth(), i + 1))];
  const today = new Date();
  const dayEvents = (eventsByDay[dayKey(selected)] || []).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

  function shiftMonth(delta) {
    const d = new Date(month);
    d.setMonth(d.getMonth() + delta);
    setMonth(d);
  }

  function openForm() {
    const base = new Date(selected);
    base.setHours(base.getHours() + 1, 0, 0, 0);
    setStart(toLocalInputValue(base));
    const endD = new Date(base);
    endD.setHours(endD.getHours() + 1);
    setEnd(toLocalInputValue(endD));
    setTitle("");
    setError("");
    setShowForm(true);
  }

  async function saveEvent() {
    if (!title.trim() || !start) return;
    setSaving(true);
    setError("");
    try {
      await onAddEvent({
        title: title.trim(),
        start_time: start,
        end_time: end || null,
        color: EVENT_COLORS[events.length % EVENT_COLORS.length],
      });
      setShowForm(false);
    } catch (err) {
      setError(err.message || "Couldn't save event.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <TopBar title={monthLabel(month)} onBack={back} right={<>
        <button onClick={() => shiftMonth(-1)} style={iconBtnStyle}><ChevronLeft size={16} color={T.ink} /></button>
        <button onClick={() => shiftMonth(1)} style={iconBtnStyle}><ChevronRight size={16} color={T.ink} /></button>
      </>} />
      <div className="orbit-split" style={screenBox}>
        <div style={{ background: T.panel, border: `1px solid ${T.line}`, borderRadius: 16, padding: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 4, marginBottom: 6 }}>
            {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => <div key={i} style={{ textAlign: "center", fontSize: 11, fontWeight: 700, color: T.inkFaint }}>{d}</div>)}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 4 }}>
            {cells.map((d, i) => {
              const hasEvent = d && eventsByDay[dayKey(d)];
              const isSel = d && dayKey(d) === dayKey(selected);
              const isToday = d && dayKey(d) === dayKey(today);
              return (
                <div key={i} onClick={() => d && setSelected(d)} style={{ aspectRatio: "1", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 10, fontSize: 12.5, fontWeight: isSel ? 800 : 500, cursor: d ? "pointer" : "default", background: isSel ? T.primary : "transparent", color: isSel ? "#fff" : d ? T.ink : "transparent", position: "relative", border: isToday && !isSel ? `1px solid ${T.primary}` : "none" }}>
                  {d && d.getDate()}
                  {hasEvent && !isSel && <span style={{ position: "absolute", bottom: 3, width: 4, height: 4, borderRadius: 99, background: T.primary }} />}
                </div>
              );
            })}
          </div>
        </div>

       <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft }}>{selected.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}</div>
          <span onClick={openForm} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12.5, fontWeight: 700, color: T.primary, cursor: "pointer" }}><Plus size={14} /> Add event</span>
        </div>

        {dayEvents.length === 0 && <div style={{ fontSize: 13, color: T.inkFaint, padding: "10px 0" }}>No events scheduled.</div>}
        {dayEvents.map((ev) => (
          <div key={ev.id} style={rowCardStyle}>
            <div style={{ width: 4, height: 34, borderRadius: 4, background: ev.color }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: T.ink }}>{ev.title}</div>
              <div style={{ fontSize: 12, color: T.inkFaint }}>
                {new Date(ev.start_time).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
                {ev.end_time && ` – ${new Date(ev.end_time).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`}
              </div>
            </div>
            <X size={15} color={T.inkFaint} style={{ cursor: "pointer" }} onClick={() => onDeleteEvent(ev.id)} />
          </div>
        ))}

        {showForm && (
          <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "stretch", gap: 10 }}>
            <FieldLabel>Title</FieldLabel>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Math 21 Quiz" style={inputStyle} autoFocus />
            <FieldLabel>Starts</FieldLabel>
            <input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} style={inputStyle} />
            <FieldLabel>Ends <span style={{ fontWeight: 500, color: T.inkFaint }}>(optional)</span></FieldLabel>
            <input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} style={inputStyle} />
            <ErrorBanner message={error} />
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => setShowForm(false)} style={{ ...secondaryBtn, flex: 1 }}>Cancel</button>
              <button onClick={saveEvent} disabled={saving || !title.trim()} style={{ ...primaryBtn, flex: 1, opacity: saving || !title.trim() ? 0.6 : 1 }}>
                {saving ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : "Save"}
              </button>
            </div>
          </div>
        )}
       </div>
      </div>
    </div>
  );
}

function TodoScreen({ tasks, back, onToggle, onAdd, onSetPriority }) {
  const [filter, setFilter] = useState("All");
  const [sort, setSort] = useState("Newest"); // "Newest" | "Priority"
  const [draft, setDraft] = useState("");
  const [draftPriority, setDraftPriority] = useState("Medium");
  const [openId, setOpenId] = useState(null); // task whose priority picker is showing

  const filtered = tasks.filter((t) => filter === "All" || (filter === "Completed" ? t.done : !t.done));
  const visible = sort === "Priority"
    ? // stable sort: finished tasks sink, then High → Medium → Low; ties keep their current order
      [...filtered].sort((x, y) => Number(x.done) - Number(y.done) || PRIORITY_LEVELS.indexOf(x.priority) - PRIORITY_LEVELS.indexOf(y.priority))
    : filtered;

  async function addTask() {
    if (!draft.trim()) return;
    await onAdd(draft.trim(), draftPriority);
    setDraft("");
  }

  const pill = (active) => ({ border: `1px solid ${active ? T.ink : T.line}`, borderRadius: 999, padding: "7px 14px", fontSize: 12.5, fontWeight: 700, cursor: "pointer", background: active ? T.ink : T.panel, color: active ? "#fff" : T.inkSoft });

  return (
    <div>
      <TopBar title="My Tasks" onBack={back} />
      <div style={screenBox}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {["All", "Active", "Completed"].map((f) => (
            <button key={f} onClick={() => setFilter(f)} style={pill(filter === f)}>{f}</button>
          ))}
          <span style={{ flex: 1 }} />
          <button onClick={() => setSort((s) => (s === "Priority" ? "Newest" : "Priority"))} style={pill(sort === "Priority")} title="Show the most urgent tasks first">
            {sort === "Priority" ? "Sorted by priority" : "Sort by priority"}
          </button>
        </div>
        {tasks.length === 0 && (
          <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "center", textAlign: "center", gap: 6, padding: "26px 16px" }}>
            <div style={{ ...iconTileStyle, background: T.primarySoft, color: T.primary }}><CheckSquare size={18} /></div>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: T.ink }}>No tasks yet</div>
            <div style={{ fontSize: 12.5, color: T.inkFaint }}>Add your first one below and give it a priority.</div>
          </div>
        )}
        <div className="orbit-grid" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {visible.map((t) => (
            <div key={t.id} style={rowCardStyle} onClick={() => onToggle(t)}>
              <div style={{ cursor: "pointer" }}>{t.done ? <CheckSquare size={19} color={T.primary} /> : <Square size={19} color={T.inkFaint} />}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: t.done ? T.inkFaint : T.ink, textDecoration: t.done ? "line-through" : "none", overflowWrap: "anywhere" }}>{t.text}</div>
                {openId === t.id && (
                  <div style={{ marginTop: 8 }} onClick={(e) => e.stopPropagation()}>
                    <PriorityChips
                      size="sm"
                      value={t.priority}
                      onChange={(level) => { setOpenId(null); if (level !== t.priority) onSetPriority(t, level); }}
                    />
                  </div>
                )}
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); setOpenId((id) => (id === t.id ? null : t.id)); }}
                aria-label={`Priority ${t.priority} — tap to change`}
                title="Change priority"
                style={{ background: "none", border: "none", padding: 0, cursor: "pointer" }}
              >
                <PriorityTag p={t.priority} />
              </button>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
          <div style={{ display: "flex", gap: 8 }}>
            <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addTask()} placeholder="Add a task…" style={inputStyle} />
            <button onClick={addTask} aria-label="Add task" style={{ ...primaryBtn, padding: "0 18px" }}><Plus size={16} /></button>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12.5, fontWeight: 700, color: T.inkSoft }}>Priority</span>
            <PriorityChips value={draftPriority} onChange={setDraftPriority} />
          </div>
        </div>
      </div>
    </div>
  );
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Older browsers / non-secure contexts: fall back to a hidden textarea.
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    } catch {
      return false;
    }
  }
}

function inviteLinkFor(code) {
  return `${window.location.origin}/?join=${code}`;
}

// Create / join flow. Creating is two steps: name it, then a "share the
// invite" screen — so the person leaves with the code in hand instead of
// being dropped into an empty chat with no idea how to bring anyone in.
function GroupFlowModal({ initialMode, onClose, onCreate, onJoin, go }) {
  const isDesktop = useIsDesktop();
  const [mode, setMode] = useState(initialMode); // "create" | "join"
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState(null);
  const [copied, setCopied] = useState("");

  function switchMode(next) {
    setMode(next);
    setInput("");
    setError("");
  }

  async function submit() {
    const value = input.trim();
    if (!value || busy) return;
    setBusy(true);
    setError("");
    try {
      if (mode === "create") {
        setCreated(await onCreate(value));
      } else {
        await onJoin(value.toLowerCase());
        onClose();
      }
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function copy(kind, text) {
    if (await copyToClipboard(text)) {
      setCopied(kind);
      setTimeout(() => setCopied(""), 1800);
    }
  }

  function share() {
    navigator.share({
      title: `Join ${created.name} on Orbit`,
      text: `Join my study group "${created.name}" on Orbit.`,
      url: inviteLinkFor(created.invite_code),
    }).catch(() => {}); // dismissing the share sheet isn't an error
  }

  const tabStyle = (active) => ({
    flex: 1, padding: "9px 0", borderRadius: 10, border: "none", cursor: "pointer", fontWeight: 700, fontSize: 13,
    background: active ? T.panel : "transparent", color: active ? T.ink : T.inkSoft,
    boxShadow: active ? "0 1px 4px rgba(8,28,19,0.12)" : "none",
  });

  return (
    <div
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(8,28,19,0.6)", zIndex: 100, display: "flex", alignItems: isDesktop ? "center" : "flex-end", justifyContent: "center", padding: isDesktop ? 24 : 0 }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ background: T.panel, border: `1px solid ${T.line}`, borderRadius: isDesktop ? 20 : "20px 20px 0 0", width: "100%", maxWidth: 440, maxHeight: "90vh", overflowY: "auto", ...STARFIELD_BG }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 20px 12px", borderBottom: `1px solid ${T.line}` }}>
          <span style={{ fontWeight: 800, fontSize: 16, color: T.ink }}>{created ? "Group created" : mode === "create" ? "New group" : "Join a group"}</span>
          <button onClick={onClose} style={iconBtnStyle} aria-label="Close"><X size={16} color={T.ink} /></button>
        </div>

        {!created ? (
          <div style={{ padding: "16px 20px 24px", display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 4, background: T.primarySoft, borderRadius: 12, padding: 4 }}>
              <button onClick={() => switchMode("create")} style={tabStyle(mode === "create")}>Create</button>
              <button onClick={() => switchMode("join")} style={tabStyle(mode === "join")}>Join with code</button>
            </div>
            <FieldLabel>{mode === "create" ? "Group name" : "Invite code"}</FieldLabel>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder={mode === "create" ? "e.g. Physics Study Group" : "8-character code"}
              maxLength={mode === "create" ? 60 : 32}
              autoFocus
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              style={inputStyle}
            />
            <div style={{ fontSize: 12, color: T.inkFaint, marginTop: -4 }}>
              {mode === "create"
                ? "You'll get an invite code and link to share as soon as it's created."
                : "Ask a group member for their invite code, or open the invite link they sent you."}
            </div>
            <ErrorBanner message={error} />
            <button onClick={submit} disabled={busy || !input.trim()} style={{ ...primaryBtn, opacity: busy || !input.trim() ? 0.6 : 1 }}>
              {busy ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : mode === "create" ? "Create group" : "Join group"}
            </button>
          </div>
        ) : (
          <div style={{ padding: "18px 20px 24px", display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ width: 52, height: 52, borderRadius: 999, background: T.primarySoft, color: T.primary, display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 8 }}><Users size={24} /></div>
              <div style={{ fontWeight: 800, fontSize: 17, color: T.ink }}>{created.name}</div>
              <div style={{ fontSize: 13, color: T.inkSoft, marginTop: 2 }}>Invite people with this code or link.</div>
            </div>
            <div style={{ background: T.primarySoft, border: `1px dashed ${T.primary}`, borderRadius: 14, padding: "14px 10px", textAlign: "center" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: T.inkSoft, letterSpacing: 0.6, textTransform: "uppercase" }}>Invite code</div>
              <div style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", fontSize: 26, fontWeight: 800, letterSpacing: 3, color: T.ink, marginTop: 4, userSelect: "all" }}>{created.invite_code}</div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => copy("code", created.invite_code)} style={{ ...secondaryBtn, flex: 1 }}>
                {copied === "code" ? <Check size={15} color={T.primary} /> : <Copy size={15} />} {copied === "code" ? "Copied" : "Copy code"}
              </button>
              <button onClick={() => copy("link", inviteLinkFor(created.invite_code))} style={{ ...secondaryBtn, flex: 1 }}>
                {copied === "link" ? <Check size={15} color={T.primary} /> : <Copy size={15} />} {copied === "link" ? "Copied" : "Copy link"}
              </button>
            </div>
            {typeof navigator !== "undefined" && navigator.share && (
              <button onClick={share} style={secondaryBtn}><Share2 size={15} /> Share…</button>
            )}
            <button onClick={() => { onClose(); go("group", created.id); }} style={primaryBtn}>Open chat</button>
          </div>
        )}
      </div>
    </div>
  );
}

function GroupsListScreen({ back, groups, go, onCreate, onJoin, activeId }) {
  const [flow, setFlow] = useState(null); // null | "create" | "join"

  return (
    <div>
      <TopBar title="Groups" />
      <div style={screenBox}>
        {groups.length === 0 && (
          <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "center", textAlign: "center", gap: 6, padding: "26px 16px" }}>
            <div style={{ ...iconTileStyle, background: T.primarySoft, color: T.primary }}><Users size={18} /></div>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: T.ink }}>No groups yet</div>
            <div style={{ fontSize: 12.5, color: T.inkFaint }}>Start one for your class or study crew, or join a friend's with an invite code.</div>
          </div>
        )}
        {groups.map((g) => (
          <div key={g.id} onClick={() => go("group", g.id)} style={{ ...rowCardStyle, cursor: "pointer", ...(g.id === activeId ? { border: `1px solid ${T.primary}`, background: T.primarySoft } : {}) }}>
            <div style={{ ...iconTileStyle, background: T.primarySoft, color: T.primary }}><Users size={18} /></div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 14.5, color: T.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{g.name}</div>
              <div style={{ fontSize: 12, color: T.inkFaint }}>{g.member_count} member{g.member_count === 1 ? "" : "s"} · code {g.invite_code}</div>
            </div>
            <ChevronRight size={17} color={T.inkFaint} />
          </div>
        ))}

        <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
          <button onClick={() => setFlow("create")} style={{ ...primaryBtn, flex: 1 }}><Plus size={16} /> New group</button>
          <button onClick={() => setFlow("join")} style={{ ...secondaryBtn, flex: 1 }}>Join with code</button>
        </div>
      </div>
      {flow && <GroupFlowModal initialMode={flow} onClose={() => setFlow(null)} onCreate={onCreate} onJoin={onJoin} go={go} />}
    </div>
  );
}

function GroupScreen({ back, user, group, embedded = false }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [connected, setConnected] = useState(false);
  const [authFailed, setAuthFailed] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const wsRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    api.groups.messages(group.id)
  .then((history) => { if (!cancelled) setMessages((prev) => [...(history || []), ...prev]); })
  .catch(() => {});

    const ws = new WebSocket(api.wsURL(group.id));
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
  }, [group.id]);

  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight); }, [messages]);

  function send() {
    if (!draft.trim() || !wsRef.current || wsRef.current.readyState !== 1) return;
    // sender_name is no longer sent — the backend derives it from the
    // authenticated connection so a message can't be posted as someone else.
    wsRef.current.send(JSON.stringify({ text: draft.trim() }));
    setDraft("");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: embedded ? "auto" : "100%", flex: embedded ? 1 : undefined, minHeight: 0 }}>
      <TopBar title={group.name} onBack={embedded ? undefined : back} right={<>
        <span style={{ fontSize: 11, fontWeight: 700, color: connected ? "#0E9F6E" : T.inkFaint, alignSelf: "center", marginRight: 4 }}>{connected ? "● live" : "connecting…"}</span>
        <button onClick={() => setShowCode((s) => !s)} style={iconBtnStyle}><Users size={15} color={T.ink} /></button>
      </>} />
      {showCode && (
        <div style={{ margin: "0 20px 10px", fontSize: 12, color: T.inkSoft, background: T.primarySoft, borderRadius: 10, padding: "8px 12px" }}>
          Invite code: <strong>{group.invite_code}</strong> · {group.member_count} member{group.member_count === 1 ? "" : "s"}
          <span
            onClick={async () => { if (await copyToClipboard(inviteLinkFor(group.invite_code))) { setLinkCopied(true); setTimeout(() => setLinkCopied(false), 1800); } }}
            style={{ marginLeft: 10, fontWeight: 700, color: T.primary, cursor: "pointer" }}
          >{linkCopied ? "Link copied ✓" : "Copy invite link"}</span>
        </div>
      )}
      {authFailed && <div style={{ margin: "0 20px 10px" }}><ErrorBanner message="Your session couldn't be verified for chat. Try signing out and back in." /></div>}
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "0 20px", display: "flex", flexDirection: "column", gap: 10 }}>
        {messages.map((m) => {
          // sender_id is the reliable signal; older messages only have a name.
          const mine = m.sender_id ? m.sender_id === user.id : m.sender_name === (user.name || user.username);
          const sentAt = m.created_at ? new Date(m.created_at.endsWith("Z") || /[+-]\d\d:\d\d$/.test(m.created_at) ? m.created_at : `${m.created_at}Z`) : null;
          return (
            <div key={m.id} style={{ alignSelf: mine ? "flex-end" : "flex-start", maxWidth: embedded ? "70%" : "78%" }}>
              {!mine && <div style={{ fontSize: 11, fontWeight: 700, color: T.primary, marginBottom: 2 }}>{m.sender_name}</div>}
              <div style={{ background: mine ? T.primary : T.panel, color: mine ? "#fff" : T.ink, border: mine ? "none" : `1px solid ${T.line}`, borderRadius: 14, padding: "10px 13px", fontSize: 13.5, overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>{m.text}</div>
              {sentAt && !isNaN(sentAt) && <div style={{ fontSize: 10.5, color: T.inkFaint, marginTop: 3, textAlign: mine ? "right" : "left" }}>{sentAt.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}</div>}
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 8, padding: embedded ? "12px 20px 16px" : "12px 20px 90px", alignItems: "center" }}>
        <Paperclip size={17} color={T.inkFaint} />
        <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Type a message…" style={inputStyle} />
        <button onClick={send} style={{ ...iconBtnStyle, background: T.primary, border: "none" }}><Send size={15} color="#fff" /></button>
      </div>
    </div>
  );
}

function InsightsScreen({ back, tasks, studySessions, onLogSession }) {
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0); // seconds
  const [saving, setSaving] = useState(false);
  const startRef = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (running) {
      startRef.current = Date.now() - elapsed * 1000;
      intervalRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)), 1000);
    }
    return () => clearInterval(intervalRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running]);

  async function stopAndLog() {
    setRunning(false);
    clearInterval(intervalRef.current);
    const minutes = Math.max(1, Math.round(elapsed / 60));
    setSaving(true);
    try {
      await onLogSession(minutes);
    } finally {
      setElapsed(0);
      setSaving(false);
    }
  }

  const done = tasks.filter((t) => t.done).length;
  const pct = tasks.length ? Math.round((done / tasks.length) * 100) : 0;

  const now = new Date();
  const last7 = Array.from({ length: 7 }, (_, i) => { const d = new Date(now); d.setDate(d.getDate() - (6 - i)); return d; });
  const minutesByDay = {};
  studySessions.forEach((s) => {
    const k = dayKey(new Date(s.started_at));
    minutesByDay[k] = (minutesByDay[k] || 0) + s.minutes;
  });
  const weekData = last7.map((d) => ({ day: d.toLocaleDateString(undefined, { weekday: "short" })[0], minutes: minutesByDay[dayKey(d)] || 0 }));
  const maxMinutes = Math.max(1, ...weekData.map((d) => d.minutes));
  const totalMinutes = weekData.reduce((sum, d) => sum + d.minutes, 0);
  const totalLabel = totalMinutes >= 60 ? `${Math.floor(totalMinutes / 60)}h ${totalMinutes % 60}m` : `${totalMinutes}m`;

  const timerLabel = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;

  return (
    <div>
      <TopBar title="Insights" onBack={back} />
      <div style={screenBox}>
        <div style={{ ...rowCardStyle, flexDirection: "column", gap: 10, padding: 18 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft }}>Study timer</div>
          <div style={{ fontSize: 34, fontWeight: 800, color: T.ink, fontVariantNumeric: "tabular-nums" }}>{timerLabel}</div>
          {!running ? (
            <button onClick={() => setRunning(true)} style={primaryBtn}>Start studying</button>
          ) : (
            <button onClick={stopAndLog} disabled={saving} style={{ ...primaryBtn, background: T.danger, opacity: saving ? 0.6 : 1 }}>
              {saving ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : "Stop & log session"}
            </button>
          )}
        </div>

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
            <div style={{ fontSize: 20, fontWeight: 800, color: T.ink }}>{totalLabel}</div>
            <div style={{ fontSize: 11.5, color: T.inkFaint, fontWeight: 700 }}>Last 7 days</div>
          </div>
        </div>

        <div style={{ ...rowCardStyle, flexDirection: "column", alignItems: "stretch", gap: 14, padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft }}>Study time this week</div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 100 }}>
            {weekData.map((d, i) => (
              <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <div style={{ width: "100%", borderRadius: 6, background: T.primary, height: `${Math.max(4, (d.minutes / maxMinutes) * 80)}px`, opacity: 0.85 }} />
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
        <div className="orbit-grid" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
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
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
          <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addReminder()} placeholder="New reminder…" style={inputStyle} />
          <button onClick={addReminder} style={{ ...primaryBtn, padding: "0 18px" }}><Plus size={16} /></button>
        </div>
      </div>
    </div>
  );
}

// Authenticated request for the account endpoints (export / delete). Kept
// here so api.js doesn't need changes; errors come back as readable messages.
async function accountRequest(path, options = {}) {
  const res = await fetch(`${String(api.base).replace(/\/$/, "")}${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${api.getToken()}`, ...(options.headers || {}) },
  });
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") msg = body.detail;
      else if (body && Array.isArray(body.detail) && body.detail.length) {
        msg = body.detail.map((d) => String((d && d.msg) || "Invalid value").replace(/^Value error,\s*/i, "")).join(" ");
      }
    } catch { /* non-JSON error body */ }
    if (res.status === 429) msg = "Too many attempts — please wait a bit and try again.";
    throw new Error(msg);
  }
  return res;
}

// Folder customization calls (kept here so api.js doesn't need changes).
const folderApi = {
  update: (id, patch) =>
    accountRequest(`/folders/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) }).then((r) => r.json()),
  remove: (id) => accountRequest(`/folders/${id}`, { method: "DELETE" }),
  reorder: (ids) =>
    accountRequest("/folders/order", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids }) }),
};

function ProfileScreen({ back, user, onLogout, onUserUpdate }) {
  const [emailInput, setEmailInput] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState("");
  const [legalModal, setLegalModal] = useState(null); // null | "terms" | "privacy"
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [showDelete, setShowDelete] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  async function exportData() {
    setExporting(true);
    setExportError("");
    try {
      const res = await accountRequest("/me/export");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `orbit-export-${user.username}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err.message || "Couldn't export your data.");
    } finally {
      setExporting(false);
    }
  }

  async function deleteAccount(e) {
    e.preventDefault();
    setDeleting(true);
    setDeleteError("");
    try {
      await accountRequest("/me/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: deletePassword }),
      });
      api.clearToken();
      window.location.reload();
    } catch (err) {
      setDeleteError(err.message || "Couldn't delete your account.");
      setDeleting(false);
    }
  }

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
      {legalModal && <LegalModal type={legalModal} onClose={() => setLegalModal(null)} />}
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

        <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft, marginTop: 10 }}>Legal</div>
        <div onClick={() => setLegalModal("terms")} style={{ ...rowCardStyle, cursor: "pointer" }}>
          <FileText size={17} color={T.inkSoft} />
          <div style={{ fontSize: 13.5, color: T.ink }}>Terms of Service</div>
        </div>
        <div onClick={() => setLegalModal("privacy")} style={{ ...rowCardStyle, cursor: "pointer" }}>
          <Lock size={17} color={T.inkSoft} />
          <div style={{ fontSize: 13.5, color: T.ink }}>Privacy Policy</div>
        </div>

        <div style={{ fontSize: 13, fontWeight: 700, color: T.inkSoft, marginTop: 10 }}>Your data</div>
        <div onClick={exporting ? undefined : exportData} style={{ ...rowCardStyle, cursor: exporting ? "default" : "pointer", opacity: exporting ? 0.6 : 1 }}>
          {exporting ? <Loader2 size={17} color={T.inkSoft} style={{ animation: "spin 1s linear infinite" }} /> : <Download size={17} color={T.inkSoft} />}
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13.5, color: T.ink }}>Export my data</div>
            <div style={{ fontSize: 11.5, color: T.inkFaint }}>Download everything in your account as a JSON file</div>
          </div>
        </div>
        {exportError && <ErrorBanner message={exportError} />}

        {!showDelete ? (
          <div onClick={() => setShowDelete(true)} style={{ ...rowCardStyle, cursor: "pointer" }}>
            <Trash2 size={17} color={T.danger} />
            <div style={{ fontSize: 13.5, color: T.danger, fontWeight: 700 }}>Delete account</div>
          </div>
        ) : (
          <form onSubmit={deleteAccount} style={{ ...rowCardStyle, flexDirection: "column", alignItems: "stretch", gap: 10, border: `1px solid ${T.danger}` }}>
            <FieldLabel icon={Trash2}>Delete your account</FieldLabel>
            <div style={{ fontSize: 12, color: T.inkSoft, lineHeight: 1.5 }}>
              This permanently deletes your folders, notes, tasks, reminders, events and study history, and signs you out everywhere. It can't be undone. Messages you've posted in groups stay visible to other members under your display name. Consider exporting your data first.
            </div>
            <input type="password" autoComplete="current-password" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} placeholder="Enter your password to confirm" style={inputStyle} />
            {deleteError && <ErrorBanner message={deleteError} />}
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" disabled={deleting} onClick={() => { setShowDelete(false); setDeletePassword(""); setDeleteError(""); }} style={{ ...secondaryBtn, flex: 1 }}>Cancel</button>
              <button type="submit" disabled={deleting || !deletePassword} style={{ ...secondaryBtn, flex: 1, background: T.danger, color: "#fff", border: "none", opacity: deleting || !deletePassword ? 0.6 : 1 }}>
                {deleting ? <Loader2 size={15} style={{ animation: "spin 1s linear infinite" }} /> : "Delete forever"}
              </button>
            </div>
          </form>
        )}

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
  { key: "groupslist", label: "Groups", icon: Users }, { key: "insights", label: "Insights", icon: BarChart3 },
  { key: "reminders", label: "Reminders", icon: Bell }, { key: "profile", label: "Profile", icon: User },
];
const MOBILE_NAV = [
  { key: "home", icon: Home, label: "Home" }, { key: "archive", icon: FolderOpen, label: "Archive" },
  { key: "capture", icon: Plus, label: "" }, { key: "groupslist", icon: Users, label: "Groups" },
  { key: "profile", icon: User, label: "Profile" },
];

// Desktop-only: group list on the left, the open chat filling the rest.
function GroupsWorkspace({ groups, activeGroup, user, go, onCreate, onJoin }) {
  const current = activeGroup || groups[0] || null;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(300px, 360px) 1fr", gap: 20, height: "100vh", boxSizing: "border-box", padding: "12px 0 20px" }}>
      <div style={{ overflowY: "auto", minHeight: 0 }}>
        <GroupsListScreen groups={groups} go={go} onCreate={onCreate} onJoin={onJoin} activeId={current ? current.id : null} />
      </div>
      <div style={{ background: T.panel, border: `1px solid ${T.line}`, borderRadius: 18, display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden" }}>
        {current ? (
          <GroupScreen key={current.id} embedded user={user} group={current} />
        ) : (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, color: T.inkFaint, textAlign: "center", padding: 24 }}>
            <Users size={34} color={T.inkFaint} />
            <div style={{ fontSize: 14, fontWeight: 700, color: T.inkSoft }}>No group selected</div>
            <div style={{ fontSize: 13 }}>Create a group or join one with an invite code to start chatting.</div>
          </div>
        )}
      </div>
    </div>
  );
}

function MainShell({ user, onLogout, onUserUpdate, pendingJoinCode, onJoinHandled }) {
  const [screen, setScreen] = useState("home");
  const [activeFolder, setActiveFolder] = useState(null);
  const [activeGroupId, setActiveGroupId] = useState(null);
  const [folderList, setFolderList] = useState([]); // ordered the way the person arranged them
  const folders = useMemo(() => Object.fromEntries(folderList.map((f) => [f.name, f])), [folderList]);
  const [tasks, setTasks] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [events, setEvents] = useState([]);
  const [studySessions, setStudySessions] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const isDesktop = useIsDesktop();
  const [inviteNotice, setInviteNotice] = useState("");
  const joinTriedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.folders.list(), api.tasks.list(), api.reminders.list(),
      api.events.list(), api.studySessions.list(), api.groups.list(),
    ])
      .then(([f, t, r, ev, ss, gr]) => {
        if (cancelled) return;
        setFolderList(f);
        setTasks(t);
        setReminders(r);
        setEvents(ev);
        setStudySessions(ss);
        setGroups(gr);
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []);

  // Someone opened an invite link (?join=CODE): join once their data has loaded.
  useEffect(() => {
    if (loading || !pendingJoinCode || joinTriedRef.current) return;
    joinTriedRef.current = true;
    joinGroup(pendingJoinCode)
      .catch((err) => setInviteNotice(err.message || "Couldn't join that group — the invite may be invalid."))
      .finally(() => onJoinHandled && onJoinHandled());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, pendingJoinCode]);

  function go(target, param) {
    if (target === "folder") setActiveFolder(param);
    if (target === "group") setActiveGroupId(param);
    setScreen(target);
  }

  async function saveItem(folderId, folderName, payload) {
    const item = await api.folders.addItem(folderId, payload);
    setFolderList((prev) => prev.map((f) => (f.name === folderName ? { ...f, items: [item, ...f.items] } : f)));
    setActiveFolder(folderName);
    setScreen("folder");
  }

  async function deleteItem(itemId) {
  if (!window.confirm("Delete this item? This can't be undone.")) return;
  await api.items.delete(itemId);
  setFolderList((prev) => prev.map((f) => (f.name === activeFolder ? { ...f, items: f.items.filter((i) => i.id !== itemId) } : f)));
}

  async function createFolder(payload) {
    const created = await api.folders.create(payload);
    setFolderList((prev) => [...prev, created]);
    return created;
  }

  async function updateFolder(id, patch) {
    const old = folderList.find((f) => f.id === id);
    const updated = await folderApi.update(id, patch);
    setFolderList((prev) => prev.map((f) => (f.id === id ? updated : f)));
    if (old && activeFolder === old.name) setActiveFolder(updated.name); // keep the open folder open after a rename
    return updated;
  }

  async function deleteFolder(id) {
    await folderApi.remove(id);
    setFolderList((prev) => prev.filter((f) => f.id !== id));
  }

  async function moveFolder(id, direction) {
    const from = folderList.findIndex((f) => f.id === id);
    const to = from + direction;
    if (from < 0 || to < 0 || to >= folderList.length) return;
    const previous = folderList;
    const next = [...folderList];
    [next[from], next[to]] = [next[to], next[from]];
    setFolderList(next); // optimistic — the list reorders instantly
    try {
      await folderApi.reorder(next.map((f) => f.id));
    } catch (err) {
      setFolderList(previous);
      setInviteNotice(err.message || "Couldn't save the new folder order.");
    }
  }

  async function toggleTask(task) {
    const updated = await api.tasks.update(task.id, { done: !task.done });
    setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
  }

  async function addTask(text, priority = "Medium") {
    const created = await api.tasks.create({ text, priority, due_date: "" });
    setTasks((prev) => [created, ...prev]);
  }

  async function setTaskPriority(task, priority) {
    setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, priority } : t))); // optimistic
    try {
      const updated = await api.tasks.update(task.id, { priority });
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
    } catch (err) {
      setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, priority: task.priority } : t)));
      setInviteNotice(err.message || "Couldn't change that task's priority.");
    }
  }

  async function addReminder(title) {
    const created = await api.reminders.create({ title, detail: "", kind: "time" });
    setReminders((prev) => [created, ...prev]);
  }

  async function addEvent(payload) {
    const created = await api.events.create(payload);
    setEvents((prev) => [...prev, created]);
  }

  async function deleteEvent(id) {
    await api.events.delete(id);
    setEvents((prev) => prev.filter((e) => e.id !== id));
  }

  async function logStudySession(minutes) {
    const created = await api.studySessions.create({ minutes });
    setStudySessions((prev) => [created, ...prev]);
  }

  async function createGroup(name) {
    const created = await api.groups.create({ name });
    setGroups((prev) => [...prev, created]);
    return created; // GroupFlowModal shows the invite step, then opens the chat
  }

  async function joinGroup(inviteCode) {
    const joined = await api.groups.join({ invite_code: inviteCode });
    setGroups((prev) => (prev.some((g) => g.id === joined.id) ? prev : [...prev, joined]));
    setActiveGroupId(joined.id);
    setScreen("group");
  }

  const activeGroup = groups.find((g) => g.id === activeGroupId);

  function renderScreen() {
    if (loading) return <CenterSpinner label="Loading your archive…" />;
    if (error) return (
  <div style={{ padding: 20 }}>
    <ErrorBanner message={error} />
    <button onClick={() => window.location.reload()} style={{ ...secondaryBtn, marginTop: 12, width: "100%" }}>
      Reload
    </button>
  </div>
  );

    switch (screen) {
      case "home": return <HomeScreen folderList={folderList} tasks={tasks} go={go} user={user} />;
      case "archive": return <ArchiveScreen folderList={folderList} go={go} onCreate={createFolder} onUpdate={updateFolder} onDelete={deleteFolder} onMove={moveFolder} />;
      case "folder": return <FolderDetailScreen name={activeFolder} folder={folders[activeFolder]} go={go} back={() => setScreen("archive")} onDeleteItem={deleteItem} onUpdate={updateFolder} onDelete={deleteFolder} />;
      case "capture": return <CaptureScreen back={() => setScreen("home")} onSave={saveItem} folders={folders} />;
      case "calendar": return <CalendarScreen back={() => setScreen("home")} events={events} onAddEvent={addEvent} onDeleteEvent={deleteEvent} />;
      case "todo": return <TodoScreen tasks={tasks} back={() => setScreen("home")} onToggle={toggleTask} onAdd={addTask} onSetPriority={setTaskPriority} />;
      case "groupslist":
        return isDesktop
          ? <GroupsWorkspace groups={groups} activeGroup={activeGroup} user={user} go={go} onCreate={createGroup} onJoin={joinGroup} />
          : <GroupsListScreen groups={groups} go={go} onCreate={createGroup} onJoin={joinGroup} />;
      case "group":
        if (isDesktop) return <GroupsWorkspace groups={groups} activeGroup={activeGroup} user={user} go={go} onCreate={createGroup} onJoin={joinGroup} />;
        return activeGroup
          ? <GroupScreen back={() => setScreen("groupslist")} user={user} group={activeGroup} />
          : <CenterSpinner label="Loading group…" />;
      case "insights": return <InsightsScreen back={() => setScreen("home")} tasks={tasks} studySessions={studySessions} onLogSession={logStudySession} />;
      case "reminders": return <RemindersScreen back={() => setScreen("home")} reminders={reminders} onAdd={addReminder} />;
      case "profile": return <ProfileScreen back={() => setScreen("home")} user={user} onLogout={onLogout} onUserUpdate={onUserUpdate} />;
      default: return null;
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "640px", background: T.bg, fontFamily: "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif", ...STARFIELD_BG }}>
      <div className="orbit-sidebar" style={{ width: 220, background: T.sidebar, padding: "22px 14px", flexShrink: 0, display: "none" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "0 8px 26px" }}>
          <OrbitCatLogo size={34} />
          <span style={{ color: "#fff", fontWeight: 800, fontSize: 16, letterSpacing: -0.3 }}>ORBIT</span>
        </div>
        {NAV_ITEMS.map((n) => (
          <div key={n.key} onClick={() => go(n.key)} style={{ display: "flex", alignItems: "center", gap: 11, padding: "10px 12px", borderRadius: 11, cursor: "pointer", marginBottom: 3, background: screen === n.key ? T.sidebarSoft : "transparent", color: screen === n.key ? "#fff" : "#7FA08C" }}>
            <n.icon size={16} /><span style={{ fontSize: 13.5, fontWeight: 600 }}>{n.label}</span>
          </div>
        ))}
        <div onClick={() => go("capture")} style={{ ...primaryBtn, marginTop: 18, width: "100%", boxSizing: "border-box" }}><Camera size={15} /> New capture</div>
      </div>

      <div className="orbit-main" style={{ flex: 1, minWidth: 0, display: "flex", justifyContent: "center" }}>
        <div className="orbit-frame" style={{ width: "100%", maxWidth: 420, background: T.bg, position: "relative", minHeight: "640px" }}>
          {inviteNotice && (
            <div style={{ margin: "12px 20px 0" }}>
              <ErrorBanner message={inviteNotice} />
              <div onClick={() => setInviteNotice("")} style={{ fontSize: 12, fontWeight: 700, color: T.inkSoft, cursor: "pointer", marginTop: 4 }}>Dismiss</div>
            </div>
          )}
          <div key={screen} className={["archive", "folder", "home", "todo", "reminders", "calendar", "groupslist", "group", "capture"].includes(screen) ? "orbit-page" : "orbit-page orbit-narrow"} style={{ animation: "fadeIn 0.32s ease" }}>{renderScreen()}</div>
          <div className="orbit-bottomnav" style={{ position: "fixed", bottom: 0, left: 0, right: 0, maxWidth: 420, margin: "0 auto", background: T.panel, borderTop: `1px solid ${T.line}`, padding: "10px 22px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            {MOBILE_NAV.map((n) => n.key === "capture" ? (
              <div key={n.key} onClick={() => go(n.key)} style={{ width: 46, height: 46, borderRadius: 999, background: `linear-gradient(135deg, #6FDA9C, ${T.primary})`, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", marginTop: -18, boxShadow: `0 6px 18px ${T.primaryGlow}` }}>
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
        @media (min-width: 860px) {
          .orbit-sidebar { display: block !important; position: sticky; top: 0; align-self: flex-start; height: 100vh; overflow-y: auto; width: 240px !important; }
          .orbit-bottomnav { display: none !important; }
          .orbit-main { justify-content: flex-start !important; }
          .orbit-frame { max-width: none !important; }
          .orbit-page { max-width: 1280px; margin: 0 auto; padding: 0 12px; box-sizing: border-box; }
          .orbit-narrow { max-width: 760px; }
          /* lists become card grids instead of one long stretched column */
          .orbit-grid { display: grid !important; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px !important; align-items: start; }
          .orbit-cols { display: grid !important; grid-template-columns: 1fr 1fr; gap: 28px !important; align-items: start; }
          .orbit-split { display: grid !important; grid-template-columns: minmax(340px, 520px) 1fr; gap: 28px !important; align-items: start; }
        }
        @media (min-width: 1500px) {
          .orbit-page { max-width: 1440px; }
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
  // An invite link (?join=CODE) must survive sign-in / sign-up, so it's parked
  // in sessionStorage and removed from the address bar straight away.
  const [pendingJoin, setPendingJoin] = useState(() => {
    const valid = (c) => (c && /^[a-z0-9]{4,32}$/i.test(c) ? c.toLowerCase() : null);
    const params = new URLSearchParams(window.location.search);
    const fromUrl = valid(params.get("join"));
    if (params.has("join")) {
      params.delete("join");
      const qs = params.toString();
      window.history.replaceState({}, "", window.location.pathname + (qs ? `?${qs}` : ""));
    }
    try {
      if (fromUrl) sessionStorage.setItem("orbit_join", fromUrl);
      return fromUrl || valid(sessionStorage.getItem("orbit_join"));
    } catch {
      return fromUrl;
    }
  });

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

  function clearPendingJoin() {
    try { sessionStorage.removeItem("orbit_join"); } catch { /* storage unavailable */ }
    setPendingJoin(null);
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
  if (!user) return (
    <>
      {pendingJoin && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 50, background: T.primarySoft, borderBottom: `1px solid ${T.line}`, color: T.ink, fontSize: 13, fontWeight: 600, textAlign: "center", padding: "10px 16px" }}>
          You've been invited to a group — sign in or create an account to join.
        </div>
      )}
      <AuthScreen onAuthed={setUser} />
    </>
  );
  // Only gate on verification if there's actually an email pending
  // verification — accounts with no email at all skip this entirely.
  if (user.email && !user.is_verified) return <VerifyPendingScreen user={user} onVerified={setUser} onLogout={handleLogout} />;
  return <MainShell user={user} onLogout={handleLogout} onUserUpdate={setUser} pendingJoinCode={pendingJoin} onJoinHandled={clearPendingJoin} />;
}
