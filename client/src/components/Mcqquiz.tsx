import React, { useState } from "react";
import axios from "axios";
import "./Mcqquiz.css";

interface Question {
  id: string;
  question: string;
  options: string[];
  correct_option: number;
  difficulty: number;
}

interface UserResponse {
  question_id: string;
  difficulty: number;
  is_correct: boolean;
  quality_score: number;
}

interface MCQQuizProps {
  questions: Question[];
  topic: string;
  onComplete: (results: any) => void;
}

const MCQQuiz: React.FC<MCQQuizProps> = ({ questions, topic, onComplete }) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [userResponses, setUserResponses] = useState<UserResponse[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const currentQuestion = questions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === questions.length - 1;

  const handleOptionSelect = (optionIndex: number) => {
    setSelectedOption(optionIndex);
  };

  const handleNext = async () => {
    if (selectedOption === null) {
      setError("Please select an answer");
      return;
    }

    const isCorrect = selectedOption + 1 === currentQuestion.correct_option;

    const response: UserResponse = {
      question_id: currentQuestion.id,
      difficulty: currentQuestion.difficulty,
      is_correct: isCorrect,
      quality_score: 1.0,
    };

    const updatedResponses = [...userResponses, response];
    setUserResponses(updatedResponses);
    setError("");

    if (isLastQuestion) {
      // Submit all responses for competence calculation
      await calculateCompetence(updatedResponses);
    } else {
      // Move to next question
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setSelectedOption(null);
    }
  };

  const calculateCompetence = async (responses: UserResponse[]) => {
    setIsSubmitting(true);

    try {
      const response = await axios.post(
        `http://localhost:5000/calculate-competence`,
        {
          topic: topic,
          responses: responses,
        }
      );

      onComplete({
        ...response.data,
        responses: responses,
      });
    } catch (err) {
      console.error("Error calculating competence:", err);
      setError("Failed to calculate results. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mcq-quiz-container">
      <div className="mcq-quiz-card">
        <div className="card-header">
          <h2 className="card-title">Topic: {topic}</h2>
          <div className="quiz-progress">
            Question {currentQuestionIndex + 1} of {questions.length}
          </div>
        </div>

        <div className="card-content">
          <div className="question-container">
            <h3 className="question-text">{currentQuestion.question}</h3>

            <div className="options-list">
              {currentQuestion.options.map((option, index) => (
                <div
                  key={index}
                  className={`option-item ${
                    selectedOption === index ? "selected" : ""
                  }`}
                  onClick={() => handleOptionSelect(index)}
                >
                  <span className="option-marker">
                    {String.fromCharCode(65 + index)}
                  </span>
                  <span className="option-text">{option}</span>
                </div>
              ))}
            </div>

            {error && <p className="error-message">{error}</p>}
          </div>

          <button
            className="next-button"
            onClick={handleNext}
            disabled={selectedOption === null || isSubmitting}
          >
            {isLastQuestion
              ? isSubmitting
                ? "Calculating..."
                : "Finish Quiz"
              : "Next Question"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MCQQuiz;
