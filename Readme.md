# binance_trading_bot

## install

```bash
git clone https://github.com/danielliwd/binance_trading_bot.git binance_trading_bot
cd binance_trading_bot
# you can use `pyenv`/`python -m venv` here. DYOR
pip install -r requirements.txt
```

## run strategy

```bash
touch .keys  # for keys: `BINANCE_API_KEY=xxx BINANCE_API_SECRET=xxx`, one key per line

export PYTHONPATH=`pwd`
exoprt PROXY_URL="http://127.0.0.1"
python -m strategies/strategy_nmacd_rsi
```

```bash
pip install python-dotenv[cli]
touch .env
dotenv python -m strategies/strategy_nmacd_rsi
```

## support

create issue, no mr/pr.