import os
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, Any, Optional, Tuple
from collections import Counter

from src import config

# Configure logging
log_file = config.LOGS_DIR / f"merge_data_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_data(
    proposal_file: str = None,
    review_file: str = None,
    simple_llm_file: str = None,
    complete_llm_file: str = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all necessary data files"""
    logger.info("Loading data files")
    
    # Set default file paths if not provided
    if proposal_file is None:
        proposal_file = config.PROPOSAL_FILE
    if review_file is None:
        review_file = config.REVIEW_FILE
    
    # Load proposal and review data
    proposal_df = pd.read_excel(proposal_file, dtype={'id': str})
    vote_df = pd.read_excel(review_file, dtype={'vote': str, 'proposal_id': str})
    vote_df['vote_int'] = vote_df['vote'].astype(int)
    
    # Load LLM data if provided
    simple_df = None
    if simple_llm_file:
        simple_df = pd.read_excel(simple_llm_file, dtype={'vote': str, 'proposal_id': str})
    
    complete_df = None
    if complete_llm_file:
        complete_df = pd.read_excel(complete_llm_file, dtype={'vote': str, 'proposal_id': str})
    
    return proposal_df, vote_df, simple_df, complete_df

def calculate_vote_statistics(vote_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate vote statistics for each proposal"""
    logger.info("Calculating vote statistics")
    
    vote_stats = vote_df.groupby('proposal_id', as_index=False).agg({
        'vote': [
            ('most_common_vote', lambda x: x.mode().iloc[0] if not x.empty else None),
            ('vote_counts', lambda x: x.value_counts().to_dict())
        ],
        'vote_int': [
            ('mean', 'mean'),
            ('std', 'std'),
            ('count', 'count'),
            ('median', 'median')
        ]
    })
    
    # Flatten column names
    vote_stats.columns = ['proposal_id' if col[0] == 'proposal_id' 
                         else f'{col[0]}_{col[1]}' for col in vote_stats.columns]
    
    return vote_stats

