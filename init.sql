-- ==============================
-- Algorithmic Trading Platform DB Schema (PostgreSQL)
-- Phase 1 (MVP) + Strategy Trade Logs
-- ==============================

-- 1. Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    phone_number VARCHAR(20),
    role VARCHAR(50) DEFAULT 'user',       -- user, admin, creator
    status VARCHAR(50) DEFAULT 'active',   -- active, inactive, banned
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Strategies Table
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),      -- intraday, positional, swing, options
    risk_level VARCHAR(50),    -- low, medium, high
    creator_id INT REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Subscriptions Table (many-to-many: users <-> strategies)
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    strategy_id INT REFERENCES strategies(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'active',   -- active, expired, cancelled
    start_date DATE DEFAULT CURRENT_DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Trade Logs Table (Base trade records)
CREATE TABLE trade_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    strategy_id INT REFERENCES strategies(id) ON DELETE CASCADE,
    mode VARCHAR(20) DEFAULT 'paper',      -- paper, live
    symbol VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(10),          -- BUY, SELL
    order_type VARCHAR(20),                -- MARKET, LIMIT, SL, SL-M
    quantity INT NOT NULL,
    price DECIMAL(12,2),
    pnl DECIMAL(12,2) DEFAULT 0,
    broker_order_id VARCHAR(100),          -- For live trading only
    metadata JSONB,                        -- Store broker response / extra details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Broker Accounts Table (Optional for Phase 1, required in Phase 2+)
CREATE TABLE broker_accounts (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    broker_name VARCHAR(50),               -- Zerodha, Dhan, Fyers
    api_key TEXT,
    api_secret TEXT,
    access_token TEXT,
    refresh_token TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- Indexes for Performance
-- ==============================

CREATE INDEX idx_trade_logs_user ON trade_logs(user_id);
CREATE INDEX idx_trade_logs_strategy ON trade_logs(strategy_id);
CREATE INDEX idx_trade_logs_created_at ON trade_logs(created_at);

CREATE INDEX idx_strategy_trade_logs_trade ON strategy_trade_logs(trade_log_id);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_strategy ON subscriptions(strategy_id);

-- ==============================
-- End of Schema
-- ==============================
