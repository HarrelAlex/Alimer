import React, { useState } from "react";
import axios from "axios";
import "./Topicsel.css";

interface Question {
  id: string;
  question: string;
  options: string[];
  correct_option: number;
  difficulty: number;
}
interface TopicSelectionProps {
  onQuestionsGenerated: (questions: Question[], topic: string) => void;
}

const TopicSelection: React.FC<TopicSelectionProps> = ({
  onQuestionsGenerated,
}) => {
  const [topic, setTopic] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleTopicChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTopic(e.target.value);
    if (error) setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!topic.trim()) {
      setError("Please enter a topic");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await axios.post(`http://localhost:5000/generate-mcq`, {
        topic: topic.trim(),
        num_questions: 5,
      });

      if (response.data.questions && response.data.questions.length > 0) {
        onQuestionsGenerated(response.data.questions, response.data.topic);
      } else {
        setError("Failed to generate questions. Please try a different topic.");
      }
    } catch (err) {
      console.error("Error generating MCQs:", err);
      setError(
        "An error occurred while generating questions. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="topic-selection-container">
      <div className="topic-selection-card">
        <div className="card-header">
          <h2 className="card-title">Topic Selection</h2>
          <p className="card-description">
            Enter a topic you want to learn about and be tested on
          </p>
        </div>

        <div className="card-content">
          <form onSubmit={handleSubmit}>
            <div className="input-group">
              <input
                type="text"
                placeholder="Enter a topic (e.g., 'React Hooks', 'Machine Learning Basics')"
                value={topic}
                onChange={handleTopicChange}
                disabled={isLoading}
                className="topic-input"
              />
              {error && <p className="error-message">{error}</p>}
            </div>

            <div className="info-box">
              <p>
                The system will generate multiple-choice questions based on your
                selected topic to assess your current knowledge level.
              </p>
            </div>

            <button
              type="submit"
              className="submit-button"
              disabled={isLoading}
            >
              {isLoading ? "Generating Questions..." : "Proceed to Questions"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default TopicSelection;
