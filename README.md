# WebChat

A real-time chat project based on `Vue 3 + Vite + Flask + WebSocket + SQLite`.

It supports registration/login, friend requests, real-time messaging, chat history sync, profile editing, avatar upload, friend remarks, and a modern light/dark UI.

## Features

- User registration and login
- Phone region support framework, currently includes `+86`
- Verification-code registration flow scaffold
- WebSocket real-time message sync
- Multi-end chat history sync after refresh or re-login
- Conversation unread indicators
- Friend request workflow with accept/reject records
- Friend search by account
- Friend profile panel inside chat
- Friend remark editing
- Friend removal
- Avatar upload, drag-and-drop, crop, and compression
- Personal profile editing
- Light/dark theme switch

## Tech Stack

### Frontend

- Vue 3
- Vite
- Axios
- Font Awesome

### Backend

- Python
- Flask
- Flask-CORS
- Flask-Sock
- SQLite

## Project Structure

```text
.
├─ backend
│  ├─ app.py
│  ├─ db.py
│  ├─ requirements.txt
│  └─ data
│     ├─ chat.sqlite3
│     └─ store.json
├─ public
│  ├─ images
│  └─ uploads
│     └─ avatars
├─ src
│  ├─ components
│  ├─ utils
│  └─ views
├─ package.json
└─ README.md
```

## Install

### Frontend dependencies

```bash
npm install
```

### Backend dependencies

```bash
pip install -r backend/requirements.txt
```

## Run

### Start backend

```bash
npm run server
```

Default backend address:

```text
http://127.0.0.1:8083
```

### Start frontend

```bash
npm run dev
```

Default frontend address:

```text
http://127.0.0.1:5173
```

## Build

```bash
npm run build
```

## Production security

- Set a unique `TOKEN_SECRET`; production startup fails when it is missing.
- Authentication is limited to 8 attempts per IP/account in 15 minutes. The Nginx template adds an independent login limit.
- Authentication tokens use `sessionStorage`, so closing the browser session clears them.
- Keep the backend bound to `127.0.0.1`; expose only Nginx ports 80/443.
- Copy `.env.example` to a server-only `.env` and replace every placeholder. Never commit `.env`.
- The bundled demo users are disabled by default. To initialize an empty deployment, set `ENABLE_DEMO_SEED=true` and a unique `DEMO_SEED_PASSWORD`; the importer replaces all bundled password hashes.
- Use `deploy/nginx.conf` as the site template. The current IP-only deployment remains HTTP; add a domain and a trusted certificate before enabling HTTPS and HSTS.
- After enabling TLS, redirect port 80 to HTTPS and add `Strict-Transport-Security: max-age=31536000; includeSubDomains` only on the HTTPS server.

## Demo Accounts

Demo account identifiers are present only for local fixtures. Passwords are supplied by `DEMO_SEED_PASSWORD` at seed time and are never stored in this repository.

## Main APIs

### Auth

- `POST /api/auth/send-code`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

### Profile

- `PUT /api/profile`
- `POST /api/profile/avatar`

### Friends

- `GET /api/users/discover?q=keyword`
- `GET /api/friend-requests`
- `POST /api/friends`
- `GET /api/friends/:friendId`
- `PUT /api/friends/:friendId/remark`
- `DELETE /api/friends/:friendId`
- `POST /api/friend-requests/:id/accept`
- `POST /api/friend-requests/:id/reject`

### Conversations

- `GET /api/conversations`
- `GET /api/conversations/:id/messages`
- `POST /api/conversations/:id/messages`

### WebSocket

- `GET /ws?token=...`

Important events:

- `connected`
- `message.created`
- `conversation.created`
- `conversation.updated`
- `profile.updated`
- `friend.request.created`
- `friend.request.updated`
- `friend.profile.updated`
- `friend.removed`

## Data Notes

- Runtime database: `backend/data/chat.sqlite3`
- Seed data: `backend/data/store.json`
- Uploaded avatars: `public/uploads/avatars`

When the database is empty on first launch, the app imports seed users, friendships, and conversations from `store.json`.

## Notes

- Current backend uses Flask development server and is intended for local development.
- Production deployment should use a proper WSGI server.
- Frontend default API base URL is `http://127.0.0.1:8083/api`
- You can override it with `VITE_API_BASE_URL`
- Avoid starting multiple backend processes on port `8083` at the same time
