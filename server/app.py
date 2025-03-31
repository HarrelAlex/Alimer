from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import json
import requests
from bs4 import BeautifulSoup
import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
import ollama
import torch
import nltk
from nltk.tokenize import sent_tokenize
import concurrent.futures
from urllib.parse import urlparse, urljoin
import time
import logging
from werkzeug.utils import secure_filename
import os
import re

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize the semantic search model
print("Loading semantic search model...")
retriever_model = SentenceTransformer('all-mpnet-base-v2')
print("Semantic search model loaded successfully!")
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


def extract_text_from_pdf(pdf_file):
    try:
        extracted_text = []
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    extracted_text.append({
                        "page": page_num + 1,
                        "text": text.strip()
                    })
        return extracted_text
    except Exception as e:
        print(f"Error reading the PDF: {e}")
        return []

def chunk_text(text_data, chunk_size=500, overlap=100):
    chunks = []
    for entry in text_data:
        words = entry["text"].split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append({
                "page": entry["page"],
                "text": chunk
            })
    return chunks

def generate_summary(text_chunks):

    # Combine all text chunks into a single string for summarization
    full_text = " ".join(chunk["text"] for chunk in text_chunks)

    prompt = f"Summarize the following text:\n{full_text}"  

    # Generate summary using the Ollama model
    summary = generate_answer(prompt)
    return summary

def retrieve_relevant_context(query, text_chunks, top_k=5):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    retriever_model.to(device)
    
    query_embedding = retriever_model.encode(query, convert_to_tensor=True).to(device)
    chunk_texts = [chunk["text"] for chunk in text_chunks]
    chunk_embeddings = retriever_model.encode(chunk_texts, convert_to_tensor=True).to(device)
    
    scores = util.pytorch_cos_sim(query_embedding, chunk_embeddings)[0]
    top_k = min(top_k, len(scores))
    
    if top_k == 0:
        return []
    
    top_results = scores.topk(k=top_k)
    relevant_chunks = [text_chunks[idx] for idx in top_results.indices]
    return relevant_chunks

def generate_answer(prompt):
    try:
        response = ollama.chat(
            model='mistral',
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant that answers questions based strictly on the provided context in a detailed summary. If the information is not in the context, say you do not know.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.7,
                'top_p': 0.9,
                'max_tokens': 500
            }
        )
        return response['message']['content'].strip()
    except Exception as e:
        print(f"Error generating answer: {e}")
        return "Sorry, I couldn't generate an answer due to a model error."

