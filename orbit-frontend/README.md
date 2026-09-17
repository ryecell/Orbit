# Orbit Frontend

Vite + React app that talks to the Orbit FastAPI backend for auth, archive
folders/items, tasks, reminders, and live group chat.

## Setup

```bash
npm install
cp .env.example .env      # then edit VITE_API_BASE if your backend isn't on localhost:8000
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). The backend must
already be running (see the `orbit-backend` README) or you'll see connection
errors on the sign-in screen.

## Build for production

```bash
npm run build      # outputs static files to dist/
npm run preview    # serve the production build locally to sanity-check it
```

Deploy the `dist/` folder to any static host (Netlify, Vercel, S3+CloudFront,
etc.), and set `VITE_API_BASE` at build time to your deployed backend's URL.

## Notes

- Calendar and Insights still use sample data — the backend has no
  calendar/analytics models yet.
- Group chat is a single shared room (`study-group-1`) for now.
