import os
import sys
import json
import logging
import pandas as pd
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# 新增以下代碼以解決導入問題
# 將專案根目錄加入 sys.path
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))

from src import config
from src.db.queries import GET_PROPOSALS_BY_CONF, GET_NEGATIVE_PROPOSALS, GET_REVIEWS_BY_PROPOSAL

# Configure logging
log_file = config.LOGS_DIR / f"db_connector_{datetime.now().strftime('%Y%m%d')}.log"
os.makedirs(config.LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MetabaseConnector:
    """Class to handle connections to Metabase API"""
    
    def __init__(self, 
                 url: str = None, 
                 username: str = None, 
                 password: str = None, 
                 database_id: int = None):
        """Initialize the connector with credentials"""
        self.url = url or config.METABASE_URL
        self.username = username or config.METABASE_USERNAME
        self.password = password or config.METABASE_PASSWORD
        self.database_id = database_id or config.METABASE_DATABASE_ID
        self.session_id = None
        
        if not self.url or not self.username or not self.password:
            logger.error("Metabase credentials are not properly configured")
            raise ValueError("Metabase credentials are not properly configured")
        
        logger.info(f"Initialized Metabase connector with URL: {self.url}")
    
    def authenticate(self) -> bool:
        """Authenticate with Metabase and get a session ID"""
        try:
            data = {
                "username": self.username,
                "password": self.password
            }
            
            auth_url = f"{self.url}/api/session"
            response = requests.post(auth_url, json=data)
            response.raise_for_status()
            
            self.session_id = response.json()["id"]
            logger.info("Successfully authenticated with Metabase")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to authenticate with Metabase: {e}")
            self.session_id = None
            return False
    
    def query_database(self, sql_query: str, params: Dict = None) -> pd.DataFrame:
        """Execute a SQL query and return the results as a DataFrame"""
        if not self.session_id:
            if not self.authenticate():
                logger.error("Authentication required before querying")
                return pd.DataFrame()
        
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Metabase-Session": self.session_id,
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            
            # Use Metabase's parameter handling instead of manual formatting
            # The API payload structure expects parameters separately
            native_query_part = {
                "query": sql_query
            }
            if params:
                # Metabase expects parameters in a list of dictionaries
                # with 'type' and 'value' keys. Type inference might be needed.
                # For simplicity here, we assume 'text' type for strings and others pass directly.
                # This part might need adjustment based on actual Metabase API requirements for parameter types.
                mb_params = []
                for key, value in params.items():
                    # Simplified parameter info - type detection might still be needed
                    # Metabase might infer types or expect specific formats
                    param_type = "text" # Default to text
                    if isinstance(value, int) or isinstance(value, float):
                        param_type = "number"
                    elif isinstance(value, (list, tuple)):
                        # For IN clauses, Metabase might expect a list directly or a specific type
                        # Let's try passing the tuple/list directly first
                        # If this fails, we might need to format it as a string or use a different type
                        param_type = "category" # Or potentially just pass the list/tuple
                        logger.warning(f"List/tuple parameter '{key}' passed directly. Verify Metabase handling.")
                    
                    # Using simpler parameter structure - check Metabase docs if this fails
                    mb_params.append({
                        "type": param_type, 
                        "value": value, 
                        "target": ["variable", ["template-tag", key]]
                    })
                native_query_part["template-tags"] = {key: {"name": key, "display-name": key, "type": param_type, "required": True} for key, param_dict in zip(params.keys(), mb_params)} # Restore template-tags definition
                # Removed explicit template-tags definition, relying on API inference

            logger.info(f"Executing SQL query: {sql_query} with params: {params}")

            data = {
                "database": self.database_id,
                "native": native_query_part, 
                "type": "native",
                "parameters": mb_params if params else []
            }

            query_url = f"{self.url}/api/dataset"
            response = requests.post(query_url, headers=headers, json=data)
            
            # Log the request payload for debugging
            logger.debug(f"Metabase request payload: {json.dumps(data)}")

            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Query result: {result}")

            # Adjust parsing based on observed structure or Metabase documentation
            if "data" not in result or not isinstance(result["data"], dict):
                logger.warning("Unexpected data structure in response.")
                if "error" in result:
                    logger.error(f"Database error: {result['error']}")
                return pd.DataFrame()

            # Check for common Metabase error responses
            if result.get("status") == "failed":
                 logger.error(f"Metabase query failed: {result.get('error')}")
                 return pd.DataFrame()

            # Check for rows and columns (adjust key names if needed based on actual response)
            rows = result["data"].get("rows")
            cols_data = result["data"].get("cols") # Metabase often uses 'cols'

            if not rows:
                logger.warning("No data rows returned from query")
                # Return empty DataFrame with columns if columns are available
                if cols_data:
                    columns = [col.get("display_name", col.get("name")) for col in cols_data]
                    return pd.DataFrame(columns=columns)
                else:
                    return pd.DataFrame()
            
            if not cols_data:
                 logger.warning("No column information returned, trying to infer from rows.")
                 # Basic inference: Use keys from the first row if rows are dicts (less reliable)
                 if rows and isinstance(rows[0], dict):
                     columns = list(rows[0].keys())
                 else:
                     # Cannot determine columns
                     logger.error("Could not determine column names.")
                     return pd.DataFrame(rows) # Return with default numbered columns
            else:
                # Get column names, preferring display_name over name
                columns = [col.get("display_name", col.get("name")) for col in cols_data]
            
            # Create DataFrame
            df = pd.DataFrame(rows, columns=columns)
            
            # Ensure proposal_id is string
            if 'proposal_id' in df.columns:
                df['proposal_id'] = df['proposal_id'].astype(str)
            
            return df
            
        except requests.RequestException as e:
            # More specific error logging
            error_details = str(e)
            if e.response is not None:
                 try:
                     error_details += f" - Response: {e.response.text}"
                 except Exception:
                     pass # Ignore if response body cannot be read
            logger.error(f"Failed to execute query: {error_details}")
            return pd.DataFrame()
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode JSON response: {e}")
             logger.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
             return pd.DataFrame()
        except Exception as e:
             logger.exception(f"An unexpected error occurred during query execution: {e}") # Log stack trace
             return pd.DataFrame()
    
    def get_proposals_by_conference(self, conference: str) -> pd.DataFrame:
        """Get proposals for a specific conference"""
        # Parameters are now handled by query_database
        return self.query_database(GET_PROPOSALS_BY_CONF, {"conference": conference})
    
    def get_negative_proposals(self, 
                             exclude_conference: str,
                             negative_threshold: float = 25.0,
                             min_reviews: int = 3) -> pd.DataFrame:
        """Get proposals with negative reviews, excluding specific conference"""
        params = {
            "exclude_conference": exclude_conference,
            "negative_threshold": negative_threshold,
            "min_reviews": min_reviews
        }
        return self.query_database(GET_NEGATIVE_PROPOSALS, params)
    
    def get_reviews_by_proposals(self, proposal_ids: List[str]) -> pd.DataFrame:
        """Get all reviews for specific proposals"""
        if not proposal_ids:
            return pd.DataFrame()
        
        params = {"proposal_ids": tuple(proposal_ids)}
        return self.query_database(GET_REVIEWS_BY_PROPOSAL, params)

def get_proposals_from_db(conference_year: str = "pycontw-2024", 
                         negative_threshold: float = 25.0,
                         min_reviews: int = 3) -> pd.DataFrame:
    """Get proposals from the database with optional filtering for negative proposals"""
    
    connector = MetabaseConnector()
    
    # Get proposals with negative reviews, excluding the current conference
    proposals_df = connector.get_negative_proposals(
        exclude_conference=conference_year,
        negative_threshold=negative_threshold,
        min_reviews=min_reviews
    )
    
    return proposals_df

def get_reviews_from_db(conference_year: str = "pycontw-2024") -> pd.DataFrame:
    """Get all reviews for proposals"""
    
    connector = MetabaseConnector()
    
    # First get all proposal IDs for the conference
    proposals_df = connector.get_proposals_by_conference(conference_year)
    if proposals_df.empty:
        return pd.DataFrame()
    
    # Then get all reviews for these proposals
    reviews_df = connector.get_reviews_by_proposals(proposals_df['proposal_id'].tolist())
    
    return reviews_df

def save_data_to_excel(proposals_df: pd.DataFrame, 
                      reviews_df: pd.DataFrame, 
                      output_dir: str = None) -> Dict[str, str]:
    """Save database data to Excel files and return file paths"""
    
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = output_dir or str(config.DATA_DIR)
    os.makedirs(output_dir, exist_ok=True)
    
    # File paths
    proposal_file = os.path.join(output_dir, f"pycon_2024_proposal_{date_str}.xlsx")
    review_file = os.path.join(output_dir, f"pycon_2024_review_{date_str}.xlsx")
    
    # Save proposals
    if not proposals_df.empty:
        proposals_df.to_excel(proposal_file, index=False)
        logger.info(f"Saved {len(proposals_df)} proposals to {proposal_file}")
    else:
        logger.warning("No proposals to save")
    
    # Save reviews
    if not reviews_df.empty:
        reviews_df.to_excel(review_file, index=False)
        logger.info(f"Saved {len(reviews_df)} reviews to {review_file}")
    else:
        logger.warning("No reviews to save")
    
    return {
        "proposal_file": proposal_file if not proposals_df.empty else None,
        "review_file": review_file if not reviews_df.empty else None
    }

def fetch_and_save_db_data(
    conference_year: str,
    include_previous: bool = False,
    negative_threshold: float = 25.0,
    min_reviews: int = 3,
    output_dir: str = None
) -> Dict[str, str]:
    """Fetch proposal and review data from the database and save them as Excel files"""
    try:
        output_dir = output_dir or 'data'
        os.makedirs(output_dir, exist_ok=True)
        
        # Connect to the database
        connector = MetabaseConnector()
        
        # Current timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Generate filenames
        proposal_file = os.path.join(output_dir, f"{conference_year}_proposal_{timestamp}.xlsx")
        review_file = os.path.join(output_dir, f"{conference_year}_review_{timestamp}.xlsx")
        
        # Conferences to include
        conferences = [conference_year]
        if include_previous:
            # Add previous conference years
            previous_conferences = get_previous_conferences(conference_year)
            conferences.extend(previous_conferences)
            logging.info(f"Including data from conferences: {conferences}")
        
        # Fetch proposals
        proposal_df = connector.get_proposals_by_conference(conferences)
        if proposal_df.empty:
            logging.warning(f"No proposals found for conferences: {conferences}")
            return {
                "proposal_file": None,
                "review_file": None
            }
        
        # Fetch reviews
        review_df = connector.get_reviews_by_proposals(proposal_df['proposal_id'].tolist())
        if review_df.empty:
            logging.warning(f"No reviews found for conferences: {conferences}")
            return {
                "proposal_file": proposal_file,
                "review_file": None
            }
        
        # Filter proposals based on negative review percentage
        if negative_threshold > 0 and min_reviews > 0:
            # Group reviews by proposal_id
            review_stats = {}
            for proposal_id, group in review_df.groupby('proposal_id'):
                votes = group['vote'].tolist()
                if len(votes) >= min_reviews:
                    negative_votes = votes.count('-0') + votes.count('-1')
                    negative_percentage = (negative_votes / len(votes)) * 100
                    if negative_percentage >= negative_threshold:
                        review_stats[proposal_id] = True
            
            # Filter proposals to include only those with sufficient negative reviews
            filtered_proposal_ids = list(review_stats.keys())
            proposal_df = proposal_df[proposal_df['proposal_id'].isin(filtered_proposal_ids)]
            review_df = review_df[review_df['proposal_id'].isin(filtered_proposal_ids)]
            
            logging.info(f"Filtered to {len(filtered_proposal_ids)} proposals with >= {negative_threshold}% negative votes")
        
        # Save to Excel
        proposal_df.to_excel(proposal_file, index=False)
        review_df.to_excel(review_file, index=False)
        
        logging.info(f"Saved {len(proposal_df)} proposals to {proposal_file}")
        logging.info(f"Saved {len(review_df)} reviews to {review_file}")
        
        return {
            "proposal_file": proposal_file,
            "review_file": review_file
        }
    
    except Exception as e:
        logging.error(f"Error fetching database data: {e}")
        return {
            "proposal_file": None,
            "review_file": None
        }

def get_previous_conferences(current_conference: str) -> List[str]:
    """Get a list of previous conference identifiers"""
    # Extract year from current conference (assuming format like 'pycontw-2024')
    try:
        current_year = int(current_conference.split('-')[-1])
        
        # Generate identifiers for previous years (e.g., 2023, 2022, etc.)
        # Go back up to 5 years but not earlier than 2012 (adjust as needed)
        previous_years = range(current_year - 1, max(current_year - 6, 2012 - 1), -1)
        
        # Generate conference identifiers
        prefix = current_conference.split('-')[0]  # e.g., 'pycontw'
        previous_conferences = [f"{prefix}-{year}" for year in previous_years]
        
        return previous_conferences
    except (ValueError, IndexError):
        logging.warning(f"Could not parse conference year from {current_conference}, using default format")
        return []

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch data from Metabase")
    parser.add_argument("--conference", default="pycontw-2024", help="Conference identifier")
    parser.add_argument("--negative", type=float, default=25.0, 
                        help="Filter proposals with negative percentage >= this value")
    parser.add_argument("--min-reviews", type=int, default=3, 
                        help="Minimum number of reviews required")
    parser.add_argument("--output-dir", help="Output directory for Excel files")
    
    args = parser.parse_args()
    
    # Fetch and save data
    file_paths = fetch_and_save_db_data(
        conference_year=args.conference,
        negative_threshold=args.negative,
        min_reviews=args.min_reviews,
        output_dir=args.output_dir
    )
    
    print(f"Proposal file: {file_paths['proposal_file']}")
    print(f"Review file: {file_paths['review_file']}") 