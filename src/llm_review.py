import os
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from src.models import ProposalReview
from src import config

# Configure logging
log_file = config.LOGS_DIR / f"llm_review_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_proposal_data(file_path: str = None, limit: int = None) -> pd.DataFrame:
    """Load proposal data from Excel file"""
    if file_path is None:
        file_path = config.PROPOSAL_FILE
    
    logger.info(f"Loading proposal data from {file_path}")

    # notice if id is int, may cause overflow
    df = pd.read_excel(file_path, dtype={'id': str})
    
    # Limit the number of proposals if requested
    if limit is not None and limit > 0:
        logger.info(f"Limiting to {limit} proposals")
        df = df.head(limit)
        
    return df

def setup_llm_chain(prompt_file: str, model_name: str):
    """Set up the LLM chain with the specified prompt and model"""
    logger.info(f"Setting up LLM chain with prompt {prompt_file} and model {model_name}")
    
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    
    prompt = PromptTemplate(input_variables=['PROPOSAL_INFO'], template=prompt_template)
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    structured_llm = llm.with_structured_output(ProposalReview)
    
    return prompt | structured_llm

def process_proposals(
    proposal_df: pd.DataFrame,
    chain,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    processed_proposals: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Process proposals through the LLM chain"""
    result = []
    
    if processed_proposals is None:
        processed_proposals = set()
    else:
        processed_proposals = set(processed_proposals)
    
    for proposal_id in proposal_df.id:
        start_time = time.time()
        
        if proposal_id in processed_proposals:
            logger.info(f"Skipping already processed proposal: {proposal_id}")
            continue
            
        logger.info(f"Processing proposal: {proposal_id}")
        proposal_info = proposal_df[proposal_df.id == proposal_id][config.PROPOSAL_INFO_COLUMNS].to_dict(orient='records')[0]
        
        for attempt in range(max_retries):
            try:
                review = chain.invoke({"PROPOSAL_INFO": str(proposal_info)})
                review_dict = review.model_dump()
                review_dict['proposal_id'] = proposal_id
                result.append(review_dict)
                break
            except Exception as e:
                logger.error(f"LLM invoke failed for proposal {proposal_id} (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Max retries ({max_retries}) exceeded for proposal {proposal_id}")
                time.sleep(sleep_time)
        
        exec_time = time.time() - start_time
        logger.info(f"Execution time for proposal {proposal_id}: {exec_time:.2f} seconds\n")
    
    return result

def save_results(results: List[Dict[str, Any]], output_file: str):
    """Save results to Excel file"""
    logger.info(f"Saving {len(results)} results to {output_file}")
    df = pd.DataFrame(results)
    df['proposal_id'] = df['proposal_id'].astype(str)
    df.to_excel(output_file, index=False)
    logger.info(f"Results saved to {output_file}")

def run_llm_review(
    prompt_file: str,
    model_name: str,
    output_file: str,
    proposal_file: str = None,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    limit: int = None
):
    """Run the LLM review process end-to-end"""
    # Load proposal data
    proposal_df = load_proposal_data(proposal_file, limit)
    
    # Set up LLM chain
    chain = setup_llm_chain(prompt_file, model_name)
    
    # Process proposals
    results = process_proposals(
        proposal_df=proposal_df,
        chain=chain,
        sleep_time=sleep_time,
        max_retries=max_retries
    )
    
    # Save results
    save_results(results, output_file)
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run LLM review on PyCon proposals")
    parser.add_argument("--prompt", choices=["simple", "full"], default="full", help="Prompt type to use")
    parser.add_argument("--model", choices=["flash", "pro"], default="flash", help="Model to use")
    parser.add_argument("--output", help="Output file path (default: auto-generated based on prompt and date)")
    parser.add_argument("--proposal-file", help="Proposal file path (default: from config)")
    parser.add_argument("--sleep-time", type=int, default=config.DEFAULT_SLEEP_TIME, help="Sleep time between retries")
    parser.add_argument("--max-retries", type=int, default=config.MAX_RETRIES, help="Maximum number of retries")
    parser.add_argument("--limit", type=int, help="Limit the number of proposals to process")
    
    args = parser.parse_args()
    
    # Determine prompt file
    prompt_file = config.FULL_PROMPT_FILE if args.prompt == "full" else config.SIMPLE_PROMPT_FILE
    
    # Determine model
    model_name = config.FLASH_MODEL if args.model == "flash" else config.PRO_MODEL
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        if args.prompt == "full":
            output_file = str(config.FULL_PROMPT_OUTPUT).format(date=date_str)
        else:
            output_file = str(config.SIMPLE_PROMPT_OUTPUT).format(date=date_str)
    
    # Run LLM review
    run_llm_review(
        prompt_file=prompt_file,
        model_name=model_name,
        output_file=output_file,
        proposal_file=args.proposal_file,
        sleep_time=args.sleep_time,
        max_retries=args.max_retries,
        limit=args.limit
    ) 