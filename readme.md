# PyCon TW 2025 提案審核工具

這個專案提供了一套工具，用於使用 LLM 來審核和評估 PyCon TW 2025 的演講提案。

## 檔案結構

```
PyCon-TW-2025/
├── data/                 # 資料目錄
│   └── db_merged_fixed/  # 處理過的資料庫資料
├── logs/                 # 日誌檔案
├── output/               # 輸出結果目錄
├── prompt/               # LLM 提示模板
│   ├── evaluation_prompt.txt  # 評估提示
│   ├── full_prompt.txt        # 完整評審提示
│   └── simple_prompt.txt      # 簡易評審提示
├── src/                  # 源代碼
│   ├── db/               # 資料庫相關模組
│   ├── llm/              # LLM 相關模組
│   ├── utils/            # 工具函數
│   ├── evaluation/       # 評估模組
│   ├── config.py         # 配置檔案
│   ├── models.py         # 資料模型
│   └── main_llm.py       # 主執行腳本
└── run_llm.py                # 主入口點腳本
└── run_categorize.py         # 提案分類腳本
```

## 如何使用

### 環境設置

1. 安裝所需的 Python 套件：

```bash
pip install -r requirements.txt
```

2. 設置環境變數（API 金鑰等）：

```bash
cp .env.example .env
# 編輯 .env 檔案，設置你的 API 金鑰
```

### get 2025 提案

#### notice
- resampled_proposals_20250404.xlsx 是之前測試 2024 年的資料
- 需要先在 metabase 建立 database 12，並且把 pycontw-2025 的資料匯入

```bash
python3 src/get_2025_proposals.py
```

### 執行 LLM 評審

```bash
python3 run_llm.py review \
  --proposal_file data/pycontw_2025_proposals_20250520.xlsx \
  --model o4-mini \
  --reasoning_effort high \
  --with_translation
```

### 執行評估

```bash
python run_llm.py evaluate \
  --llm_reviews_file output/llm_review_o3-mini_20250404.xlsx \
  --human_reviews_file data/db_merged_fixed/reviews_20250404.xlsx \
  --model o3-mini \
  --reasoning_effort high
```

### 同時執行評審和評估

```bash
python3 run_llm.py \
  --model o4-mini \
  --reasoning_effort high \
  review \
  --proposal_file data/pycontw_2025_proposals_20250520.xlsx \
  --with_translation
```

### 執行提案分類

```bash
python3 run_categorize.py \
  --proposal_file data/pycontw_2025_proposals_20250520.xlsx \
  --model o4-mini \
  --reasoning_effort high
```

### 執行提案分類 (限制處理 5 筆提案, --limit 5)

```bash
python3 run_categorize.py \
  --proposal_file data/pycontw_2025_proposals_20250407.xlsx \
  --model o3-mini \
  --reasoning_effort medium \
  --limit 5
```

### 執行提案差異比較

```bash
python3 run_proposal_diff.py \
  --stage1_file data/pycontw_2025_proposals_snapshot_20250427.xlsx \
  --stage2_file data/pycontw_2025_proposals_20250520.xlsx \
  --model o4-mini \
  --reasoning_effort high \
  --translation_model gpt-4o-mini
```

## 命令列選項

### 通用選項

- `--data_dir` - 資料目錄路徑，預設為 `data/db_merged_fixed`
- `--output_dir` - 輸出目錄路徑，預設為 `output`
- `--model` - LLM 模型名稱，預設為 `o3-mini`
- `--reasoning_effort` - 推理努力級別（僅適用於 OpenAI 模型），可選 `low`、`medium`、`high`，預設為 `high`

### Review 命令選項

- `--proposal_file` - 提案資料檔案路徑（必須）
- `--prompt_file` - 提示模板檔案路徑，預設為 `prompt/full_prompt.txt`
- `--output_file` - 輸出檔案路徑（若未指定，則自動生成）
- `--limit` - 要處理的提案數量上限（用於測試）
- `--with_translation` - 是否進行翻譯
- `--translation_model` - 翻譯用 LLM 模型名稱，預設為 `gpt-4o-mini`

### Evaluate 命令選項

- `--llm_reviews_file` - LLM 評審結果檔案路徑（必須）
- `--human_reviews_file` - 人類評審結果檔案路徑（必須）
- `--prompt_file` - 評估提示模板檔案路徑，預設為 `prompt/evaluation_prompt.txt`
- `--output_file` - 評估結果輸出檔案路徑（若未指定，則自動生成）
- `--limit` - 要評估的提案數量上限（用於測試）

### Categorize 命令選項

- `--proposal_file` - 提案資料檔案路徑（必須）
- `--prompt_file` - 分類提示模板檔案路徑，預設為 `prompt/categorization_prompt.txt`
- `--output_file` - 輸出檔案路徑（若未指定，則自動生成）
- `--model` - LLM 模型名稱，預設為 `o3-mini`
- `--reasoning_effort` - 推理努力級別，可選 `low`、`medium`、`high`，預設為 `medium`
- `--limit` - 要處理的提案數量上限（用於測試）

### Proposal Diff 命令選項

- `--stage1_file` - Stage 1 提案檔案路徑（必須）
- `--stage2_file` - Stage 2 提案檔案路徑（必須）
- `--prompt_file` - 差異分析提示模板檔案路徑，預設為 `prompt/proposal_diff_prompt.txt`
- `--output_file` - 輸出檔案路徑（若未指定，則自動生成）
- `--model` - LLM 模型名稱，預設為 `o4-mini`
- `--reasoning_effort` - 推理努力級別，可選 `low`、`medium`、`high`，預設為 `high`
- `--translation_model` - 翻譯用 LLM 模型名稱，預設為 `gpt-4o-mini`
- `--limit` - 要處理的提案數量上限（用於測試）

## 例子

### 使用 o3-mini 模型執行 LLM 評審 (限制處理 5 筆提案)

```bash
python run_llm.py review \
  --proposal_file data/db_merged_fixed/resampled_proposals_20250404.xlsx \
  --model o3-mini \
  --reasoning_effort high \
  --limit 5
```

### 使用 o3-mini 模型評估 LLM 評審結果 (限制評估 5 筆提案)

```bash
python run_llm.py evaluate \
  --llm_reviews_file output/llm_review_o3-mini_20250404.xlsx \
  --human_reviews_file data/db_merged_fixed/reviews_20250404.xlsx \
  --model o3-mini \
  --reasoning_effort high \
  --limit 5
```

### 使用 o3-mini 模型對提案進行分類 (限制處理 5 筆提案 & reasoning_effort low 測試)
### --limit 參數的功能實際上是正常的。問題只是在 README 裡的命令示例缺少了反斜線 \。

```bash
python3 run_categorize.py \
  --proposal_file data/pycontw_2025_proposals_20250407.xlsx \
  --model o3-mini \
  --reasoning_effort medium
```

### 執行提案差異比較 (限制處理 3 筆提案用於測試)

**注意：新版本已改進效能和格式**
- 使用並發處理，大幅提升執行速度
- proposal_id 輸出為字串格式，避免 Excel 整數溢位
- 簡化 prompt 輸出，僅顯示有實際變更的內容

```bash
python3 run_proposal_diff.py \
  --stage1_file data/pycontw_2025_proposals_snapshot_20250427.xlsx \
  --stage2_file data/pycontw_2025_proposals_20250520.xlsx \
  --model o4-mini \
  --reasoning_effort high \
  --limit 3
```


### note

the api script is not working (pycon_api_client.py, notebook_api_example.py, api_test.py, simple_api_example.py)