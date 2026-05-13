from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-74ab513e45e3486ba0488ca43840b9cf")
MODEL_NAME = os.getenv("MULTI_AGENT_MODEL_NAME", "qwen3.6-max-preview")

AGENT_OUTPUT_ROOT = Path(r"D:\CAutoD\solidworks_agent\agent_output")
KNOWLEDGE_BASE_ROOT = PACKAGE_ROOT / "knowledge_base"
