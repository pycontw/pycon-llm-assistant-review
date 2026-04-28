#!/usr/bin/env python3
"""
PyCon TW 2025 Proposal Review System
主要入口點腳本，用於從項目根目錄運行 LLM 評審和評估工具
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

# 直接執行主模組中的 main 函數
from main_llm import main

if __name__ == "__main__":
    main() 