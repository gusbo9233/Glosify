import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Quiz, Word, User, Folder, QuizPracticeSettings } from '../types';
import quizService from '../api/quizService';
import folderService from '../api/folderService';
import authService from '../api/authService';

interface AppState {
  // Auth
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // Data
  quizzes: Quiz[];
  folders: Folder[];
  selectedQuiz: Quiz | null;
  selectedWord: Word | null;
  
  // Practice
  practiceSettings: QuizPracticeSettings;
  isPracticing: boolean;
  
  // UI
  sidebarCollapsed: boolean;
}

interface AppContextType extends AppState {
  // Auth actions
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  
  // Data actions
  loadQuizzes: () => Promise<void>;
  selectQuiz: (quiz: Quiz | null) => void;
  selectWord: (word: Word | null) => void;
  createQuiz: (name: string, sourceLanguage?: string, targetLanguage?: string, prompt?: string) => Promise<Quiz | null>;
  createQuizFromText: (name: string, language: string, content: string, context?: string) => Promise<Quiz | null>;
  importTextToQuiz: (quizId: number, language: string, content: string, context?: string) => Promise<void>;
  importImageToQuiz: (quizId: number, imageBase64: string, context?: string) => Promise<void>;
  deleteQuiz: (quizId: number) => Promise<void>;
  addWordToQuiz: (quizId: number, lemma: string, translation: string) => Promise<void>;
  
  // Folder actions
  createFolder: (name: string, parentId?: number) => Promise<Folder>;
  deleteFolder: (folderId: number) => Promise<void>;
  moveQuizToFolder: (quizId: number, folderId: number | null) => Promise<void>;
  toggleFolderExpanded: (folderId: number) => void;
  
  // Practice actions
  startPractice: () => void;
  stopPractice: () => void;
  updatePracticeSettings: (settings: Partial<QuizPracticeSettings>) => void;
  
  // UI actions
  toggleSidebar: () => void;
}

