# Orbit Desktop

A desktop window around the live Orbit web app (https://my-orbit.indevs.in).
Because it loads the real site, every website update reaches the desktop app automatically — there is nothing to re-release for normal changes.

## Get installers (easiest — no setup on your computer)
1. Put this `orbit-desktop/` folder and `.github/workflows/desktop.yml` in the root of your GitHub repo (next to `orbit-backend/` and `orbit-frontend/`) and push.
2. On GitHub: **Actions → Desktop app → Run workflow**. After ~5–10 minutes, download the installers from the run's **Artifacts**
   (`.exe` for Windows, `.dmg` for macOS, `.AppImage` for Linux).
3. To publish a download page, push a tag: `git tag desktop-v1.0.0 && git push --tags` — installers are attached to a GitHub Release.

## Build on your own computer
Needs Node.js 20+.
```
cd orbit-desktop
npm install
npm start          # try it in a window
npm run dist       # builds an installer for the OS you're on, into dist/
```
(Windows installers must be built on Windows, macOS ones on a Mac — that's why the GitHub workflow builds all three.)

## Good to know
- **Unsigned installers:** Windows shows a "Windows protected your PC" SmartScreen warning (More info → Run anyway); macOS says the app is from an unidentified developer (right-click → Open). Removing these warnings needs a code-signing certificate (Windows) / Apple Developer account ($99/yr) — worth it only once you have real users.
- **Google Calendar connect:** Google doesn't allow sign-in inside embedded windows, so "Connect Google Calendar" opens your normal browser. Finish there, come back to the desktop app and press Ctrl+R (Cmd+R on Mac) to refresh.
- **Needs internet:** like the website, it talks to the Orbit server. If it can't connect, a retry screen appears and reconnects automatically.
- **Pointing at another address** (testing): `ORBIT_URL=http://localhost:5173 npm start`.
- **Security:** the window has no Node access, only talks to Orbit's own origin, sends every other link to your browser, and grants camera/notification access to Orbit only.
