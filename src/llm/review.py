import os
import time
import pandas as pd
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import json

from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.models import ProposalReview, EnhancedProposalReview
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

def setup_llm_chain(prompt_file: str, model_name: str, output_model=ProposalReview):
    """Set up the LLM chain with the specified prompt and model"""
    logger.info(f"Setting up LLM chain with prompt {prompt_file} and model {model_name}")
    
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    
    prompt = PromptTemplate(input_variables=['PROPOSAL_INFO'], template=prompt_template)
    
    if "gemini" in model_name.lower():
        llm = ChatGoogleGenerativeAI(model=model_name)
    elif "gpt-4o-mini" == model_name:
        llm = ChatOpenAI(model=model_name, temperature=0)
    elif "o4" in model_name.lower() or "o3" in model_name.lower():
        llm = ChatOpenAI(model=model_name, reasoning_effort="high")
    else:
        raise ValueError(f"Unsupported model type: {model_name}")
        
    structured_llm = llm.with_structured_output(output_model)
    
    return prompt | structured_llm

def setup_translation_chain(model_name: str = "gpt-4o-mini"):
    """Set up chain for translating reviews from TC to EN"""
    logger.info(f"Setting up translation chain with model {model_name}")
    
    # Load translation prompt from file
    translation_prompt_path = config.PROMPT_DIR / "translation_prompt.txt"
    with open(translation_prompt_path, "r", encoding="utf-8") as f:
        translation_prompt_template = f.read()
    
    prompt = PromptTemplate(input_variables=['TEXT_TO_TRANSLATE'], template=translation_prompt_template)
    llm = ChatOpenAI(model=model_name, temperature=0)
    
    return prompt | llm

async def process_proposal_async(
    proposal_id: str, 
    proposal_info: Dict[str, Any],
    chain,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES
) -> Dict[str, Any]:
    """Process a single proposal asynchronously"""
    logger.info(f"Processing proposal: {proposal_id}")
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            review = await chain.ainvoke({"PROPOSAL_INFO": str(proposal_info)})
            review_dict = review.model_dump()
            review_dict['proposal_id'] = proposal_id
            
            # Add title if available in proposal_info
            if 'title' in proposal_info:
                review_dict['title'] = proposal_info['title']
            
            exec_time = time.time() - start_time
            logger.info(f"Execution time for proposal {proposal_id}: {exec_time:.2f} seconds")
            
            return review_dict
        except Exception as e:
            logger.error(f"LLM invoke failed for proposal {proposal_id} (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise Exception(f"Max retries ({max_retries}) exceeded for proposal {proposal_id}")
            await asyncio.sleep(sleep_time)

async def translate_review_async(
    review_dict: Dict[str, Any],
    translation_chain,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES
) -> Dict[str, Any]:
    """Translate a review from TC to EN asynchronously"""
    proposal_id = review_dict['proposal_id']
    logger.info(f"Translating review for proposal: {proposal_id}")
    start_time = time.time()
    
    enhanced_review = {
        "proposal_id": proposal_id,
        "vote": review_dict['vote'],
        "summary": review_dict['summary'],
        "comment": review_dict['comment'],
    }
    
    # Add title if available
    if 'title' in review_dict:
        enhanced_review['title'] = review_dict['title']
    
    logger.info(f"Processing translation for fields: {list(review_dict.keys())}")
    
    # Prepare texts to translate
    texts_to_translate = {
        "summary": enhanced_review['summary'],
        "comment": enhanced_review['comment']
    }
    
    # Translate each text
    for key, text in texts_to_translate.items():
        logger.info(f"Translating {key} for proposal {proposal_id}")
        for attempt in range(max_retries):
            try:
                translation = await translation_chain.ainvoke({"TEXT_TO_TRANSLATE": text})
                enhanced_review[f"{key}_en"] = translation.content
                logger.info(f"Successfully translated {key} for proposal {proposal_id}")
                break
            except Exception as e:
                logger.error(f"Translation failed for {key} of proposal {proposal_id} (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    enhanced_review[f"{key}_en"] = f"[Translation failed: {e}]"
                await asyncio.sleep(sleep_time)
    
    exec_time = time.time() - start_time
    logger.info(f"Translation time for proposal {proposal_id}: {exec_time:.2f} seconds")
    
    return enhanced_review

async def process_proposals_async(
    proposal_df: pd.DataFrame,
    review_chain,
    translation_chain=None,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    processed_proposals: Optional[List[str]] = None,
    with_translation: bool = True
) -> List[Dict[str, Any]]:
    """Process proposals through the LLM chain asynchronously"""
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
            review_chain, 
            sleep_time, 
            max_retries
        ))
    
    # Process all proposals in parallel without batching
    results = []
    if tasks:
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for result in all_results:
            if isinstance(result, Exception):
                logger.error(f"Failed to process proposal: {result}")
            else:
                valid_results.append(result)
        
        # Translate if needed
        if with_translation and translation_chain and valid_results:
            translation_tasks = [
                translate_review_async(review, translation_chain, sleep_time, max_retries)
                for review in valid_results
            ]
            translated_results = await asyncio.gather(*translation_tasks, return_exceptions=True)
            
            for result in translated_results:
                if isinstance(result, Exception):
                    logger.error(f"Failed to translate review: {result}")
                else:
                    results.append(result)
        else:
            results.extend(valid_results)
    
    return results

