#!/usr/bin/env python3
import os
import argparse
from datetime import datetime
import logging

from src.llm_review import run_llm_review
from src.merge_data import run_merge_and_analyze
from src import config

# Configure logging
log_file = config.LOGS_DIR / f"main_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="PyCon Proposal Review Pipeline")
    
    # Main operation mode
    parser.add_argument("--mode", choices=["review", "merge", "full"], default="full",
                        help="Operation mode: review (LLM review only), merge (merge data only), or full (both)")
    
    # LLM review options
    parser.add_argument("--prompt", choices=["simple", "full", "both"], default="full",
                        help="Prompt type to use for LLM review")
    parser.add_argument("--model", choices=["flash", "pro"], default="flash",
                        help="Model to use for LLM review")
    
    # File paths
    parser.add_argument("--proposal-file", help="Proposal file path (default: from config)")
    parser.add_argument("--review-file", help="Review file path (default: from config)")
    parser.add_argument("--output-dir", help="Output directory (default: data/)")
    parser.add_argument("--simple-llm-file", help="Simple LLM review file path (required for merge mode)")
    parser.add_argument("--complete-llm-file", help="Complete LLM review file path (required for merge mode)")
    
    # Other options
    parser.add_argument("--sleep-time", type=int, default=config.DEFAULT_SLEEP_TIME,
                        help="Sleep time between retries")
    parser.add_argument("--max-retries", type=int, default=config.MAX_RETRIES,
                        help="Maximum number of retries")
    parser.add_argument("--no-analyze", action="store_true",
                        help="Skip vote distribution analysis")
    parser.add_argument("--limit", type=int, help="Limit the number of proposals to process")
    
    return parser.parse_args()

def main():
    """Main function to run the pipeline"""
    args = parse_args()
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Determine output directory
    output_dir = args.output_dir if args.output_dir else str(config.DATA_DIR)
    os.makedirs(output_dir, exist_ok=True)
    
    # File paths
    simple_output = None
    complete_output = None
    merged_output = os.path.join(output_dir, f"pycon_2024_proposal_with_llm_and_review_{date_str}.xlsx")
    analysis_output = os.path.join(output_dir, f"vote_analysis_{date_str}.json")
    
    # Run LLM review if requested
    if args.mode in ["review", "full"]:
        logger.info("Running LLM review")
        
        # Determine which prompts to use
        run_simple = args.prompt in ["simple", "both"]
        run_complete = args.prompt in ["full", "both"]
        
        # Run simple prompt if requested
        if run_simple:
            simple_output = os.path.join(output_dir, f"simple_prompt_gemini_{args.model}_{date_str}.xlsx")
            logger.info(f"Running simple prompt review with output to {simple_output}")
            
            run_llm_review(
                prompt_file=str(config.SIMPLE_PROMPT_FILE),
                model_name=config.FLASH_MODEL if args.model == "flash" else config.PRO_MODEL,
                output_file=simple_output,
                proposal_file=args.proposal_file,
                sleep_time=args.sleep_time,
                max_retries=args.max_retries,
                limit=args.limit
            )
        
        # Run complete prompt if requested
        if run_complete:
            complete_output = os.path.join(output_dir, f"full_prompt_gemini_{args.model}_{date_str}.xlsx")
            logger.info(f"Running complete prompt review with output to {complete_output}")
            
            run_llm_review(
                prompt_file=str(config.FULL_PROMPT_FILE),
                model_name=config.FLASH_MODEL if args.model == "flash" else config.PRO_MODEL,
                output_file=complete_output,
                proposal_file=args.proposal_file,
                sleep_time=args.sleep_time,
                max_retries=args.max_retries,
                limit=args.limit
            )
    
    # Run merge and analysis if requested
    if args.mode in ["merge", "full"]:
        logger.info("Running data merge and analysis")
        
        # If we're in merge-only mode, we need to get the LLM output files from arguments
        if args.mode == "merge":
            if args.simple_llm_file:
                simple_output = args.simple_llm_file
            if args.complete_llm_file:
                complete_output = args.complete_llm_file
            
            # 在 merge 模式下，如果沒有提供 LLM 檔案，則提示用戶
            if args.prompt in ["simple", "both"] and not simple_output:
                logger.error("Simple LLM file is required for merge mode with simple prompt. Use --simple-llm-file to specify.")
                return
            
            if args.prompt in ["full", "both"] and not complete_output:
                logger.error("Complete LLM file is required for merge mode with full prompt. Use --complete-llm-file to specify.")
                return
        
        # Run merge and analysis
        merged_df, analysis_results = run_merge_and_analyze(
            output_file=merged_output,
            proposal_file=args.proposal_file,
            review_file=args.review_file,
            simple_llm_file=simple_output,
            complete_llm_file=complete_output,
            analyze=not args.no_analyze,
            analysis_output_file=analysis_output if not args.no_analyze else None
        )
        
        logger.info(f"Merged data saved to {merged_output}")
        if not args.no_analyze and analysis_results:
            logger.info(f"Analysis results saved to {analysis_output}")
            logger.info(f"Analysis report saved to {os.path.splitext(analysis_output)[0] + '.txt'}")

if __name__ == "__main__":
    main() 