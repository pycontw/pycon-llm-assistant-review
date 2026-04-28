#!/usr/bin/env python3
"""
PyCon TW 2025 提案差異比較工具
比較兩個階段的提案，分析變更並生成差異報告
"""

import sys
import os
from pathlib import Path

# 確保 src 目錄在 Python 路徑中
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

# 修改環境變數，設置模型溫度為 0
os.environ["OPENAI_TEMPERATURE"] = "0"

import argparse
import logging
from datetime import datetime

from llm.proposal_diff import run_proposal_diff_analysis_sync
import config

# 配置日誌記錄
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / f"proposal_diff_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函數：解析命令行參數並執行提案差異比較"""
    parser = argparse.ArgumentParser(description="PyCon TW 2025 提案差異比較工具")
    
    # 基本參數
    parser.add_argument("--stage1_file", type=str, required=True,
                        help="Stage 1 提案檔案路徑 (.xlsx)")
    parser.add_argument("--stage2_file", type=str, required=True,
                        help="Stage 2 提案檔案路徑 (.xlsx)")
    parser.add_argument("--prompt_file", type=str,
                        default="prompt/proposal_diff_prompt.txt",
                        help="差異分析提示模板檔案路徑")
    parser.add_argument("--output_file", type=str,
                        help="輸出檔案路徑 (預設根據日期生成)")
    parser.add_argument("--output_dir", type=str, default="output",
                        help="輸出目錄路徑")
    parser.add_argument("--model", type=str, default="o4-mini",
                        help="LLM 模型名稱")
    parser.add_argument("--reasoning_effort", type=str, default="high",
                        choices=["low", "medium", "high"],
                        help="推理努力級別 (僅適用於 OpenAI 模型)")
    parser.add_argument("--translation_model", type=str, default="gpt-4o-mini",
                        help="翻譯用 LLM 模型名稱")
    parser.add_argument("--limit", type=int, default=None,
                        help="要處理的提案數量上限 (用於測試)")

    args = parser.parse_args()

    # 執行提案差異比較
    logger.info("開始執行提案差異比較")
    
    # 確保輸出目錄存在
    output_dir = Path(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # 設定輸出檔案路徑
    if not args.output_file:
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"proposal_diff_{args.model}_{date_str}.xlsx"
    else:
        output_file = Path(args.output_file)
    
    # 檢查輸入檔案是否存在
    stage1_file = Path(args.stage1_file)
    if not stage1_file.exists():
        logger.error(f"Stage 1 提案檔案不存在: {stage1_file}")
        return
        
    stage2_file = Path(args.stage2_file)
    if not stage2_file.exists():
        logger.error(f"Stage 2 提案檔案不存在: {stage2_file}")
        return
        
    prompt_file = Path(args.prompt_file)
    if not prompt_file.exists():
        logger.error(f"差異分析提示模板檔案不存在: {prompt_file}")
        return
    
    try:
        logger.info(f"使用 limit={args.limit} 限制提案數量")
        result = run_proposal_diff_analysis_sync(
            stage1_file=str(stage1_file),
            stage2_file=str(stage2_file),
            prompt_file=str(prompt_file),
            output_file=str(output_file),
            model_name=args.model,
            reasoning_effort=args.reasoning_effort,
            translation_model=args.translation_model,
            limit=args.limit
        )
        logger.info(f"提案差異比較完成，結果已保存至: {result}")
    except Exception as e:
        logger.error(f"執行提案差異比較時發生錯誤: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main() 