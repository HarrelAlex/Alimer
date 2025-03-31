import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict
import ollama
import json
import re

# Enums
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

def main():
    user_id = str(uuid.uuid4())
    topic = input("Enter the topic you want to study: ")
    
    questions = generate_mcq_questions(topic)
    if not questions:
        print("Failed to generate questions. Please try again.")
        return

    responses = []
    for i, question in enumerate(questions):
        print(f"\nQuestion {i+1}: {question['question']}")
        for j, option in enumerate(question['options']):
            print(f"{j+1}. {option}")
        
        while True:
            try:
                answer = int(input("Your answer (option number): "))
                if 1 <= answer <= 4:
                    break
                print("Please enter a number between 1 and 4.")
            except ValueError:
                print("Invalid input. Please enter a number.")
        
        is_correct = (answer == question['correct_option'])
        response = TopicResponse(
            question_id=str(uuid.uuid4()),
            difficulty=DifficultyLevel(question['difficulty']),
            is_correct=is_correct,
            quality_score=1.0,
            timestamp=datetime.now()
        )
        responses.append(response)

    competence_score = CompetenceScoreCalculator.calculate_competence_score(topic, responses)
    confidence = CompetenceScoreCalculator.calculate_confidence(responses)

    print(f"\nYour competency score for {topic} is: {competence_score}/10")
    print(f"Confidence level: {confidence.value}")

if __name__ == "__main__":
    main()