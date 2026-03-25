# BTC AI Alert Bot

Bot nay lay du lieu BTCUSDT futures, gom market structure + order book + open interest + long/short ratios + funding + crypto news, sau do gui vao OpenAI Responses API de sinh ra setup `Long / Short / Wait`. Ket qua duoc format va gui qua Telegram.

## Bot lay nhung gi

- Nen `1h`, `4h`, `1d` tu Binance Futures
- Chi phan tich tren nen da dong, khong lay cay dang chay
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

Bot chi gui Telegram khi `action` la `long` hoac `short`. Neu `action=wait` thi bot chi log ket qua, khong ban notification.

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
- chay moi gio 1 lan vao phut `02`

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
- Khi market qua nhieu, GPT duoc prompt de uu tien `wait` thay vi ep phai vao lenh.

## Deploy len AWS Lambda + EventBridge Scheduler

Kien truc nay hop voi bot hien tai vi bot chi la mot tac vu ngan, stateless, chay 1 lan roi thoat. Tuy nhien no chi giai quyet duoc van de scheduler/serverless, con van de Binance `451` thi phu thuoc vao region AWS ban chon.

Handler Lambda:

- `btc_alert_bot.lambda_handler.handler`
- SAM template: `template.yaml`

Build file zip de upload:

```powershell
.\scripts\build-lambda.ps1
```

File zip tao ra:

- `dist/btc-alert-lambda.zip`

Khuyen nghi:

- Build package tren `Linux`, `WSL`, `Docker`, hoac `AWS CloudShell` de tranh loi dependency khac he dieu hanh giua Windows va Lambda Linux.
- Script build dang ep dependency ve dang pure-Python de zip de portable hon giua Windows va Lambda Linux.

Neu muon deploy bang AWS SAM:

```bash
sam validate --template-file template.yaml --region ap-southeast-1
sam build --template-file template.yaml --region ap-southeast-1
sam local invoke BtcAlertFunction -e events/scheduler-event.json --env-vars events/sam-env.example.json
sam deploy --guided --region ap-southeast-1
```

Local invoke bang SAM can `Docker`.

Neu muon bam mot lan tren Windows:

```powershell
.\scripts\sam-deploy-guided.ps1
```

Neu muon doi region:

```powershell
.\scripts\sam-deploy-guided.ps1 -Region ap-northeast-1
```

Neu muon test nhanh xem may/region co bi Binance Futures chan khong:

```powershell
.\scripts\test-binance-access.ps1
```

Trinh tu deploy de it loi nhat:

1. Chon region AWS va test Binance truoc. Tao mot Lambda test hoac EC2 nho trong region do, goi:

```bash
curl "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=1"
```

Neu tra JSON thi region do kha nang dung duoc. Neu van ra `451` thi doi region hoac doi provider.

2. Tao Lambda:
- Runtime: `Python 3.12`
- Handler: `btc_alert_bot.lambda_handler.handler`
- Timeout: `120s`
- Memory: `512 MB`
- Khong attach VPC neu ban khong that su can, de function giu internet access de goi Binance/OpenAI/Telegram

3. Upload file `dist/btc-alert-lambda.zip`

4. Set Environment variables trong Lambda:
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
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

5. Test function bang nut `Test` trong Lambda console

6. Tao `EventBridge Scheduler`:
- Target: Lambda function cua ban
- Recurring schedule: mac dinh trong `template.yaml` la `cron(2 * * * ? *)` theo timezone `Asia/Ho_Chi_Minh`
- Flexible time window: `Off`
- Retry policy: nen bat retry
- DLQ: nen gan SQS neu muon debug job loi

7. Kiem tra log trong CloudWatch Logs

Luu y:

- `EventBridge Scheduler` goi Lambda async, nen retry/DLQ hoat dong tot cho job dang nay.
- Lambda toi da chay `15 phut`, bot nay du kien ngan hon rat nhieu nen phu hop.
- Lambda co internet mac dinh neu khong gan vao VPC. Neu gan VPC thi ban phai cau hinh internet/NAT rieng.
- Chi phi thuong rat thap cho job moi gio; EventBridge Scheduler va Lambda deu co free tier, va workload nay thuong nam trong muc rat nho.

## Cau truc thu muc

```text
.github/workflows/btc-alert.yml
scripts/build-lambda.ps1
scripts/sam-deploy-guided.ps1
scripts/test-binance-access.ps1
template.yaml
events/scheduler-event.json
events/sam-env.example.json
src/btc_alert_bot/config.py
src/btc_alert_bot/http.py
src/btc_alert_bot/lambda_handler.py
src/btc_alert_bot/market.py
src/btc_alert_bot/news.py
src/btc_alert_bot/openai_client.py
src/btc_alert_bot/telegram_client.py
src/btc_alert_bot/main.py
```
