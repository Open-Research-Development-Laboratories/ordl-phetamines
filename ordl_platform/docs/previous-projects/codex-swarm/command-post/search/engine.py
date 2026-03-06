#!/usr/bin/env python3
"""
ORDL Search Engine - Real implementation with Playwright and SerpAPI
Classification: TOP SECRET//NOFORN
"""
import os
import json
import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote_plus, urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("search_engine")


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    rank: int
    scraped_content: Optional[str] = None
    metadata: Optional[Dict] = None


class PlaywrightScraper:
    """Headless browser scraping using Playwright"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self._lock = asyncio.Lock()
    
    async def _init_browser(self):
        """Initialize browser if not already done"""
        if self.browser is None:
            try:
                from playwright.async_api import async_playwright
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                logger.info("Playwright browser initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Playwright: {e}")
                raise
    
    async def scrape(self, url: str, wait_for: str = None, timeout: int = 30000) -> Dict[str, Any]:
        """Scrape a URL using headless browser"""
        await self._init_browser()
        
        async with self._lock:
            page = None
            try:
                page = await self.browser.new_page()
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                # Set user agent
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                # Navigate and wait for load
                response = await page.goto(url, wait_until='networkidle', timeout=timeout)
                
                if wait_for:
                    await page.wait_for_selector(wait_for, timeout=10000)
                
                # Wait a bit for dynamic content
                await asyncio.sleep(2)
                
                # Extract data
                title = await page.title()
                content = await page.content()
                
                # Extract text content
                text_content = await page.evaluate('''() => {
                    const scripts = document.querySelectorAll('script, style, nav, footer, header');
                    scripts.forEach(s => s.remove());
                    return document.body.innerText;
                }''')
                
                # Extract links
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => ({href: a.href, text: a.innerText.trim()}))
                        .filter(a => a.href.startsWith('http'));
                }''')
                
                # Extract meta description
                meta_desc = await page.evaluate('''() => {
                    const meta = document.querySelector('meta[name="description"]') ||
                                document.querySelector('meta[property="og:description"]');
                    return meta ? meta.content : '';
                }''')
                
                return {
                    'url': url,
                    'title': title,
                    'content': text_content[:10000],  # Limit content
                    'html': content[:50000],
                    'description': meta_desc,
                    'links': links[:20],
                    'status_code': response.status if response else 0,
                    'scraped_at': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Scraping error for {url}: {e}")
                return {
                    'url': url,
                    'error': str(e),
                    'scraped_at': datetime.utcnow().isoformat()
                }
            finally:
                if page:
                    await page.close()
    
    async def search_google(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Search Google using headless browser"""
        await self._init_browser()
        
        page = None
        try:
            page = await self.browser.new_page()
            
            # Navigate to Google
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
            await page.goto(search_url, wait_until='networkidle')
            
            # Wait for results
            await page.wait_for_selector('div#search', timeout=10000)
            
            # Extract results
            results = await page.evaluate('''(num) => {
                const items = [];
                const elements = document.querySelectorAll('div.g, div.tF2Cxc, [data-ved]');
                
                for (let i = 0; i < Math.min(elements.length, num); i++) {
                    const el = elements[i];
                    const link = el.querySelector('a[href]');
                    const title = el.querySelector('h3');
                    const snippet = el.querySelector('span.VwiC3b, div.VwiC3b, .s3v94d');
                    
                    if (link && title) {
                        items.push({
                            title: title.innerText,
                            url: link.href,
                            snippet: snippet ? snippet.innerText : ''
                        });
                    }
                }
                return items;
            }''', num_results)
            
            search_results = []
            for idx, item in enumerate(results):
                if item.get('url') and not item['url'].startswith('/'):
                    search_results.append(SearchResult(
                        title=item.get('title', ''),
                        url=item.get('url', ''),
                        snippet=item.get('snippet', '')[:300],
                        source='google',
                        rank=idx + 1
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Google search error: {e}")
            return []
        finally:
            if page:
                await page.close()
    
    async def close(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None


class SerpAPIClient:
    """SerpAPI integration for search"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        self.base_url = 'https://serpapi.com/search'
    
    async def search(self, query: str, engine: str = 'google', num_results: int = 10) -> List[SearchResult]:
        """Search using SerpAPI"""
        if not self.api_key:
            logger.warning("No SerpAPI key configured")
            return []
        
        params = {
            'q': query,
            'engine': engine,
            'num': num_results,
            'api_key': self.api_key,
            'output': 'json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        organic = data.get('organic_results', [])
                        for idx, item in enumerate(organic[:num_results]):
                            results.append(SearchResult(
                                title=item.get('title', ''),
                                url=item.get('link', ''),
                                snippet=item.get('snippet', ''),
                                source='serpapi',
                                rank=idx + 1
                            ))
                        
                        return results
                    else:
                        logger.error(f"SerpAPI error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"SerpAPI request failed: {e}")
            return []


class SearchEngine:
    """Main search engine combining multiple sources"""
    
    def __init__(self):
        self.serpapi = SerpAPIClient()
        self.playwright = None
        self.proxy_pool = []
        self._load_proxies()
    
    def _load_proxies(self):
        """Load proxy list from environment"""
        proxy_env = os.getenv('PROXY_LIST', '')
        if proxy_env:
            self.proxy_pool = [p.strip() for p in proxy_env.split(',') if p.strip()]
            logger.info(f"Loaded {len(self.proxy_pool)} proxies")
    
    async def _get_playwright(self) -> PlaywrightScraper:
        """Get or create Playwright scraper"""
        if self.playwright is None:
            self.playwright = PlaywrightScraper()
        return self.playwright
    
    async def search(self, query: str, engine: str = "auto", num_results: int = 10) -> List[SearchResult]:
        """
        Search across multiple engines
        
        Args:
            query: Search query
            engine: 'google', 'serpapi', or 'auto'
            num_results: Number of results to return
        """
        results = []
        
        # Try SerpAPI first if available and auto/serpapi selected
        if engine in ('auto', 'serpapi') and self.serpapi.api_key:
            serp_results = await self.serpapi.search(query, num_results=num_results)
            results.extend(serp_results)
        
        # Fallback to Playwright for Google if needed
        if engine in ('auto', 'google') and len(results) < num_results:
            try:
                pw = await self._get_playwright()
                pw_results = await pw.search_google(query, num_results=num_results)
                # Merge results, avoiding duplicates
                existing_urls = {r.url for r in results}
                for r in pw_results:
                    if r.url not in existing_urls:
                        results.append(r)
            except Exception as e:
                logger.error(f"Playwright search failed: {e}")
        
        # Sort by rank and limit
        results.sort(key=lambda x: x.rank)
        return results[:num_results]
    
    async def deep_search(self, query: str, num_results: int = 10, 
                         scrape_content: bool = False) -> Dict[str, Any]:
        """
        Perform deep search with optional content scraping
        
        Args:
            query: Search query
            num_results: Number of search results
            scrape_content: Whether to scrape full content of each result
        """
        start_time = datetime.utcnow()
        
        # Get search results
        results = await self.search(query, num_results=num_results)
        
        scraped_pages = []
        
        # Optionally scrape full content
        if scrape_content and results:
            pw = await self._get_playwright()
            
            # Scrape top 3 results
            for result in results[:3]:
                try:
                    scraped = await pw.scrape(result.url)
                    if 'error' not in scraped:
                        scraped_pages.append({
                            'url': result.url,
                            'title': scraped.get('title', ''),
                            'content': scraped.get('content', '')[:5000],
                            'description': scraped.get('description', ''),
                            'links': len(scraped.get('links', []))
                        })
                        result.scraped_content = scraped.get('content', '')[:2000]
                except Exception as e:
                    logger.error(f"Failed to scrape {result.url}: {e}")
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "query": query,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source,
                    "rank": r.rank,
                    "scraped_preview": r.scraped_content[:500] if r.scraped_content else None
                }
                for r in results
            ],
            "scraped_pages": scraped_pages,
            "total_results": len(results),
            "search_time_seconds": round(elapsed, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def scrape_url(self, url: str, wait_for: str = None) -> Dict[str, Any]:
        """Scrape a single URL"""
        pw = await self._get_playwright()
        return await pw.scrape(url, wait_for=wait_for)
    
    async def close(self):
        """Cleanup resources"""
        if self.playwright:
            await self.playwright.close()
            self.playwright = None


# Singleton instance
_search_engine: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    """Get singleton search engine instance"""
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine


# Synchronous wrapper for convenience
def search_sync(query: str, num_results: int = 10) -> Dict[str, Any]:
    """Synchronous search wrapper"""
    engine = get_search_engine()
    return asyncio.run(engine.deep_search(query, num_results))


if __name__ == "__main__":
    # Test the search engine
    async def test():
        engine = get_search_engine()
        
        print("Testing search...")
        results = await engine.deep_search("python asyncio tutorial", num_results=5, scrape_content=True)
        
        print(json.dumps(results, indent=2))
        
        await engine.close()
    
    asyncio.run(test())
