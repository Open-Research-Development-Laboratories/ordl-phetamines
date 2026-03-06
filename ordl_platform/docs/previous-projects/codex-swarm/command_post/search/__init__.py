"""ORDL Search Module - Web Search & Scraping"""
from .engine import get_search_engine, SearchEngine, SearchResult, PlaywrightScraper, SerpAPIClient

__all__ = ['get_search_engine', 'SearchEngine', 'SearchResult', 'PlaywrightScraper', 'SerpAPIClient']
