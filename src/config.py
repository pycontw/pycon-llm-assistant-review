import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROMPT_DIR = BASE_DIR / "prompt"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Prompt files
SIMPLE_PROMPT_FILE = PROMPT_DIR / "simple_prompt.txt"
FULL_PROMPT_FILE = PROMPT_DIR / "full_prompt.txt"

# Model configurations
FLASH_MODEL = "gemini-2.0-flash"
PRO_MODEL = "gemini-2.0-pro-exp-02-05"

# Default settings
DEFAULT_SLEEP_TIME = 20
MAX_RETRIES = 6

# Data files
PROPOSAL_FILE = DATA_DIR / "pycon_2024_proposal.xlsx"
REVIEW_FILE = DATA_DIR / "pycon_2024_review.xlsx"
SIMPLE_PROMPT_OUTPUT = OUTPUT_DIR / "simple_prompt_gemini_flash_{date}.xlsx"
FULL_PROMPT_OUTPUT = OUTPUT_DIR / "full_prompt_gemini_flash_{date}.xlsx"
MERGED_OUTPUT = OUTPUT_DIR / "pycon_2024_proposal_with_llm_and_review_{date}.xlsx"
ANALYSIS_OUTPUT = OUTPUT_DIR / "vote_analysis_{date}.json"
ANALYSIS_REPORT = OUTPUT_DIR / "vote_analysis_{date}.txt"

# Proposal info columns to extract
PROPOSAL_INFO_COLUMNS = [
    'title',
    'abstract',
    'detailed_description',
    'outline',
    'objective'
] 