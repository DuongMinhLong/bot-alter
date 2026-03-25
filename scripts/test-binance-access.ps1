Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

@'
import json
import sys

import requests

url = "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=1"

try:
    response = requests.get(url, timeout=30)
    print(f"HTTP Status: {response.status_code}")
    print(response.text)
    response.raise_for_status()
except Exception as exc:
    print(str(exc), file=sys.stderr)
    raise
'@ | python -
