"""
LLM Review Evaluator - Compares LLM reviews with human reviews and evaluates their quality
"""
import os
import json
import logging
import pandas as pd
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 修正為正確的導入路徑
from src.llm.client import OpenAIClient
from src import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

class ReviewEvaluator:
    """Evaluates LLM reviews by comparing them with human reviews"""
    
    def __init__(self, llm_reviews_file: str, human_reviews_file: str, prompt_file: str, model_name: str = "o3-mini", reasoning_effort: str = "high"):
        """
        Initialize the evaluator with the reviews and model configuration
        
        Args:
            llm_reviews_file: Path to the LLM reviews file (Excel/CSV)
            human_reviews_file: Path to the human reviews file (Excel/CSV)
            prompt_file: Path to the evaluation prompt template
            model_name: LLM model to use for evaluation
            reasoning_effort: Reasoning effort level for OpenAI models
        """
        self.llm_reviews_file = llm_reviews_file
        self.human_reviews_file = human_reviews_file
        self.prompt_file = prompt_file
        self.model_name = model_name
        self.reasoning_effort = reasoning_effort
        
        # Initialize the LLM client for evaluation
        self.llm_client = OpenAIClient(model=model_name, reasoning_effort=reasoning_effort)
        
        # Load prompt template
        with open(prompt_file, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()
            
        # Initialize dataframes as None
        self.llm_df = None
        self.human_df = None
        self.merged_df = None
        self.evaluation_results = []
        
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load LLM and human reviews data
        
        Returns:
            Tuple of LLM reviews DataFrame and human reviews DataFrame
        """
        logger.info(f"Loading LLM reviews from {self.llm_reviews_file}")
        
        # Determine file type and load accordingly
        if self.llm_reviews_file.endswith('.csv'):
            self.llm_df = pd.read_csv(self.llm_reviews_file)
        else:  # Assume Excel
            self.llm_df = pd.read_excel(self.llm_reviews_file)
            
        logger.info(f"Loading human reviews from {self.human_reviews_file}")
        if self.human_reviews_file.endswith('.csv'):
            self.human_df = pd.read_csv(self.human_reviews_file)
        else:  # Assume Excel
            self.human_df = pd.read_excel(self.human_reviews_file)
            
        # Ensure proposal_id is string type
        if 'proposal_id' in self.llm_df.columns:
            self.llm_df['proposal_id'] = self.llm_df['proposal_id'].astype(str)
        if 'proposal_id' in self.human_df.columns:
            self.human_df['proposal_id'] = self.human_df['proposal_id'].astype(str)
            
        return self.llm_df, self.human_df
    
    def merge_reviews(self) -> pd.DataFrame:
        """
        Merge LLM and human reviews on proposal_id
        
        Returns:
            Merged DataFrame with both LLM and human reviews
        """
        if self.llm_df is None or self.human_df is None:
            self.load_data()
            
        logger.info("Merging LLM and human reviews")
        
        # Determine the correct merge columns based on available columns
        llm_id_col = 'proposal_id' if 'proposal_id' in self.llm_df.columns else 'id'
        human_id_col = 'proposal_id' if 'proposal_id' in self.human_df.columns else 'id'
        
        # Merge the dataframes
        self.merged_df = pd.merge(
            self.llm_df, 
            self.human_df,
            left_on=llm_id_col,
            right_on=human_id_col,
            suffixes=('_llm', '_human'),
            how='inner'
        )
        
        # Calculate vote difference if vote columns exist
        if 'vote_llm' in self.merged_df.columns and 'vote_human' in self.merged_df.columns:
            self.merged_df['vote_diff'] = self.merged_df['vote_llm'] - self.merged_df['vote_human']
            
        logger.info(f"Merged dataset contains {len(self.merged_df)} proposals")
        return self.merged_df
    
    def prepare_evaluation_data(self, proposal_row: pd.Series) -> Dict[str, Any]:
        """
        Prepare evaluation data for a single proposal
        
        Args:
            proposal_row: Row from the merged DataFrame containing both LLM and human reviews
            
        Returns:
            Dictionary with formatted evaluation data
        """
        proposal_id = proposal_row['proposal_id_llm'] if 'proposal_id_llm' in proposal_row else proposal_row['proposal_id']
        
        # Extract LLM review data
        llm_review = {
            "vote": proposal_row.get('vote_llm', ''),
            "summary": proposal_row.get('summary_tc', proposal_row.get('summary_llm', '')),
            "comment": proposal_row.get('comment_tc', proposal_row.get('comment_llm', ''))
        }
        
        # Add advantages, disadvantages, suggestions if available
        for field in ['advantages', 'disadvantages', 'suggestions']:
            field_tc = f"{field}_tc"
            field_llm = f"{field}_llm"
            if field_tc in proposal_row:
                llm_review[field] = proposal_row[field_tc]
            elif field_llm in proposal_row:
                llm_review[field] = proposal_row[field_llm]
        
        # Extract human review data
        human_review = {
            "vote": proposal_row.get('vote_human', ''),
            "comments": proposal_row.get('comment_human', '')
        }
        
        # Create the evaluation data dictionary
        evaluation_data = {
            "proposal_id": proposal_id,
            "title": proposal_row.get('title', f"Proposal {proposal_id}"),
            "llm_review": llm_review,
            "human_review": human_review,
            "vote_diff": proposal_row.get('vote_diff', 'N/A')
        }
        
        return evaluation_data
    
    async def evaluate_single_review(self, evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single LLM review against human review
        
        Args:
            evaluation_data: Dictionary with proposal and review data
            
        Returns:
            Dictionary with evaluation results
        """
        proposal_id = evaluation_data["proposal_id"]
        logger.info(f"Evaluating review for proposal {proposal_id}")
        
        # Format the evaluation data into the prompt
        prompt = self.prompt_template.replace("{EVALUATION_DATA}", json.dumps(evaluation_data, ensure_ascii=False, indent=2))
        
        try:
            # Call the LLM for evaluation
            response = await self.llm_client.generate_response(prompt)
            
            # Parse the JSON response
            content = response.text if hasattr(response, 'text') else response.content if hasattr(response, 'content') else str(response)
            
            # Extract the JSON part from the response
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    evaluation_result = json.loads(json_content)
                else:
                    # If no JSON format found, use the entire response as the overall assessment
                    evaluation_result = {
                        "consistency_score": 0,
                        "quality_score": 0,
                        "overall_assessment": content,
                        "error": "Couldn't parse JSON from response"
                    }
            except json.JSONDecodeError:
                evaluation_result = {
                    "consistency_score": 0,
                    "quality_score": 0,
                    "overall_assessment": content,
                    "error": "Invalid JSON format in response"
                }
                
            # Add metadata
            evaluation_result["proposal_id"] = proposal_id
            evaluation_result["title"] = evaluation_data["title"]
            evaluation_result["vote_diff"] = evaluation_data["vote_diff"]
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"Error evaluating review for proposal {proposal_id}: {str(e)}")
            return {
                "proposal_id": proposal_id,
                "title": evaluation_data["title"],
                "error": str(e),
                "overall_assessment": f"Evaluation failed: {str(e)}"
            }
    
    async def evaluate_all_reviews(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Evaluate all reviews in the merged dataset
        
        Args:
            limit: Maximum number of reviews to evaluate (for testing)
            
        Returns:
            List of evaluation results
        """
        if self.merged_df is None:
            self.merge_reviews()
            
        df_to_evaluate = self.merged_df.head(limit) if limit else self.merged_df
        logger.info(f"Evaluating {len(df_to_evaluate)} reviews")
        
        evaluation_tasks = []
        for _, row in df_to_evaluate.iterrows():
            evaluation_data = self.prepare_evaluation_data(row)
            evaluation_tasks.append(self.evaluate_single_review(evaluation_data))
            
        # Execute all evaluation tasks
        self.evaluation_results = await asyncio.gather(*evaluation_tasks)
        return self.evaluation_results
    
    def save_results(self, output_file: str) -> str:
        """
        Save evaluation results to file
        
        Args:
            output_file: Path to save the results
            
        Returns:
            Path to the saved file
        """
        if not self.evaluation_results:
            logger.warning("No evaluation results to save")
            return None
            
        # Convert to DataFrame
        results_df = pd.DataFrame(self.evaluation_results)
        
        # Save according to file extension
        if output_file.endswith('.csv'):
            results_df.to_csv(output_file, index=False)
        else:  # Default to Excel
            results_df.to_excel(output_file, index=False)
            
        logger.info(f"Evaluation results saved to {output_file}")
        return output_file
    
    def generate_summary_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a summary report of the evaluation results
        
        Args:
            output_file: Optional path to save the summary report
            
        Returns:
            Dictionary with summary statistics
        """
        if not self.evaluation_results:
            logger.warning("No evaluation results to summarize")
            return {}
            
        results_df = pd.DataFrame(self.evaluation_results)
        
        # Calculate summary statistics
        summary = {
            "total_proposals": len(results_df),
            "avg_consistency_score": results_df.get('consistency_score', pd.Series()).mean(),
            "avg_quality_score": results_df.get('quality_score', pd.Series()).mean(),
            "perfect_match_pct": (results_df.get('vote_diff', pd.Series()) == 0).mean() * 100 if 'vote_diff' in results_df else 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save summary if output file is provided
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logger.info(f"Summary report saved to {output_file}")
            
        return summary
    
    async def close(self):
        """安全關閉評估器使用的資源"""
        if hasattr(self.llm_client, 'aclose'):
            await self.llm_client.aclose()


async def run_evaluation(
    llm_reviews_file: str,
    human_reviews_file: str,
    prompt_file: str,
    output_file: str,
    model_name: str = "o3-mini",
    reasoning_effort: str = "high",
    limit: Optional[int] = None
) -> str:
    """
    Run the full evaluation process
    
    Args:
        llm_reviews_file: Path to LLM reviews file
        human_reviews_file: Path to human reviews file
        prompt_file: Path to evaluation prompt template
        output_file: Path to save evaluation results
        model_name: LLM model name
        reasoning_effort: Reasoning effort level
        limit: Maximum number of reviews to evaluate
        
    Returns:
        Path to the saved evaluation results
    """
    logger.info(f"Starting evaluation with model {model_name}")
    
    # Initialize evaluator
    evaluator = ReviewEvaluator(
        llm_reviews_file=llm_reviews_file,
        human_reviews_file=human_reviews_file,
        prompt_file=prompt_file,
        model_name=model_name,
        reasoning_effort=reasoning_effort
    )
    
    try:
        # Load and merge data
        evaluator.load_data()
        evaluator.merge_reviews()
        
        # Run evaluation
        results = await evaluator.evaluate_all_reviews(limit=limit)
        
        # Save results
        output_path = evaluator.save_results(output_file)
        
        # Generate and save summary report
        summary_file = output_file.replace('.xlsx', '.json').replace('.csv', '.json')
        summary = evaluator.generate_summary_report(summary_file)
        
        logger.info(f"Evaluation complete. Results saved to {output_path}")
        logger.info(f"Average consistency score: {summary.get('avg_consistency_score', 0):.2f}")
        logger.info(f"Average quality score: {summary.get('avg_quality_score', 0):.2f}")
        
        return output_path
    finally:
        # 確保資源被正確釋放，無論評估過程是否成功
        await evaluator.close()


def evaluate_reviews(
    llm_reviews_file: str,
    human_reviews_file: str,
    prompt_file: str,
    output_file: str,
    model_name: str = "o3-mini",
    reasoning_effort: str = "high",
    limit: Optional[int] = None
) -> str:
    """
    Synchronous wrapper for review evaluation
    
    Args:
        llm_reviews_file: Path to LLM reviews file
        human_reviews_file: Path to human reviews file
        prompt_file: Path to evaluation prompt template
        output_file: Path to save evaluation results
        model_name: LLM model name
        reasoning_effort: Reasoning effort level
        limit: Maximum number of reviews to evaluate
        
    Returns:
        Path to the saved evaluation results
    """
    return asyncio.run(run_evaluation(
        llm_reviews_file=llm_reviews_file,
        human_reviews_file=human_reviews_file,
        prompt_file=prompt_file,
        output_file=output_file,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        limit=limit
    )) 