import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  Dimensions,
  StatusBar,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { AppProvider, useApp } from './src/context/AppContext';
import { colors } from './src/utils/theme';
import Sidebar from './src/components/Sidebar';
import QuizDetailScreen from './src/screens/QuizDetailScreen';
import WordDetailScreen from './src/screens/WordDetailScreen';
import PracticeScreen from './src/screens/PracticeScreen';
import AnkiPracticeScreen from './src/screens/AnkiPracticeScreen';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import HomeScreen from './src/screens/HomeScreen';
import { Word, Quiz } from './src/types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const isTablet = SCREEN_WIDTH > 768;

type Screen = 'home' | 'quiz' | 'word' | 'practice' | 'anki';
type AuthScreen = 'login' | 'register';

const MainApp: React.FC = () => {
  const {
    isAuthenticated,
    isLoading,
    selectedQuiz,
    selectQuiz,
    selectWord,
    startPractice,
    stopPractice,
    isPracticing,
  } = useApp();

  const [currentScreen, setCurrentScreen] = useState<Screen>('home');
  const [authScreen, setAuthScreen] = useState<AuthScreen>('login');
  const [showSidebar, setShowSidebar] = useState(false);
  const [selectedWordIds, setSelectedWordIds] = useState<Set<number>>(new Set());
  const [isAnkiMode, setIsAnkiMode] = useState(false);

  const handleHomeClick = () => {
    setCurrentScreen('home');
    selectQuiz(null);
  };

  const handleQuizPress = async (quiz: Quiz) => {
    await selectQuiz(quiz);
    setCurrentScreen('quiz');
  };

  const handleWordPress = (word: Word) => {
    selectWord(word);
    setCurrentScreen('word');
  };

  const handleStartPractice = (wordIds: Set<number>) => {
    setSelectedWordIds(wordIds);
    startPractice();
    setCurrentScreen('practice');
  };

  const handleStartAnkiPractice = () => {
    setIsAnkiMode(true);
  };

  const handleClosePractice = () => {
    stopPractice();
    setCurrentScreen('home');
  };

  const handleCloseAnkiPractice = () => {
    setIsAnkiMode(false);
  };

  const handleBackFromWord = () => {
    selectWord(null);
    if (selectedQuiz) {
      setCurrentScreen('quiz');
    } else {
      setCurrentScreen('home');
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  // Auth screens
  if (!isAuthenticated) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={colors.background} />
        {authScreen === 'login' ? (
          <LoginScreen onSwitchToRegister={() => setAuthScreen('register')} />
        ) : (
          <RegisterScreen onSwitchToLogin={() => setAuthScreen('login')} />
        )}
      </SafeAreaView>
    );
  }

  // Practice mode (fullscreen)
  if (isPracticing) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={colors.background} />
        <PracticeScreen onClose={handleClosePractice} selectedWordIds={selectedWordIds} />
      </SafeAreaView>
    );
  }

  // Anki practice mode (fullscreen)
  if (isAnkiMode) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={colors.background} />
        <AnkiPracticeScreen onClose={handleCloseAnkiPractice} />
      </SafeAreaView>
    );
  }

  // Main app layout
  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />

      <View style={styles.mainLayout}>
        {/* Sidebar - Always visible */}
        {isTablet ? (
          <Sidebar 
            onHomeClick={handleHomeClick}
            onQuizSelect={() => setCurrentScreen('quiz')} 
          />
        ) : (
          <Modal
            visible={showSidebar}
            animationType="slide"
            transparent={false}
            onRequestClose={() => setShowSidebar(false)}
          >
            <SafeAreaView style={styles.modalSidebar}>
              <Sidebar
                onClose={() => setShowSidebar(false)}
                onHomeClick={() => {
                  handleHomeClick();
                  setShowSidebar(false);
                }}
                onQuizSelect={() => {
                  setCurrentScreen('quiz');
                  setShowSidebar(false);
                }}
              />
            </SafeAreaView>
          </Modal>
        )}

        {/* Main Content */}
        <View style={styles.mainContent}>
          {/* Mobile Header */}
          {!isTablet && (
            <View style={styles.mobileHeader}>
              <TouchableOpacity
                style={styles.menuButton}
                onPress={() => setShowSidebar(true)}
              >
                <Ionicons name="menu" size={24} color={colors.textPrimary} />
              </TouchableOpacity>
            </View>
          )}

          {/* Content Area */}
          {currentScreen === 'home' && (
            <HomeScreen 
              onQuizPress={handleQuizPress}
            />
          )}
          {currentScreen === 'quiz' && (
            <QuizDetailScreen
              onWordPress={handleWordPress}
              onStartPractice={handleStartPractice}
              onStartAnkiPractice={handleStartAnkiPractice}
            />
          )}
          {currentScreen === 'word' && (
            <WordDetailScreen onBack={handleBackFromWord} />
          )}
        </View>
      </View>
    </SafeAreaView>
  );
};

export default function App() {
  return (
    <SafeAreaProvider>
      <AppProvider>
        <MainApp />
      </AppProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  mainLayout: {
    flex: 1,
    flexDirection: 'row',
  },
  mainContent: {
    flex: 1,
    backgroundColor: colors.background,
  },
  mobileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    paddingTop: Platform.OS === 'android' ? 16 : 0,
  },
  menuButton: {
    padding: 8,
  },
  modalSidebar: {
    flex: 1,
    backgroundColor: colors.background,
  },
});
