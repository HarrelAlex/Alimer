import mongoose, { Schema, Document } from 'mongoose';
import { v4 as uuidv4 } from 'uuid';


enum DifficultyLevel {
  VeryEasy = 1,
  Easy = 2,
  Medium = 3,
  Hard = 4,
  VeryHard = 5
}

enum ConfidenceLevel {
  Low = 'Low',
  Medium = 'Medium', 
  High = 'High'
}


interface TopicResponse {
  questionId: string;
  difficulty: DifficultyLevel;
  isCorrect: boolean;
  qualityScore: number;
  timestamp: Date;
}

interface TopicCompetence {
  score: number;
  confidence: ConfidenceLevel;
  lastUpdated: Date;
  responses: TopicResponse[];
}

interface StudentTopicCompetences {
  [topic: string]: {
    [subtopic: string]: TopicCompetence
  }
}


interface IStudent extends Document {
  userId: string;
  competenceScores: StudentTopicCompetences;
}

const StudentSchema: Schema = new Schema({
  userId: { type: String, required: true, unique: true },
  competenceScores: { 
    type: Schema.Types.Mixed, 
    default: {} 
  }
});

const Student = mongoose.model<IStudent>('Student', StudentSchema);

class CompetenceScoreCalculator {
  static calculateCompetenceScore(  
    topic: string, 
    responses: TopicResponse[]
  ): number {
    if (responses.length === 0) return 0;

    console.log(topic)
    const totalQuestions = responses.length;
    const correctAnswers = responses.filter(r => r.isCorrect).length;
    
    
    const accuracy = correctAnswers / totalQuestions;

    
    const weightedDifficultyScore = responses
      .filter(r => r.isCorrect)
      .reduce((total, response) => 
        total + (response.difficulty * response.qualityScore), 0
      );
    
    const totalDifficulty = responses.reduce(
      (total, response) => total + response.difficulty, 0
    );

    
    const accuracyWeight = Math.min(0.6, 0.4 + (totalQuestions / 100));
    const difficultyWeight = 1 - accuracyWeight;

    
    const rawScore = (
      (accuracy * accuracyWeight + 
      (weightedDifficultyScore / totalDifficulty) * difficultyWeight) * 
      100
    );

    
    const finalScore = 100 / (1 + Math.exp(-0.1 * (rawScore - 50)));

    return Number(finalScore.toFixed(2));
  }

  static calculateConfidence(responses: TopicResponse[]): ConfidenceLevel {
    const totalQuestions = responses.length;
    
    if (totalQuestions < 5) return ConfidenceLevel.Low;
    if (totalQuestions < 20) return ConfidenceLevel.Medium;
    return ConfidenceLevel.High;
  }

  static async updateCompetenceScore(
    userId: string, 
    topic: string, 
    subtopic: string, 
    newResponse: TopicResponse
  ) {
    try {
     
      let student = await Student.findOne({ userId });
      if (!student) {
        student = new Student({ 
          userId, 
          competenceScores: {} 
        });
      }

     
      if (!student.competenceScores[topic]) {
        student.competenceScores[topic] = {};
      }
      if (!student.competenceScores[topic][subtopic]) {
        student.competenceScores[topic][subtopic] = {
          score: 0,
          confidence: ConfidenceLevel.Low,
          lastUpdated: new Date(),
          responses: []
        };
      }

     
      const topicCompetence = student.competenceScores[topic][subtopic];
      topicCompetence.responses.push(newResponse);

     
      topicCompetence.score = this.calculateCompetenceScore(
        topic, 
        topicCompetence.responses
      );
      topicCompetence.confidence = this.calculateConfidence(
        topicCompetence.responses
      );
      topicCompetence.lastUpdated = new Date();

      // Save updated student
      await student.save();

      return topicCompetence;
    } catch (error) {
      console.error('Error updating competence score:', error);
      throw error;
    }
  }

  static async getCompetenceScore(
    userId: string, 
    topic: string, 
    subtopic: string
  ) {
    const student = await Student.findOne({ userId });
    
    if (!student || 
        !student.competenceScores[topic] || 
        !student.competenceScores[topic][subtopic]) {
      return null;
    }

    return student.competenceScores[topic][subtopic];
  }
}


async function exampleUsage() {
  
  await mongoose.connect('mongodb://localhost:27017/alimer');

  const userId = uuidv4();
  const topic = 'Mathematics';
  const subtopic = 'Algebra';

  
  const responses: TopicResponse[] = [
    {
      questionId: uuidv4(),
      difficulty: DifficultyLevel.Easy,
      isCorrect: true,
      qualityScore: 0.9,
      timestamp: new Date()
    },
    {
      questionId: uuidv4(),
      difficulty: DifficultyLevel.Medium,
      isCorrect: true,
      qualityScore: 0.8,
      timestamp: new Date()
    }
  ];

  
  const result = await CompetenceScoreCalculator.updateCompetenceScore(
    userId, 
    topic, 
    subtopic, 
    responses[0]
  );

  
  const competenceInfo = await CompetenceScoreCalculator.getCompetenceScore(
    userId, 
    topic, 
    subtopic
  );

  console.log('Competence Score:', competenceInfo, result);
}

exampleUsage();

export { 
  CompetenceScoreCalculator as default 
};

export type {
  DifficultyLevel,
  ConfidenceLevel,
  TopicResponse,
  IStudent,
  StudentTopicCompetences,
  TopicCompetence
};