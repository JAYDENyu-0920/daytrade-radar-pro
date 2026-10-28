台股當沖雷達 Pro V0.5.1
請保留資料夾結構，上傳 index.html、app.js、sw.js、update_data.py 和 .github/workflows/update-stocks.yml 到 GitHub 專案根目錄。
進入 Actions > 更新台股行情 > Run workflow 手動執行，成功後應出現 data/stocks.json。
如果 Actions 工作流程失敗，查看「擷取官方行情」步驟日誌。此版尚未經線上 API 實測，可能需要依官方欄位調整。
排程為週一至週五台灣時間 15:45（GitHub 排程可能延遲）；不提供即時行情。
首次部署後在 Safari 重新整理；若仍顯示舊版，清除網站資料或移除再加入主畫面。
注意：date 欄位標示擷取日期，不代表官方驗證交易日；官方 API 若延遲可能是舊資料，交易前務必核對。
