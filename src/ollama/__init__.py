"""
Ollama integration module for webcam detection system.

Provides image description capabilities using local Ollama Gemma3 model.
"""

from .client import OllamaClient, OllamaConfig, OllamaError

__all__ = ['OllamaClient', 'OllamaConfig', 'OllamaError'] 