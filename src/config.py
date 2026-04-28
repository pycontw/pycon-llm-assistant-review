import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROMPT_DIR = BASE_DIR / "prompt"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Prompt files
SIMPLE_PROMPT_FILE = PROMPT_DIR / "simple_prompt.txt"
FULL_PROMPT_FILE = PROMPT_DIR / "full_prompt.txt"

# Model configurations
FLASH_MODEL = "gemini-2.0-flash" # Google Gemini model
PRO_MODEL = "gemini-2.0-pro-exp-02-05" # Google Gemini model
GPT4O_MODEL = "gpt-4o" # OpenAI GPT-4o model
GPT4O_MINI_MODEL = "gpt-4o-mini" # OpenAI GPT-4o-mini model

# Retry and timeout configurations
DEFAULT_SLEEP_TIME = 20
MAX_RETRIES = 6

# Get date string for file naming
DATE_STR = datetime.now().strftime("%Y%m%d")

# Data files
PROPOSAL_FILE = DATA_DIR / "pycon_2024_proposal.xlsx"
REVIEW_FILE = DATA_DIR / "pycon_2024_review.xlsx"

# Output file templates
def get_output_filename(prompt_type, model_name, with_date=True):
    """Generate output filename based on prompt type and model name"""
    date_suffix = f"_{DATE_STR}" if with_date else ""
    return f"{prompt_type}_{model_name}{date_suffix}.xlsx"

# Output files for enhanced evaluation
RESAMPLED_PROPOSALS = DATA_DIR / f"resampled_proposals_{DATE_STR}.xlsx"
RESAMPLED_PROPOSALS_COMMENTS = DATA_DIR / f"resampled_proposals_{DATE_STR}_comments.xlsx"
ENHANCED_EVALUATION = DATA_DIR / f"enhanced_evaluation_{DATE_STR}.xlsx"

# Analysis files
ANALYSIS_OUTPUT = OUTPUT_DIR / f"vote_analysis_{DATE_STR}.json"
ANALYSIS_REPORT = OUTPUT_DIR / f"vote_analysis_{DATE_STR}.txt"

# Proposal info columns to extract
PROPOSAL_INFO_COLUMNS = [
    'title',
    'abstract',
    'detailed_description',
    'outline',
    'objective'
]

# Metabase API configuration
METABASE_URL = os.getenv("METABASE_URL")
METABASE_USERNAME = os.getenv("METABASE_USERNAME")
METABASE_PASSWORD = os.getenv("METABASE_PASSWORD")
METABASE_DATABASE_ID = 12
# LLM API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") 