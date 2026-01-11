# teamfight-tactics

Teamfight Tactics 助手（CLI 範例），可連動 Riot 帳號並提供最新版本陣容推薦。

## 使用方式

1. 安裝相依套件：

```bash
pip install -r requirements.txt
```

2. 只看陣容推薦：

```bash
python tft_assistant.py --comps-only
```

3. 連動 Riot 帳號並查看排位：

```bash
export RIOT_API_KEY="YOUR_RIOT_API_KEY"
python tft_assistant.py --summoner-name "你的召喚師名稱" --region tw2
```

## 參數說明

- `--summoner-name`：召喚師名稱。
- `--region`：Riot API 區域代碼（預設 `tw2`）。
- `--api-key`：Riot API 金鑰（或使用 `RIOT_API_KEY` 環境變數）。
- `--comps-only`：只輸出陣容推薦。
- `--category`：`beginner` / `expert` / `all`。

## 陣容資料

陣容資料位於 `data/comp_recommendations.json`，可自行更新最新版本與推薦內容。