def merge_data(
    proposal_df: pd.DataFrame,
    vote_stats: pd.DataFrame,
    simple_df: Optional[pd.DataFrame] = None,
    complete_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """Merge all data into a single DataFrame"""
    logger.info("Merging data")
    
    # Merge proposal data with vote statistics
    final_df = proposal_df.merge(vote_stats, left_on='id', right_on='proposal_id', how='left')
    
    # Merge with LLM data if provided
    if simple_df is not None:
        final_df = final_df.merge(
            simple_df, 
            left_on='id', 
            right_on='proposal_id', 
            how='left',
            suffixes=('', '_simple')
        )
    
    if complete_df is not None:
        final_df = final_df.merge(
            complete_df, 
            left_on='id', 
            right_on='proposal_id', 
            how='left',
            suffixes=('', '_complete')
        )
    
    # Add human evaluation column
    final_df['human_eval'] = ''
    
    return final_df

def analyze_vote_distribution(merged_df: pd.DataFrame, llm_vote_column: str = 'vote') -> Dict[str, Any]:
    """Analyze vote distribution and agreement between human and LLM votes"""
    logger.info("Analyzing vote distribution")
    
    # Check if the required columns exist
    if llm_vote_column not in merged_df.columns or 'vote_most_common_vote' not in merged_df.columns:
        logger.error(f"Required columns not found: {llm_vote_column} or vote_most_common_vote")
        logger.info(f"Available columns: {merged_df.columns.tolist()}")
        return {}
    
    # LLM votes distribution
    llm_distribution = merged_df[llm_vote_column].value_counts(normalize=True).round(3).to_dict()
    
    # Human votes distribution
    human_distribution = merged_df['vote_most_common_vote'].value_counts(normalize=True).round(3).to_dict()
    
    # Vote agreement analysis
    agreement = (merged_df[llm_vote_column] == merged_df['vote_most_common_vote'])
    agreement_rate = agreement.mean()
    
    # Confusion matrix
    confusion_matrix = pd.crosstab(
        merged_df[llm_vote_column], 
        merged_df['vote_most_common_vote'],
        margins=True
    ).to_dict()
    
    return {
        'llm_distribution': llm_distribution,
        'human_distribution': human_distribution,
        'agreement_rate': agreement_rate,
        'confusion_matrix': confusion_matrix
    }

def run_merge_and_analyze(
    output_file: str = None,
    proposal_file: str = None,
    review_file: str = None,
    simple_llm_file: str = None,
    complete_llm_file: str = None,
    analyze: bool = True,
    analysis_output_file: str = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Run the full merge and analysis process"""
    # Load data
    proposal_df, vote_df, simple_df, complete_df = load_data(
        proposal_file, review_file, simple_llm_file, complete_llm_file
    )
    
    # Calculate vote statistics
    vote_stats = calculate_vote_statistics(vote_df)
    
    # Merge data
    merged_df = merge_data(proposal_df, vote_stats, simple_df, complete_df)
    
    # Save merged data if output file is provided
    if output_file:
        logger.info(f"Saving merged data to {output_file}")
        merged_df.to_excel(output_file, index=False)
    
    # Analyze vote distribution if requested
    analysis_results = {}
    if analyze:
        if simple_df is not None:
            # 注意：在合併後的 merged_df 中，列名已經是 'vote'，而不是 'vote_x' 或其他
            # 因此我們需要確保分析函數使用正確的列名
            logger.info(f"Merged DataFrame columns: {merged_df.columns.tolist()}")
            
            # 直接使用 merged_df 進行分析，而不是再次合併
            simple_analysis = analyze_vote_distribution(merged_df, llm_vote_column='vote')
            analysis_results['simple'] = simple_analysis
        
        if complete_df is not None:
            # 直接使用 merged_df 進行分析，使用 vote_complete 列
            complete_analysis = analyze_vote_distribution(merged_df, llm_vote_column='vote_complete')
            analysis_results['complete'] = complete_analysis
        
        # 保存分析結果到 JSON 文件
        if analysis_results and analysis_output_file:
            import json
            logger.info(f"Saving analysis results to {analysis_output_file}")
            with open(analysis_output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, indent=4, ensure_ascii=False)
                
            # 同時生成人類可讀的文本報告
            report_file = os.path.splitext(analysis_output_file)[0] + '.txt'
            logger.info(f"Saving analysis report to {report_file}")
            with open(report_file, 'w', encoding='utf-8') as f:
                for prompt_type, results in analysis_results.items():
                    f.write(f"\n=== {prompt_type.capitalize()} Prompt Analysis ===\n")
                    
                    if not results:  # 檢查結果是否為空
                        f.write("No analysis results available.\n")
                        continue
                        
                    f.write("\nLLM Vote Distribution:\n")
                    for vote, proportion in results.get('llm_distribution', {}).items():
                        f.write(f"{vote}: {proportion:.3f}\n")
                    
                    f.write("\nHuman Vote Distribution:\n")
                    for vote, proportion in results.get('human_distribution', {}).items():
                        f.write(f"{vote}: {proportion:.3f}\n")
                    
                    if 'agreement_rate' in results:
                        f.write(f"\nOverall Agreement Rate: {results['agreement_rate']:.3f}\n")
                    
                    if 'confusion_matrix' in results:
                        f.write("\nConfusion Matrix:\n")
                        confusion_df = pd.DataFrame(results['confusion_matrix'])
                        f.write(confusion_df.to_string())
                        f.write("\n\n")
    
    return merged_df, analysis_results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Merge proposal, review, and LLM data")
    parser.add_argument("--output", help="Output file path (default: auto-generated based on date)")
    parser.add_argument("--proposal-file", help="Proposal file path (default: from config)")
    parser.add_argument("--review-file", help="Review file path (default: from config)")
    parser.add_argument("--simple-llm-file", help="Simple LLM review file path")
    parser.add_argument("--complete-llm-file", help="Complete LLM review file path")
    parser.add_argument("--no-analyze", action="store_true", help="Skip vote distribution analysis")
    parser.add_argument("--analysis-output", help="Analysis output file path (default: auto-generated based on date)")
    
    args = parser.parse_args()
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = str(config.MERGED_OUTPUT).format(date=date_str)
    
    # Determine analysis output file
    if args.analysis_output:
        analysis_output_file = args.analysis_output
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        analysis_output_file = str(config.OUTPUT_DIR / f"vote_analysis_{date_str}.json")
    
    # Run merge and analysis
    merged_df, analysis_results = run_merge_and_analyze(
        output_file=output_file,
        proposal_file=args.proposal_file,
        review_file=args.review_file,
        simple_llm_file=args.simple_llm_file,
        complete_llm_file=args.complete_llm_file,
        analyze=not args.no_analyze,
        analysis_output_file=analysis_output_file if not args.no_analyze else None
    )
    
    # Print analysis results
    if analysis_results and not args.no_analyze:
        print(f"\nAnalysis results saved to {analysis_output_file}")
        print(f"Analysis report saved to {os.path.splitext(analysis_output_file)[0] + '.txt'}")
        
        for prompt_type, results in analysis_results.items():
            print(f"\n=== {prompt_type.capitalize()} Prompt Analysis ===")
            
            if not results:  # 檢查結果是否為空
                print("No analysis results available.")
                continue
                
            print("\nLLM Vote Distribution:")
            for vote, proportion in results.get('llm_distribution', {}).items():
                print(f"{vote}: {proportion:.3f}")
            
            print("\nHuman Vote Distribution:")
            for vote, proportion in results.get('human_distribution', {}).items():
                print(f"{vote}: {proportion:.3f}")
            
            if 'agreement_rate' in results:
                print(f"\nOverall Agreement Rate: {results['agreement_rate']:.3f}")
            
            if 'confusion_matrix' in results:
                print("\nConfusion Matrix:")
                confusion_df = pd.DataFrame(results['confusion_matrix'])
                print(confusion_df) 