# PyCon TW 2025 Proposal Review Assistant

This project aims to develop an LLM-based system to assist in the review process of PyCon Taiwan conference proposals. The system provides AI-generated preliminary reviews to support human reviewers.

## Project Goals

1. Assist human reviewers by providing AI-generated preliminary reviews
2. Validate the effectiveness of LLM-based review assistance
3. Integrate human review and LLM review data for comparative analysis

## Data Source

Currently, the data source is from the Metabase, and the file is exported as an Excel file.
The data is stored in the Google Drive, and the file is shared with the team members.

## Project Structure

```
.
├── src/                     # Source code directory
│   ├── __init__.py          # Python package initialization file
│   ├── config.py            # Configuration file with paths and settings
│   ├── models.py            # Data model definitions
│   ├── llm_review.py        # LLM review functionality
│   ├── merge_data.py        # Data merging and analysis functionality
│   └── main.py              # Main program entry point
├── data/                    # Data directory (sample data or test data)
├── output/                  # Output directory
│   ├── simple_prompt_gemini_flash_*.xlsx    # LLM review results using simple prompt
│   ├── full_prompt_gemini_flash_*.xlsx      # LLM review results using full prompt
│   ├── pycon_2024_proposal_with_llm_and_review_*.xlsx  # Merged data
│   ├── vote_analysis_*.json                 # Vote analysis results (JSON format)
│   └── vote_analysis_*.txt                  # Vote analysis report (human-readable format)
├── logs/                    # Log directory
│   ├── llm_review_*.log     # LLM review logs
│   ├── merge_data_*.log     # Data merging logs
│   └── main_*.log           # Main program logs
├── prompt/                  # Prompt directory
│   ├── simple_prompt.txt    # Simple prompt template
│   └── full_prompt.txt      # Full prompt template
└── run.py                   # Entry point script
```

## Installation Dependencies

```bash
pip install pandas langchain-core langchain-google-genai python-dotenv openpyxl pydantic jupyter numpy
```

## Environment Variables Setup

Create a `.env` file in the project root directory and set the following environment variables:

```
GOOGLE_API_KEY=your_google_api_key_here
```

## Usage

### Main Program

The entry point script `run.py` provides a complete workflow for running LLM reviews, data merging, and analysis.

```bash
# Run the complete workflow (LLM review + data merging and analysis)
python run.py

# Only run LLM review
python run.py --mode review

# Only run data merging and analysis
python run.py --mode merge

# Use simple prompt
python run.py --prompt simple

# Use full prompt
python run.py --prompt full

# Use both prompts
python run.py --prompt both

# Use different model
python run.py --model pro

# Specify output directory
python run.py --output-dir ./output

# Skip analysis
python run.py --no-analyze
```

### Using LLM Review Functionality Separately

```bash
python -m src.llm_review --prompt simple --model flash
```

### Using Data Merging Functionality Separately

```bash
python -m src.merge_data --simple-llm-file output/simple_prompt_gemini_flash_YYYYMMDD.xlsx --complete-llm-file output/full_prompt_gemini_flash_YYYYMMDD.xlsx
```

## Output File Description

### LLM Review Results

LLM review results are saved in Excel files in the `output/` directory:

- `simple_prompt_gemini_flash_*.xlsx`: LLM review results using simple prompt
- `full_prompt_gemini_flash_*.xlsx`: LLM review results using full prompt

These files contain the following columns:
- `proposal_id`: Proposal ID
- `summary`: Proposal summary
- `comment`: Review comments
- `vote`: Voting result (-1, -0, +0, +1)

### Merged Data

Merged data is saved in the `output/pycon_2024_proposal_with_llm_and_review_*.xlsx` file, containing proposal data, human review data, and LLM review data.

### Analysis Results

Analysis results are saved in two formats:

1. JSON format (`output/vote_analysis_*.json`): Contains complete analysis results, suitable for programmatic reading and further processing.

2. Text report (`output/vote_analysis_*.txt`): Human-readable analysis report, including:
   - LLM vote distribution
   - Human review vote distribution
   - Consistency rate between LLM and human reviews
   - Confusion matrix

These analysis results help evaluate the effectiveness of LLM reviews and compare them with human reviews.

## Implementation Details

### LLM Review Process
1. **Model**: Using Gemini Flash (gemini-2.0-flash)
2. **Review Format**:
   ```python
   class ProposalReview(BaseModel):
       summary: str
       comment: str
       vote: Literal['+1', '+0', '-0', '-1']
   ```

### Analysis Results Example

#### 1. Vote Distribution Comparison

| Vote Type | Human Reviews | Simple Prompt | Full Prompt |
|-----------|---------------|---------------|-------------|
| +0        | 62.3%         | 75.3%         | 85.7%       |
| +1        | 18.2%         | 22.1%         | 10.4%       |
| -0        | 15.6%         | 1.3%          | 3.9%        |
| -1        | 3.9%          | 1.3%          | 0%          |

