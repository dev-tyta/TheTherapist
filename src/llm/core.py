# llm_core.py
from langchain_core.tools import tool
from langchain_community.llms.ollama import Ollama
from langchain_ollama import OllamaLLM
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import FAISS
from pathlib import Path
from typing import Annotated
import os

class FAISSVectorSearch:
    """Encapsulated vector search operations"""
    
    def __init__(
        self,
        embedding_model: HuggingFaceBgeEmbeddings,
        db_path: Path,
        k: int = 5
    ):
        self.vectorstore = FAISS.load_local(
            str(db_path),
            embedding_model,
            allow_dangerous_deserialization=True
        )
        self.k = k

    def __call__(self, query: str) -> str:
        """Search interface"""
        results = self.vectorstore.similarity_search(query, k=self.k)
        return "\n".join([res.page_content for res in results])

class TheTherapistLLM:
    """LLM wrapper with proper resource management"""
    
    def __init__(
        self,
        model_name: str = "llama3.1",
        temperature: float = 0.7,
        max_retries: int = 3
    ):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=temperature,
            max_retries=max_retries
        )
        self._session_active = False

    def generate(self, prompt: str) -> str:
        """Safely generate responses"""
        if not self._session_active:
            self._start_session()
            
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            raise LLMError(f"Generation failed: {str(e)}")

    def _start_session(self) -> None:
        """Resource-intensive initialization"""
        try:
            # Add any session setup logic here  
            self._session_active = True
        except Exception as e:
            raise LLMError(f"Session initialization failed: {str(e)}")

class LLMError(Exception):
    """Custom exception for LLM operations"""
    pass