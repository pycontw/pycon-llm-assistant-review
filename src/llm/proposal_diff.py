#!/usr/bin/env python3
"""
提案差異比較模組
比較兩個階段的 PyCon TW 2025 提案，分析變更並生成差異報告
"""

import asyncio
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from llm.client import OpenAIClient
from utils.helpers import export_to_excel

logger = logging.getLogger(__name__)

class ProposalDiffAnalyzer:
    """提案差異分析器"""
    
    def __init__(self, model_name: str = "o4-mini", reasoning_effort: str = "high", 
                 translation_model: str = "gpt-4o-mini"):
        """
        初始化差異分析器
        
        Args:
            model_name: 用於差異分析的 LLM 模型
            reasoning_effort: OpenAI 模型的推理努力級別
            translation_model: 用於翻譯的模型
        """
        self.model_name = model_name
        self.reasoning_effort = reasoning_effort
        self.translation_model = translation_model
        
        # 初始化 LLM 客戶端
        self.llm_client = OpenAIClient(model=model_name, reasoning_effort=reasoning_effort)
        self.translation_client = OpenAIClient(model=translation_model, reasoning_effort="low")
        
    def load_proposals(self, stage1_file: str, stage2_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        載入兩個階段的提案資料
        
        Args:
            stage1_file: Stage 1 提案檔案路徑
            stage2_file: Stage 2 提案檔案路徑
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: Stage 1 和 Stage 2 的資料
        """
        logger.info(f"載入 Stage 1 資料: {stage1_file}")
        stage1_df = pd.read_excel(stage1_file)
        
        logger.info(f"載入 Stage 2 資料: {stage2_file}")
        stage2_df = pd.read_excel(stage2_file)
        
        logger.info(f"Stage 1 資料: {stage1_df.shape[0]} 筆提案")
        logger.info(f"Stage 2 資料: {stage2_df.shape[0]} 筆提案")
        
        return stage1_df, stage2_df
    
    def find_matching_proposals(self, stage1_df: pd.DataFrame, stage2_df: pd.DataFrame) -> pd.DataFrame:
        """
        找出兩個階段中匹配的提案
        
        Args:
            stage1_df: Stage 1 資料
            stage2_df: Stage 2 資料
            
        Returns:
            pd.DataFrame: 包含匹配提案資訊的資料框
        """
        # 確保 proposal_id 欄位存在
        if 'proposal_id' not in stage1_df.columns:
            logger.error("Stage 1 資料缺少 proposal_id 欄位")
            raise ValueError("Stage 1 資料缺少 proposal_id 欄位")
            
        if 'proposal_id' not in stage2_df.columns:
            logger.error("Stage 2 資料缺少 proposal_id 欄位")
            raise ValueError("Stage 2 資料缺少 proposal_id 欄位")
        
        # 以 Stage 1 為主進行 left join
        merged_df = stage1_df.merge(
            stage2_df,
            on='proposal_id',
            how='left',
            suffixes=('_stage1', '_stage2')
        )
        
        # 過濾出 Stage 2 中也存在的提案（即有變更可能的提案）
        matched_df = merged_df[merged_df['title_stage2'].notna()].copy()
        
        logger.info(f"找到 {matched_df.shape[0]} 筆匹配的提案")
        
        return matched_df
    
    def create_diff_prompt(self, stage1_data: Dict[str, Any], stage2_data: Dict[str, Any], 
                          prompt_template: str) -> str:
        """
        創建差異分析的提示文字
        
        Args:
            stage1_data: Stage 1 提案資料
            stage2_data: Stage 2 提案資料
            prompt_template: 提示模板
            
        Returns:
            str: 格式化的提示文字
        """
        return prompt_template.format(
            stage1_title=stage1_data.get('title', ''),
            stage1_abstract=stage1_data.get('abstract', ''),
            stage1_detailed_description=stage1_data.get('detailed_description', ''),
            stage1_outline=stage1_data.get('outline', ''),
            stage1_objective=stage1_data.get('objective', ''),
            stage2_title=stage2_data.get('title', ''),
            stage2_abstract=stage2_data.get('abstract', ''),
            stage2_detailed_description=stage2_data.get('detailed_description', ''),
            stage2_outline=stage2_data.get('outline', ''),
            stage2_objective=stage2_data.get('objective', '')
        )
    
    async def analyze_proposal_diff(self, stage1_data: Dict[str, Any], stage2_data: Dict[str, Any],
                                   prompt_template: str) -> str:
        """
        分析單個提案的差異
        
        Args:
            stage1_data: Stage 1 提案資料
            stage2_data: Stage 2 提案資料
            prompt_template: 提示模板
            
        Returns:
            str: LLM 生成的差異分析
        """
        prompt = self.create_diff_prompt(stage1_data, stage2_data, prompt_template)
        
        try:
            response = await self.llm_client.generate_response(prompt)
            return response
        except Exception as e:
            logger.error(f"分析提案差異時發生錯誤: {str(e)}")
            return f"錯誤: {str(e)}"
    
    async def translate_diff(self, diff_text: str) -> str:
        """
        將差異分析翻譯成英文
        
        Args:
            diff_text: 繁體中文的差異分析
            
        Returns:
            str: 英文翻譯
        """
        translation_prompt = f"""
Please translate the following Traditional Chinese proposal difference analysis into English. 
Maintain the structure and professional tone of the original text.

Traditional Chinese text:
{diff_text}

English translation:
"""
        
        try:
            response = await self.translation_client.generate_response(translation_prompt)
            return response
        except Exception as e:
            logger.error(f"翻譯差異分析時發生錯誤: {str(e)}")
            return f"Translation error: {str(e)}"
    
    async def process_proposal_row(self, row: pd.Series, prompt_template: str, idx: int, total_proposals: int) -> Dict[str, Any]:
        """
        處理單個提案行，生成差異分析
        
        Args:
            row: 單個提案的資料行
            prompt_template: 提示模板
            idx: 當前索引
            total_proposals: 總提案數量
            
        Returns:
            Dict[str, Any]: 包含差異分析結果的字典
        """
        proposal_id = str(row['proposal_id'])  # 確保 proposal_id 是字串格式
        logger.info(f"處理提案 {idx + 1}/{total_proposals}: {proposal_id}")
        
        # 準備 Stage 1 資料
        stage1_data = {
            'title': row.get('title_stage1', ''),
            'abstract': row.get('abstract_stage1', ''),
            'detailed_description': row.get('detailed_description_stage1', ''),
            'outline': row.get('outline_stage1', ''),
            'objective': row.get('objective_stage1', '')
        }
        
        # 準備 Stage 2 資料
        stage2_data = {
            'title': row.get('title_stage2', ''),
            'abstract': row.get('abstract_stage2', ''),
            'detailed_description': row.get('detailed_description_stage2', ''),
            'outline': row.get('outline_stage2', ''),
            'objective': row.get('objective_stage2', '')
        }
        
        # 分析差異
        diff_analysis = await self.analyze_proposal_diff(stage1_data, stage2_data, prompt_template)
        
        # 翻譯差異分析
        translated_diff = await self.translate_diff(diff_analysis)
        
        result = {
            'proposal_id': proposal_id,
            'stage_diff': diff_analysis,
            'translated_stage_diff': translated_diff
        }
        
        return result

    async def process_proposals(self, matched_df: pd.DataFrame, prompt_template: str,
                               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        並發處理所有匹配的提案，生成差異分析
        
        Args:
            matched_df: 匹配的提案資料
            prompt_template: 提示模板
            limit: 處理提案數量限制
            
        Returns:
            List[Dict[str, Any]]: 包含差異分析結果的列表
        """
        if limit:
            matched_df = matched_df.head(limit)
            logger.info(f"限制處理 {limit} 筆提案")
        
        total_proposals = len(matched_df)
        logger.info(f"開始並發處理 {total_proposals} 筆提案")
        
        # 創建並發任務
        tasks = []
        for idx, (_, row) in enumerate(matched_df.iterrows()):
            task = self.process_proposal_row(row, prompt_template, idx, total_proposals)
            tasks.append(task)
        
        # 並發執行所有任務
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理結果和例外
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                proposal_id = str(matched_df.iloc[i]['proposal_id'])
                logger.error(f"處理提案 {proposal_id} 時發生錯誤: {str(result)}")
                # 添加錯誤結果
                error_result = {
                    'proposal_id': proposal_id,
                    'stage_diff': f"錯誤: {str(result)}",
                    'translated_stage_diff': f"Error: {str(result)}"
                }
                successful_results.append(error_result)
            else:
                successful_results.append(result)
        
        logger.info(f"成功處理 {len(successful_results)} 筆提案")
        return successful_results
    
    async def aclose(self):
        """關閉 LLM 客戶端"""
        try:
            await self.llm_client.aclose()
            await self.translation_client.aclose()
        except Exception as e:
            logger.warning(f"關閉客戶端時發生錯誤: {str(e)}")

async def run_proposal_diff_analysis(stage1_file: str, stage2_file: str, prompt_file: str,
                                    output_file: str, model_name: str = "o4-mini",
                                    reasoning_effort: str = "high", 
                                    translation_model: str = "gpt-4o-mini",
                                    limit: Optional[int] = None) -> str:
    """
    執行提案差異分析
    
    Args:
        stage1_file: Stage 1 提案檔案路徑
        stage2_file: Stage 2 提案檔案路徑
        prompt_file: 提示模板檔案路徑
        output_file: 輸出檔案路徑
        model_name: LLM 模型名稱
        reasoning_effort: 推理努力級別
        translation_model: 翻譯模型名稱
        limit: 處理提案數量限制
        
    Returns:
        str: 輸出檔案路徑
    """
    logger.info("開始執行提案差異分析")
    
    # 讀取提示模板
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    analyzer = ProposalDiffAnalyzer(
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        translation_model=translation_model
    )
    
    try:
        # 載入資料
        stage1_df, stage2_df = analyzer.load_proposals(stage1_file, stage2_file)
        
        # 找出匹配的提案
        matched_df = analyzer.find_matching_proposals(stage1_df, stage2_df)
        
        if matched_df.empty:
            logger.warning("沒有找到匹配的提案")
            return output_file
        
        # 處理提案差異分析
        results = await analyzer.process_proposals(matched_df, prompt_template, limit)
        
        # 創建結果資料框
        results_df = pd.DataFrame(results)
        
        # 輸出到 Excel
        export_to_excel(results_df, output_file)
        
        logger.info(f"提案差異分析完成，結果已保存至: {output_file}")
        logger.info(f"共處理 {len(results)} 筆提案")
        
        return output_file
        
    except Exception as e:
        logger.error(f"執行提案差異分析時發生錯誤: {str(e)}")
        raise
    finally:
        await analyzer.aclose()

def run_proposal_diff_analysis_sync(stage1_file: str, stage2_file: str, prompt_file: str,
                                   output_file: str, model_name: str = "o4-mini",
                                   reasoning_effort: str = "high",
                                   translation_model: str = "gpt-4o-mini", 
                                   limit: Optional[int] = None) -> str:
    """
    同步版本的提案差異分析執行函數
    
    Args:
        stage1_file: Stage 1 提案檔案路徑
        stage2_file: Stage 2 提案檔案路徑
        prompt_file: 提示模板檔案路徑
        output_file: 輸出檔案路徑
        model_name: LLM 模型名稱
        reasoning_effort: 推理努力級別
        translation_model: 翻譯模型名稱
        limit: 處理提案數量限制
        
    Returns:
        str: 輸出檔案路徑
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            run_proposal_diff_analysis(
                stage1_file=stage1_file,
                stage2_file=stage2_file,
                prompt_file=prompt_file,
                output_file=output_file,
                model_name=model_name,
                reasoning_effort=reasoning_effort,
                translation_model=translation_model,
                limit=limit
            )
        )
        return result
    finally:
        loop.close() 