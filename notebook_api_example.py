"""
PyCon API 自動化登入範例 - 專為 Jupyter Notebook 設計
==================================================

這個模組提供簡單易用的 API 來操作 PyCon LLM Reviews，
無需手動複製 cookie，自動處理登入和 session 管理。

使用方式：
1. 修改下方的 USERNAME 和 PASSWORD
2. 執行相關的 cell
3. 使用提供的函數進行 GET/PUT 操作
"""

# ======= 設定區域 =======
USERNAME = "your_username"  # 請替換為你的實際用戶名
PASSWORD = "your_password"  # 請替換為你的實際密碼
USE_STAGING = True  # True 使用 staging 環境，False 使用 production

# ======= 匯入必要的模組 =======
import sys
import os
import logging
from typing import List, Dict, Any, Optional

# 設定路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# 設定日誌（避免太多輸出）
logging.basicConfig(level=logging.WARNING)

# ======= 主要 API 類別 =======
class SimpleAPI:
    """簡化的 PyCon API 介面"""
    
    def __init__(self, username: str, password: str, staging: bool = True):
        from utils.pycon_api_client import PyConAPIClient
        
        self.client = PyConAPIClient(staging=staging)
        self.authenticated = False
        
        # 自動登入
        if self.client.login(username, password):
            self.authenticated = True
            print(f"✅ 成功登入 {'Staging' if staging else 'Production'} 環境")
        else:
            print("❌ 登入失敗，請檢查用戶名和密碼")
    
    def get_reviews(self) -> List[Dict[str, Any]]:
        """取得所有 LLM reviews"""
        if not self.authenticated:
            print("❌ 未登入，無法取得資料")
            return []
        
        reviews = self.client.get_llm_reviews()
        print(f"📋 取得 {len(reviews)} 個 reviews")
        return reviews
    
    def get_review(self, review_id: int) -> Optional[Dict[str, Any]]:
        """取得特定的 review"""
        if not self.authenticated:
            print("❌ 未登入，無法取得資料")
            return None
        
        review = self.client.get_llm_review(review_id)
        if review:
            print(f"📄 取得 Review {review_id}: {review['proposal']['title']}")
        else:
            print(f"❌ 找不到 Review {review_id}")
        return review
    
    def update_vote(self, review_id: int, vote: str, comment: str = None) -> bool:
        """更新 review 的投票"""
        if not self.authenticated:
            print("❌ 未登入，無法更新資料")
            return False
        
        # 先取得當前資料
        current = self.client.get_llm_review(review_id)
        if not current:
            print(f"❌ 找不到 Review {review_id}")
            return False
        
        # 準備更新資料
        update_data = {
            "proposal_id": current['proposal']['id'],
            "stage": current['stage'],
            "categories": current['categories'],
            "summary": current['summary'],
            "comment": comment or current['comment'],
            "translated_summary": current['translated_summary'],
            "translated_comment": current['translated_comment'],
            "vote": vote,
            "stage_diff": current['stage_diff'],
            "translated_stage_diff": current['translated_stage_diff'],
        }
        
        success = self.client.update_llm_review(review_id, update_data)
        if success:
            print(f"✅ 成功更新 Review {review_id}: {vote}")
        else:
            print(f"❌ 更新失敗")
        return success
    
    def show_reviews_summary(self, limit: int = 10):
        """顯示 reviews 摘要"""
        reviews = self.get_reviews()
        
        print(f"\n📊 Reviews 摘要 (前 {min(limit, len(reviews))} 個):")
        print("-" * 80)
        
        for i, review in enumerate(reviews[:limit]):
            proposal = review['proposal']
            print(f"{i+1:2d}. ID: {review['id']:2d} | "
                  f"投票: {review['vote']:2s} | "
                  f"提案: {proposal['title'][:40]}...")
    
    def close(self):
        """關閉連線"""
        if hasattr(self, 'client'):
            self.client.close()
            print("👋 已關閉連線")

# ======= 快速使用函數 =======

def quick_start():
    """快速開始 - 初始化 API 並取得基本資訊"""
    global api
    api = SimpleAPI(USERNAME, PASSWORD, USE_STAGING)
    
    if api.authenticated:
        api.show_reviews_summary()
        print("\n🎉 API 已初始化完成！")
        print("💡 你可以使用以下命令：")
        print("   - api.get_reviews()           # 取得所有 reviews")
        print("   - api.get_review(id)          # 取得特定 review")
        print("   - api.update_vote(id, vote)   # 更新投票 (+1, +0, -1)")
        print("   - api.show_reviews_summary()  # 顯示摘要")
        print("   - api.close()                 # 關閉連線")
    
    return api

# ======= Jupyter Notebook 專用函數 =======

def batch_update_votes(review_votes: Dict[int, str]):
    """批次更新投票
    
    Args:
        review_votes: {review_id: vote} 的字典，例如 {1: '+1', 2: '-1', 3: '+0'}
    """
    if 'api' not in globals() or not api.authenticated:
        print("❌ 請先執行 quick_start() 初始化 API")
        return
    
    success_count = 0
    total_count = len(review_votes)
    
    print(f"🔄 開始批次更新 {total_count} 個 reviews...")
    
    for review_id, vote in review_votes.items():
        if api.update_vote(review_id, vote):
            success_count += 1
    
    print(f"✅ 完成！成功更新 {success_count}/{total_count} 個 reviews")

def filter_reviews_by_vote(vote: str) -> List[Dict[str, Any]]:
    """根據投票篩選 reviews"""
    if 'api' not in globals() or not api.authenticated:
        print("❌ 請先執行 quick_start() 初始化 API")
        return []
    
    all_reviews = api.get_reviews()
    filtered = [r for r in all_reviews if r['vote'] == vote]
    
    print(f"🔍 找到 {len(filtered)} 個投票為 '{vote}' 的 reviews")
    return filtered

# ======= 使用說明 =======
print("""
🚀 PyCon API 自動化工具已載入！

📝 使用步驟：
1. 修改上方的 USERNAME 和 PASSWORD
2. 執行: api = quick_start()
3. 開始使用 API 功能

💡 常用範例：
```python
# 初始化
api = quick_start()

# 取得所有 reviews
reviews = api.get_reviews()

# 查看特定 review
review = api.get_review(1)

# 更新投票
api.update_vote(1, '+1')  # 接受
api.update_vote(2, '-1')  # 拒絕  
api.update_vote(3, '+0')  # 中性

# 批次更新
batch_update_votes({1: '+1', 2: '-1', 3: '+0'})

# 篩選特定投票的 reviews
positive_reviews = filter_reviews_by_vote('+1')

# 關閉連線
api.close()
```

⚠️  注意：這會實際修改伺服器上的資料，請謹慎使用！
""")

# 全域變數供 notebook 使用
api = None 