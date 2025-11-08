# SeatApp MVP (On‑Prem, Local Auth)

Generisano: 2025-10-29T21:43:00.376548

## Šta je uključeno
- **Local auth** (username/password) — /api/login, /api/logout, /api/me (cookie session)
- **DB konekcija** (PostgreSQL, SQLAlchemy Core)
- Minimalni ekrani: **Login**, **Mapa** (lista sedišta), **Izveštaji** (weekly/monthly/yearly JSON)
- 3 reporting API endpointa: /api/reports/weekly, /api/reports/monthly, /api/reports/yearly

## Brzi start (dev)
1. `cp .env.example .env` i prilagodi vrednosti.
2. `docker compose up -d --build`
3. Otvori `http://localhost` (web), `http://localhost/api/health` (API health preko nginx-a).

## Default korisnik
- **admin / Admin#12345** — PROMENITI ODMAH (u bazi: `app_user.password_hash`).

## Napomena
- Sessions su in‑memory (u jednoj API instanci) — za HA koristi Redis/DB sessije.
- Ovaj skeleton je za razvoj; za produkciju dodati TLS, hardening, backup politike, i RBAC na rute.
