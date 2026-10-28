當沖雷達 Pro V0.5.3.3 — 交易日資料來源修正（測試版）

上傳至 GitHub 專案根目錄，覆蓋：
  update_data.py
  freshness.js
  sw.js

將 ZIP 內 .github/workflows/update-stocks.yml 上傳到 GitHub 的同名資料夾覆蓋舊檔。
其他檔案保留；請勿刪除 data/stocks.json。

上傳後進入 Actions 手動 Run workflow。檢查「擷取官方指定日期行情」的詳細日誌。
若只有 TWSE 成功，會只更新 TWSE 並保留舊 TPEx，首頁會警告 TPEx 未驗證。
若兩個市場都失敗，不會覆蓋行情檔，Actions 會顯示失敗。

注意：官方歷史端點的實際 2026/10/28 回應無法在本地網路驗證，仍須透過 GitHub Actions 真實測試。
這個版本沒有自動取得隔日沖券商分點排行。
