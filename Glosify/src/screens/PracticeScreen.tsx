import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Animated,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius, shadows } from '../utils/theme';
import { useApp } from '../context/AppContext';
import { Word, Variant, Sentence } from '../types';
import CyrillicKeyboard from '../components/CyrillicKeyboard';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface PracticeItem {
  id: string;
  question: string;
  answer: string;
  hint?: string;
  word?: Word;
  variant?: Variant;
  sentence?: Sentence;
}

interface PracticeScreenProps {
  onClose: () => void;
  selectedWordIds: Set<number>;
}

const PracticeScreen: React.FC<PracticeScreenProps> = ({ onClose, selectedWordIds }) => {
  const { selectedQuiz, practiceSettings } = useApp();
  const [items, setItems] = useState<PracticeItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState('');
  const [showAnswer, setShowAnswer] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [isFinished, setIsFinished] = useState(false);
  const [showCyrillicKeyboard, setShowCyrillicKeyboard] = useState(false);

  const progressAnim = useState(new Animated.Value(0))[0];
  const answerInputRef = useRef<TextInput>(null);

  // Auto-focus input when answer is shown to allow Enter key
  useEffect(() => {
    if (showAnswer && answerInputRef.current) {
      setTimeout(() => {
        answerInputRef.current?.focus();
      }, 100);
    }
  }, [showAnswer]);

  // Build practice items from quiz, filtering by selected words/sentences
  useEffect(() => {
    let practiceItems: PracticeItem[] = [];

    if (practiceSettings.mode === 'sentences') {
      // Handle sentences mode
      if (!selectedQuiz?.sentences) {
        setItems([]);
        return;
      }

      // For sentences mode, use all sentences (or filter if we add selection later)
      const selectedSentences = selectedQuiz.sentences;

      if (selectedSentences.length === 0) {
        setItems([]);
        return;
      }

      practiceItems = selectedSentences.map(sentence => ({
        id: `sentence-${sentence.id}`,
        question: practiceSettings.direction === 'forward' ? sentence.text : sentence.translation,
        answer: practiceSettings.direction === 'forward' ? sentence.translation : sentence.text,
        sentence,
      }));
    } else {
      // Handle words and variants modes
      if (!selectedQuiz?.words) {
        setItems([]);
        return;
      }

      // Filter words to only include selected ones
      const selectedWords = selectedQuiz.words.filter(word => selectedWordIds.has(word.id));

      if (selectedWords.length === 0) {
        setItems([]);
        return;
      }

      if (practiceSettings.mode === 'words') {
        practiceItems = selectedWords.map(word => ({
          id: `word-${word.id}`,
          question: practiceSettings.direction === 'forward' ? word.lemma : word.translation,
          answer: practiceSettings.direction === 'forward' ? word.translation : word.lemma,
          hint: word.example_sentence,
          word,
        }));
      } else if (practiceSettings.mode === 'variants') {
        selectedWords.forEach(word => {
          // Add the base word
          practiceItems.push({
            id: `word-${word.id}`,
            question: practiceSettings.direction === 'forward' ? word.lemma : word.translation,
            answer: practiceSettings.direction === 'forward' ? word.translation : word.lemma,
            hint: word.example_sentence,
            word,
          });

          // Add variants
          word.variants?.forEach(variant => {
            practiceItems.push({
              id: `variant-${variant.id}`,
              question: practiceSettings.direction === 'forward' ? variant.value : variant.translation,
              answer: practiceSettings.direction === 'forward' ? variant.translation : variant.value,
              word,
              variant,
            });
          });
        });
      }
    }

    // Shuffle if enabled
    if (practiceSettings.shuffle) {
      practiceItems = practiceItems.sort(() => Math.random() - 0.5);
    }

    setItems(practiceItems);
    setCurrentIndex(0);
    setScore({ correct: 0, total: 0 });
    setIsFinished(false);
  }, [selectedQuiz, practiceSettings, selectedWordIds]);

  // Update progress animation
  useEffect(() => {
    if (items.length > 0) {
      Animated.timing(progressAnim, {
        toValue: (currentIndex / items.length) * 100,
        duration: 300,
        useNativeDriver: false,
      }).start();
    }
  }, [currentIndex, items.length]);

  const currentItem = items[currentIndex];

  const checkAnswer = useCallback(() => {
    if (!currentItem) return;

    const normalizedUserAnswer = userAnswer.trim().toLowerCase();
    const normalizedCorrectAnswer = currentItem.answer.trim().toLowerCase();

    // Handle multiple correct answers (separated by comma)
    const correctAnswers = normalizedCorrectAnswer.split(',').map(a => a.trim());
    const correct = correctAnswers.some(a => a === normalizedUserAnswer);

    setIsCorrect(correct);
    setShowAnswer(true);
    setScore(prev => ({
      correct: prev.correct + (correct ? 1 : 0),
      total: prev.total + 1,
    }));
  }, [currentItem, userAnswer]);

  const nextItem = useCallback(() => {
    if (currentIndex < items.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setUserAnswer('');
      setShowAnswer(false);
      setIsCorrect(null);
    } else {
      setIsFinished(true);
    }
  }, [currentIndex, items.length]);

  const restart = () => {
    let shuffledItems = [...items];
    if (practiceSettings.shuffle) {
      shuffledItems = shuffledItems.sort(() => Math.random() - 0.5);
    }
    setItems(shuffledItems);
    setCurrentIndex(0);
    setUserAnswer('');
    setShowAnswer(false);
    setIsCorrect(null);
    setScore({ correct: 0, total: 0 });
    setIsFinished(false);
  };

  if (isFinished) {
    const percentage = Math.round((score.correct / score.total) * 100);
    return (
      <View style={styles.container}>
        <View style={styles.finishedContainer}>
          <View style={styles.finishedIcon}>
            <Ionicons
              name={percentage >= 70 ? 'trophy' : 'ribbon'}
              size={60}
              color={percentage >= 70 ? colors.warning : colors.primary}
            />
          </View>
          <Text style={styles.finishedTitle}>Practice Complete!</Text>
          <Text style={styles.finishedScore}>
            {score.correct} / {score.total}
          </Text>
          <Text style={styles.finishedPercentage}>{percentage}% correct</Text>

          <View style={styles.finishedActions}>
            <TouchableOpacity style={styles.restartButton} onPress={restart}>
              <Ionicons name="refresh" size={20} color={colors.textPrimary} />
              <Text style={styles.restartButtonText}>Practice Again</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Text style={styles.closeButtonText}>Done</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    );
  }

  if (!currentItem) {
    return (
      <View style={styles.container}>
        <View style={styles.emptyContainer}>
          <Ionicons name="sad-outline" size={60} color={colors.textMuted} />
          <Text style={styles.emptyText}>No items to practice</Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Text style={styles.closeButtonText}>Close</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onClose} style={styles.headerButton}>
          <Ionicons name="chevron-down" size={28} color={colors.textPrimary} />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>{selectedQuiz?.name}</Text>
          <Text style={styles.headerSubtitle}>
            {currentIndex + 1} of {items.length}
          </Text>
        </View>
        <View style={styles.headerButton} />
      </View>

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <Animated.View
          style={[
            styles.progressBar,
            {
              width: progressAnim.interpolate({
                inputRange: [0, 100],
                outputRange: ['0%', '100%'],
              }),
            },
          ]}
        />
      </View>

      {/* Main Content */}
      <View style={styles.content}>
        {/* Question */}
        <View style={styles.questionContainer}>
          <Text style={styles.questionLabel}>
            {practiceSettings.direction === 'forward' ? 'Translate' : 'What is'}
          </Text>
          <Text style={styles.question}>{currentItem.question}</Text>
          {practiceSettings.showHints && currentItem.hint && !showAnswer && (
            <TouchableOpacity style={styles.hintButton}>
              <Ionicons name="bulb-outline" size={16} color={colors.primary} />
              <Text style={styles.hintText}>Tap for hint</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Answer Input */}
        <View style={styles.answerSection}>
          <View style={styles.inputContainer}>
            <TextInput
              ref={answerInputRef}
              style={[
                styles.answerInput,
                showAnswer && (isCorrect ? styles.inputCorrect : styles.inputIncorrect),
              ]}
              placeholder={showAnswer ? "Press Enter to continue..." : "Type your answer..."}
              placeholderTextColor={colors.textMuted}
              value={showAnswer ? currentItem.answer : userAnswer}
              onChangeText={(text) => {
                if (!showAnswer) {
                  setUserAnswer(text);
                }
              }}
              editable={true}
              autoFocus={!showCyrillicKeyboard}
              onSubmitEditing={showAnswer ? nextItem : checkAnswer}
              returnKeyType={showAnswer ? "next" : "done"}
            />
            {!showAnswer && (
              <TouchableOpacity
                style={styles.keyboardToggle}
                onPress={() => {
                  setShowCyrillicKeyboard(!showCyrillicKeyboard);
                  if (showCyrillicKeyboard) {
                    answerInputRef.current?.blur();
                  }
                }}
              >
                <Ionicons
                  name={showCyrillicKeyboard ? 'keyboard' : 'keyboard-outline'}
                  size={24}
                  color={showCyrillicKeyboard ? colors.primary : colors.textSecondary}
                />
              </TouchableOpacity>
            )}
          </View>

          {showAnswer && (
            <View style={styles.answerFeedback}>
              <Ionicons
                name={isCorrect ? 'checkmark-circle' : 'close-circle'}
                size={24}
                color={isCorrect ? colors.success : colors.error}
              />
              <Text
                style={[
                  styles.feedbackText,
                  isCorrect ? styles.feedbackCorrect : styles.feedbackIncorrect,
                ]}
              >
                {isCorrect ? 'Correct!' : `Correct answer: ${currentItem.answer}`}
              </Text>
            </View>
          )}
        </View>

        {/* Cyrillic Keyboard */}
        {showCyrillicKeyboard && !showAnswer && (
          <CyrillicKeyboard
            onKeyPress={(key) => {
              setUserAnswer(prev => prev + key);
            }}
            onBackspace={() => {
              setUserAnswer(prev => prev.slice(0, -1));
            }}
            onClose={() => setShowCyrillicKeyboard(false)}
          />
        )}

        {/* Action Buttons */}
        <View style={styles.actions}>
          {!showAnswer ? (
            <TouchableOpacity
              style={[styles.checkButton, !userAnswer.trim() && styles.buttonDisabled]}
              onPress={checkAnswer}
              disabled={!userAnswer.trim()}
            >
              <Text style={styles.checkButtonText}>Check</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.nextButton} onPress={nextItem}>
              <Text style={styles.nextButtonText}>
                {currentIndex < items.length - 1 ? 'Next' : 'Finish'}
              </Text>
              <Ionicons name="arrow-forward" size={20} color={colors.background} />
            </TouchableOpacity>
          )}
        </View>

        {/* Score */}
        <View style={styles.scoreContainer}>
          <Text style={styles.scoreText}>
            Score: {score.correct}/{score.total}
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: spacing.md,
    paddingTop: spacing.xl,
  },
  headerButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerCenter: {
    alignItems: 'center',
  },
  headerTitle: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  headerSubtitle: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    marginTop: 2,
  },
  progressContainer: {
    height: 4,
    backgroundColor: colors.backgroundLighter,
    marginHorizontal: spacing.md,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: colors.primary,
  },
  content: {
    flex: 1,
    padding: spacing.lg,
    justifyContent: 'center',
  },
  questionContainer: {
    alignItems: 'center',
    marginBottom: spacing.xxl,
  },
  questionLabel: {
    color: colors.textMuted,
    fontSize: fontSize.md,
    marginBottom: spacing.sm,
  },
  question: {
    color: colors.textPrimary,
    fontSize: fontSize.title,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  hintButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: spacing.md,
    padding: spacing.sm,
  },
  hintText: {
    color: colors.primary,
    fontSize: fontSize.sm,
  },
  answerSection: {
    marginBottom: spacing.xl,
  },
  inputContainer: {
    position: 'relative',
  },
  answerInput: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    paddingRight: 60,
    fontSize: fontSize.xl,
    color: colors.textPrimary,
    textAlign: 'center',
    borderWidth: 2,
    borderColor: colors.border,
  },
  keyboardToggle: {
    position: 'absolute',
    right: spacing.md,
    top: '50%',
    transform: [{ translateY: -12 }],
    padding: spacing.xs,
  },
  inputCorrect: {
    borderColor: colors.success,
    backgroundColor: 'rgba(29, 185, 84, 0.1)',
  },
  inputIncorrect: {
    borderColor: colors.error,
    backgroundColor: 'rgba(226, 33, 52, 0.1)',
  },
  answerFeedback: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  feedbackText: {
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  feedbackCorrect: {
    color: colors.success,
  },
  feedbackIncorrect: {
    color: colors.error,
  },
  actions: {
    alignItems: 'center',
  },
  checkButton: {
    backgroundColor: colors.backgroundLighter,
    paddingHorizontal: spacing.xxl,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.full,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  checkButtonText: {
    color: colors.textPrimary,
    fontSize: fontSize.lg,
    fontWeight: '600',
  },
  nextButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.xxl,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.full,
  },
  nextButtonText: {
    color: colors.background,
    fontSize: fontSize.lg,
    fontWeight: '600',
  },
  scoreContainer: {
    alignItems: 'center',
    marginTop: spacing.xl,
  },
  scoreText: {
    color: colors.textMuted,
    fontSize: fontSize.md,
  },
  finishedContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  finishedIcon: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  finishedTitle: {
    color: colors.textPrimary,
    fontSize: fontSize.xxl,
    fontWeight: 'bold',
    marginBottom: spacing.md,
  },
  finishedScore: {
    color: colors.primary,
    fontSize: fontSize.title,
    fontWeight: 'bold',
  },
  finishedPercentage: {
    color: colors.textSecondary,
    fontSize: fontSize.lg,
    marginTop: spacing.sm,
  },
  finishedActions: {
    marginTop: spacing.xxl,
    gap: spacing.md,
    width: '100%',
    maxWidth: 300,
  },
  restartButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    backgroundColor: colors.surface,
    padding: spacing.md,
    borderRadius: borderRadius.full,
  },
  restartButtonText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  closeButton: {
    alignItems: 'center',
    padding: spacing.md,
  },
  closeButtonText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.md,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: fontSize.lg,
  },
});

export default PracticeScreen;

