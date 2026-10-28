# 台股當沖雷達 Pro V0.2 — iOS PWA

這是可運行的**離線優先前端原型**，沒有連接即時股價、當沖資格或交易所 API。示範股票完全虛構，策略參考價不是交易建議。

## 使用方法
1. 將整個資料夾部署至 GitHub Pages（或其他 HTTPS 靜態主機），不要只上傳 index.html。
2. 用 iPhone Safari 開啟 HTTPS 網址，點選「分享」→「加入主畫面」。
3. 從主畫面開啟，於「資料設定」載入示範資料或匯入自己的 CSV。
4. Windows 可透過 HTTPS 或 localhost 使用；直接雙擊 index.html 可預覽基本功能，但不會註冊 Service Worker。

## CSV 格式
`code,name,close,high,low,volume,prev`，價格單位元，volume 單位張，必須為同一天的行情。支援含引號的 CSV 欄位。

## 限制
- 僅支援日行情匯入與簡單量價評分，沒有即時行情、VWAP、RSI、分鐘 K、回測或推播。
- 交易日誌損益未扣除手續費、證交稅及滑價。
- 教學突破價採固定 0.05 元示意，未依台股各價位跳動單位或個股當沖資格校驗，不可用於下單。
- 本機資料儲存在 localStorage，請定期匯出備份。
- 目前不需要伺服器或 API 金鑰。

## 後續架構
前端 PWA → HTTPS API (FastAPI) → 合規行情來源／PostgreSQL → 排程分析與通知。資料源與授權確認後才能開啟盤中訊號。
