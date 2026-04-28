#!/usr/bin/env python3
"""
主腳本：執行 PyCon TW 2025 提案的 LLM 評審和評估
"""
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

# 使用不帶src前綴的絕對導入
from llm.review import run_llm_review
from llm.proposal_diff import run_proposal_diff_analysis_sync
from evaluation.evaluator import evaluate_reviews
import config

# 配置日誌記錄
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / f"llm_main_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函數：解析命令行參數並執行相應的任務"""
    parser = argparse.ArgumentParser(description="PyCon TW 2025 LLM Review Tool")
    
    # 通用參數
    parser.add_argument("--data_dir", type=str, default="data/db_merged_fixed",
                        help="資料目錄路徑")
    parser.add_argument("--output_dir", type=str, default="output",
                        help="輸出目錄路徑")
    parser.add_argument("--model", type=str, default="o3-mini",
                        help="LLM 模型名稱 (o3-mini 預設)")
    parser.add_argument("--reasoning_effort", type=str, default="high",
                        choices=["low", "medium", "high"],
                        help="推理努力級別 (僅適用於 OpenAI 模型)")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="要執行的命令")
    
    # LLM 評審子命令
    review_parser = subparsers.add_parser("review", help="執行 LLM 評審")
    review_parser.add_argument("--proposal_file", type=str, required=True,
                            help="提案資料檔案路徑 (.xlsx)")
    review_parser.add_argument("--prompt_file", type=str, 
                             default=str(config.FULL_PROMPT_FILE),
                             help="提示模板檔案路徑")
    review_parser.add_argument("--output_file", type=str,
                             help="輸出檔案路徑 (預設根據模型和日期生成)")
    review_parser.add_argument("--limit", type=int, default=None,
                             help="要處理的提案數量上限 (用於測試)")
    review_parser.add_argument("--with_translation", action="store_true",
                             help="是否進行翻譯")
    review_parser.add_argument("--translation_model", type=str, default="gpt-4o-mini",
                             help="翻譯用 LLM 模型名稱")
    
    # 評估子命令
    eval_parser = subparsers.add_parser("evaluate", help="評估 LLM 評審結果")
    eval_parser.add_argument("--llm_reviews_file", type=str, required=True,
                           help="LLM 評審結果檔案路徑 (.xlsx/.csv)")
    eval_parser.add_argument("--human_reviews_file", type=str, required=True,
                           help="人類評審結果檔案路徑 (.xlsx/.csv)")
    eval_parser.add_argument("--prompt_file", type=str, 
                           default="prompt/evaluation_prompt.txt",
                           help="評估提示模板檔案路徑")
    eval_parser.add_argument("--output_file", type=str,
                           help="評估結果輸出檔案路徑 (預設根據模型和日期生成)")
    eval_parser.add_argument("--limit", type=int, default=None,
                           help="要評估的提案數量上限 (用於測試)")
    
    # 運行 review 和 evaluate 的子命令
    both_parser = subparsers.add_parser("both", help="執行 LLM 評審並評估結果")
    both_parser.add_argument("--proposal_file", type=str, required=True,
                           help="提案資料檔案路徑 (.xlsx)")
    both_parser.add_argument("--human_reviews_file", type=str, required=True,
                           help="人類評審結果檔案路徑 (.xlsx/.csv)")
    both_parser.add_argument("--review_prompt_file", type=str, 
                           default=str(config.FULL_PROMPT_FILE),
                           help="評審提示模板檔案路徑")
    both_parser.add_argument("--eval_prompt_file", type=str, 
                           default="prompt/evaluation_prompt.txt",
                           help="評估提示模板檔案路徑")
    both_parser.add_argument("--limit", type=int, default=None,
                           help="要處理的提案數量上限 (用於測試)")
    both_parser.add_argument("--with_translation", action="store_true",
                           help="是否進行翻譯")
    both_parser.add_argument("--translation_model", type=str, default="gpt-4o-mini",
                           help="翻譯用 LLM 模型名稱")
    
    # 提案差異比較子命令
    diff_parser = subparsers.add_parser("diff", help="比較兩個階段的提案差異")
    diff_parser.add_argument("--stage1_file", type=str, required=True,
                           help="Stage 1 提案檔案路徑 (.xlsx)")
    diff_parser.add_argument("--stage2_file", type=str, required=True,
                           help="Stage 2 提案檔案路徑 (.xlsx)")
    diff_parser.add_argument("--prompt_file", type=str,
                           default="prompt/proposal_diff_prompt.txt",
                           help="差異分析提示模板檔案路徑")
    diff_parser.add_argument("--output_file", type=str,
                           help="輸出檔案路徑 (預設根據日期生成)")
    diff_parser.add_argument("--limit", type=int, default=None,
                           help="要處理的提案數量上限 (用於測試)")
    diff_parser.add_argument("--translation_model", type=str, default="gpt-4o-mini",
                           help="翻譯用 LLM 模型名稱")
    
    args = parser.parse_args()
    
    # 執行相應的命令
    if args.command == "review":
        execute_review(args)
    elif args.command == "evaluate":
        execute_evaluation(args)
    elif args.command == "both":
        execute_both(args)
    elif args.command == "diff":
        execute_diff(args)
    else:
        parser.print_help()
        
