# Zählwerk WebApp (React + Mantine)

Migration des Frontends von Vue 3 / Material Design 3 auf **React + TypeScript +
Mantine UI** (Desktop-first, voll responsive). Ersetzt das frühere
`backend/frontend` (statisches Vue) in-place; der Docker-Build erzeugt aus
diesem Verzeichnis die ausgelieferten statischen Dateien.

## Stack

- **React 18** + **TypeScript** (strict), Build via **Vite**
- **@mantine/core / form / hooks / notifications** – UI, Formular-State, Feedback
- **ECharts** (`echarts-for-react`) – Diagramme
- **react-router-dom** – Routing, **@tabler/icons-react** – Icons

## Struktur

```
src/
├── main.tsx                 # MantineProvider + Router + AuthProvider
├── App.tsx                  # Auth-Gate (Login/Onboarding) + Routen
├── theme.ts                 # kompakte Desktop-Defaults (dichte Tabellen, size sm)
├── api/{client,useApi,types}.ts   # fetch-Wrapper (1:1-Port), Lade-Hook, Typen
├── auth/AuthContext.tsx     # Sitzungsstatus, Login/Logout, Rechte
├── layout/AppLayout.tsx     # AppShell (Header + Navbar/Burger + Main)
├── components/{EChart,Placeholder}.tsx
├── util/format.ts           # de-DE-Zahlen/Kosten/Datum/Bytes
└── features/                # Dashboard, Systeme (Zählerstände), Auth, Stubs …
```

## Entwicklung

```bash
npm install
npm run dev        # Vite-Dev-Server, /api wird an http://127.0.0.1:8000 geproxyt
npm run build      # Typecheck (tsc --noEmit) + Produktions-Build -> dist/
```

Im Container übernimmt die erste Docker-Stufe `npm ci && npm run build` und legt
`dist/` als `/app/frontend` ab (von FastAPI unter `/` ausgeliefert).

## Migrationsstand

Fertig: Build-Foundation, AppShell (Desktop/Mobile), Theme (Light/Dark),
Auth-Fluss (Setup/Login/2FA/Onboarding), Dashboard (Kennzahlen + ECharts),
Zählerstände-Tabelle. **Ausstehend (schrittweise Parität):** Tarife, Auswertungen/
Berichte, Audit-Log, Einstellungen, Admin-Bereiche (Monitoring/DB/Diagnose/SQL/
Logs), Zählerstands-Erfassung inkl. OCR, MQTT-Geräteverwaltung, Command-Palette.
