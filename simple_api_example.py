"""
簡化的 PyCon API 使用範例
可以直接在 Jupyter notebook 中使用
"""

import sys
import os

# 添加 src 目錄到路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.pycon_api_client import PyConAPIClient

# === 快速開始 ===

# 1. 初始化客戶端
client = PyConAPIClient(staging=True)  # 使用 staging 環境

# 2. 登入 (請替換為你的實際帳號密碼)
username = "your_username"  # 替換為你的用戶名
password = "your_password"  # 替換為你的密碼

if client.login(username, password):
    print("✅ 登入成功!")
    
    # 3. 取得所有 reviews (GET)
    reviews = client.get_llm_reviews()
    print(f"📋 找到 {len(reviews)} 個 reviews")
    
    # 顯示前幾個
    for i, review in enumerate(reviews[:3]):
        print(f"  {i+1}. ID: {review['id']}, 提案: {review['proposal']['title'][:50]}..., 投票: {review['vote']}")
    
    # 4. 取得特定 review (GET)
    if reviews:
        first_review_id = reviews[0]['id']
        review_detail = client.get_llm_review(first_review_id)
        print(f"\n📄 Review {first_review_id} 詳細資訊:")
        print(f"  提案: {review_detail['proposal']['title']}")
        print(f"  投票: {review_detail['vote']}")
        print(f"  摘要: {review_detail['summary'][:100]}...")
    
    # 5. 更新 review (PUT)
    # 注意：這會實際更新資料，請小心使用！
    """
    if reviews:
        review_id = reviews[0]['id']
        update_data = {
            "proposal_id": reviews[0]['proposal']['id'],
            "stage": reviews[0]['stage'],
            "categories": reviews[0]['categories'],
            "summary": reviews[0]['summary'],
            "comment": "這是更新後的評論",  # 新的評論
            "translated_summary": reviews[0]['translated_summary'],
            "translated_comment": reviews[0]['translated_comment'],
            "vote": "+1",  # 新的投票
            "stage_diff": reviews[0]['stage_diff'],
            "translated_stage_diff": reviews[0]['translated_stage_diff'],
        }
        
        if client.update_llm_review(review_id, update_data):
            print(f"✅ 成功更新 Review {review_id}")
        else:
            print(f"❌ 更新失敗")
    """
    
else:
    print("❌ 登入失敗，請檢查用戶名和密碼")

# 6. 關閉連線
client.close()


# === 函數封裝版本 ===

def get_authenticated_client(username, password, staging=True):
    """取得已認證的客戶端"""
    client = PyConAPIClient(staging=staging)
    if client.login(username, password):
        return client
    else:
        client.close()
        return None

def get_all_reviews(client):
    """取得所有 reviews"""
    return client.get_llm_reviews()

def update_review_vote(client, review_id, new_vote, new_comment=None):
    """更新 review 的投票和評論"""
    # 先取得當前資料
    current_review = client.get_llm_review(review_id)
    if not current_review:
        return False
    
    # 準備更新資料
    update_data = {
        "proposal_id": current_review['proposal']['id'],
        "stage": current_review['stage'],
        "categories": current_review['categories'],
        "summary": current_review['summary'],
        "comment": new_comment or current_review['comment'],
        "translated_summary": current_review['translated_summary'],
        "translated_comment": current_review['translated_comment'],
        "vote": new_vote,
        "stage_diff": current_review['stage_diff'],
        "translated_stage_diff": current_review['translated_stage_diff'],
    }
    
    return client.update_llm_review(review_id, update_data)

# === 使用範例 ===
"""
# 在 Jupyter notebook 中使用：

# 1. 初始化和登入
client = get_authenticated_client("your_username", "your_password")

if client:
    # 2. 取得所有 reviews
    reviews = get_all_reviews(client)
    print(f"找到 {len(reviews)} 個 reviews")
    
    # 3. 更新特定 review
    success = update_review_vote(client, review_id=1, new_vote="+1", new_comment="更新的評論")
    print(f"更新結果: {success}")
    
    # 4. 關閉連線
    client.close()
""" 