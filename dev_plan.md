Goal:
請完成 proposal 審核輔助系統，產生類似 data/recover_sample 目錄中的結果檔案。

## 執行步驟

### 1. 資料獲取與準備
- 從資料庫獲取 2024 年的提案資訊及評論
- 篩選出負面評價比例超過 25% 的提案（使用 pycon_llm_sql 檔案中的 SQL 查詢）
- 確保將 proposal id 轉換為字串格式，避免 Excel 整數溢位問題
- 使用 pandas 處理表格資料，確保資料一致性和完整性

### 2. LLM 審核 (使用繁體中文)
- 利用 LLM API 分析每個提案內容
  - 使用 o3-mini 模型進行初步評審
  - 根據特定 prompt 結構化輸出評審意見
- 實作非同步處理（async）以優化 API 請求效率
  - 使用 asyncio 和 aiohttp 實現並發請求
- 針對提案內容生成結構化評論，參考負面提案特徵分析
- 每個評論需包含：
  - summary_tc: 提案內容摘要（100字以內）
  - comment_tc: 綜合評論
    - advantages_tc: 提案優點（3-5點）
    - disadvantages_tc: 提案缺點
    - suggestions_tc: 改進建議
  - vote: 投票結果（+1, +0, -0, -1）

### 3. 評論翻譯
- 將 LLM 生成的繁體中文評論翻譯為英文 (使用 gpt-4o-mini)
  - 翻譯保持原始評論的專業術語和技術性表達
  - 確保維持評論的結構和條理性
- 保持評論的原始結構和關鍵點
  - 使用特定翻譯提示詞增強翻譯品質
- 同樣實作非同步處理以提高效率
  - 翻譯每個提案的多個評論部分 (摘要、優點、缺點、建議)
  - 實施錯誤處理和重試機制

### 4. 結果評估與輸出
- 比較歷史評論與 LLM 評論的差異
  - 計算 vote 一致性和差異程度
  - 評估 LLM 評審意見與人類評審的符合程度
- 計算一致性分數和效能指標
  - llm_human_vote_diff: LLM 投票與人類平均投票的絕對差距
  - llm_agreement_pct: LLM 投票與人類投票完全一致的百分比
- 生成以下輸出檔案：
  1. resampled_proposals_[日期].xlsx - 原始提案資料
  2. resampled_proposals_[日期]_comments.xlsx - 提案連同評論
  3. [prompt]_[model_reasoning_effort]_[日期].xlsx - 包含 LLM 評論和翻譯
  4. enhanced_evaluation_[日期].xlsx - 評估結果和比較分析

## 技術實作細節

### 資料模型設計
- 使用 Pydantic 模型確保資料結構一致性
  - `ProposalReview`: 基本評審模型
  - `EnhancedProposalReview`: 增強版評審模型，包含中英文評論
  - `VoteStats`: 投票統計模型

### 異步處理框架
- 主要使用 asyncio 實現非同步操作
- 使用 aiohttp 處理非同步 HTTP 請求
- 實現批次處理避免 API 速率限制
  - 每次處理 5 個提案，確保不超過 API 限制
  - 使用 asyncio.gather() 並行處理多個請求

### LLM 整合
- 使用 LangChain 整合不同 LLM 模型
  - ChatGoogleGenerativeAI 使用 Gemini 模型
  - ChatOpenAI 使用 OpenAI 模型
- 使用結構化輸出格式獲取 LLM 評論
  - 定義完整的評論提示詞格式
  - 使用 structured_llm = llm.with_structured_output(模型) 確保輸出規範

### 錯誤處理與重試
- 實作階段性重試機制
  - 配置預設重試次數 (max_retries)
  - 設定重試間隔時間 (sleep_time)
- 當 API 請求失敗時進行指數退避重試
- 完整的錯誤日誌記錄，便於問題診斷

### 命令行介面
- 提供靈活的命令行選項
  - 操作模式：review, merge, full
  - 提示詞類型：simple, full
  - 模型選擇：gemini, gpt4o
  - 翻譯模型：gpt4o-mini 等