def execute_review(args):
    """執行 LLM 評審任務"""
    logger.info("開始執行 LLM 評審任務")
    
    # 確保資料和輸出目錄存在
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # 設定輸出檔案路徑
    if not args.output_file:
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"llm_review_{args.model}_{date_str}.xlsx"
    else:
        output_file = Path(args.output_file)
    
    # 執行 LLM 評審
    proposal_file = Path(args.proposal_file)
    if not proposal_file.exists():
        logger.error(f"提案檔案不存在: {proposal_file}")
        return
        
    prompt_file = Path(args.prompt_file)
    if not prompt_file.exists():
        logger.error(f"提示模板檔案不存在: {prompt_file}")
        return
    
    try:
        logger.info(f"使用 limit={args.limit} 限制提案數量")
        result = run_llm_review(
            prompt_file=str(prompt_file),
            model_name=args.model,
            output_file=str(output_file),
            proposal_file=str(proposal_file),
            limit=args.limit,
            with_translation=args.with_translation,
            translation_model=args.translation_model
        )
        logger.info(f"LLM 評審任務完成，結果已保存至: {result}")
    except Exception as e:
        logger.error(f"執行 LLM 評審時發生錯誤: {str(e)}", exc_info=True)

def execute_evaluation(args):
    """執行 LLM 評審結果評估任務"""
    logger.info("開始執行 LLM 評審結果評估任務")
    
    # 確保資料和輸出目錄存在
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # 設定輸出檔案路徑
    if not args.output_file:
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = output_dir / f"llm_evaluation_{args.model}_{date_str}.xlsx"
    else:
        output_file = Path(args.output_file)
    
    # 檢查輸入檔案是否存在
    llm_reviews_file = Path(args.llm_reviews_file)
    if not llm_reviews_file.exists():
        logger.error(f"LLM 評審結果檔案不存在: {llm_reviews_file}")
        return
        
    human_reviews_file = Path(args.human_reviews_file)
    if not human_reviews_file.exists():
        logger.error(f"人類評審結果檔案不存在: {human_reviews_file}")
        return
        
    prompt_file = Path(args.prompt_file)
    if not prompt_file.exists():
        logger.error(f"評估提示模板檔案不存在: {prompt_file}")
        return
    
    try:
        result = evaluate_reviews(
            llm_reviews_file=str(llm_reviews_file),
            human_reviews_file=str(human_reviews_file),
            prompt_file=str(prompt_file),
            output_file=str(output_file),
            model_name=args.model,
            reasoning_effort=args.reasoning_effort,
            limit=args.limit
        )
        logger.info(f"LLM 評審結果評估任務完成，結果已保存至: {result}")
    except Exception as e:
        logger.error(f"執行 LLM 評審結果評估時發生錯誤: {str(e)}", exc_info=True)

def execute_both(args):
    """執行 LLM 評審並評估結果"""
    logger.info("開始執行 LLM 評審並評估結果")
    
    # 首先執行評審
    date_str = datetime.now().strftime("%Y%m%d")
    review_output = Path(args.output_dir) / f"llm_review_{args.model}_{date_str}.xlsx"
    
    try:
        # 執行評審
        logger.info(f"使用 limit={args.limit} 限制提案數量")
        review_result = run_llm_review(
            prompt_file=str(Path(args.review_prompt_file)),
            model_name=args.model,
            output_file=str(review_output),
            proposal_file=str(Path(args.proposal_file)),
            limit=args.limit,
            with_translation=args.with_translation,
            translation_model=args.translation_model
        )
        logger.info(f"LLM 評審完成，結果已保存至: {review_result}")
        
        # 然後執行評估
        eval_output = Path(args.output_dir) / f"llm_evaluation_{args.model}_{date_str}.xlsx"
        
        # 創建新事件循環並在單獨的上下文中執行評估
        # 這樣可以避免在連續運行兩個使用 asyncio 的函數時出現事件循環關閉錯誤
        import asyncio
        from evaluation.evaluator import run_evaluation
        
        # 使用 asyncio.new_event_loop() 創建新的事件循環
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            eval_result = loop.run_until_complete(run_evaluation(
                llm_reviews_file=str(review_output),
                human_reviews_file=str(Path(args.human_reviews_file)),
                prompt_file=str(Path(args.eval_prompt_file)),
                output_file=str(eval_output),
                model_name=args.model,
                reasoning_effort=args.reasoning_effort,
                limit=args.limit
            ))
            logger.info(f"LLM 評審結果評估完成，結果已保存至: {eval_result}")
        finally:
            # 確保事件循環被妥善關閉
            loop.close()
            
    except Exception as e:
        logger.error(f"執行 LLM 評審和評估時發生錯誤: {str(e)}", exc_info=True)

def execute_diff(args):
    """執行提案差異比較任務"""
    logger.info("開始執行提案差異比較任務")
    
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
        logger.info(f"提案差異比較任務完成，結果已保存至: {result}")
    except Exception as e:
        logger.error(f"執行提案差異比較時發生錯誤: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main() 