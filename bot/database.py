"""
Слой доступа к SQLite. Один класс Database инкапсулирует все запросы,
чтобы хендлеры не знали про SQL напрямую.
"""
import time
import aiosqlite
from bot.config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id             INTEGER PRIMARY KEY,
    username            TEXT,
    balance             INTEGER NOT NULL DEFAULT 0,
    tickets_count       INTEGER NOT NULL DEFAULT 0,          -- билеты розыгрыша/бонусов
    subscription_status TEXT NOT NULL DEFAULT 'none',        -- none | trial | active | expired
    subscription_plan   TEXT,                                -- forever | 2y | 1y | 6m | 3m | 1m
    subscription_expires_at INTEGER,                         -- unix timestamp, NULL = навсегда
    free_trial_used     INTEGER NOT NULL DEFAULT 0,           -- 0/1
    discount_active_until INTEGER,                            -- unix timestamp окончания скидки 30%
    referrer_id         INTEGER,                              -- кто пригласил этого пользователя
    referral_code       TEXT UNIQUE,                          -- собственный промокод пользователя
    created_at          INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS referrals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id     INTEGER NOT NULL,
    referred_id     INTEGER NOT NULL UNIQUE,
    status          TEXT NOT NULL DEFAULT 'pending',   -- pending | completed
    reward_rub      INTEGER NOT NULL DEFAULT 0,
    reward_tickets  INTEGER NOT NULL DEFAULT 0,
    created_at      INTEGER NOT NULL,
    completed_at    INTEGER
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    amount          INTEGER NOT NULL,
    method          TEXT NOT NULL,      -- sbp | card | stars | crypto
    purpose         TEXT NOT NULL,      -- subscription:<plan> | balance_topup | gift:<target_id>
    status          TEXT NOT NULL DEFAULT 'pending',   -- pending | success | failed
    external_id     TEXT,               -- id платежа во внешней системе
    created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    subject         TEXT,
    message         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open',   -- open | answered | closed
    created_at      INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL,
    sender      TEXT NOT NULL,   -- user | admin
    text        TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
);
"""


class Database:
    def __init__(self, path: str = config.database_path):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    # ---------- users ----------

    async def get_or_create_user(self, user_id: int, username: str | None,
                                  referrer_id: int | None = None) -> dict:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            if row:
                if username:
                    await db.execute("UPDATE users SET username = ? WHERE user_id = ?",
                                      (username, user_id))
                    await db.commit()
                return dict(row)

            now = int(time.time())
            referral_code = f"AIVPN{user_id}"
            # реферер засчитывается только при первом создании пользователя
            valid_referrer = referrer_id if referrer_id and referrer_id != user_id else None

            await db.execute(
                """INSERT INTO users (user_id, username, referrer_id, referral_code, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, username, valid_referrer, referral_code, now),
            )

            if valid_referrer:
                await db.execute(
                    """INSERT OR IGNORE INTO referrals (referrer_id, referred_id, created_at)
                       VALUES (?, ?, ?)""",
                    (valid_referrer, user_id, now),
                )
            await db.commit()

            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            return dict(row)

    async def get_user(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def set_subscription(self, user_id: int, status: str, plan: str | None,
                                expires_at: int | None):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """UPDATE users SET subscription_status = ?, subscription_plan = ?,
                   subscription_expires_at = ? WHERE user_id = ?""",
                (status, plan, expires_at, user_id),
            )
            await db.commit()

    async def mark_free_trial_used(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET free_trial_used = 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def set_discount(self, user_id: int, until_ts: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET discount_active_until = ? WHERE user_id = ?",
                              (until_ts, user_id))
            await db.commit()

    async def change_balance(self, user_id: int, delta: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?",
                              (delta, user_id))
            await db.commit()

    async def add_tickets(self, user_id: int, count: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET tickets_count = tickets_count + ? WHERE user_id = ?",
                              (count, user_id))
            await db.commit()

    # ---------- referrals ----------

    async def get_referral_stats(self, user_id: int) -> dict:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM referrals WHERE referrer_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            rows = [dict(r) for r in await cur.fetchall()]

        invited_total = len(rows)
        completed = [r for r in rows if r["status"] == "completed"]
        pending = [r for r in rows if r["status"] == "pending"]
        tickets_earned = sum(r["reward_tickets"] for r in rows)
        rub_earned = sum(r["reward_rub"] for r in rows)

        return {
            "invited_total": invited_total,
            "completed_count": len(completed),
            "pending_count": len(pending),
            "tickets_earned": tickets_earned,
            "rub_earned": rub_earned,
        }

    async def get_pending_referral(self, referred_id: int) -> dict | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM referrals WHERE referred_id = ? AND status = 'pending'",
                (referred_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def complete_referral(self, referred_id: int, reward_rub: int, reward_tickets: int) -> dict | None:
        """Помечает реферала выполненным и начисляет бонусы пригласившему.
        Возвращает запись реферала (со заполненным referrer_id) или None, если реферала не было."""
        referral = await self.get_pending_referral(referred_id)
        if not referral:
            return None

        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """UPDATE referrals SET status = 'completed', reward_rub = ?,
                   reward_tickets = ?, completed_at = ? WHERE id = ?""",
                (reward_rub, reward_tickets, now, referral["id"]),
            )
            await db.execute(
                "UPDATE users SET balance = balance + ?, tickets_count = tickets_count + ? WHERE user_id = ?",
                (reward_rub, reward_tickets, referral["referrer_id"]),
            )
            await db.commit()
        return referral

    # ---------- payments ----------

    async def create_payment(self, user_id: int, amount: int, method: str, purpose: str,
                              external_id: str | None = None) -> int:
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """INSERT INTO payments (user_id, amount, method, purpose, external_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, amount, method, purpose, external_id, now),
            )
            await db.commit()
            return cur.lastrowid

    async def set_payment_status(self, payment_id: int, status: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE payments SET status = ? WHERE payment_id = ?",
                              (status, payment_id))
            await db.commit()

    async def get_payment_history(self, user_id: int, limit: int = 10) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
            return [dict(r) for r in await cur.fetchall()]

    # ---------- tickets ----------

    async def create_ticket(self, user_id: int, subject: str, message: str) -> int:
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """INSERT INTO tickets (user_id, subject, message, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, subject, message, now, now),
            )
            await db.commit()
            return cur.lastrowid

    async def get_user_tickets(self, user_id: int) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            return [dict(r) for r in await cur.fetchall()]


db = Database()
