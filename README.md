# 台股當沖雷達 Pro V0.5

## 部署
將本資料夾內的檔案與 `.github/workflows/update.yml` 上傳到 GitHub 儲存庫根目錄。注意 GitHub 網頁上傳工具可能不保留隱藏資料夾 `.github`；建議使用 GitHub 網頁 Create new file 直接建立 `.github/workflows/update.yml`，或使用 GitHub Desktop / git push。

Settings > Pages > Deploy from a branch > main > /(root)。

Actions > 更新台股行情 > Run workflow，確認成功且 `data/stocks.json` 產生後，重新整理網站。排程為 UTC 07:20，即台灣 15:20，僅平日，並非盤中即時行情。GitHub Actions 排程可能延遲或暫停，請檢查日期。

**注意**：官方 API 欄位可能變動，TPEx 端點或雲端連線可能受限制。程式刻意在資料源失敗或日期不一致時停止，避免顯示不完整或假資料。請先確認首次 Action 成功，否則不能承諾隔日可用。

## 使用限制
本版只提供收盤資料盤前觀察。高點突破價、停損、2R 目標為條件式參考，未經回測，不代表預期獲利。未確認當沖資格、借券、處置及即時成交量，不能用於自動下單。股票價格 40–100 元，成交量單位預設 API 成交股數轉張。開盤跳空、除權息等情況需人工確認。
