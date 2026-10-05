# HanJiang Open Portal

HanJiang Open Portal is the developer-portal frontend of the [HanJiang full-stack rapid development platform](https://github.com/cross-lang/x-HanJiang). Built with Vue 3 + TypeScript + Vite + Element Plus and paired with the FastAPI backend, it provides external developers with a one-stop open platform entry for app onboarding, capability documentation and authentication guides.

[中文](README.md) | English

## ✨ Features

- **Developer Account**: register / login (stateful session: JWT + Redis login state; old tokens invalidated on logout / password change / refresh), profile maintenance, personal / enterprise certification application
- **App Management**: create app (AppId generated + AppKey returned once), edit / delete (soft), scope request & adjustment, AppKey rotation, approval status & notes tracking (apps not yet approved cannot call open APIs)
- **Open Capability Docs**: a built-in catalog of 18 open endpoints (Health / App Info / User / Role / File), each documenting request headers, Query / Body parameters, response fields & examples, and cURL examples (HanJiang-1 HMAC signature mode)
- **Auth & Authorization Docs**: HanJiang-1 signature guide (algorithm / anti-replay time window), common request parameters, gateway auth error codes
- **Station Messages**: top-bar bell unread badge (15s polling), message list, mark one read / mark all read
- **Profile Center**: developer profile, certification status, change password
- **Code Highlighting**: API doc code blocks rendered with highlight.js

## 🛠️ Tech Stack

| Category         | Technology                                     |
| ---------------- | ---------------------------------------------- |
| **Framework**    | Vue 3.5 (Composition API)                      |
| **Language**     | TypeScript 5.7                                 |
| **Build Tool**   | Vite 6                                         |
| **UI Library**   | Element Plus 2.9 + @element-plus/icons-vue     |
| **State**        | Pinia (developer session state)                |
| **Router**       | Vue Router 4 (with auth guard)                 |
| **HTTP Client**  | Axios 1.7 (unified wrapper)                    |
| **Highlight**    | highlight.js 11                                |

## 🚀 Quick Start

### ⚙️ Environment Requirements

| Tool    | Version |
| ------- | ------- |
| Node.js | >= 18   |
| npm     | >= 9    |

### 📦 Install Dependencies

```bash
npm install
```

### 💻 Dev Server

```bash
npm run dev
```

Open http://localhost:5174. Vite proxies `/api/`, `/docs`, `/redoc` and `/openapi.json` requests to the backend at `http://127.0.0.1:8000`, so no CORS handling is needed during development.

> Note: the portal dev port is **5174** (distinct from the admin console's 5173); Vite proxies only the `/api/` prefix so frontend routes starting with `/api` (e.g. `/api-docs`) are not swallowed.

### 🏭 Production Build

```bash
npm run build
```

The build runs `vue-tsc` type checking + Vite bundling, outputting to `dist/`. Deploy to a static server such as Nginx (reverse-proxy `/api` to the backend).

### 🖥️ Local Preview

```bash
npm run preview
```

## 📁 Project Structure

```
open_portal/
├── src/
│   ├── api/                # API wrappers
│   │   ├── request.ts      # Axios instance (interceptors, unified errors, baseURL /api/open-portal/v1)
│   │   ├── auth.ts         # Register / login / refresh / logout / change password
│   │   ├── developer.ts    # Developer profile & certification
│   │   ├── apps.ts         # App CRUD / scope requests / key rotation
│   │   ├── scopes.ts       # Scope catalog
│   │   └── messages.ts     # Station messages (unread / list / read)
│   ├── components/         # Shared components
│   │   ├── GroupCheckboxPanel.vue # Grouped scope checkbox panel
│   │   ├── NotificationBell.vue   # Top-bar bell (unread badge)
│   │   └── SecretResultDialog.vue # One-time AppKey display dialog
│   ├── composables/
│   │   └── useScopeCatalog.ts     # Scope catalog data
│   ├── data/
│   │   └── capability.ts   # Open capability endpoint catalog (18 endpoints, one-to-one with /api/open/v1)
│   ├── router/
│   │   └── index.ts        # Routes + auth guard
│   ├── stores/
│   │   └── developer.ts    # Developer session state (Pinia)
│   ├── types/              # TypeScript type definitions
│   ├── views/              # Page components
│   │   ├── home/           # Home (capability module overview)
│   │   ├── apps/           # App management (CRUD / scope requests / approval status)
│   │   ├── capability/     # Endpoint docs (three-level menu: module → endpoint)
│   │   ├── auth/           # Auth & authorization docs (signature / common params / error codes)
│   │   ├── login/ register/ # Login & register
│   │   └── profile/        # Profile center
│   ├── App.vue             # Root component
│   └── main.ts             # Entry
├── index.html
├── vite.config.ts          # Vite config (alias @, port 5174, backend proxy)
├── package.json
├── tsconfig.json           # TypeScript config
└── tsconfig.node.json
```

## 🧭 Pages & Routes

| Route                         | Page              | Description                                                            |
| ----------------------------- | ----------------- | ---------------------------------------------------------------------- |
| `/login`                      | Login             | Developer login                                                        |
| `/register`                   | Register          | Register developer account                                              |
| `/home`                       | Home              | Capability module overview + my apps summary                           |
| `/apps`                       | App Management    | App CRUD + scope requests + AppKey rotation + approval status          |
| `/capability/:module/:apiId`  | Capability        | Endpoint docs (headers / params / response / cURL examples)            |
| `/auth/signature`             | Signature Guide   | HanJiang-1 signature algorithm & anti-replay explanation               |
| `/auth/params`                | Common Params     | Common request headers & response envelope                              |
| `/auth/errors`                | Gateway Errors    | Open API auth error codes                                               |
| `/profile`                    | Profile           | Profile maintenance / certification / change password                  |

## 🔗 API Conventions

The portal frontend consumes two API groups with strictly separated prefixes and auth:

| Type          | Prefix                  | Auth                                              |
| ------------- | ----------------------- | ------------------------------------------------- |
| Portal APIs   | `/api/open-portal/v1`   | Developer session JWT (`Authorization: Bearer <access_token>` in localStorage) |
| Open APIs     | `/api/open/v1`          | `X-App-Id` / `X-App-Key` + HanJiang-1 HMAC signature |

- Unified response envelope: `{ code, message, data, timestamp, request_id }`
- Pagination: `data: { items, total, page, page_size, total_pages }`
- New apps enter the admin approval workflow (`approval_status = pending`); only approved apps may call open APIs
- App/scope applications and approval results are delivered via developer station messages (`developer_messages` table)

> See [API_DEPENDENCIES.md](./API_DEPENDENCIES.md) for the full backend endpoint dependency list.

## 🤝 Integration Notes

- Start the backend first (see [server/README.md](../../server/README.md)), default port `8000`
- The portal uses a separate developer account system, isolated from the admin user system (developer tables + developer session login state)
- After a production build, `dist/` is pure static output; reverse-proxy `/api` (and other prefixes) to the backend on your web server (e.g. Nginx)
