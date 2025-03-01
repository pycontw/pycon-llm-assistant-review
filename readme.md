# PyCon TW Proposal Review Assistant

This project aims to develop an LLM-powered system to assist in the review process of PyCon Taiwan conference proposals. The system helps review assistance to reviewers.

## Project Goals
1. Assist human reviewers by providing AI-generated preliminary reviews
2. Validate the effectiveness of LLM-based review assistance

## Setup

### Prerequisites
- Python 3.11+
- Access to Google's Gemini API

### Required Packages
```
langchain
langchain-google-genai
pandas
numpy
jupyter
python-dotenv
openpyxl  # for Excel file handling
pydantic  # for data validation and parsing
```

### Environment Setup
1. Clone this repository
2. Create a `.env` file with your API keys:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

3. Install packages

## Project Structure
```
.
├── data/                   # Data files (stored in organization drive for privacy)
│   ├── pycon_2024_proposal.xlsx     # Raw proposal data
│   ├── pycon_2024_review.xlsx       # Human review data
│   └── *_prompt_gemini_*.xlsx       # LLM review results
├── prompt/                 # LLM prompt templates
│   ├── full_prompt.txt    # Detailed review prompt
│   └── simple_prompt.txt  # Basic review prompt
├── llm_review_v2.ipynb   # Main LLM review notebook
├── merge_llm_and_reviews.ipynb  # Analysis notebook
└── README.md
```

## Implementation Details

### LLM Review Process
1. **Model**: Using Gemini Flash (gemini-2.0-flash-exp)
2. **Review Format**:
   ```python
   class ProposalReview(BaseModel):
       summary: str
       comment: str
       vote: Literal['+1', '+0', '-0', '-1']
   ```

### Analysis Results (2025-02-17)

#### 1. Vote Distribution

| Vote Type | Human Reviews | Simple Prompt | Complete Prompt |
|-----------|--------------|---------------|-----------------|
| +0        | 62.3%       | 75.3%         | 85.7%          |
| +1        | 18.2%       | 22.1%         | 10.4%          |
| -0        | 15.6%       | 1.3%          | 3.9%           |
| -1        | 3.9%        | 1.3%          | 0%             |

#### 2. Agreement Rates
- Simple Prompt: 59.7%
- Complete Prompt: 55.8%

#### 3. Confusion Matrices

Simple Prompt Agreement Analysis:
```
vote_most_common_vote  +0  +1  -0  -1  All
LLM_vote                                  
+0                     38   8  10   2   58
+1                     10   6   1   0   17
-0                      0   0   1   0    1
-1                      0   0   0   1    1
All                    48  14  12   3   77
```

Complete Prompt Agreement Analysis:
```
vote_most_common_vote  +0  +1  -0  -1  All
LLM_vote                                  
+0                     41  13  11   1   66
+1                      7   1   0   0    8
-0                      0   0   1   2    3
All                    48  14  12   3   77
```

### Key Findings
1. Conservative Tendency:
   - All evaluation methods tend to give neutral ratings (+0)
   - Complete Prompt shows extremely conservative behavior (85.7% +0)
   - Human reviews show more balanced distribution

2. Model Performance:
   - Simple Prompt Agreement Rate: 59.7%
   - Complete Prompt Agreement Rate: 55.8%
   - Confusion matrices show both models tend to be more conservative than human reviewers
   - Simple prompt shows slightly better agreement with human reviewers
   - Limited negative vote prediction
   - Need for better calibration with human reviewers

## TODO
### first priority
- [ ] Gather more negative reviews (-1) before 2024 PyCon TW
- [ ] Check the red line principle
### second priority
- [ ] Test other LLM models:
  - Gemini Pro 1.5 / 2
  - Claude 3 Haiku
  - GPT-4 Mini
- [ ] LLM result 中英文 translation
- [ ] LLM-as-a-Judge: evaluate review alignment

## References
1. [Gemini API Documentation](https://ai.google.dev/gemini-api/docs/models/experimental-models?hl=zh-tw)
2. [LLM as a Judge: 用語言模型來評估好壞](https://ywctech.net/ml-ai/paper-llm-as-a-judge/)

## Contributing
Contributions are welcome! Please:
1. Open issues for bugs or feature requests
2. Submit pull requests with improvements
3. Help improve documentation
4. Share insights about the review process

## Dislike features of proposal

summary from claude 3.7 Sonnet thinking mode, from -1 review portion over 25% on single proposal

不好稿件的共同特徵分析
根據提供的審查過程中被拒絕或評價不佳的稿件，歸納出以下幾個明顯的問題特徵：

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