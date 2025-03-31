import React, { useState } from "react";
import TopicSelection from "./Topicsel";
import MCQQuiz from "./Mcqquiz";
import LearningMaterials from "./Materials";

interface Question {
  id: string;
  question: string;
  options: string[];
  correct_option: number;
  difficulty: number;
}

interface CompetenceResult {
  topic: string;
  competence_score: number;
  normalized_score: number;
  confidence_level: string;
  total_questions: number;
  correct_answers: number;
  responses: any[];
}

const Recommend: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<"topic" | "quiz" | "results">(
    "topic"
  );
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentTopic, setCurrentTopic] = useState<string>("");
  const [competenceResult, setCompetenceResult] = useState<CompetenceResult>({
    topic: "null",
    competence_score: 0,
    normalized_score: 0,
    confidence_level: "null",
    total_questions: 0,
    correct_answers: 0,
    responses: [],
  });
  const handleQuestionsGenerated = (
    generatedQuestions: Question[],
    topic: string
  ) => {
    setQuestions(generatedQuestions);
    setCurrentTopic(topic);
    setCurrentStep("quiz");
  };

  const handleQuizComplete = (results: any) => {
    // Handle quiz completion, possibly storing results and moving to results page
    setCompetenceResult(results);
    setCurrentStep("results");
    console.log(results);
    // Store results for competence calculation
  };

  const handleTryAnotherTopic = () => {
    setCurrentStep("topic");
    setQuestions([]);
    setCurrentTopic("");
    setCompetenceResult({
      topic: "null",
      competence_score: 0,
      normalized_score: 0,
      confidence_level: "null",
      total_questions: 0,
      correct_answers: 0,
      responses: [],
    });
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h2 className="title stitle">Personalized Learning Assistant</h2>
      </header>

      <main className="app-content">
        {currentStep === "topic" && (
          <TopicSelection
            onQuestionsGenerated={(questions, topic) =>
              handleQuestionsGenerated(questions, topic)
            }
          />
        )}

        {currentStep === "quiz" && questions.length > 0 && (
          <MCQQuiz
            questions={questions}
            topic={currentTopic}
            onComplete={handleQuizComplete}
          />
        )}

        {currentStep === "results" && (
          <div className="results-container">
            <h2>Your Assessment Results</h2>
            <div className="results-summary">
              <p>
                <strong>Topic:</strong> {currentTopic}
              </p>
              <p>
                <strong>Competence Score:</strong>{" "}
                {competenceResult.competence_score}/100
              </p>
              <p>
                <strong>Questions Answered:</strong>{" "}
                {competenceResult.total_questions}
              </p>
              <p>
                <strong>Correct Answers:</strong>{" "}
                {competenceResult.correct_answers}
              </p>
            </div>

            {/* Integrate LearningMaterials component */}
            <div className="learning-resources-section">
              <h3>Personalized Learning Resources</h3>
              <LearningMaterials
                topic={currentTopic}
                competenceScore={competenceResult.competence_score}
              />
            </div>

            <div className="navigation-buttons">
              <button
                className="try-another-button"
                onClick={handleTryAnotherTopic}
              >
                Try Another Topic
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Recommend;
