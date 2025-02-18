import os
import asyncio
import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from src.llm.core.config import settings
from src.llm.memory.vector_store import FAISSVectorSearch
from src.llm.models.schemas import ContextInfo
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper

class ContextAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialize_tools()

    def _initialize_tools(self) -> None:
        """Lazy-load expensive resources"""
        self.web_search = TavilySearchResults(
            max_results=settings.TAVILY_MAX_RESULTS,
            include_answer=settings.TAVILY_INCLUDE_ANSWER,
            include_images=settings.TAVILY_INCLUDE_IMAGES,
            api_wrapper=TavilySearchAPIWrapper(tavily_api_key=settings.TAVILY_API_KEY)
        )
        
        self.vector_search = FAISSVectorSearch()

    def process(self, query: str) -> ContextInfo:
        """Gather context from multiple sources"""
        web_context = self._get_web_context(query)
        vector_context = self._get_vector_context(query)

        combined_context = f"{web_context}\n\n{vector_context}"
        
        self._log_action(action="context_gathered", metadata={"query": query, "web_context": web_context, "vector_context": vector_context}, level=logging.INFO)  
        return ContextInfo(
            query=query,
            web_context=web_context,
            vector_context=vector_context,
            combined_context=combined_context,
        )
    
    def _get_web_context(self, query: str) -> str:
        try:
            results = self.web_search.invoke(query)
            return "\n".join([res["content"] for res in results])
        except Exception as e:
            self._log_action(action="web_search_error", metadata={"error": str(e)}, level=logging.ERROR)
            return "Web search unavailable"
    
    def _get_vector_context(self, query: str) -> str:
        try:
            return self.vector_search.search(query)
        except Exception as e:
            self._log_action(action="vector_search_error", metadata={"error": str(e)}, level=logging.ERROR)
            return "Vector search unavailable"


    # Updated async web search handling
    async def _get_web_context_async(self, query: str) -> str:
        """Async version of web context retrieval"""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.web_search.invoke(query)
            )
            return "\n".join([res["content"] for res in results])
        except Exception as e:
            self._log_action(action="web_search_error", metadata={"error": str(e)}, level=logging.ERROR)
            return "Web search unavailable"

    async def process_async(self, query: str) -> ContextInfo:
        """Async version with parallel context gathering"""
        web_task = self._get_web_context_async(query)
        vector_task = asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._get_vector_context(query)
        )
        
        web_context, vector_context = await asyncio.gather(web_task, vector_task)
        
        combined_context = f"{web_context}\n\n{vector_context}"
        
        self._log_action(action="context_gathered", metadata={"query": query}, level=logging.INFO)
        return ContextInfo(
            query=query,
            web_context=web_context,
            vector_context=vector_context,
            combined_context=combined_context,
        )