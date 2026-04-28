"""
PyCon Taiwan API client — 自動登入 + session 管理,用於操作 LLM Reviews 後台。

⚠️  Security note(交接給未來維護者):
本檔早期版本的所有 requests 呼叫都帶有 ``verify=False``,當時是為了繞過
staging 環境自簽憑證的測試摩擦。

``verify=False`` 會關掉 TLS 憑證驗證,代表網路路徑上的攻擊者(公共 Wi-Fi、
被入侵的 proxy 等)可以攔截登入 POST 並竊取帳號密碼 — 對攜帶 credentials
的呼叫來說是真實風險。

目前已恢復 ``requests`` 預設行為(``verify=True``)。若你在私有 staging 上
遇到自簽憑證問題,**請不要**把 ``verify`` 改回 ``False``;改用以下方式:

    self.session.verify = "/path/to/ca-bundle.pem"

在 ``__init__`` 中設定一次,既明確又集中,還能透過環境變數注入,日後審查
也容易 grep 到。
"""

import requests
import time
import logging
from typing import Dict, Any, Optional, List
from requests.sessions import Session
import json

logger = logging.getLogger(__name__)

class PyConAPIClient:
    """PyCon Taiwan API 客戶端，提供自動登入和 session 管理"""
    
    def __init__(self, base_url: str = "https://tw.pycon.org", 
                 staging: bool = False,
                 username: str = None, 
                 password: str = None):
        """
        初始化 API 客戶端
        
        Args:
            base_url: API 基礎 URL
            staging: 是否使用 staging 環境
            username: 登入用戶名
            password: 登入密碼
        """
        self.base_url = "https://staging.pycon.tw" if staging else base_url
        self.username = username
        self.password = password
        self.session = Session()
        self._csrf_token = None
        self._session_id = None
        
        # 設置預設 headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        })
        
        logger.info(f"Initialized PyCon API Client for {self.base_url}")
    
    def login(self, username: str = None, password: str = None) -> bool:
        """
        自動登入到 PyCon 系統
        
        Args:
            username: 用戶名 (可選，會覆蓋初始化時的設定)
            password: 密碼 (可選，會覆蓋初始化時的設定)
            
        Returns:
            bool: 登入是否成功
        """
        try:
            # 使用傳入的憑證或初始化時的憑證
            login_username = username or self.username
            login_password = password or self.password
            
            if not login_username or not login_password:
                logger.error("Username and password are required for login")
                return False
            
            # 首先獲取登入頁面以取得 CSRF token
            login_page_url = f"{self.base_url}/accounts/login/"
            response = self.session.get(login_page_url)
            response.raise_for_status()
            
            # 從回應中提取 CSRF token
            csrf_token = self._extract_csrf_token(response)
            if not csrf_token:
                logger.error("Failed to extract CSRF token from login page")
                return False
            
            self._csrf_token = csrf_token
            
            # 更新 session headers
            self.session.headers.update({
                'X-CSRFToken': csrf_token,
                'Referer': login_page_url,
            })
            
            # 準備登入資料
            login_data = {
                'username': login_username,
                'password': login_password,
                'csrfmiddlewaretoken': csrf_token,
            }
            
            # 發送登入請求
            login_response = self.session.post(
                login_page_url,
                data=login_data,
            )
            
            # 檢查登入是否成功
            if login_response.status_code == 200 and 'sessionid' in self.session.cookies:
                self._session_id = self.session.cookies.get('sessionid')
                logger.info("Successfully logged in to PyCon")
                return True
            else:
                logger.error(f"Login failed. Status code: {login_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
    
    def _extract_csrf_token(self, response) -> Optional[str]:
        """從回應中提取 CSRF token"""
        try:
            # 嘗試從 cookies 中取得
            csrf_token = response.cookies.get('csrftoken')
            if csrf_token:
                return csrf_token
            
            # 嘗試從 HTML 中解析
            if 'csrfmiddlewaretoken' in response.text:
                import re
                pattern = r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']'
                match = re.search(pattern, response.text)
                if match:
                    return match.group(1)
            
            logger.warning("Could not extract CSRF token")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting CSRF token: {str(e)}")
            return None
    
    def _ensure_authenticated(self) -> bool:
        """確保已經認證，如果沒有則嘗試登入"""
        if not self._session_id or 'sessionid' not in self.session.cookies:
            logger.info("No valid session found, attempting to login...")
            return self.login()
        return True
    
    def get_llm_reviews(self, **params) -> List[Dict[str, Any]]:
        """
        取得 LLM reviews 列表
        
        Args:
            **params: 查詢參數 (如 page, limit 等)
            
        Returns:
            List[Dict]: LLM reviews 資料
        """
        if not self._ensure_authenticated():
            logger.error("Authentication failed, cannot fetch LLM reviews")
            return []
        
        try:
            url = f"{self.base_url}/prs/api/proposals/llm-reviews/"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 處理分頁回應
            if isinstance(data, dict) and 'results' in data:
                logger.info(f"Successfully fetched {len(data['results'])} LLM reviews")
                return data['results']
            elif isinstance(data, list):
                logger.info(f"Successfully fetched {len(data)} LLM reviews")
                return data
            else:
                logger.warning("Unexpected response format")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching LLM reviews: {str(e)}")
            return []
    
    def get_llm_review(self, review_id: int) -> Optional[Dict[str, Any]]:
        """
        取得特定的 LLM review
        
        Args:
            review_id: Review ID
            
        Returns:
            Dict: LLM review 資料
        """
        if not self._ensure_authenticated():
            logger.error("Authentication failed, cannot fetch LLM review")
            return None
        
        try:
            url = f"{self.base_url}/prs/api/proposals/llm-reviews/{review_id}/"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched LLM review {review_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching LLM review {review_id}: {str(e)}")
            return None
    
    def update_llm_review(self, review_id: int, data: Dict[str, Any]) -> bool:
        """
        更新 LLM review
        
        Args:
            review_id: Review ID
            data: 要更新的資料
            
        Returns:
            bool: 更新是否成功
        """
        if not self._ensure_authenticated():
            logger.error("Authentication failed, cannot update LLM review")
            return False
        
        try:
            url = f"{self.base_url}/prs/api/proposals/llm-reviews/{review_id}/"
            
            # 確保 CSRF token 在 headers 中
            if self._csrf_token:
                self.session.headers.update({'X-CSRFToken': self._csrf_token})
            
            response = self.session.put(url, json=data)
            response.raise_for_status()
            
            logger.info(f"Successfully updated LLM review {review_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating LLM review {review_id}: {str(e)}")
            return False
    
    def create_llm_review(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        建立新的 LLM review
        
        Args:
            data: Review 資料
            
        Returns:
            Dict: 建立的 review 資料
        """
        if not self._ensure_authenticated():
            logger.error("Authentication failed, cannot create LLM review")
            return None
        
        try:
            url = f"{self.base_url}/prs/api/proposals/llm-reviews/"
            
            # 確保 CSRF token 在 headers 中
            if self._csrf_token:
                self.session.headers.update({'X-CSRFToken': self._csrf_token})
            
            response = self.session.post(url, json=data)
            response.raise_for_status()
            
            result = response.json()
            logger.info("Successfully created new LLM review")
            return result
            
        except Exception as e:
            logger.error(f"Error creating LLM review: {str(e)}")
            return None
    
    def close(self):
        """關閉 session"""
        if self.session:
            self.session.close()
            logger.info("API client session closed")


# 使用範例函數
def example_usage():
    """使用範例"""
    
    # 初始化客戶端
    client = PyConAPIClient(staging=True)  # 使用 staging 環境
    
    # 手動登入（需要提供實際的用戶名和密碼）
    if client.login("your_username", "your_password"):
        
        # 取得所有 LLM reviews
        reviews = client.get_llm_reviews()
        print(f"Found {len(reviews)} reviews")
        
        # 取得特定 review
        if reviews:
            first_review = client.get_llm_review(reviews[0]['id'])
            print(f"First review: {first_review['proposal']['title']}")
            
            # 更新 review
            update_data = {
                "vote": "+1",
                "comment": "Updated comment",
                "summary": "Updated summary"
            }
            success = client.update_llm_review(reviews[0]['id'], update_data)
            print(f"Update successful: {success}")
    
    # 關閉客戶端
    client.close()


if __name__ == "__main__":
    example_usage() 