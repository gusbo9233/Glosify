import apiClient from './client';
import { API_ENDPOINTS } from './config';
import { Quiz, Word, Sentence, Variant, AnkiCardsResponse, AnkiReviewResponse } from '../types';

export interface QuizListResponse {
  quizzes: Quiz[];
}

export interface QuizDetailResponse {
  quiz: Quiz;
  words: Word[];
}

export interface QuizStatusResponse {
  status: string;
  message: string;
}

// Since the Flask backend uses server-side rendering, we need to parse HTML
// or create new API endpoints. For now, we'll create JSON API endpoints.

export const quizService = {
  // Get all quizzes for the logged-in user
  async getQuizzes(): Promise<Quiz[]> {
    try {
      const response = await apiClient.get('/api/quizzes');
      return response.data.quizzes || [];
    } catch (error) {
      console.error('Error fetching quizzes:', error);
      throw error;
    }
  },

  // Get quiz details with words and sentences
  async getQuizDetail(quizId: number): Promise<{ quiz: Quiz; words: Word[]; sentences: Sentence[] }> {
    try {
      const response = await apiClient.get(`/api/quiz/${quizId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching quiz detail:', error);
      throw error;
    }
  },

  // Create a new quiz
  async createQuiz(
    name: string,
    sourceLanguage?: string,
    targetLanguage?: string,
    prompt?: string
  ): Promise<Quiz> {
    try {
      const response = await apiClient.post('/api/quizzes', {
        name,
        source_language: sourceLanguage,
        target_language: targetLanguage,
        prompt,
      });
      return response.data.quiz;
    } catch (error) {
      console.error('Error creating quiz:', error);
      throw error;
    }
  },

  // Delete a quiz
  async deleteQuiz(quizId: number): Promise<void> {
    try {
      await apiClient.delete(`/api/quiz/${quizId}`);
    } catch (error) {
      console.error('Error deleting quiz:', error);
      throw error;
    }
  },

  // Add word to quiz
  async addWord(quizId: number, lemma: string, translation: string): Promise<Word> {
    try {
      const response = await apiClient.post(`/api/quiz/${quizId}/words`, {
        lemma,
        translation,
      });
      return response.data.word;
    } catch (error) {
      console.error('Error adding word:', error);
      throw error;
    }
  },

  // Delete a word
  async deleteWord(wordId: number): Promise<void> {
    try {
      await apiClient.delete(`/api/word/${wordId}`);
    } catch (error) {
      console.error('Error deleting word:', error);
      throw error;
    }
  },

  // Update a word
  async updateWord(
    wordId: number,
    payload: {
      lemma?: string;
      translation?: string;
      example_sentence?: string | null;
      explanation?: string | null;
      properties?: Record<string, string>;
      variants?: Array<{
        value: string;
        translation: string;
        tags?: Record<string, string>;
      }>;
    }
  ): Promise<Word> {
    try {
      const response = await apiClient.put(`/api/word/${wordId}`, payload);
      return response.data.word;
    } catch (error) {
      console.error('Error updating word:', error);
      throw error;
    }
  },

  // Copy a word to another quiz
  async copyWordToQuiz(wordId: number, targetQuizId: number): Promise<void> {
    try {
      await apiClient.post(`/api/word/${wordId}/copy`, {
        target_quiz_id: targetQuizId,
      });
    } catch (error) {
      console.error('Error copying word to quiz:', error);
      throw error;
    }
  },

  // Get quiz status (for processing)
  async getQuizStatus(quizId: number): Promise<QuizStatusResponse> {
    try {
      const response = await apiClient.get(API_ENDPOINTS.quizStatus(quizId));
      return response.data;
    } catch (error) {
      console.error('Error fetching quiz status:', error);
      throw error;
    }
  },

  // Create quiz from any text content - AI extracts vocabulary automatically
  async createFromText(
    name: string,
    language: string,
    content: string,
    context?: string
  ): Promise<Quiz> {
    try {
      const response = await apiClient.post('/api/import-text', {
        name,
        language,
        content,
        context,
      });
      return response.data.quiz;
    } catch (error) {
      console.error('Error creating quiz from text:', error);
      throw error;
    }
  },

  // Alias for backward compatibility
  async createSongQuiz(
    name: string,
    language: string,
    lyrics: string,
    context?: string
  ): Promise<Quiz> {
    return this.createFromText(name, language, lyrics, context);
  },

  // Get word details (for "artist" page)
  async getWordDetail(wordId: number): Promise<Word> {
    try {
      const response = await apiClient.get(`/api/word/${wordId}`);
      return response.data.word;
    } catch (error) {
      console.error('Error fetching word detail:', error);
      throw error;
    }
  },

  // Import text into existing quiz
  async importTextToQuiz(
    quizId: number,
    language: string,
    content: string,
    context?: string
  ): Promise<void> {
    try {
      await apiClient.post(`/api/quiz/${quizId}/import-text`, {
        language,
        content,
        context,
      });
    } catch (error) {
      console.error('Error importing text to quiz:', error);
      throw error;
    }
  },

  // Import image (OCR) into existing quiz
  async importImageToQuiz(
    quizId: number,
    imageBase64: string,
    context?: string
  ): Promise<void> {
    try {
      await apiClient.post(`/api/quiz/${quizId}/import-image`, {
        image: imageBase64,
        context,
      });
    } catch (error) {
      console.error('Error importing image to quiz:', error);
      throw error;
    }
  },

  // Cancel ongoing processing
  async cancelProcessing(quizId: number): Promise<void> {
    try {
      await apiClient.post(`/api/quiz/${quizId}/cancel-processing`);
    } catch (error) {
      console.error('Error cancelling processing:', error);
      throw error;
    }
  },

  // Anki-style spaced repetition methods
  async getAnkiCards(
    quizId: number, 
    mode: 'words' | 'sentences' = 'words',
    direction: 'forward' | 'reverse' = 'forward'
  ): Promise<AnkiCardsResponse> {
    try {
      const response = await apiClient.get(`/api/quiz/${quizId}/anki-cards`, {
        params: { mode, direction }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching Anki cards:', error);
      throw error;
    }
  },

  async reviewWord(
    wordId: number, 
    rating: 1 | 2 | 3 | 4,
    direction: 'forward' | 'reverse' = 'forward'
  ): Promise<AnkiReviewResponse> {
    try {
      const response = await apiClient.post(`/api/word/${wordId}/review`, { rating, direction });
      return response.data;
    } catch (error) {
      console.error('Error reviewing word:', error);
      throw error;
    }
  },

  async reviewSentence(
    sentenceId: number, 
    rating: 1 | 2 | 3 | 4,
    direction: 'forward' | 'reverse' = 'forward'
  ): Promise<AnkiReviewResponse> {
    try {
      const response = await apiClient.post(`/api/sentence/${sentenceId}/review`, { rating, direction });
      return response.data;
    } catch (error) {
      console.error('Error reviewing sentence:', error);
      throw error;
    }
  },

  // Get Anki statistics across all quizzes
  async getAnkiStats(): Promise<{
    total_due_words: number;
    total_new_words: number;
    total_due_sentences: number;
    total_new_sentences: number;
    total_due: number;
    total_new: number;
    quizzes_with_due: Array<{
      id: number;
      name: string;
      due_words: number;
      due_sentences: number;
      new_words: number;
      new_sentences: number;
    }>;
  }> {
    try {
      const response = await apiClient.get('/api/anki-stats');
      return response.data;
    } catch (error) {
      console.error('Error fetching Anki stats:', error);
      throw error;
    }
  },
};

export default quizService;

