import os
from tavily import TavilyClient

async def tavily_search(query: str, num_results: int = 5):
    key = os.getenv("TAVILY_API_KEY")
    tavily_client = TavilyClient(api_key=key)
    response = tavily_client.search(query, num_results=num_results, include_images=True)
    return response
