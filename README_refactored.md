# PyCon TW 2025 提案評審系統

這個專案是用於 PyCon TW 2025 提案評審的工具，包含 LLM 自動評審和人工評審資料的整合與分析。

## 專案結構

```
.
├── src/                     # 源代碼目錄
│   ├── __init__.py          # Python 包初始化文件
│   ├── config.py            # 配置文件，包含路徑和設定
│   ├── models.py            # 資料模型定義
│   ├── llm_review.py        # LLM 評審功能
│   ├── merge_data.py        # 資料合併和分析功能
│   └── main.py              # 主程式入口
├── data/                    # 資料目錄
│   ├── pycon_2024_proposal.xlsx             # 提案資料
│   └── pycon_2024_review.xlsx               # 人工評審資料
├── output/                  # 輸出目錄
│   ├── simple_prompt_gemini_flash_*.xlsx    # 簡單提示的 LLM 評審結果
│   ├── full_prompt_gemini_flash_*.xlsx      # 完整提示的 LLM 評審結果
│   ├── pycon_2024_proposal_with_llm_and_review_*.xlsx  # 合併後的資料
│   ├── vote_analysis_*.json                 # 投票分析結果 (JSON 格式)
│   └── vote_analysis_*.txt                  # 投票分析報告 (人類可讀格式)
├── logs/                    # 日誌目錄
│   ├── llm_review_*.log     # LLM 評審日誌
│   ├── merge_data_*.log     # 資料合併日誌
│   └── main_*.log           # 主程式日誌
├── prompt/                  # 提示詞目錄
│   ├── simple_prompt.txt    # 簡單提示詞
│   └── full_prompt.txt      # 完整提示詞
└── run.py                   # 入口點腳本
```

## 安裝依賴

```bash
pip install pandas langchain-core langchain-google-genai python-dotenv openpyxl
```

## 環境變數設定

在專案根目錄創建 `.env` 文件，並設定以下環境變數：

```
GOOGLE_API_KEY=your_google_api_key_here
```

## 使用方法

### 主程式

使用入口點腳本 `run.py` 提供了完整的工作流程，可以執行 LLM 評審、資料合併和分析。

```bash
# 執行完整流程（LLM 評審 + 資料合併分析）
python run.py

# 只執行 LLM 評審
python run.py --mode review

# 只執行資料合併分析
python run.py --mode merge

# 使用簡單提示詞
python run.py --prompt simple

# 使用完整提示詞
python run.py --prompt full

# 同時使用兩種提示詞
python run.py --prompt both

# 使用不同的模型
python run.py --model pro

# 指定輸出目錄
python run.py --output-dir ./output

# 跳過分析
python run.py --no-analyze
```

### 單獨使用 LLM 評審功能

```bash
python -m src.llm_review --prompt simple --model flash
```

### 單獨使用資料合併功能

```bash
python -m src.merge_data --simple-llm-file output/simple_prompt_gemini_flash_20240228.xlsx --complete-llm-file output/full_prompt_gemini_flash_20240228.xlsx
```

## 輸出文件說明

### LLM 評審結果

LLM 評審結果保存在 `output/` 目錄下的 Excel 文件中：

- `simple_prompt_gemini_flash_*.xlsx`：使用簡單提示詞的 LLM 評審結果
- `full_prompt_gemini_flash_*.xlsx`：使用完整提示詞的 LLM 評審結果

這些文件包含以下列：
- `proposal_id`：提案 ID
- `summary`：提案摘要
- `comment`：評審意見
- `vote`：投票結果（0-3）

### 合併後的資料

合併後的資料保存在 `output/pycon_2024_proposal_with_llm_and_review_*.xlsx` 文件中，包含提案資料、人工評審資料和 LLM 評審資料。

### 分析結果

分析結果保存在兩種格式的文件中：

1. JSON 格式（`output/vote_analysis_*.json`）：包含完整的分析結果，適合程式讀取和進一步處理。

2. 文本報告（`output/vote_analysis_*.txt`）：人類可讀的分析報告，包含：
   - LLM 投票分佈
   - 人工評審投票分佈
   - LLM 和人工評審的一致性比率
   - 混淆矩陣

這些分析結果可以幫助評估 LLM 評審的效果，並與人工評審進行比較。

## 擴展建議

1. 添加更多的分析指標，如 Cohen's Kappa 係數來評估評審一致性。

2. 實現視覺化功能，生成評審結果的圖表和報告。

3. 添加更多的 LLM 模型支援，如 OpenAI 的 GPT 模型。