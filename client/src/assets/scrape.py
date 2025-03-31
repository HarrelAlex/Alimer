import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Tuple, Optional
import json
import nltk
from nltk.tokenize import sent_tokenize
import time
import logging
nltk.download('punkt_tab')
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Download NLTK resources (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class ComplexityLevel(Enum):
    BEGINNER = 1
    ELEMENTARY = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5

class MaterialType(Enum):
    ARTICLE = "article"
    VIDEO = "video"
    TUTORIAL = "tutorial"
    DOCUMENTATION = "documentation"
    COURSE = "course"
    BOOK = "book"
    BLOG = "blog"
    OTHER = "other"

class ContentScraper:
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        self.session.headers.update({'User-Agent': self.user_agents[0]})
        
    def _rotate_user_agent(self):
        """Rotate user agents to avoid being blocked"""
        current = self.session.headers['User-Agent']
        index = self.user_agents.index(current)
        next_index = (index + 1) % len(self.user_agents)
        self.session.headers.update({'User-Agent': self.user_agents[next_index]})
        
    def fetch_webpage(self, url: str) -> Optional[str]:
        """Fetch a webpage and return its HTML content"""
        try:
            self._rotate_user_agent()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
            
    def extract_text_content(self, html: str) -> str:
        """Extract meaningful text content from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        # Extract text from main content areas
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|article|post|main'))
        
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            # Fallback to body if no specific content container found
            text = soup.get_text(separator=' ', strip=True)
            
        # Clean the text
        text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
        text = re.sub(r'\.([A-Z])', r'. \1', text)  # Fix missing spaces after periods
        
        return text
        
    def extract_meta_information(self, html: str, url: str) -> Dict:
        """Extract metadata from the webpage"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else ""
        
        # Extract description
        description = soup.find('meta', attrs={'name': 'description'})
        if not description:
            description = soup.find('meta', attrs={'property': 'og:description'})
        description_text = description['content'] if description and 'content' in description.attrs else ""
        
        # Extract author
        author = soup.find('meta', attrs={'name': 'author'})
        if not author:
            author = soup.find('meta', attrs={'property': 'og:author'})
        author_text = author['content'] if author and 'content' in author.attrs else ""
        
        # Extract date
        date = soup.find('meta', attrs={'name': 'date'})
        if not date:
            date = soup.find('time')
        date_text = date['datetime'] if date and 'datetime' in date.attrs else ""
        if not date_text and date:
            date_text = date.get_text(strip=True)
        
        # Determine material type
        material_type = self._determine_material_type(soup, url)
        
        return {
            "title": title_text,
            "description": description_text,
            "author": author_text,
            "date": date_text,
            "material_type": material_type.value
        }
        
    def _determine_material_type(self, soup: BeautifulSoup, url: str) -> MaterialType:
        """Determine the type of learning material"""
        url_lower = url.lower()
        
        # Check URL patterns
        if 'youtube.com' in url_lower or 'vimeo.com' in url_lower or 'video' in url_lower:
            return MaterialType.VIDEO
        elif 'docs.' in url_lower or 'documentation' in url_lower:
            return MaterialType.DOCUMENTATION
        elif 'tutorial' in url_lower:
            return MaterialType.TUTORIAL
        elif 'course' in url_lower or 'udemy' in url_lower or 'coursera' in url_lower:
            return MaterialType.COURSE
        elif 'blog' in url_lower:
            return MaterialType.BLOG
        elif 'book' in url_lower:
            return MaterialType.BOOK
            
        # Check content patterns
        if soup.find('video') or soup.find('iframe', src=re.compile(r'youtube|vimeo')):
            return MaterialType.VIDEO
        
        # Default to article for text-based content
        return MaterialType.ARTICLE
        
class ComplexityAnalyzer:
    def __init__(self, llm_client=None):
        # Initialize with optional LLM client
        self.llm_client = llm_client
        
    def analyze_text_complexity(self, text: str) -> Dict:
        """Analyze text complexity using readability metrics"""
        if not text or len(text.strip()) < 100:
            return {
                "complexity_level": ComplexityLevel.INTERMEDIATE.value,
                "confidence": 0.5,
                "factors": {
                    "sentence_length": 0,
                    "vocabulary_complexity": 0,
                    "concepts_complexity": 0
                }
            }
        
        # Calculate basic metrics
        sentences = sent_tokenize(text)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        # Sample the text if it's too long
        sample_text = self._sample_text(text, max_len=2000)
        
        # Basic complexity assessment (in absence of LLM)
        complexity_level = self._assess_complexity_basic(sample_text, avg_sentence_length)
        
        # If LLM client is available, use it for better assessment
        if self.llm_client:
            try:
                llm_assessment = self._assess_with_llm(sample_text)
                return llm_assessment
            except Exception as e:
                logger.error(f"LLM assessment failed, using basic assessment: {e}")
                
        # Fallback to basic assessment
        return {
            "complexity_level": complexity_level,
            "confidence": 0.6,
            "factors": {
                "sentence_length": avg_sentence_length,
                "technical_vocabulary": "medium",
                "concept_complexity": "medium"
            }
        }
    
    def _sample_text(self, text: str, max_len: int = 2000) -> str:
        """Sample text to reduce token usage"""
        if len(text) <= max_len:
            return text
            
        # Take first chunk, middle chunk, and last chunk
        chunk_size = max_len // 3
        first_chunk = text[:chunk_size]
        middle_start = len(text) // 2 - chunk_size // 2
        middle_chunk = text[middle_start:middle_start + chunk_size]
        last_chunk = text[-chunk_size:]
        
        return f"{first_chunk}...\n\n{middle_chunk}...\n\n{last_chunk}"
    
    def _assess_complexity_basic(self, text: str, avg_sentence_length: float) -> int:
        """Basic complexity assessment based on sentence length and keyword density"""
        # Count technical terms (simplified approach)
        technical_terms = [
            "algorithm", "framework", "implementation", "architecture", "methodology",
            "paradigm", "optimization", "infrastructure", "interface", "middleware",
            "protocol", "quantum", "synthesis", "theoretical", "proprietary"
        ]
        
        technical_term_count = sum(1 for term in technical_terms if term.lower() in text.lower())
        term_density = technical_term_count / (len(text.split()) / 100)  # Per 100 words
        
        # Determine complexity based on sentence length and term density
        if avg_sentence_length < 12 and term_density < 0.5:
            return ComplexityLevel.BEGINNER.value
        elif avg_sentence_length < 15 and term_density < 1:
            return ComplexityLevel.ELEMENTARY.value
        elif avg_sentence_length < 20 and term_density < 2:
            return ComplexityLevel.INTERMEDIATE.value
        elif avg_sentence_length < 25 and term_density < 4:
            return ComplexityLevel.ADVANCED.value
        else:
            return ComplexityLevel.EXPERT.value
    
    def _assess_with_llm(self, text: str) -> Dict:
        """Use LLM to assess complexity (requires LLM client implementation)"""
        # Implementation depends on the LLM client
        # Mock implementation for now
        return {
            "complexity_level": 3,
            "confidence": 0.7,
            "factors": {
                "technical_vocabulary": "moderate",
                "concept_complexity": "moderate",
                "prior_knowledge": "some required"
            }
        }

class ResourcesFinder:
    def __init__(self, llm_client=None):
        self.scraper = ContentScraper()
        self.analyzer = ComplexityAnalyzer(llm_client)
        self.search_engines = [
            "https://www.google.com/search?q=",
            "https://duckduckgo.com/?q="
        ]
        
    def search_materials(self, topic: str, complexity_level: int, num_results: int = 5) -> List[Dict]:
        """Search for learning materials on a given topic with appropriate complexity"""
        complexity_terms = {
            1: ["beginner", "introduction", "basic", "101", "tutorial"],
            2: ["elementary", "fundamentals", "guide", "primer"],
            3: ["intermediate", "guide", "overview"],
            4: ["advanced", "comprehensive", "in-depth"],
            5: ["expert", "technical", "specialized", "research"]
        }
        
        complexity_term = complexity_terms.get(complexity_level, [""])[0]
        query = f"{topic} {complexity_term} tutorial"
        
        # Search for URLs
        urls = self._search_web(query, num_results * 2)  # Get more results as some might fail
        
        # Process and filter the results
        results = []
        for url in urls[:num_results*2]:
            try:
                logger.info(f"Processing URL: {url}")
                html = self.scraper.fetch_webpage(url)
                if not html:
                    continue
                    
                text = self.scraper.extract_text_content(html)
                if len(text.strip()) < 100:  # Skip pages with little content
                    continue
                    
                meta = self.scraper.extract_meta_information(html, url)
                complexity = self.analyzer.analyze_text_complexity(text)
                
                # Only include resources within +/- 1 complexity level of target
                if abs(complexity["complexity_level"] - complexity_level) <= 1:
                    results.append({
                        "url": url,
                        "title": meta["title"],
                        "description": meta["description"],
                        "author": meta["author"],
                        "date": meta["date"],
                        "material_type": meta["material_type"],
                        "complexity": complexity["complexity_level"],
                        "complexity_confidence": complexity["confidence"],
                        "complexity_factors": complexity["factors"],
                        "preview_text": text[:500] + "..." if len(text) > 500 else text
                    })
                    
                    if len(results) >= num_results:
                        break
                        
                # Respect rate limits
                time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                
        return results[:num_results]
        
    def _search_web(self, query: str, num_results: int) -> List[str]:
        """Mock web search function that returns URLs
        In a real implementation, you would use a search API or web scraping"""
        
        # This is a mockup. In production, you would:
        # 1. Use a search API like Google Custom Search, Bing Search, or SerpAPI
        # 2. Or scrape search results (respecting robots.txt)
        
        # For the prototype, return hardcoded education websites with the query params
        base_urls = [
            "https://www.khanacademy.org/search?page_search_query=",
            "https://www.w3schools.com/search/search.asp?q=",
            "https://developer.mozilla.org/en-US/search?q=",
            "https://www.tutorialspoint.com/index.htm?search=",
            "https://www.geeksforgeeks.org/search/?q=",
            "https://www.youtube.com/results?search_query=",
            "https://medium.com/search?q=",
            "https://dev.to/search?q=",
            "https://www.freecodecamp.org/news/search/?query=",
            "https://stackoverflow.com/search?q="
        ]
        
        # For demo/prototype purposes only - in production use a proper search API
        encoded_query = query.replace(' ', '+')
        return [f"{base}{encoded_query}" for base in base_urls[:num_results]]

def find_learning_resources(topic, competence_score=50, material_types=None, num_results=5):
    """
    Standalone function to find learning resources based on topic and competence level
    
    Args:
        topic (str): The learning topic to search for
        competence_score (int): User's competence score (0-100)
        material_types (list): Types of materials to include (articles, videos, etc.)
        num_results (int): Number of results to return
        
    Returns:
        dict: Dictionary with topic, complexity level, and materials list
    """
    if material_types is None:
        material_types = ['article', 'tutorial', 'video']
        
    # Convert competence score to complexity level (inverse relationship)
    if competence_score < 20:
        complexity_level = 1  # Beginner
    elif competence_score < 40:
        complexity_level = 2  # Elementary
    elif competence_score < 60:
        complexity_level = 3  # Intermediate
    elif competence_score < 80:
        complexity_level = 4  # Advanced
    else:
        complexity_level = 5  # Expert
        
    # Initialize resources finder
    # You can optionally pass an LLM client for better complexity analysis
    resources_finder = ResourcesFinder()
    
    # Find materials with appropriate complexity
    materials = resources_finder.search_materials(topic, complexity_level, num_results)
    
    # Filter by material types if specified
    if material_types and material_types != ['all']:
        materials = [m for m in materials if m['material_type'] in material_types]
        
    return {
        "topic": topic,
        "competence_score": competence_score,
        "complexity_level": complexity_level,
        "materials": materials
    }

# Example usage
if __name__ == '__main__':
    # Example: Find Python learning resources for someone with moderate knowledge
    topic = input("Enter learning topic: ")
    competence = int(input("Enter your competence level (0-100): "))
    
    print(f"Searching for materials on '{topic}'...")
    results = find_learning_resources(
        topic=topic,
        competence_score=competence,
        material_types=['article', 'tutorial', 'video', 'documentation'],
        num_results=3
    )
    
    print(f"\nFound {len(results['materials'])} resources for '{topic}' (Complexity Level: {results['complexity_level']}):")
    for i, material in enumerate(results['materials'], 1):
        print(f"\n{i}. {material['title']}")
        print(f"   URL: {material['url']}")
        print(f"   Type: {material['material_type']} (Complexity: {material['complexity']})")
        print(f"   Description: {material['description'][:100]}..." if material['description'] else "   No description available")