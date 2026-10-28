V0.5.3.4 歷史行情唯讀測試

覆蓋 GitHub 根目錄 update_data.py 與 .github/workflows/update-stocks.yml。
GitHub Actions → 更新台股行情 → Run workflow → test_date 輸入 2026-10-28 → 執行。
歷史測試不會寫入 data/stocks.json；即使失敗也會列出各市場的錯誤。
留空 test_date 則維持台灣時間 16:00 後正式更新。
注意：此版本尚未證實兩個官方 API 的欄位與日期均可通過；以 GitHub Actions 實際紀錄為準。
