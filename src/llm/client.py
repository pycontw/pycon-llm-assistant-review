import os
import json
import logging
import asyncio
import warnings
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from openai import AsyncOpenAI
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# 忽略 httpx 在事件循環關閉時的警告
warnings.filterwarnings("ignore", message=".*Event loop is closed.*")

class LLMClient:
    """Base class for LLM Clients"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the base LLM client"""
        self.api_key = api_key
        
    async def generate_response(self, prompt: str) -> Any:
        """Generate a response from the LLM"""
        raise NotImplementedError("Subclasses must implement this method")
        
    async def retry_with_exponential_backoff(
        self, 
        operation, 
        max_retries: int = 5, 
        initial_delay: float = 1.0, 
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        errors_to_retry: Optional[List[Exception]] = None
    ):
        """Retry an operation with exponential backoff"""
        errors_to_retry = errors_to_retry or [Exception]
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                return await operation()
            except tuple(errors_to_retry) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Operation failed after {max_retries} attempts: {str(e)}")
                    raise
                
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f} seconds...")
                actual_delay = delay * (0.75 + 0.5 * attempt / max_retries)
                await asyncio.sleep(actual_delay)
                delay = min(delay * backoff_factor, max_delay)
                
        return None

class OpenAIClient(LLMClient):
    """Client for OpenAI API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "o3-mini", reasoning_effort: str = "high"):
        """Initialize the OpenAI client"""
        super().__init__(api_key)
        
        env_values = dotenv_values()
        self.api_key = api_key or env_values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.reasoning_effort = reasoning_effort
        
        if not self.api_key:
            logger.error("OpenAI API key is not set")
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info(f"Initialized OpenAI client with model: {self.model}, reasoning effort: {self.reasoning_effort}")
    
    async def _generate_chat_completion(self, prompt: str) -> Any:
        """Generate a chat completion with OpenAI API"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant specialized in analyzing technical proposal data."},
            {"role": "user", "content": prompt}
        ]
        
        # 針對不同模型使用不同參數
        if self.model.startswith("gpt-"):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0
            )
        elif self.model.startswith("o"):
            # 支援 o4 系列模型
            response = await self.client.chat.completions.create(
                model=self.model,
                reasoning_effort=self.reasoning_effort,
                messages=messages
            )
        return response
    
    async def generate_response(self, prompt: str) -> Any:
        """Generate a response from OpenAI with retries"""
        operation = lambda: self._generate_chat_completion(prompt)
        
        errors_to_retry = [
            Exception,
        ]
        
        try:
            response = await self.retry_with_exponential_backoff(
                operation=operation,
                max_retries=5,
                errors_to_retry=errors_to_retry
            )
            
            if hasattr(response, 'choices') and len(response.choices) > 0:
                return response.choices[0].message.content
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate response from OpenAI: {str(e)}")
            return f"Error: {str(e)}"
    
    async def aclose(self):
        """安全關閉客戶端，確保所有連接正確關閉"""
        try:
            # 使用更安全的方式關閉 httpx 客戶端
            # 避免直接訪問底層 httpx 客戶端，而是使用一個更高層級的方法來防止錯誤
            if hasattr(self.client, '_transport_context') and self.client._transport_context:
                transport = getattr(self.client._transport_context, '_transport', None)
                if transport and hasattr(transport, 'close'):
                    transport.close()
            elif hasattr(self.client, 'http_client') and hasattr(self.client.http_client, 'aclose'):
                # 嘗試使用 asyncio.shield 來保護操作不被取消
                try:
                    await asyncio.shield(self.client.http_client.aclose())
                except (asyncio.CancelledError, RuntimeError):
                    pass
            elif hasattr(self.client, '_client') and hasattr(self.client._client, 'aclose'):
                try:
                    await asyncio.shield(self.client._client.aclose())
                except (asyncio.CancelledError, RuntimeError):
                    pass
                
            logger.debug("Successfully closed OpenAI client connections")
        except Exception as e:
            # 記錄錯誤但不拋出異常，以避免影響主程序
            logger.warning(f"Error while closing OpenAI client (this can be safely ignored): {str(e)}")