#### 2. Consistency Rates
- Simple Prompt: 59.7%
- Full Prompt: 55.8%

#### 3. Confusion Matrix Examples

Simple Prompt Agreement Analysis:
```
Human Reviews  +0  +1  -0  -1  All
LLM Vote                      
+0            38   8  10   2   58
+1            10   6   1   0   17
-0             0   0   1   0    1
-1             0   0   0   1    1
All           48  14  12   3   77
```

Full Prompt Agreement Analysis:
```
Human Reviews  +0  +1  -0  -1  All
LLM Vote                       
+0            41  13  11   1   66
+1             7   1   0   0    8
-0             0   0   1   2    3
All           48  14  12   3   77
```

### Key Findings

1. Conservative Tendency:
   - All evaluation methods tend to give neutral ratings (+0)
   - Full prompt shows extremely conservative behavior (85.7% +0)
   - Human reviews show more balanced distribution

2. Model Performance:
   - Simple Prompt Agreement Rate: 59.7%
   - Full Prompt Agreement Rate: 55.8%
   - Confusion matrices show both models tend to be more conservative than human reviewers
   - Simple prompt shows slightly better agreement with human reviewers
   - Limited capability for negative vote prediction
   - Need for better calibration with human reviewers

## Common Problems in Rejected Proposals

Based on data collected during the review process, we found that unsuitable proposals often have the following characteristics:

1. **Insufficient or Overly Brief Information**
   - Only provides a title, lacking summary, outline, or objectives
   - Vague outline, making it difficult to judge content quality
   - No time allocation for the presentation
   - Merely copying and pasting the same content into different fields

2. **Insufficient Relevance to Python**
   - Topic has weak or no connection to the Python language or ecosystem
   - More suitable for other technical conferences
   - Fails to explain why the topic should be shared at a Python conference

3. **Lack of Depth and Originality**
   - Numerous similar tutorials already available online, offering no novel insights
   - Basic tutorial content without advanced applications
   - Unable to provide value beyond basic tutorials in the limited time

4. **Inappropriate Topic Scope**
   - Too broad, attempting to cover too many topics in a short time
   - Topic too vague, lacking specific content and clear focus
   - Not considering how much information the audience can digest in limited time

5. **Lack of Practical Cases and Application Scenarios**
   - Missing practical application cases or usage scenarios
   - Not demonstrating how to solve real problems
   - Failing to clearly explain the practical value of the technology to the audience

6. **Too Commercial or Promotional**
   - Focused on product or service promotion, lacking technical depth
   - Content resembling an advertisement rather than technical sharing
   - Failing to provide neutral technical insights

7. **Unclear Target Audience and Expected Outcomes**
   - Not clearly defining the target audience
   - Not explaining what value or skills the audience will gain from the presentation
   - Unclear or inconsistent description of the required background knowledge

8. **Structural and Organizational Issues**
   - Proposal content doesn't match the title
   - Lack of consistency or logical coherence between sections
   - Obvious spelling or grammatical errors, showing insufficient preparation

9. **Timeliness Issues**
   - Topic is outdated or lacks innovation
   - Discussing technology that has been widely explored without providing new perspectives
   - Failing to reflect current technology trends or industry developments

These problem characteristics are often interrelated, and a poor proposal typically exhibits multiple issues.

## TODO

### High Priority
- Optimize the LLM review system to improve consistency
- Improve analysis methods to provide more useful metrics
- Add more model comparison tests

### Medium Priority
- Test other LLM models:
  - Gemini Pro 1.5 / 2
  - Claude 3 Haiku
  - GPT-4 Mini
- LLM result English-Chinese translation functionality
- LLM-as-a-Judge: Evaluate review alignment

## Extension Suggestions

1. Add more analysis metrics, such as Cohen's Kappa coefficient to evaluate review consistency.

2. Implement visualization features to generate charts and reports of review results.

3. Add support for more LLM models, such as OpenAI's GPT models.

## Contributing

Contributions are welcome! Please:
1. Open issues for bugs or feature requests
2. Submit pull requests with improvements
3. Help improve documentation
4. Share insights about the review process

## Privacy and Security Considerations

This project involves proposal review data. Please note:

1. **Do Not Upload Real Proposal Data**:
   - Use anonymized or hypothetical data for testing
   - If using real data, ensure you have authorization and properly anonymize it

2. **Protect API Keys**:
   - Do not commit the `.env` file to public repositories
   - Rotate API keys regularly
   - Use environment variables instead of hardcoding keys

3. **Output Data Handling**:
   - Do not share analysis results containing sensitive information in public
   - Check and remove any personally identifiable information before sharing results

## References

1. [Gemini API Documentation](https://ai.google.dev/gemini-api/docs/models/experimental-models?hl=en)
2. [LLM as a Judge: Using Language Models to Evaluate Quality](https://ywctech.net/ml-ai/paper-llm-as-a-judge/)