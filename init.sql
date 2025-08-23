-- Users & Authentication

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE brokers (
    broker_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    api_base_url TEXT
);

CREATE TABLE user_broker_accounts (
    account_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    broker_id INT REFERENCES brokers(broker_id),
    api_key TEXT,
    api_secret TEXT,
    account_tag TEXT, -- e.g., “Dhan-Paper” or “Zerodha-Live”
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- Market Data

CREATE TABLE symbols (
    symbol_id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,      -- e.g., "NIFTY", "BANKNIFTY"
    exchange TEXT NOT NULL,    -- NSE, BSE
    instrument_token BIGINT,   -- broker-specific ID
    tick_size NUMERIC(10,2)
);

CREATE TABLE ohlc_data (
    ohlc_id BIGSERIAL PRIMARY KEY,
    symbol_id INT REFERENCES symbols(symbol_id),
    interval TEXT, -- "1m", "5m", etc.
    open NUMERIC(15,5),
    high NUMERIC(15,5),
    low NUMERIC(15,5),
    close NUMERIC(15,5),
    volume BIGINT,
    candle_time TIMESTAMPTZ,
    UNIQUE(symbol_id, interval, candle_time)
);

CREATE TABLE live_ticks (
    tick_id BIGSERIAL PRIMARY KEY,
    symbol_id INT REFERENCES symbols(symbol_id),
    ltp NUMERIC(15,5),
    bid NUMERIC(15,5),
    ask NUMERIC(15,5),
    tick_time TIMESTAMPTZ
);


-- Strategies

CREATE TABLE strategies (
    strategy_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_by INT REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_strategies (
    user_strategy_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    strategy_id INT REFERENCES strategies(strategy_id),
    params JSONB,  -- Store flexible strategy parameters
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Orders & Trades

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_strategy_id INT REFERENCES user_strategies(user_strategy_id),
    symbol_id INT REFERENCES symbols(symbol_id),
    broker_order_id TEXT,
    side TEXT, -- BUY or SELL
    quantity INT,
    price NUMERIC(15,5),
    order_type TEXT, -- MARKET, LIMIT
    status TEXT, -- PENDING, FILLED, CANCELLED
    placed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE TABLE trades (
    trade_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    fill_price NUMERIC(15,5),
    fill_qty INT,
    trade_time TIMESTAMPTZ
);

-- Positions & Pnl

CREATE TABLE positions (
    position_id SERIAL PRIMARY KEY,
    user_strategy_id INT REFERENCES user_strategies(user_strategy_id),
    symbol_id INT REFERENCES symbols(symbol_id),
    net_qty INT,
    avg_price NUMERIC(15,5),
    realized_pnl NUMERIC(15,2) DEFAULT 0,
    unrealized_pnl NUMERIC(15,2) DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Logs & Audit

CREATE TABLE activity_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    action TEXT,
    details JSONB,
    log_time TIMESTAMPTZ DEFAULT NOW()
);