- 支援限制處理提案數量 (--limit)
- 可自定義輸出目錄和文件名稱

### 資料處理與合併
- 實作多階段資料處理流程
  - merge_reviews_with_proposals: 合併提案與人工評審
  - merge_llm_reviews_with_proposals: 合併提案與 LLM 評審
  - calculate_agreement_metrics: 計算一致性指標

## 改進與優化
- 實現增量處理機制，支援處理過程中斷後續處理
- 優化批次大小和並行度，找出最佳 API 請求效率平衡點
- 增強數據驗證，確保輸入和輸出保持一致性
- 擴展評估指標，加入更多量化分析維度
- 添加視覺化分析模組，生成評估報告圖表

## 輸出格式要求
- 所有輸出檔案使用 .xlsx 格式
- 檔名需包含處理日期（格式：YYYYMMDD）
- 確保資料欄位名稱與 recover_sample 中的範例一致
- 確保中英文欄位對應關係清晰：
  - *_tc: 繁體中文版本
  - *_en: 英文翻譯版本

## 參考資料
0. 使用 async 處理 LLM API 請求以提高效率

1. proposal id 應轉換為字串格式，避免 Excel 整數溢位問題

2. 負面提案特徵分析

不好稿件的共同特徵分析
根據提供的審查過程中被拒絕或評價不佳的稿件，我歸納出以下幾個明顯的問題特徵：

1. 資訊不足或過於簡略
僅提供標題，缺少摘要、大綱或目標
大綱空泛，無法讓審查者判斷內容質量
未提供演講時間分配，難以評估是否能在規定時間內完成
僅僅複製貼上相同內容到不同欄位（如「詳細描述」和「大綱」相同）
2. 與 Python 相關性不足
主題與 Python 語言或生態系統關聯性微弱或完全無關
更適合在其他技術會議發表（如 Julia、AI、銷售或管理相關會議）
未能說明為何要在 Python 會議分享此主題
3. 內容深度與原創性不足
網路上已有大量類似教學，未提供新穎見解
基礎教學內容，未展示進階應用或獨特見解
無法在有限時間內提供超越基礎教學的價值
4. 主題範圍不適當
範圍過大，試圖在短時間內涵蓋太多內容（如一次介紹多種工具或技術）
主題太模糊，缺乏具體內容和明確重點
未考慮聽眾能在有限時間內消化的信息量
5. 缺乏實用案例與應用場景
缺少實際應用案例或使用場景
沒有展示如何解決實際問題
未能清楚說明技術對聽眾的實際價值
6. 過於商業或宣傳導向
偏向產品或服務的宣傳，缺乏技術深度
內容像是廣告而非技術分享
未能提供中立的技術見解
7. 目標聽眾和預期收獲不明確
未清晰定義目標聽眾群體
沒有說明聽眾將從演講中獲得什麼價值或技能
對聽眾所需背景知識的描述不明確或不一致
8. 結構與組織問題
提案內容與標題不符
各部分之間缺乏一致性或邏輯連貫性
明顯的拼寫錯誤或語法問題，顯示準備不足
9. 時效性問題
主題已經過時或缺乏創新性
討論已經被廣泛探討過的技術，未提供新觀點
未能反映當前技術趨勢或行業發展
這些問題特徵往往相互關聯，一個不好的稿件通常會同時存在多個問題。成功的提案應該避免這些問題，確保內容豐富、與 Python 相關、具有深度和原創性，且結構清晰、目標明確。

3. 從 API 取得資料範例

import requests

# get api token

data = {
    "username": "username",
    "password": "password"
}

response = requests.post(f"{METABASE_URL}/api/session", json=data)

session = response.json()["id"]

# query dataset

url = f"{METABASE_URL}/api/dataset"

headers = {
    "Content-Type": "application/json",
    "X-Metabase-Session": session,
}

data = {
    "database": 11,
    "native": {
      "query": "SELECT id, title FROM proposals_talkproposal WHERE conference = 'pycontw-2024' LIMIT 1;"
    },
    "type": "native"
}

response = requests.post(url, headers=headers, json=data)
# response.json()['data']['rows']