@app.route('/extract-text', methods=['POST'])
def extract_text():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        extracted_text = extract_text_from_pdf(filepath)
        os.remove(filepath)  # Clean up the uploaded file

        # Generate summary from the extracted text
        summary = generate_summary(extracted_text)
        length = len(summary.split())
        return jsonify({
            'extractedText': extracted_text,
            'summary': summary,
            'text_length': length
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/query', methods=['POST'])
def process_query():
    try:
        data = request.json
        query = data.get('query')
        text_chunks = data.get('extractedText', [])
        
        if not query or not text_chunks:
            return jsonify({'error': 'Missing query or text data'}), 400
        
        # Chunk the text and retrieve relevant context
        chunks = chunk_text(text_chunks)
        relevant_chunks = retrieve_relevant_context(query, chunks)
        
        if not relevant_chunks:
            return jsonify({'answer': "I couldn't find any relevant information in the document."})
        
        # Generate answer using the relevant context
        context = " ".join([chunk["text"] for chunk in relevant_chunks])
        prompt = f"Context: {context}\nQuestion: {query}\nProvide a detailed answer based only on the given context:"
        answer = generate_answer(prompt)
        
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

class DifficultyLevel(Enum):
    VeryEasy = 1
    Easy = 2
    Medium = 3
    Hard = 4
    VeryHard = 5

class ConfidenceLevel(Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"

# Data Classes
@dataclass
class TopicResponse:
    question_id: str
    difficulty: DifficultyLevel
    is_correct: bool
    quality_score: float
    timestamp: datetime

@dataclass
class TopicCompetence:
    score: float
    confidence: ConfidenceLevel
    last_updated: datetime
    responses: List[TopicResponse] = field(default_factory=list)

@dataclass
class Student:
    user_id: str
    competence_scores: Dict[str, Dict[str, TopicCompetence]] = field(default_factory=dict)

class CompetenceScoreCalculator:
    @staticmethod
    def calculate_competence_score(topic: str, responses: List[TopicResponse]) -> float:
        if not responses:
            return 0

        total_questions = len(responses)
        correct_answers = sum(1 for r in responses if r.is_correct)
        accuracy = correct_answers / total_questions

        weighted_difficulty_score = sum(
            r.difficulty.value * r.quality_score for r in responses if r.is_correct
        )
        total_difficulty = sum(r.difficulty.value for r in responses)

        accuracy_weight = min(0.6, 0.4 + (total_questions / 100))
        difficulty_weight = 1 - accuracy_weight

        raw_score = (
            (accuracy * accuracy_weight +
             (weighted_difficulty_score / total_difficulty) * difficulty_weight) * 100
        )
        final_score = 100 / (1 + pow(2.71828, -0.1 * (raw_score - 50)))

        return round(final_score, 2)

    @staticmethod
    def calculate_confidence(responses: List[TopicResponse]) -> ConfidenceLevel:
        total_questions = len(responses)
        if total_questions < 5:
            return ConfidenceLevel.Low
        if total_questions < 20:
            return ConfidenceLevel.Medium
        return ConfidenceLevel.High

def generate_mcq_questions(topic: str, num_questions: int = 5) -> List[Dict]:
    try:
        prompt = f"Generate {num_questions} multiple-choice questions (MCQs) on the topic of {topic}. Each question should have 4 options and a correct answer. Provide the response as a valid JSON list with fields: 'question', 'options', 'correct_option', and 'difficulty' (1-5). The 'correct_option' should be the index (1-4) of the correct answer, not the text of the correct answer."
        
        response = ollama.chat(
            model='mistral',
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant that generates multiple-choice questions. Always provide a valid JSON response with correct_option as an integer index.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.7,
                'top_p': 0.9,
                'max_tokens': 1000
            }
        )
        
        content = response['message']['content'].strip()
        content = re.sub(r'^```(json)?|```$', '', content, flags=re.MULTILINE).strip()
        
        questions = json.loads(content)
        
        validated_questions = []
        for q in questions:
            validated_q = {
                'question': str(q['question']),
                'options': [str(opt) for opt in q['options']],
                'correct_option': int(q.get('correct_option', 0)),
                'difficulty': int(q.get('difficulty', 2))
            }
            
            if not (1 <= validated_q['correct_option'] <= 4):
                validated_q['correct_option'] = 1  # Default to first option if invalid
            
            if not (1 <= validated_q['difficulty'] <= 5):
                validated_q['difficulty'] = 2  # Default to medium difficulty
            
            if len(validated_q['options']) != 4:
                continue  # Skip questions without 4 options
            
            validated_questions.append(validated_q)
        
        return validated_questions
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing questions: {e}")
        return []
    except Exception as e:
        print(f"Error generating questions: {e}")
        return []

# API Routes
@app.route('/generate-mcq', methods=['POST'])
def generate_mcq():
    try:
        data = request.json
        topic = data.get('topic')
        num_questions = data.get('num_questions', 5)
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
            
        questions = generate_mcq_questions(topic, num_questions)
        
        if not questions:
            return jsonify({"error": "Failed to generate questions"}), 500
            
        # Add topic to the response for reference
        response_data = {
            "topic": topic,
            "questions": [
                {
                    "id": str(uuid.uuid4()),
                    "question": q["question"],
                    "options": q["options"],
                    "correct_option": q["correct_option"],
                    "difficulty": q["difficulty"]
                } for q in questions
            ]
        }
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/calculate-competence', methods=['POST'])
def calculate_competence():
    try:
        data = request.json
        topic = data.get('topic')
        user_responses = data.get('responses', [])
        
        if not topic or not user_responses:
            return jsonify({"error": "Topic and responses are required"}), 400
            
        # Convert responses to TopicResponse objects
        topic_responses = []
        for resp in user_responses:
            topic_responses.append(
                TopicResponse(
                    question_id=resp.get("question_id", str(uuid.uuid4())),
                    difficulty=DifficultyLevel(resp.get("difficulty", 2)),
                    is_correct=resp.get("is_correct", False),
                    quality_score=resp.get("quality_score", 1.0),
                    timestamp=datetime.now()
                )
            )
            
        competence_score = CompetenceScoreCalculator.calculate_competence_score(topic, topic_responses)
        confidence_level = CompetenceScoreCalculator.calculate_confidence(topic_responses)
        
        response_data = {
            "topic": topic,
            "competence_score": competence_score,
            "normalized_score": round(competence_score / 10, 2),  # Normalize to 0-10 scale
            "confidence_level": confidence_level.value,
            "total_questions": len(topic_responses),
            "correct_answers": sum(1 for r in topic_responses if r.is_correct)
        }
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    def __init__(self):
        # Initialize readability metrics
        pass
        
    def analyze_text_complexity(self, text: str) -> Dict:
        """Analyze text complexity using readability metrics and LLM"""
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
        
        # Get LLM assessment
        llm_assessment = self._assess_with_llm(sample_text)
        
        return llm_assessment
    
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
    
    def _assess_with_llm(self, text: str) -> Dict:
        """Use LLM to assess complexity"""
        try:
            prompt = f"""
            Analyze the following educational text and determine its complexity level. 
            
            Text sample:
            ---
            {text[:1500]}
            ---
            
            Rate the complexity on a scale from 1 to 5:
            1 - Beginner (elementary knowledge, simple concepts, basic terminology)
            2 - Elementary (foundational knowledge, straightforward concepts)
            3 - Intermediate (requires some prior knowledge, moderate complexity)
            4 - Advanced (complex concepts, specialized knowledge required)
            5 - Expert (highly technical, deep domain expertise needed)
            
            Consider factors like:
            - Technical vocabulary density
            - Concept complexity
            - Required prior knowledge
            - Abstraction level
            
            Provide a JSON response with:
            - complexity_level (integer 1-5)
            - confidence (float 0-1)
            - factors (object with assessment of key complexity factors)
            """
            
            response = ollama.chat(
                model='mistral',
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are an expert educational content analyst. Analyze text to determine its complexity level.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': 0.1,
                    'top_p': 0.9,
                    'max_tokens': 500
                }
            )
            
            content = response['message']['content'].strip()
            # Extract JSON if it's wrapped in code blocks
            content = re.sub(r'^```(json)?|```$', '', content, flags=re.MULTILINE).strip()
            
            result = json.loads(content)
            
            # Validate and ensure correct structure
            complexity_level = int(result.get('complexity_level', 3))
            if not 1 <= complexity_level <= 5:
                complexity_level = 3
                
            confidence = float(result.get('confidence', 0.7))
            if not 0 <= confidence <= 1:
                confidence = 0.7
                
            factors = result.get('factors', {})
            if not isinstance(factors, dict):
                factors = {}
                
            return {
                "complexity_level": complexity_level,
                "confidence": confidence,
                "factors": factors
            }
            
        except Exception as e:
            # Fallback to intermediate complexity
            return {
                "complexity_level": ComplexityLevel.INTERMEDIATE.value,
                "confidence": 0.5,
                "factors": {
                    "technical_vocabulary": "moderate",
                    "concept_complexity": "moderate",
                    "prior_knowledge": "some required"
                }
            }

class ResourcesFinder:
    def __init__(self):
        self.scraper = ContentScraper()
        self.analyzer = ComplexityAnalyzer()
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
                html = self.scraper.fetch_webpage(url)
                if not html:
                    continue
                    
                text = self.scraper.extract_text_content(html)
                if len(text.strip()) < 100:  # Skip pages with little content
                    continue
                    
                meta = self.scraper.extract_meta_information(html, url)
                complexity = self.analyzer.analyze_text_complexity(text)
                
                # Only include resources within +/- 1 complexity level of target
                if abs(complexity["complexity_level"] - complexity_level) <= 3:
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
                print(e)
                
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
# Initialize resources finder
resources_finder = ResourcesFinder()

@app.route('/materials', methods=['POST'])
def get_materials():
    try:
        data = request.json
        topic = data.get('topic')
        competence_score = data.get('competence_score', 50)  # 0-100 scale
        material_types = data.get('material_types', ['article', 'tutorial', 'video'])
        num_results = data.get('num_results', 5)
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
            
        # Convert competence score to complexity level (inverse relationship)
        # Lower competence = need simpler materials
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
            
        # Find materials with appropriate complexity
        materials = resources_finder.search_materials(topic, complexity_level, num_results)
        
        # Filter by material types if specified
        if material_types and material_types != ['all']:
            materials = [m for m in materials if m['material_type'] in material_types]
            
        return jsonify({
            "topic": topic,
            "competence_score": competence_score,
            "complexity_level": complexity_level,
            "materials": materials
        })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)