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