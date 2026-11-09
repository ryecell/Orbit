// Orbit desktop shell: a secure window around the live Orbit web app.
// The app itself (frontend + API) is unchanged — updating the website updates the desktop app too.
const { app, BrowserWindow, Menu, session, shell } = require("electron");
const fs = require("fs");
const path = require("path");

const APP_URL = process.env.ORBIT_URL || "https://my-orbit.indevs.in";
const APP_ORIGIN = new URL(APP_URL).origin;
const STATE_FILE = path.join(app.getPath("userData"), "window-state.json");

let win = null;

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, "utf8")); } catch { return {}; }
}
function saveState() {
  if (!win || win.isDestroyed()) return;
  try {
    const maximized = win.isMaximized();
    const bounds = maximized ? (loadState().bounds || win.getNormalBounds()) : win.getBounds();
    fs.writeFileSync(STATE_FILE, JSON.stringify({ bounds, maximized }));
  } catch { /* not worth crashing over */ }
}

function isAppUrl(url) {
  try { return new URL(url).origin === APP_ORIGIN; } catch { return false; }
}
function openExternally(url) {
  // Only hand real web links to the OS — never file:, javascript:, custom protocols, etc.
  try {
    const u = new URL(url);
    if (u.protocol === "https:" || u.protocol === "http:" || u.protocol === "mailto:") shell.openExternal(url);
  } catch { /* ignore malformed */ }
}

function createWindow() {
  const state = loadState();
  win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 380,
    minHeight: 560,
    ...(state.bounds || {}),
    show: false,
    backgroundColor: "#0C2A1F",
    title: "Orbit",
    icon: path.join(__dirname, "build", "icon.png"),
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
    },
  });
  if (state.maximized) win.maximize();
  win.once("ready-to-show", () => win.show());
  win.on("close", saveState);

  // Keep the window on Orbit. Anything else (Google sign-in, help links…) opens in the real browser —
  // Google refuses sign-in inside embedded windows anyway.
  win.webContents.on("will-navigate", (event, url) => {
    if (isAppUrl(url) || url.startsWith("file://")) return;
    event.preventDefault();
    openExternally(url);
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    openExternally(url);
    return { action: "deny" };
  });

  // No connection / server asleep: show a friendly page that retries on its own.
  win.webContents.on("did-fail-load", (_e, code, _desc, url, isMainFrame) => {
    if (!isMainFrame || code === -3 /* aborted */ || url.startsWith("file://")) return;
    win.loadFile(path.join(__dirname, "offline.html"), { query: { u: APP_URL } });
  });

  win.loadURL(APP_URL);
}

function setupPermissions() {
  // Camera/microphone (photo capture) and notifications are fine — but only for Orbit itself.
  const allowed = new Set(["media", "notifications", "clipboard-sanitized-write"]);
  session.defaultSession.setPermissionRequestHandler((wc, permission, callback, details) => {
    callback(allowed.has(permission) && isAppUrl(details.requestingUrl || wc.getURL()));
  });
  session.defaultSession.setPermissionCheckHandler((wc, permission, origin) => allowed.has(permission) && isAppUrl(origin));
}

function setupMenu() {
  const isMac = process.platform === "darwin";
  const template = [
    ...(isMac ? [{ role: "appMenu" }] : []),
    { role: "editMenu" },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
        ...(app.isPackaged ? [] : [{ type: "separator" }, { role: "toggleDevTools" }]),
      ],
    },
    { role: "windowMenu" },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
  });
  app.whenReady().then(() => {
    setupPermissions();
    setupMenu();
    createWindow();
    app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
  });
  app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
}
