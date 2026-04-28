import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

def create_prompt_with_examples(proposal_data: Dict[str, Any], language: str = "zh-tw") -> str:
    """
    創建用於 LLM 的提示文字，包含範例和提案資料
    
    Args:
        proposal_data: 提案資料字典，包含 id, title, abstract, detailed_description, outline, objective 和 reviews
        language: 生成摘要的語言 ('zh-tw' 或 'en')
    
    Returns:
        str: 格式化的提示文字
    """
    # 提取提案資料
    proposal_id = proposal_data.get('id', 'unknown')
    title = proposal_data.get('title', '')
    abstract = proposal_data.get('abstract', '')
    detailed_description = proposal_data.get('detailed_description', '')
    outline = proposal_data.get('outline', '')
    objective = proposal_data.get('objective', '')
    reviews = proposal_data.get('reviews', [])
    
    # 將評論格式化為文字
    reviews_text = ""
    for i, review in enumerate(reviews, 1):
        vote = review.get('vote', '')
        comment = review.get('comment', '')
        reviews_text += f"Review {i} [Vote: {vote}]: {comment}\n\n"
    
    # 根據語言選擇提示模板
    if language == "zh-tw":
        prompt = f"""
你是 PyCon Taiwan 的計劃審核委員會成員。你需要審核一個演講提案並生成一份摘要，說明該提案的優缺點，以及拒絕或接受該提案的理由。

請根據以下提案資料和評審意見，生成一份全面的摘要：

# 提案資料
提案 ID: {proposal_id}
標題: {title}
摘要: {abstract}
詳細描述: {detailed_description}
大綱: {outline}
目標: {objective}

# 評審意見
{reviews_text}

請以繁體中文回答，並遵循以下結構：
1. 提案摘要：簡要介紹提案內容，確保保留原提案的主要觀點和價值主張。
2. 優點：列出評審意見中提到的主要優點。
3. 缺點/改進建議：列出評審意見中提到的主要缺點或可改進的地方。
4. 綜合評價：根據評審意見給出一個整體評價，說明為什麼該提案應該被接受或拒絕。

請保持客觀、專業、有建設性，並確保你的建議能幫助演講者改進他們的提案。
"""
    else:  # English
        prompt = f"""
You are a member of the PyCon Taiwan Program Committee. You need to review a talk proposal and generate a summary that outlines the strengths and weaknesses of the proposal, and the reasons for rejecting or accepting it.

Based on the following proposal data and reviewer comments, generate a comprehensive summary:

# Proposal Data
Proposal ID: {proposal_id}
Title: {title}
Abstract: {abstract}
Detailed Description: {detailed_description}
Outline: {outline}
Objective: {objective}

# Reviewer Comments
{reviews_text}

Please respond in English and follow this structure:
1. Proposal Summary: Briefly introduce the proposal content, ensuring to preserve the main points and value proposition of the original proposal.
2. Strengths: List the major strengths mentioned in the review comments.
3. Weaknesses/Suggestions for Improvement: List the major weaknesses or areas for improvement mentioned in the review comments.
4. Overall Assessment: Based on the review comments, provide an overall assessment explaining why the proposal should be accepted or rejected.

Please be objective, professional, and constructive, ensuring your suggestions help the speaker improve their proposal.
"""
    
    return prompt

def export_to_excel(df: pd.DataFrame, output_file: str) -> str:
    """
    將結果資料框輸出到 Excel 檔案
    
    Args:
        df: 包含結果的 Pandas DataFrame
        output_file: 輸出 Excel 檔案的路徑
    
    Returns:
        str: 輸出檔案的路徑
    """
    # 確保輸出目錄存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 將評論列轉換為字串以避免 Excel 輸出問題
    if 'original_reviews' in df.columns:
        df['original_reviews_text'] = df['original_reviews'].apply(
            lambda reviews: '\n\n'.join([f"Review {i+1} [Vote: {r.get('vote', '')}]: {r.get('comment', '')}" 
                                           for i, r in enumerate(reviews)])
        )
        # 移除原始評論欄位以避免 Excel 輸出問題
        df = df.drop(columns=['original_reviews'])
    
    # 輸出到 Excel
    df.to_excel(output_file, index=False)
    return output_file

def create_template_analysis_file(output_file: str) -> str:
    """
    創建用於分析的模板 Excel 檔案
    
    Args:
        output_file: 輸出模板檔案的路徑
        
    Returns:
        str: 輸出檔案的路徑
    """
    # 確保輸出目錄存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 創建模板 DataFrame
    template_df = pd.DataFrame({
        'category': ['Clarity of content', 'Technical depth', 'Novelty/Originality', 
                     'Relevance to audience', 'Speaker expertise', 'Overall quality'],
        'description': [
            'Is the proposal clearly written and well-structured?',
            'Does the proposal demonstrate sufficient technical depth?',
            'Is the topic original or presenting a novel perspective?',
            'Is the topic relevant to the PyCon audience?',
            'Does the speaker show expertise in the subject matter?',
            'Overall assessment of the proposal quality'
        ],
        'rating_1_to_5': [0, 0, 0, 0, 0, 0],
        'notes': ['', '', '', '', '', ''],
        'common_issues': ['', '', '', '', '', '']
    })
    
    # 創建一個 Excel 寫入器
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 寫入模板數據
        template_df.to_excel(writer, sheet_name='Analysis Template', index=False)
        
        # 創建資料總覽工作表
        summary_df = pd.DataFrame({
            'metric': ['Total proposals analyzed', 'Average overall quality (1-5)', 
                       'Most common issue', 'Highest rated category', 'Lowest rated category'],
            'value': ['', '', '', '', ''],
            'notes': ['', '', '', '', '']
        })
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # 創建分類工作表
        categories_df = pd.DataFrame({
            'category': ['Topic A', 'Topic B', 'Topic C'],
            'count': [0, 0, 0],
            'average_quality': [0, 0, 0],
            'common_issues': ['', '', ''],
            'notes': ['', '', '']
        })
        categories_df.to_excel(writer, sheet_name='Topic Categories', index=False)
    
    return output_file 