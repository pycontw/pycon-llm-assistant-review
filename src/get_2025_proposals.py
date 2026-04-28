import os
import sys
from pathlib import Path

# Add the project root directory to Python path
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))

from src.db.connector import MetabaseConnector
import pandas as pd
from datetime import datetime

def main():
    # Initialize connector
    connector = MetabaseConnector()
    
    # Get proposals for PyCon TW 2024 (for testing)
    proposals_df = connector.get_proposals_by_conference("pycontw-2025")
    
    if proposals_df.empty:
        print("No proposals found for PyCon TW 2025")
        return
    
    # Save to Excel
    timestamp = datetime.now().strftime("%Y%m%d")
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"pycontw_2025_proposals_{timestamp}.xlsx")
    proposals_df.to_excel(output_file, index=False)
    print(f"Saved {len(proposals_df)} proposals to {output_file}")

if __name__ == "__main__":
    main() 