import httpx
from config import DefaultConfig
CONFIG = DefaultConfig()

async def make_get_request(url):
    async with httpx.AsyncClient() as client:
        print(CONFIG.base_url + url)
        response = await client.get(CONFIG.base_url + url, timeout=None)
        return response

async def make_post_request(url, payload):
    async with httpx.AsyncClient() as client:
        response = await client.post(CONFIG.base_url + url, json=payload)
        return response
