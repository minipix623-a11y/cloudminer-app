# CloudMiner Mini App — Specification

## Overview
Telegram Mini App (WebApp) + Telegram Bot. Demo version with game economy (virtual currency, no real withdrawals).

## Tech Stack
- **Frontend:** Vanilla HTML/CSS/JS (Telegram WebApp SDK)
- **Backend:** Python + Flask + SQLite
- **Bot:** python-telegram-bot

## Project Structure
```
mining_app/
├── SPEC.md
├── README.md
├── backend/
│   ├── app.py           # Flask API
│   ├── bot.py           # Telegram bot
│   ├── models.py        # Database models
│   └── data/            # SQLite DB
├── frontend/
│   └── index.html       # Mini App (WebApp)
└── .env
```

## Features (Demo)

### 1. Miners Shop (10 miners)
| ID | Name | Price ($) | Income/hr | Payback |
|----|------|-----------|-----------|---------|
| 1 | Pico Miner | 5 | 0.015 | ~14 days |
| 2 | Nano Miner | 15 | 0.045 | ~14 days |
| 3 | Micro Rig | 50 | 0.15 | ~14 days |
| 4 | Mini Farm | 100 | 0.30 | ~14 days |
| 5 | Office Rig | 250 | 0.75 | ~14 days |
| 6 | Garage Farm | 500 | 1.50 | ~14 days |
| 7 | Industrial | 750 | 2.25 | ~14 days |
| 8 | Mega Cluster | 1000 | 3.00 | ~14 days |
| 9 | Quantum Core | 2000 | 6.00 | ~14 days |
| 10 | Hyper Reactor | 5000 | 15.00 | ~14 days |

### 2. Miner Upgrades
- Each miner can be upgraded (⬆️)
- Cost: 50% of original price per level
- Bonus: +10% income per level
- Max level: unlimited (cost scales linearly)

### 3. Daily Tasks
| Task | Reward | Target |
|------|--------|--------|
| Ежедневный вход | 5$ | 1 |
| Купи майнер | 15$ | 1 |
| Заработай 10$ | 20$ | 10$ total |
| Пригласи друга | 50$ | 1 referral |
| Крути колесо | 10$ | 1 spin |

### 4. Wheel of Fortune
- 1 spin per 24 hours
- Prizes:
  - x1.5 income (60 min)
  - x2 income (30 min)
  - x3 income (10 min)
  - +5$, +15$, +50$
  - Miss (5% chance)
- Active booster shown in UI

### 5. User Profile
- Telegram avatar (from initData)
- Total earnings (virtual)
- Income per hour
- Rating position
- Avatar unlocked based on total spend

### 3. Rating System
- Top 100 users
- Show: rank, name, income/hr
- Weekly rewards (demo: virtual badges)

### 4. Referral System
- Unique referral link per user
- 3% of referral earnings
- Referral stats: count, total earnings

### 5. Side Menu
- Support (Telegram link)
- Referral link
- Profile
- FAQ

## API Endpoints

### User
- `GET /api/user/:id` — get user profile
- `POST /api/user` — create/update user

### Miners
- `GET /api/miners` — list all miners
- `POST /api/buy` — buy miner (demo: instant credit)

### Balance
- `GET /api/balance/:id` — get user balance
- `POST /api/income` — calc income (called by frontend timer)

### Rating
- `GET /api/rating` — top 100 users

### Referrals
- `GET /api/referrals/:id` — referral stats
- `POST /api/referral/credit` — credit referral earnings

## Security Notes
- initData validation for Telegram user
- Demo mode: no real payments
- Virtual currency only
- Rate limiting on API

## Game Economy (Virtual)
- Currency: "Credits" (not real money)
- Income calculated per hour, credited every minute
- No withdrawal in demo mode
- Clear disclaimer that this is a game/simulation