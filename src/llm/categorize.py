#!/usr/bin/env python3
"""
模組：將 PyCon TW 2025 提案進行分類
"""
import os
import time
import pandas as pd
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src import config

# Configure logging
log_file = config.LOGS_DIR / f"llm_categorize_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define categories mapping - Short code to full name
CATEGORYCHOICES = (
    ('APPL', 'Application'),
    ('PRAC', 'Best Practices & Patterns'),
    ('COM', 'Community'),
    ('DB', 'Databases'),
    ('DATA', 'Data Analysis'),
    ('EDU', 'Education'),
    ('EMBED', 'Embedded Systems'),
    ('FIN', 'FinTech'),
    ('IOT', 'Internet of Things'),
    ('GAME', 'Gaming'),
    ('GRAPH', 'Graphics'),
    ('ML', 'Machine Learning'),
    ('NLP', 'Natural Language Processing'),
    ('CORE', 'Python Core (language, stdlib, etc.)'),
    ('TOOL', 'Project Tooling'),
    ('SCI', 'Science'),
    ('SEC', 'Security'),
    ('ADMIN', 'Systems Administration'),
    ('TEST', 'Testing'),
    ('WEB', 'Web Frameworks'),
    ('OTHER', 'Other'),
)

# Create mapping dictionaries for easy lookup
FULL_TO_SHORT = {full: short for short, full in CATEGORYCHOICES}
SHORT_TO_FULL = {short: full for short, full in CATEGORYCHOICES}

# Function to convert full category name to short code
def full_to_short_category(full_name):
    """Convert full category name to short code"""
    return FULL_TO_SHORT.get(full_name, 'OTHER')

# Function to convert short code to full category name
def short_to_full_category(short_code):
    """Convert short code to full category name"""
    return SHORT_TO_FULL.get(short_code, 'Other')

# Original categories list (commented out, may be needed later)
# CATEGORIES = [
#     "AI/ML Fundamentals",
#     "LLM Applications & Engineering",
#     "Computer Vision & Multimodal AI",
#     "MLOps & AI Production",
#     "Natural Language Processing",
#     "Data Engineering & Analysis",
#     "Data Visualization & Analytics",
#     "Python Core & Performance",
#     "Async & Web Development",
#     "DevOps & Deployment",
#     "Libraries & Tools",
#     "Scientific Computing & Domain Applications",
#     "Application Development",
#     "Security & Ethical Development",
#     "Software Engineering & Best Practices",
#     "Open Source & Community",
#     "Others"
# ]

# Use the full names from CATEGORYCHOICES for the categorization process
CATEGORIES = [full for _, full in CATEGORYCHOICES]

class ProposalCategories(BaseModel):
    """Categories for a PyCon proposal"""
    proposal_id: str
    category1: str  # Mandatory - most relevant
    category2: Optional[str] = None  # Optional - second most relevant
    category3: Optional[str] = None  # Optional - third most relevant
    reasoning: str = Field(description="Brief reasoning for the categories")

def load_proposal_data(file_path: str = None, limit: int = None) -> pd.DataFrame:
    """Load proposal data from Excel file or DataFrame"""
    if file_path is None:
        file_path = config.PROPOSAL_FILE
    
    logger.info(f"Loading proposal data from {file_path}")

    # If file_path is already a DataFrame, use it directly
    if isinstance(file_path, pd.DataFrame):
        df = file_path
    else:
        # notice if id is int, may cause overflow
        df = pd.read_excel(file_path, dtype={'proposal_id': str})
    
    # Limit the number of proposals if requested
    if limit is not None and limit > 0:
        logger.info(f"Limiting to {limit} proposals")
        df = df.head(limit)
        
    return df

def setup_categorization_chain(prompt_file: str, model_name: str, reasoning_effort: str = "medium"):
    """Set up the LLM chain for categorization"""
    logger.info(f"Setting up categorization chain with model {model_name} and prompt {prompt_file}")
    
    # Load the prompt template from file
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    
    prompt = PromptTemplate(input_variables=['PROPOSAL_INFO', 'THINKING'], template=prompt_template)
    
    # Setup LLM
    if "o3-mini" == model_name:
        llm = ChatOpenAI(model=model_name)
    elif "gpt" in model_name.lower() or "o3" in model_name.lower() or "o4" in model_name.lower():
        print(f"Using model {model_name} with reasoning effort high")
        llm = ChatOpenAI(model=model_name, reasoning_effort="high")
    else:
        raise ValueError(f"Unsupported model type: {model_name}")
        
    structured_llm = llm.with_structured_output(ProposalCategories)
    
    return prompt | structured_llm

