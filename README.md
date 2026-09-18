# AlgoBot

AlgoBot is an algorithmic trading bot for Indian markets that subscribes to Dhan market data, tracks Nifty option strikes, aggregates candle data, and applies simple option strategies based on live ticks.

This project is structured around:

- live market feed ingestion from Dhan
- Redis-based tick publishing
- candle aggregation and indicator logic
- strategy execution for ATM/OTM option trading
- PostgreSQL storage for OHLC data
- Telegram notifications for trade/order events

## Project overview

The application starts from `main.py`, which initializes:

- the Dhan feed handler
- the Nifty OTM strategy
- the Nifty ATM strategy

Each runs in a separate thread so live ticks can be processed continuously.

## Repository structure

```text
algobot/
├── Dockerfile
├── main.py
├── requirements.txt
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── connections/
│   │   ├── cache.py
│   │   ├── connectDB.py
│   │   ├── connectTel.py
│   │   └── ...
│   ├── dataaggregators/
│   │   ├── candleAggregator.py
│   │   ├── strikeFinder.py
│   │   └── ...
│   ├── indicators/
│   │   ├── bep.py
│   │   └── ...
│   ├── strategies/
│   │   ├── nifty_atm.py
│   │   ├── nifty_otm.py
│   │   └── ...
│   └── utils/
│       ├── base.py
│       └── ...
└── ...
```

## Key components

### `main.py`
Starts the market feed and strategy threads.

### `src/utils/base.py`
Contains the `DhanFeedHandler` class that:

- loads environment variables
- creates the Dhan client
- subscribes to the required instruments
- reads tick updates from Dhan market feed
- publishes tick events to Redis

### `src/strategies/nifty_otm.py`
Defines the Nifty OTM strategy logic. It:

- assigns the underlying strike using OHLC data
- identifies ATM and OTM option contracts
- tracks LTP values
- computes break-even points
- persists candle data
- can place real orders through Dhan

### `src/strategies/nifty_atm.py`
Defines a related ATM strategy and follows a similar pattern to the OTM strategy.

### `src/dataaggregators/`
Responsible for building candles and related price aggregation logic.

### `src/indicators/`
Contains indicator-related functions such as break-even and rounding helpers.

### `src/connections/`
Handles integration points such as:

- Redis cache
- Telegram alerts
- PostgreSQL database connections

## Requirements

Install project dependencies:

```bash
pip install -r requirements.txt
```

The project depends on packages including:

- `danhq`
- `redis`
- `psycopg2`
- `pandas`
- `numpy`
- `python-dotenv`
- `TA-Lib`

## Environment setup

Create a `.env` file in the project root with the required credentials:

```env
CLIENT_ID=your_dhan_client_id
ACCESS_TOKEN=your_dhan_access_token
```

You may also need a Redis instance and PostgreSQL database configured for the connection modules used by the bot.

## Running the bot

From the project root:

```bash
python main.py
```

This starts the feed and strategy threads. The bot continues running in the foreground until interrupted.

## Docker

A basic Dockerfile is included, but it currently only prints a placeholder message:

```dockerfile
FROM ubuntu:latest
CMD ["echo","Hello World"]
```

If you want to containerize the bot properly, the Docker setup should be updated to install Python dependencies and run `python main.py` inside the container.

## Important note

This project interacts with live market data and trading APIs. It is intended for learning and experimentation and should be used with caution. Trading financial instruments carries risk, and production-grade safeguards should be added before using it with real money.

## Future improvements

A few useful next steps for this project could be:

- add a proper `.env.example` file
- improve logging and monitoring
- add unit tests for indicators and strategies
- refactor strategy logic into cleaner modules
- configure Docker for the real app
- add a health check and graceful shutdown flow
- protect real trading actions behind explicit enablement flags

## License

No explicit license has been configured in this repository yet.
