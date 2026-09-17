const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const TOKEN_KEY = "orbit_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    // no JSON body
  }

  if (!res.ok) {
    throw new Error((data && data.detail) || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  base: API_BASE,

  register: (payload) => request("/auth/register", { method: "POST", body: payload, auth: false }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload, auth: false }),
  logout: () => request("/auth/logout", { method: "POST" }),
  resendVerification: () => request("/auth/resend-verification", { method: "POST" }),
  forgotPassword: (payload) => request("/auth/forgot-password", { method: "POST", body: payload, auth: false }),
  resetPassword: (payload) => request("/auth/reset-password", { method: "POST", body: payload, auth: false }),
  linkEmail: (payload) => request("/me/email", { method: "PATCH", body: payload }),
  me: () => request("/me"),

  folders: {
    list: () => request("/folders"),
    create: (payload) => request("/folders", { method: "POST", body: payload }),
    addItem: (folderId, payload) => request(`/folders/${folderId}/items`, { method: "POST", body: payload }),
  },

  items: {
    delete: (id) => request(`/items/${id}`, { method: "DELETE" }),
  },

  tasks: {
    list: () => request("/tasks"),
    create: (payload) => request("/tasks", { method: "POST", body: payload }),
    update: (id, payload) => request(`/tasks/${id}`, { method: "PATCH", body: payload }),
    delete: (id) => request(`/tasks/${id}`, { method: "DELETE" }),
  },

  reminders: {
    list: () => request("/reminders"),
    create: (payload) => request("/reminders", { method: "POST", body: payload }),
  },

  groups: {
    messages: (groupId) => request(`/groups/${groupId}/messages`),
    postMessage: (groupId, payload) => request(`/groups/${groupId}/messages`, { method: "POST", body: payload }),
  },

  ai: {
    analyze: (payload) => request("/ai/analyze", { method: "POST", body: payload }),
  },

  // Token travels as a query param because browsers can't set custom headers
  // on a WebSocket handshake — the server validates it before accepting the connection.
  wsURL: (groupId) => `${API_BASE.replace(/^http/, "ws")}/ws/groups/${groupId}?token=${encodeURIComponent(getToken() || "")}`,

  setToken: (t) => localStorage.setItem(TOKEN_KEY, t),
  clearToken: () => localStorage.removeItem(TOKEN_KEY),
  getToken,
};