const defaultPracticeSettings: QuizPracticeSettings = {
  shuffle: false,
  showHints: true,
  mode: 'words',
  direction: 'forward',
};

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AppState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    quizzes: [],
    folders: [],
    selectedQuiz: null,
    selectedWord: null,
    practiceSettings: defaultPracticeSettings,
    isPracticing: false,
    sidebarCollapsed: false,
  });

  // Check auth on mount
  useEffect(() => {
    checkAuth();
  }, []);

  // Poll for quiz processing status updates
  useEffect(() => {
    if (!state.isAuthenticated) return;

    // Check if there are any quizzes still processing
    const hasProcessingQuizzes = state.quizzes.some(
      q => q.processing_status === 'pending' || q.processing_status === 'processing'
    );

    if (!hasProcessingQuizzes) return;

    // Poll every 2 seconds for processing quizzes
    const intervalId = setInterval(async () => {
      try {
        const quizzes = await quizService.getQuizzes();
        
        setState(prev => {
          // Update selected quiz if it exists
          let updatedSelectedQuiz = prev.selectedQuiz;
          const previousSelectedQuiz = prev.selectedQuiz;
          
          if (updatedSelectedQuiz) {
            const updatedQuiz = quizzes.find(q => q.id === updatedSelectedQuiz!.id);
            if (updatedQuiz) {
              updatedSelectedQuiz = { ...updatedSelectedQuiz, ...updatedQuiz };
              
              // If quiz was processing and is now completed, reload it with full details
              const wasProcessing = 
                previousSelectedQuiz!.processing_status === 'pending' || 
                previousSelectedQuiz!.processing_status === 'processing';
              const isNowCompleted = updatedQuiz.processing_status === 'completed';
              
              if (wasProcessing && isNowCompleted) {
                // Quiz just completed - reload it with full details including words
                quizService.getQuizDetail(updatedQuiz.id).then(({ quiz, words, sentences }) => {
                  setState(prevState => ({
                    ...prevState,
                    selectedQuiz: { ...quiz, words, sentences },
                  }));
                }).catch((error) => {
                  console.error('Error reloading completed quiz:', error);
                  // If quiz was deleted or not found, clear selection
                  setState(prevState => ({
                    ...prevState,
                    selectedQuiz: null,
                  }));
                });
              }
            } else {
              // Selected quiz was not found in the updated list (likely deleted or moved to folder)
              // Clear the selection
              updatedSelectedQuiz = null;
            }
          }
          return { ...prev, quizzes, selectedQuiz: updatedSelectedQuiz };
        });
      } catch (error) {
        console.error('Error polling quiz status:', error);
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [state.isAuthenticated, state.quizzes]);

  const checkAuth = async () => {
    try {
      const response = await authService.checkAuth();
      if (response.success && response.user) {
        setState(prev => ({
          ...prev,
          user: response.user!,
          isAuthenticated: true,
          isLoading: false,
        }));
        await loadQuizzes();
        await loadFolders();
      } else {
        setState(prev => ({ ...prev, isLoading: false }));
      }
    } catch {
      setState(prev => ({ ...prev, isLoading: false }));
    }
  };

  const login = async (username: string, password: string): Promise<boolean> => {
    const response = await authService.login(username, password);
    if (response.success && response.user) {
      setState(prev => ({
        ...prev,
        user: response.user!,
        isAuthenticated: true,
      }));
      await loadQuizzes();
      return true;
    }
    return false;
  };

  const register = async (username: string, password: string): Promise<boolean> => {
    const response = await authService.register(username, password);
    if (response.success) {
      return await login(username, password);
    }
    return false;
  };

  const logout = async () => {
    await authService.logout();
    setState(prev => ({
      ...prev,
      user: null,
      isAuthenticated: false,
      quizzes: [],
      selectedQuiz: null,
      selectedWord: null,
    }));
  };

  const loadQuizzes = async () => {
    try {
      const quizzes = await quizService.getQuizzes();
      setState(prev => {
        // If we have a selected quiz, update it if it was processing
        let updatedSelectedQuiz = prev.selectedQuiz;
        if (updatedSelectedQuiz) {
          const updatedQuiz = quizzes.find(q => q.id === updatedSelectedQuiz!.id);
          if (updatedQuiz) {
            // Update the selected quiz with new data
            updatedSelectedQuiz = { ...updatedSelectedQuiz, ...updatedQuiz };
          }
        }
        return { ...prev, quizzes, selectedQuiz: updatedSelectedQuiz };
      });
    } catch (error) {
      console.error('Failed to load quizzes:', error);
    }
  };

  const loadFolders = async () => {
    try {
      const folders = await folderService.getFolders();
      // Add isExpanded property to each folder for UI state
      const foldersWithState = folders.map(folder => ({
        ...folder,
        isExpanded: folder.isExpanded ?? false,
      }));
      setState(prev => ({ ...prev, folders: foldersWithState }));
    } catch (error) {
      console.error('Failed to load folders:', error);
    }
  };

  const selectQuiz = async (quiz: Quiz | null) => {
    if (quiz) {
      try {
        const { quiz: fullQuiz, words, sentences } = await quizService.getQuizDetail(quiz.id);
        setState(prev => ({
          ...prev,
          selectedQuiz: { ...fullQuiz, words, sentences },
          selectedWord: null,
          isPracticing: false,
        }));
      } catch {
        setState(prev => ({
          ...prev,
          selectedQuiz: quiz,
          selectedWord: null,
          isPracticing: false,
        }));
      }
    } else {
      setState(prev => ({
        ...prev,
        selectedQuiz: null,
        selectedWord: null,
        isPracticing: false,
      }));
    }
  };

  const selectWord = async (word: Word | null) => {
    if (word) {
      try {
        const fullWord = await quizService.getWordDetail(word.id);
        setState(prev => ({ ...prev, selectedWord: fullWord }));
      } catch {
        setState(prev => ({ ...prev, selectedWord: word }));
      }
    } else {
      setState(prev => ({ ...prev, selectedWord: null }));
    }
  };

  const createQuiz = async (
    name: string,
    sourceLanguage?: string,
    targetLanguage?: string,
    prompt?: string
  ): Promise<Quiz | null> => {
    try {
      const quiz = await quizService.createQuiz(name, sourceLanguage, targetLanguage, prompt);
      await loadQuizzes();
      return quiz;
    } catch {
      return null;
    }
  };

  const createQuizFromText = async (
    name: string,
    language: string,
    content: string,
    context?: string
  ): Promise<Quiz | null> => {
    try {
      const quiz = await quizService.createFromText(name, language, content, context);
      await loadQuizzes();
      return quiz;
    } catch {
      return null;
    }
  };

  const importTextToQuiz = async (
    quizId: number,
    language: string,
    content: string,
    context?: string
  ): Promise<void> => {
    try {
      await quizService.importTextToQuiz(quizId, language, content, context);
      // Reload quiz to get updated words
      const quiz = state.quizzes.find((q: Quiz) => q.id === quizId);
      if (quiz) {
        await selectQuiz(quiz);
      } else if (state.selectedQuiz?.id === quizId) {
        // If it's the currently selected quiz, reload it
        await selectQuiz(state.selectedQuiz);
      }
    } catch (error) {
      console.error('Failed to import text to quiz:', error);
      throw error;
    }
  };

  const importImageToQuiz = async (
    quizId: number,
    imageBase64: string,
    context?: string
  ): Promise<void> => {
    try {
      await quizService.importImageToQuiz(quizId, imageBase64, context);
      // Reload quiz to get updated words
      const quiz = state.quizzes.find((q: Quiz) => q.id === quizId);
      if (quiz) {
        await selectQuiz(quiz);
      } else if (state.selectedQuiz?.id === quizId) {
        await selectQuiz(state.selectedQuiz);
      }
    } catch (error) {
      console.error('Failed to import image to quiz:', error);
      throw error;
    }
  };

  const deleteQuiz = async (quizId: number) => {
    try {
      await quizService.deleteQuiz(quizId);
      // Clear selection if the deleted quiz was selected
      setState(prev => {
        if (prev.selectedQuiz?.id === quizId) {
          return { ...prev, selectedQuiz: null };
        }
        return prev;
      });
      // Reload both quizzes and folders (quiz might have been in a folder)
      await loadQuizzes();
      await loadFolders();
    } catch (error) {
      console.error('Failed to delete quiz:', error);
      throw error;
    }
  };

  const addWordToQuiz = async (quizId: number, lemma: string, translation: string): Promise<void> => {
    // Run in background - don't block UI
    return quizService.addWord(quizId, lemma, translation)
      .then(async () => {
        // Refresh quiz after word is added
        if (state.selectedQuiz?.id === quizId) {
          await selectQuiz(state.selectedQuiz);
        }
      })
      .catch((error) => {
        console.error('Failed to add word:', error);
        throw error; // Re-throw so caller can handle if needed
      });
  };

  // Helper function to recursively find a folder in the tree
  const findFolder = (folders: Folder[], folderId: number): Folder | null => {
    for (const folder of folders) {
      if (folder.id === folderId) {
        return folder;
      }
      const found = findFolder(folder.subfolders, folderId);
      if (found) {
        return found;
      }
    }
    return null;
  };

  // Helper function to recursively update folders
  const updateFolderInTree = (folders: Folder[], folderId: number, updater: (folder: Folder) => Folder): Folder[] => {
    return folders.map(folder => {
      if (folder.id === folderId) {
        return updater(folder);
      }
      return {
        ...folder,
        subfolders: updateFolderInTree(folder.subfolders, folderId, updater),
      };
    });
  };

  const createFolder = async (name: string, parentId?: number) => {
    try {
      const newFolder = await folderService.createFolder(name, parentId);
      await loadFolders();
      return newFolder;
    } catch (error) {
      console.error('Failed to create folder:', error);
      throw error;
    }
  };

  const moveQuizToFolder = async (quizId: number, folderId: number | null) => {
    try {
      await folderService.moveQuizToFolder(quizId, folderId);
      await loadQuizzes();
      await loadFolders();
    } catch (error) {
      console.error('Failed to move quiz to folder:', error);
      throw error;
    }
  };

  const deleteFolder = async (folderId: number) => {
    try {
      await folderService.deleteFolder(folderId);
      await loadFolders();
    } catch (error) {
      console.error('Failed to delete folder:', error);
      throw error;
    }
  };

  const toggleFolderExpanded = (folderId: number) => {
    setState(prev => ({
      ...prev,
      folders: updateFolderInTree(prev.folders, folderId, (folder) => ({
        ...folder,
        isExpanded: !folder.isExpanded,
      })),
    }));
  };

  const startPractice = () => {
    setState(prev => ({ ...prev, isPracticing: true }));
  };

  const stopPractice = () => {
    setState(prev => ({ ...prev, isPracticing: false }));
  };

  const updatePracticeSettings = (settings: Partial<QuizPracticeSettings>) => {
    setState(prev => ({
      ...prev,
      practiceSettings: { ...prev.practiceSettings, ...settings },
    }));
  };

  const toggleSidebar = () => {
    setState(prev => ({ ...prev, sidebarCollapsed: !prev.sidebarCollapsed }));
  };

  const contextValue: AppContextType = {
    ...state,
    login,
    register,
    logout,
    loadQuizzes,
    selectQuiz,
    selectWord,
    createQuiz,
    createQuizFromText,
    importTextToQuiz,
    importImageToQuiz,
    deleteQuiz,
    addWordToQuiz,
    createFolder,
    deleteFolder,
    moveQuizToFolder,
    toggleFolderExpanded,
    startPractice,
    stopPractice,
    updatePracticeSettings,
    toggleSidebar,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export default AppContext;

