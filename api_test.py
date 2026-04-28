#!/usr/bin/env python3
"""
PyCon API 測試腳本
使用自動化登入來操作 LLM Reviews API
"""

import logging
import sys
import os
from getpass import getpass

# 添加 src 目錄到路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.pycon_api_client import PyConAPIClient

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """主要測試函數"""
    
    print("🚀 PyCon API 自動化測試工具")
    print("=" * 50)
    
    # 取得用戶輸入
    print("\n📝 請輸入登入資訊:")
    username = input("用戶名: ")
    password = getpass("密碼: ")
    
    # 選擇環境
    env_choice = input("\n🌍 選擇環境 (1: Production, 2: Staging) [2]: ").strip()
    staging = env_choice != "1"
    
    print(f"\n🔗 連接到 {'Staging' if staging else 'Production'} 環境...")
    
    # 初始化客戶端
    client = PyConAPIClient(staging=staging)
    
    try:
        # 登入
        print("\n🔐 正在登入...")
        if not client.login(username, password):
            print("❌ 登入失敗！請檢查用戶名和密碼。")
            return
        
        print("✅ 登入成功！")
        
        # 測試 GET 操作
        print("\n📋 取得 LLM Reviews...")
        reviews = client.get_llm_reviews()
        
        if not reviews:
            print("❌ 沒有找到任何 reviews")
            return
        
        print(f"✅ 找到 {len(reviews)} 個 reviews")
        
        # 顯示前幾個 reviews
        print("\n📄 前 3 個 Reviews:")
        for i, review in enumerate(reviews[:3]):
            proposal = review.get('proposal', {})
            print(f"  {i+1}. ID: {review['id']}, "
                  f"提案: {proposal.get('title', 'N/A')[:50]}..., "
                  f"投票: {review.get('vote', 'N/A')}")
        
        # 互動式操作
        while True:
            print("\n🛠️  可用操作:")
            print("  1. 查看特定 review")
            print("  2. 更新 review")
            print("  3. 重新取得列表")
            print("  0. 退出")
            
            choice = input("\n選擇操作 [0-3]: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                # 查看特定 review
                try:
                    review_id = int(input("輸入 Review ID: "))
                    review = client.get_llm_review(review_id)
                    if review:
                        print(f"\n📄 Review {review_id}:")
                        print(f"  提案: {review['proposal']['title']}")
                        print(f"  投票: {review['vote']}")
                        print(f"  摘要: {review['summary'][:100]}...")
                        print(f"  評論: {review['comment'][:100]}...")
                    else:
                        print(f"❌ 找不到 Review {review_id}")
                except ValueError:
                    print("❌ 請輸入有效的數字")
            
            elif choice == "2":
                # 更新 review
                try:
                    review_id = int(input("輸入要更新的 Review ID: "))
                    
                    # 先取得當前資料
                    current_review = client.get_llm_review(review_id)
                    if not current_review:
                        print(f"❌ 找不到 Review {review_id}")
                        continue
                    
                    print(f"\n📄 當前 Review {review_id}:")
                    print(f"  提案: {current_review['proposal']['title']}")
                    print(f"  當前投票: {current_review['vote']}")
                    
                    # 取得新的投票值
                    print("\n投票選項: +1 (接受), +0 (中性), -1 (拒絕)")
                    new_vote = input(f"新投票 [{current_review['vote']}]: ").strip()
                    if not new_vote:
                        new_vote = current_review['vote']
                    
                    # 取得新的評論
                    print("\n輸入新評論 (留空保持不變):")
                    new_comment = input().strip()
                    if not new_comment:
                        new_comment = current_review['comment']
                    
                    # 準備更新資料
                    update_data = {
                        "proposal_id": current_review['proposal']['id'],
                        "stage": current_review['stage'],
                        "categories": current_review['categories'],
                        "summary": current_review['summary'],
                        "comment": new_comment,
                        "translated_summary": current_review['translated_summary'],
                        "translated_comment": current_review['translated_comment'],
                        "vote": new_vote,
                        "stage_diff": current_review['stage_diff'],
                        "translated_stage_diff": current_review['translated_stage_diff'],
                    }
                    
                    # 執行更新
                    print("\n🔄 正在更新...")
                    if client.update_llm_review(review_id, update_data):
                        print("✅ 更新成功！")
                    else:
                        print("❌ 更新失敗")
                        
                except ValueError:
                    print("❌ 請輸入有效的數字")
                except Exception as e:
                    print(f"❌ 更新時發生錯誤: {e}")
            
            elif choice == "3":
                # 重新取得列表
                print("\n🔄 重新取得 Reviews...")
                reviews = client.get_llm_reviews()
                print(f"✅ 找到 {len(reviews)} 個 reviews")
                
                for i, review in enumerate(reviews[:5]):
                    proposal = review.get('proposal', {})
                    print(f"  {i+1}. ID: {review['id']}, "
                          f"提案: {proposal.get('title', 'N/A')[:50]}..., "
                          f"投票: {review.get('vote', 'N/A')}")
            
            else:
                print("❌ 無效的選擇")
    
    except KeyboardInterrupt:
        print("\n\n👋 程式已中斷")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
    finally:
        # 關閉客戶端
        client.close()
        print("\n👋 已關閉連線")

if __name__ == "__main__":
    main() 