// API Configuration
// Change this to your server's IP when testing on physical device

// For local development:
// - iOS Simulator: use 'localhost'
// - Android Emulator: use '10.0.2.2'
// - Physical device: use your computer's local IP address

import { Platform } from 'react-native';

const getWebHostname = (): string => {
  // When running in a browser, "localhost" would refer to the user's computer,
  // not the Raspberry Pi. Use the current page hostname instead.
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return window.location.hostname;
  }
  // Fallback for non-browser environments
  return 'localhost';
};

const getBaseUrl = () => {
  if (__DEV__) {
    // Development mode
    if (Platform.OS === 'android') {
      // Android emulator uses 10.0.2.2 to access host localhost
      return 'http://10.0.2.2:5001';
    } else if (Platform.OS === 'ios') {
      // iOS simulator can use localhost
      return 'http://localhost:5001';
    } else {
      // Web
      return `http://${getWebHostname()}:5001`;
    }
  }
  // Production - replace with your actual server URL
  if (Platform.OS === 'web') {
    return `http://${getWebHostname()}:5001`;
  }
  return 'http://localhost:5001';
};

export const API_BASE_URL = getBaseUrl();

export const API_ENDPOINTS = {
  // Auth
  login: '/login',
  register: '/register',
  logout: '/logout',
  
  // Quizzes
  dashboard: '/dashboard',
  quizDetail: (id: number) => `/quiz/${id}`,
  deleteQuiz: (id: number) => `/quiz/${id}/delete`,
  quizStatus: (id: number) => `/quiz/${id}/status`,
  practiceQuiz: (id: number) => `/quiz/${id}/practice`,
  createSongQuiz: '/create-song-quiz',
  
  // Words
  deleteWord: (id: number) => `/word/${id}/delete`,
  addVariant: (id: number) => `/word/${id}/variant`,
  
  // Variants
  deleteVariant: (id: number) => `/variant/${id}/delete`,
  
  // Sentences
  deleteSentence: (id: number) => `/sentence/${id}/delete`,
};

