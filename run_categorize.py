#!/usr/bin/env python3
"""
主腳本：執行 PyCon TW 2025 提案分類
"""
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

# 直接導入分類模組
from src.llm.categorize import run_categorization
from src import config

# 配置日誌記錄
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / f"categorize_main_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函數：解析命令行參數並執行分類任務"""
    parser = argparse.ArgumentParser(description="PyCon TW 2025 Proposal Categorization Tool")
    
    # 參數設置
    parser.add_argument("--data_dir", type=str, default="data/db_merged_fixed",
                        help="資料目錄路徑")
    parser.add_argument("--output_dir", type=str, default="output",
                        help="輸出目錄路徑")
    parser.add_argument("--proposal_file", type=str, required=True,
                      help="提案資料檔案路徑 (.xlsx)")
    parser.add_argument("--prompt_file", type=str, 
                      default=str(Path("prompt/categorization_prompt.txt")),
                      help="分類提示模板檔案路徑")
    parser.add_argument("--output_file", type=str,
                      help="輸出檔案路徑 (預設根據模型和日期生成)")
    parser.add_argument("--model", type=str, default="o3-mini",
                      help="LLM 模型名稱 (o3-mini 預設)")
    parser.add_argument("--reasoning_effort", type=str, default="medium",
                      choices=["low", "medium", "high"],
                      help="推理努力級別 (預設 medium)")
    parser.add_argument("--limit", type=int, default=None,
                      help="要處理的提案數量上限 (用於測試)")
    parser.add_argument("--sleep_time", type=int, default=config.DEFAULT_SLEEP_TIME,
                      help="重試間隔時間 (秒)")
    parser.add_argument("--max_retries", type=int, default=config.MAX_RETRIES,
                      help="最大重試次數")

    args = parser.parse_args()
    
    # 執行分類任務
    execute_categorization(args)

def execute_categorization(args):
    """執行提案分類任務"""
    logger.info("開始執行提案分類任務")
    
    # 確保資料和輸出目錄存在
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # 設定輸出檔案路徑
    if not args.output_file:
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"proposal_categories_{args.model}_{date_str}.xlsx"
    else:
        output_file = Path(args.output_file)
    
    # 檢查提案檔案是否存在
    proposal_file = Path(args.proposal_file)
    if not proposal_file.exists():
        logger.error(f"提案檔案不存在: {proposal_file}")
        return
        
    # 檢查提示模板檔案是否存在
    prompt_file = Path(args.prompt_file)
    if not prompt_file.exists():
        logger.error(f"提示模板檔案不存在: {prompt_file}")
        return
    
    try:
        logger.info(f"使用 limit={args.limit} 限制提案數量")
        result = run_categorization(
            prompt_file=str(prompt_file),
            model_name=args.model,
            output_file=str(output_file),
            proposal_file=str(proposal_file),
            sleep_time=args.sleep_time,
            max_retries=args.max_retries,
            limit=args.limit,
            reasoning_effort=args.reasoning_effort
        )
        logger.info(f"提案分類任務完成，結果已保存至: {result}")
    except Exception as e:
        logger.error(f"執行提案分類時發生錯誤: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main() 