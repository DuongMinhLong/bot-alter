# BTC AI Alert Bot

Bot nay lay du lieu BTCUSDT futures, gom market structure + order book + open interest + long/short ratios + funding + crypto news, sau do gui vao OpenAI Responses API de sinh ra setup `Long / Short / Wait`. Ket qua duoc format va gui qua Telegram.

## Bot lay nhung gi

- Nến `1h`, `4h`, `1d` tu Binance Futures
- RSI, EMA20, EMA50, ATR14, volume anomaly, range 20 candles
- Order book snapshot: spread, imbalance, top walls, thanh khoan quanh `0.5%` va `1%`
- Funding rate, mark/index basis, open interest hien tai
- Open interest history theo `1h`, `4h`, `1d`
- Global long/short ratio, top trader account ratio, top trader position ratio
- Taker buy/sell volume ratio
- Fear & Greed index
- News moi nhat tu CoinDesk, Cointelegraph, Decrypt

## Output GPT

Bot ep model tra ve JSON schema co dinh gom:

- `action`
- `market_bias`
- `summary`
- `timeframe_alignment`
- `key_levels`
- `long_scenario`
- `short_scenario`
- `risk_notes`

`action` co 3 gia tri:

- `long`: vao lenh ngay
- `short`: vao lenh ngay
- `wait`: khong vao lenh

Bot chi gui Telegram khi `action` la `long` hoac `short`. Neu `action=wait` thi bot chi log ket qua, khong bắn notification.

Moi scenario co:

- `entry`
- `stop_loss`
- `take_profits`
- `confidence`
- `risk_reward`
- `trigger`
- `invalidation`
- `management`

## Cai dat local

1. Tao file `.env` tu `.env.example`
2. Dien cac gia tri:
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
3. Cai dependency:

```bash
pip install -r requirements.txt
```

4. Chay bot:

```bash
set PYTHONPATH=src
python -m btc_alert_bot
```

Neu muon test ma khong gui Telegram, set:

```bash
DRY_RUN=true
```

De log phan request/response voi OpenAI:

```bash
LOG_OPENAI_IO=true
LOG_OPENAI_MAX_CHARS=20000
```

Bot se log:

- `system prompt`
- `user payload` gui sang model
- `raw output_text`
- `parsed JSON`

## Deploy len GitHub Actions

1. Tao repo moi tren GitHub
2. Trong `C:\bot_alter`, chay:

```bash
git init
git add .
git commit -m "Initial BTC alert bot"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

3. Vao `Settings -> Secrets and variables -> Actions`
4. Tao `Secrets`:
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
5. Tao `Variables` neu can:
- `OPENAI_MODEL`
- `OPENAI_REASONING_EFFORT`
- `LOG_OPENAI_IO`
- `LOG_OPENAI_MAX_CHARS`
- `BINANCE_SYMBOL`
- `KLINE_LIMIT`
- `ORDER_BOOK_LIMIT`
- `NEWS_LIMIT`
- `REQUEST_TIMEOUT_SECONDS`
- `INCLUDE_FEAR_GREED`
- `DRY_RUN`

Workflow mac dinh nam o:

- `.github/workflows/btc-alert.yml`

Workflow hien tai:

- cho phep `workflow_dispatch`
- chay moi gio 1 lan vao phut `05`

Neu muon chay test tren GitHub ma khong gui Telegram, set:

- `DRY_RUN=true`

Neu muon xem log prompt/output tren GitHub Actions:

- `LOG_OPENAI_IO=true`
- `LOG_OPENAI_MAX_CHARS=20000`

Sau khi push source:

1. Vao tab `Actions`
2. Chon workflow `BTC Alert Bot`
3. Bam `Run workflow` de test manual
4. Sau do workflow se tu chay moi gio

## Telegram

- Tao bot bang `@BotFather`
- Lay `TELEGRAM_BOT_TOKEN`
- Lay `TELEGRAM_CHAT_ID` bang cach nhan tin cho bot, sau do goi API `getUpdates` hoac dung bot/utility lay chat id

## Luu y thuc te

- GitHub Actions dung runner public. Neu mot ngay Binance chan IP runner theo khu vuc, bot co the fail du workflow van dung. Khi do ban can chuyen sang VPS hoac doi data provider.
- Bot nay la he thong scenario planning, khong phai lenh giao dich tu dong.
- Khi market qua nhiu, GPT duoc prompt de uu tien `wait` thay vi ep phai vao lenh.

## Cau truc thu muc

```text
.github/workflows/btc-alert.yml
src/btc_alert_bot/config.py
src/btc_alert_bot/http.py
src/btc_alert_bot/market.py
src/btc_alert_bot/news.py
src/btc_alert_bot/openai_client.py
src/btc_alert_bot/telegram_client.py
src/btc_alert_bot/main.py
```