async def process_proposal_async(
    proposal_id: str,
    proposal_info: Dict[str, Any],
    categorization_chain,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    reasoning_effort: str = "medium"
) -> Dict[str, Any]:
    """Process a single proposal with the categorization chain"""
    logger.info(f"Processing proposal {proposal_id} for categorization")
    
    # Format the proposal info
    proposal_text = []
    for key, value in proposal_info.items():
        if pd.notna(value) and value:  # Check if value exists and is not empty
            proposal_text.append(f"{key}: {value}")
    
    formatted_info = "\n\n".join(proposal_text)
    
    # Add thinking based on reasoning effort
    if reasoning_effort == "low":
        thinking = "簡單分析提案內容，識別主要主題。"
    elif reasoning_effort == "medium":
        thinking = "分析提案標題、摘要和描述，識別主要主題和次要主題，考慮可能的重疊領域。"
    else:  # high
        thinking = "深入分析提案的所有部分，識別主要主題和次要主題，考慮技術複雜性、應用領域和目標受眾。評估每個類別的相關性程度。"
    
    # Retry mechanism
    retries = 0
    while retries <= max_retries:
        try:
            result = await categorization_chain.ainvoke({
                "PROPOSAL_INFO": formatted_info,
                "THINKING": thinking
            })
            
            # Create result dictionary
            result_dict = result.dict()
            result_dict["proposal_id"] = proposal_id
            
            return result_dict
            
        except Exception as e:
            retries += 1
            logger.error(f"Error processing proposal {proposal_id} (attempt {retries}/{max_retries}): {str(e)}")
            
            if retries <= max_retries:
                logger.info(f"Retrying in {sleep_time} seconds...")
                await asyncio.sleep(sleep_time)
            else:
                logger.error(f"Failed to process proposal {proposal_id} after {max_retries} attempts")
                return {
                    "proposal_id": proposal_id,
                    "category1": "Others",
                    "category2": None,
                    "category3": None,
                    "reasoning": f"Error: {str(e)}"
                }

async def process_proposals_async(
    proposal_df: pd.DataFrame,
    categorization_chain,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    processed_proposals: Optional[List[str]] = None,
    reasoning_effort: str = "medium"
) -> List[Dict[str, Any]]:
    """Process proposals through the categorization chain asynchronously"""
    tasks = []
    
    if processed_proposals is None:
        processed_proposals = set()
    else:
        processed_proposals = set(processed_proposals)
    
    # Create tasks for all proposals that haven't been processed yet
    for idx, row in proposal_df.iterrows():
        proposal_id = row['proposal_id']
        
        if proposal_id in processed_proposals:
            logger.info(f"Skipping already processed proposal: {proposal_id}")
            continue
            
        proposal_info = {col: row[col] for col in config.PROPOSAL_INFO_COLUMNS if col in row}
        tasks.append(process_proposal_async(
            proposal_id, 
            proposal_info, 
            categorization_chain, 
            sleep_time, 
            max_retries,
            reasoning_effort
        ))
    
    # Process all proposals in parallel
    results = []
    if tasks:
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in all_results:
            if isinstance(result, Exception):
                logger.error(f"Failed to process proposal: {result}")
            else:
                results.append(result)
    
    return results

def save_results(results: List[Dict[str, Any]], output_file: str):
    """Save categorization results to Excel file"""
    logger.info(f"Saving {len(results)} categorization results to {output_file}")
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    
    # Convert full category names to short codes for output
    if 'category1' in df.columns:
        df['category1_code'] = df['category1'].apply(lambda x: full_to_short_category(x) if pd.notna(x) else None)
        # Rename columns to keep full names for reference
        df.rename(columns={'category1': 'category1_full', 'category1_code': 'category1'}, inplace=True)
    
    if 'category2' in df.columns:
        df['category2_code'] = df['category2'].apply(lambda x: full_to_short_category(x) if pd.notna(x) else None)
        df.rename(columns={'category2': 'category2_full', 'category2_code': 'category2'}, inplace=True)
    
    if 'category3' in df.columns:
        df['category3_code'] = df['category3'].apply(lambda x: full_to_short_category(x) if pd.notna(x) else None)
        df.rename(columns={'category3': 'category3_full', 'category3_code': 'category3'}, inplace=True)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save to Excel
    df.to_excel(output_file, index=False)
    
    logger.info(f"Categorization results saved to {output_file}")
    return output_file

async def run_categorization_async(
    prompt_file: str,
    model_name: str,
    output_file: str,
    proposal_file: str = None,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    limit: int = None,
    reasoning_effort: str = "medium"
):
    """Run the categorization process end-to-end asynchronously"""
    # Load proposal data
    proposal_df = load_proposal_data(proposal_file, limit)
    
    # Set up LLM chain
    categorization_chain = setup_categorization_chain(prompt_file, model_name, reasoning_effort)
    
    # Process proposals
    results = await process_proposals_async(
        proposal_df=proposal_df,
        categorization_chain=categorization_chain,
        sleep_time=sleep_time,
        max_retries=max_retries,
        reasoning_effort=reasoning_effort
    )
    
    # Save results
    save_results(results, output_file)
    
    return output_file

def run_categorization(
    prompt_file: str = "prompt/categorization_prompt.txt",
    model_name: str = "o3-mini",
    output_file: str = None,
    proposal_file: str = None,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    limit: int = None,
    reasoning_effort: str = "medium"
):
    """Non-async wrapper for the async categorization function"""
    # If output_file is not specified, generate one
    if output_file is None:
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = config.OUTPUT_DIR / f"proposal_categories_{model_name}_{date_str}.xlsx"
    
    # If we're already in an event loop, use that
    if asyncio.get_event_loop().is_running():
        # Create a new loop for asyncio.run
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(run_categorization_async(
                prompt_file=prompt_file,
                model_name=model_name,
                output_file=str(output_file),
                proposal_file=proposal_file,
                sleep_time=sleep_time,
                max_retries=max_retries,
                limit=limit,
                reasoning_effort=reasoning_effort
            ))
        finally:
            loop.close()
    else:
        # No running event loop, safe to use asyncio.run
        return asyncio.run(run_categorization_async(
            prompt_file=prompt_file,
            model_name=model_name,
            output_file=str(output_file),
            proposal_file=proposal_file,
            sleep_time=sleep_time,
            max_retries=max_retries,
            limit=limit,
            reasoning_effort=reasoning_effort
        )) 