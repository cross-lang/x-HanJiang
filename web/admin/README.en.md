# HanJiang Admin Console

HanJiang Admin is the frontend project of the [HanJiang (HanJiang) full-stack rapid development platform](https://github.com/cross-lang/x-HanJiang). Built with Vue 3 + TypeScript + Vite + Element Plus and paired with the FastAPI backend, it provides an out-of-the-box admin interface for enterprise management systems.

[中文](README.md) | English

## ✨ Features

- **Login & Security**: username / password login, automatic JWT attachment, auto-redirect to login on 401
- **Dashboard**: stat cards + ECharts charts + recent records + my recent activity
- **User Management**: user list (paged / keyword / status filter), multi-role assignment, edit / disable / reset password, CSV import & export
- **Role Management**: role CRUD, grouped permission checkboxes, bind / unbind permissions
- **Permission Management**: permission list (auto-scanned & registered by the backend) and permission metadata
- **Audit & Logs**: business audit logs, login logs (with details and export)
- **File Management**: upload, list, download, delete
- **Notification Center**: notification record list / stats, station-message unread count & read, notification preferences & recipients
- **System Notice Management**: publish / withdraw system notices (normal / maintenance, broadcast to all active users), published-record list, channel-config view / update (hot reload), channel test, system monitoring status
- **Open Platform**: app CRUD (split views: mine / pending my approval), application approval workflow (approve / reject with notes), scope authorization, AppKey rotation, scope list, developer management (list / owned apps)
- **Announcement Management**: create / edit / delete / publish / unpublish announcements, homepage board & banner placements, validity period and ordering, Markdown / rich-text content (sanitized before rendering to prevent XSS)
- **Profile Center**: profile maintenance, password change (verification-code two-factor auth), phone / email change
- **Global Search**: cross-user / role / permission / app / file keyword search (top-bar search box)
- **AI Assistant**: top-bar entry + right-side drawer, SSE streaming chat (token / navigate / done events rendered in real time), conversation management & history restore, 👍👎 feedback
- **API Docs**: embedded Swagger UI for in-browser API debugging

## 🛠️ Tech Stack

| Category         | Technology                                          |
| ---------------- | --------------------------------------------------- |
| **Framework**    | Vue 3.5 (Composition API)                           |
| **Language**     | TypeScript 5.7                                      |
| **Build Tool**   | Vite 6                                              |
| **UI Library**   | Element Plus 2.9 + @element-plus/icons-vue          |
| **State**        | Pinia                                               |
| **Router**       | Vue Router 4 (with auth guard)                      |
| **HTTP Client**  | Axios 1.7 (unified wrapper)                         |
| **Charts**       | ECharts 6 + vue-echarts                             |
| **Rendering**    | marked (Markdown) + DOMPurify (XSS sanitization)    |

## 🚀 Quick Start

### ⚙️ Environment Requirements

| Tool   | Version |
| ------ | ------- |
| Node.js | >= 18  |
| npm    | >= 9    |

### 📦 Install Dependencies

```bash
npm install
```

### 💻 Dev Server

```bash
npm run dev
```

Open http://localhost:5173. Vite proxies `/api`, `/docs`, `/redoc` and `/openapi.json` requests to the backend at `http://127.0.0.1:8000`, so no CORS handling is needed during development.

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
admin/
├── src/
│   ├── api/                # API wrappers (split by business module, see src/api/*.ts)
│   │   ├── request.ts      # Axios instance (interceptors, unified error handling)
│   │   ├── auth.ts         # Auth endpoints (login / current user / menus / logout)
│   │   ├── user.ts / role.ts / permission.ts # System management endpoints
│   │   ├── openapi.ts      # Open platform apps / approval / developers
│   │   ├── assistant.ts    # AI assistant endpoints (conversations / feedback / SSE chat)
│   │   └── ...             # announcement / notification / audit / file / dashboard / search / profile
│   ├── assets/             # Static assets
│   ├── components/         # Shared components
│   │   ├── Search.vue           # Top-bar global search
│   │   └── NotificationBell.vue # Top-bar notification bell (unread count)
│   ├── composables/        # Composable logic (useChatSse / useConversations / useScopeCatalog ...)
│   ├── router/
│   │   └── index.ts        # Routes + auth guard
│   ├── stores/
│   │   └── user.ts         # User state (Pinia)
│   ├── types/              # TypeScript type definitions
│   ├── utils/
│   │   ├── format.ts       # Formatting utilities (dates etc.)
│   │   └── announcement.ts # Announcement body rendering (marked + DOMPurify)
│   ├── views/              # Page components
│   ├── App.vue             # Root component
│   └── main.ts             # Entry (Element Plus zh-CN locale, global icon registration)
├── index.html
├── vite.config.ts          # Vite config (alias @, port 5173, backend proxy)
├── package.json
├── tsconfig.json           # TypeScript config
└── tsconfig.node.json
```

## 🧭 Pages & Routes

| Route                 | Page             | Description                                                                          |
| --------------------- | ---------------- | ------------------------------------------------------------------------------------ |
| `/login`              | Login            | Username / password login                                                            |
| `/`                   | Layout           | Sidebar + top bar (global search, notification bell, AI assistant entry)             |
| `/dashboard`          | Home             | Welcome message + quick entries                                                      |
| `/panel`              | Dashboard        | Stat cards + ECharts charts + recent records                                         |
| `/users`              | User Management  | User list + multi-role + edit / disable / reset password + import / export           |
| `/roles`              | Role Management  | Role list + grouped permission checkboxes + edit / delete / enable-disable           |
| `/permissions`        | Permission Mgmt  | Permission list (backend auto-registered) + metadata                                 |
| `/apis/swagger`       | Swagger Docs     | Embedded Swagger UI for online API debugging                                         |
| `/audit`              | Audit Logs       | Business operation logs (with export)                                                |
| `/audit/login`        | Login Logs       | Login logs (with export)                                                             |
| `/apps`               | Open Apps        | App CRUD + approval flow (mine / pending my approval) + scope grant + key rotation   |
| `/app-scopes`         | App Scopes       | Open platform scope list                                                             |
| `/open-developers`    | Developers       | Developer list (incl. certification status) + owned apps (`openapi_dev:view`)        |
| `/system-notification`| System Notices   | Publish / withdraw system notices (normal / maintenance) + channel config / test / monitor |
| `/announcements`      | Announcements    | Create / edit / delete / publish / unpublish, status / placement / keyword filter, validity display |
| `/profile`            | Profile          | Personal info + change password / phone / email (2FA code) + notification preferences / recipients |
| `/files`              | File Management  | Upload / list / download / delete                                                    |

## 🔗 Request Conventions

- `src/api/request.ts` creates the Axios instance with `baseURL` `/api/v1`
- **Request interceptor**: reads `access_token` from `localStorage` and injects `Authorization: Bearer <token>`
- **Response interceptor**: returns `response.data` directly; on 401 clears the token and redirects to login; other errors show a unified `ElMessage` toast
- Business pages call endpoints through `request` with paths matching the backend `/api/v1` prefix (e.g. `/users`, `/profile/me`)

## 🔀 Backend Proxy

`vite.config.ts` configures these dev proxies:

| Prefix         | Target                  |
| -------------- | ----------------------- |
| `/api`         | http://127.0.0.1:8000   |
| `/docs`        | http://127.0.0.1:8000   |
| `/redoc`       | http://127.0.0.1:8000   |
| `/openapi.json`| http://127.0.0.1:8000   |

## 🤝 Integration Notes

- Start the backend first (see [server/README.md](../../server/README.md)), default port `8000`
- Default super admin: `superadmin` / `admin@123456` — change it in production
- After a production build, `dist/` is pure static output; reverse-proxy `/api` (and other prefixes) to the backend on your web server (e.g. Nginx)