def save_results(results: List[Dict[str, Any]], output_file: str):
    """Save results to Excel file"""
    logger.info(f"Saving {len(results)} results to {output_file}")
    df = pd.DataFrame(results)
    if 'proposal_id' in df.columns:
        df['proposal_id'] = df['proposal_id'].astype(str)
    df.to_excel(output_file, index=False)
    logger.info(f"Results saved to {output_file}")

async def run_llm_review_async(
    prompt_file: str,
    model_name: str,
    output_file: str,
    proposal_file: str = None,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    limit: int = None,
    with_translation: bool = True,
    translation_model: str = "gpt-4o-mini"
):
    """Run the LLM review process end-to-end asynchronously"""
    # Load proposal data
    proposal_df = load_proposal_data(proposal_file, limit)
    
    # Set up LLM chain
    review_chain = setup_llm_chain(prompt_file, model_name, EnhancedProposalReview if with_translation else ProposalReview)
    
    # Set up translation chain if needed
    translation_chain = None
    if with_translation:
        translation_chain = setup_translation_chain(translation_model)
    
    # Process proposals
    results = await process_proposals_async(
        proposal_df=proposal_df,
        review_chain=review_chain,
        translation_chain=translation_chain,
        sleep_time=sleep_time,
        max_retries=max_retries,
        with_translation=with_translation
    )
    
    # Save results
    save_results(results, output_file)
    
    return results

def run_llm_review(
    prompt_file: str,
    model_name: str,
    output_file: str,
    proposal_file: str = None,
    sleep_time: int = config.DEFAULT_SLEEP_TIME,
    max_retries: int = config.MAX_RETRIES,
    limit: int = None,
    with_translation: bool = True,
    translation_model: str = "gpt-4o-mini"
):
    """Non-async wrapper for the async review function"""
    # If we're already in an event loop, use that
    if asyncio.get_event_loop().is_running():
        # Create a new loop for asyncio.run
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(run_llm_review_async(
                prompt_file=prompt_file,
                model_name=model_name,
                output_file=output_file,
                proposal_file=proposal_file,
                sleep_time=sleep_time,
                max_retries=max_retries,
                limit=limit,
                with_translation=with_translation,
                translation_model=translation_model
            ))
        finally:
            loop.close()
    else:
        # No running event loop, safe to use asyncio.run
        return asyncio.run(run_llm_review_async(
            prompt_file=prompt_file,
            model_name=model_name,
            output_file=output_file,
            proposal_file=proposal_file,
            sleep_time=sleep_time,
            max_retries=max_retries,
            limit=limit,
            with_translation=with_translation,
            translation_model=translation_model
        ))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run LLM review on PyCon proposals")
    parser.add_argument("--prompt", choices=["simple", "full"], default="full", help="Prompt type to use")
    parser.add_argument("--model", choices=["gemini", "gpt4o"], default="gemini", help="Model to use")
    parser.add_argument("--output", help="Output file path (default: auto-generated based on prompt and date)")
    parser.add_argument("--proposal-file", help="Proposal file path (default: from config)")
    parser.add_argument("--sleep-time", type=int, default=config.DEFAULT_SLEEP_TIME, help="Sleep time between retries")
    parser.add_argument("--max-retries", type=int, default=config.MAX_RETRIES, help="Maximum number of retries")
    parser.add_argument("--limit", type=int, help="Limit the number of proposals to process")
    parser.add_argument("--no-translation", action="store_true", help="Skip translation of reviews")
    parser.add_argument("--translation-model", default="gpt-4o-mini", help="Model to use for translation")
    
    args = parser.parse_args()
    
    # Determine prompt file
    prompt_file = config.FULL_PROMPT_FILE if args.prompt == "full" else config.SIMPLE_PROMPT_FILE
    
    # Determine model
    if args.model == "gemini":
        model_name = config.FLASH_MODEL
    elif args.model == "gpt4o":
        model_name = "gpt-4o"
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        effort_level = "full" if args.prompt == "full" else "simple"
        model_short = args.model
        output_file = os.path.join(str(config.DATA_DIR), f"{effort_level}_{model_short}_{date_str}.xlsx")
    
    # Run LLM review
    run_llm_review(
        prompt_file=prompt_file,
        model_name=model_name,
        output_file=output_file,
        proposal_file=args.proposal_file,
        sleep_time=args.sleep_time,
        max_retries=args.max_retries,
        limit=args.limit,
        with_translation=not args.no_translation,
        translation_model=args.translation_model
    ) 