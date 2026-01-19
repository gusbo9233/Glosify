// Types matching the Flask backend models

export interface User {
  id: number;
  username: string;
}

export interface Variant {
  id: number;
  value: string;
  translation: string;
  tags: Record<string, string>;
  word_id: number;
}

export interface Word {
  id: number;
  lemma: string;
  translation: string;
  properties: Record<string, string>;
  example_sentence?: string;
  explanation?: string;
  quiz_id: number;
  variants?: Variant[];
  // Anki spaced repetition fields
  ease_factor?: number;
  interval?: number;
  repetitions?: number;
  due_date?: string;
  is_new?: boolean;
  is_due?: boolean;
}

// Union type for Anki cards (can be word or sentence)
export interface AnkiWordCard extends Word {
  type?: 'word';
}

export interface AnkiSentenceCard extends Sentence {
  type: 'sentence';
}

export type AnkiCard = AnkiWordCard | AnkiSentenceCard;

export interface AnkiCardsResponse {
  due_cards: AnkiCard[];
  new_cards: AnkiCard[];
  total_due: number;
  total_new: number;
  total_words?: number;
  total_sentences?: number;
  mode?: 'words' | 'sentences';
}

export interface AnkiReviewResponse {
  success: boolean;
  word_id: number;
  ease_factor: number;
  interval: number;
  repetitions: number;
  due_date: string;
}

export interface Sentence {
  id: number;
  text: string;
  translation: string;
  quiz_id: number;
  // Anki spaced repetition fields
  ease_factor?: number;
  interval?: number;
  repetitions?: number;
  due_date?: string;
  is_new?: boolean;
  is_due?: boolean;
}

export interface Quiz {
  id: number;
  name: string;
  user_id: number;
  created_at: string;
  is_song_quiz: boolean;
  processing_status: 'pending' | 'processing' | 'completed' | 'error';
  processing_message?: string;
  source_language?: string;
  target_language?: string;
  anki_tracking_enabled?: boolean;
  is_public?: boolean;
  original_quiz_id?: number;
  word_count?: number;
  sentence_count?: number;
  words?: Word[];
  sentences?: Sentence[];
}

export interface Folder {
  id: number;
  name: string;
  user_id: number;
  parent_id: number | null;
  created_at: string;
  quizzes: Quiz[];
  subfolders: Folder[];
  isExpanded?: boolean;  // Frontend-only property for UI state
}

export interface AuthResponse {
  success: boolean;
  message?: string;
  user?: User;
}

export interface QuizPracticeSettings {
  shuffle: boolean;
  showHints: boolean;
  mode: 'words' | 'sentences' | 'variants';
  direction: 'forward' | 'reverse'; // forward: show lemma, guess translation
}

