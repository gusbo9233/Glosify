import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius, shadows } from '../utils/theme';
import { useApp } from '../context/AppContext';
import { AnkiCard, AnkiCardsResponse } from '../types';
import quizService from '../api/quizService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface AnkiPracticeScreenProps {
  onClose: () => void;
}

const AnkiPracticeScreen: React.FC<AnkiPracticeScreenProps> = ({ onClose }) => {
  const { selectedQuiz, practiceSettings } = useApp();
  const [isLoading, setIsLoading] = useState(true);
  const [cards, setCards] = useState<AnkiCard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [stats, setStats] = useState({ totalDue: 0, totalNew: 0, reviewed: 0 });
  const [isFinished, setIsFinished] = useState(false);
  const [mode, setMode] = useState<'words' | 'sentences'>('words');

  const flipAnim = useState(new Animated.Value(0))[0];

  // Load due cards based on practice mode and direction
  useEffect(() => {
    loadCards();
  }, [selectedQuiz?.id, practiceSettings.mode, practiceSettings.direction]);

  const loadCards = async () => {
    if (!selectedQuiz) return;
    
    setIsLoading(true);
    try {
      // Use 'sentences' mode if practiceSettings.mode is 'sentences', otherwise 'words'
      const cardMode = practiceSettings.mode === 'sentences' ? 'sentences' : 'words';
      setMode(cardMode);
      
      // Pass direction to get cards due for that specific direction
      const response: AnkiCardsResponse = await quizService.getAnkiCards(
        selectedQuiz.id, 
        cardMode,
        practiceSettings.direction
      );
      // Include both due cards and new cards (due first, then new)
      const allCards = [...response.due_cards, ...response.new_cards];
      setCards(allCards);
      setStats({
        totalDue: response.total_due,
        totalNew: response.total_new,
        reviewed: 0,
      });
      setCurrentIndex(0);
      setShowAnswer(false);
      setIsFinished(allCards.length === 0);
    } catch (error) {
      console.error('Failed to load Anki cards:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetAnki = async () => {
    if (!selectedQuiz) return;
    
    setIsLoading(true);
    try {
      const cardMode = practiceSettings.mode === 'sentences' ? 'sentences' : 'words';
      await quizService.resetAnki(selectedQuiz.id, cardMode, practiceSettings.direction);
      await loadCards();
    } catch (error) {
      console.error('Failed to reset Anki:', error);
      setIsLoading(false);
    }
  };

  const currentCard = cards[currentIndex];

  const flipCard = () => {
    if (showAnswer) return;
    
    Animated.spring(flipAnim, {
      toValue: 1,
      useNativeDriver: true,
      friction: 8,
      tension: 10,
    }).start();
    setShowAnswer(true);
  };

  const handleRating = async (rating: 1 | 2 | 3 | 4) => {
    if (!currentCard) return;

    try {
      // Call the appropriate review endpoint based on card type and direction
      if (currentCard.type === 'sentence') {
        await quizService.reviewSentence(currentCard.id, rating, practiceSettings.direction);
      } else {
        await quizService.reviewWord(currentCard.id, rating, practiceSettings.direction);
      }
      
      // If "Again" (rating 1), re-add card to end of queue for this session
      if (rating === 1) {
        setCards(prev => [...prev, currentCard]);
      }
      
      // Move to next card
      const nextIndex = currentIndex + 1;
      setStats(prev => ({ ...prev, reviewed: prev.reviewed + 1 }));
      
      if (nextIndex >= cards.length && rating !== 1) {
        // Only finish if we didn't just add a card back
        setIsFinished(true);
      } else if (nextIndex >= cards.length && rating === 1) {
        // Card was re-added, continue to it
        setCurrentIndex(nextIndex);
        setShowAnswer(false);
        flipAnim.setValue(0);
      } else {
        setCurrentIndex(nextIndex);
        setShowAnswer(false);
        flipAnim.setValue(0);
      }
    } catch (error) {
      console.error('Failed to review card:', error);
    }
  };

  const getQuestion = () => {
    if (!currentCard) return '';
    
    // For sentences, show text as question
    if (currentCard.type === 'sentence') {
      return practiceSettings.direction === 'forward' 
        ? currentCard.text 
        : currentCard.translation;
    }
    
    // For words, show lemma as question
    return practiceSettings.direction === 'forward' 
      ? (currentCard as any).lemma 
      : currentCard.translation;
  };

  const getAnswer = () => {
    if (!currentCard) return '';
    
    // For sentences, show translation as answer
    if (currentCard.type === 'sentence') {
      return practiceSettings.direction === 'forward' 
        ? currentCard.translation 
        : currentCard.text;
    }
    
    // For words, show translation as answer
    return practiceSettings.direction === 'forward' 
      ? currentCard.translation 
      : (currentCard as any).lemma;
  };

  const frontInterpolate = flipAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ['0deg', '90deg', '90deg'],
  });

  const backInterpolate = flipAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ['90deg', '90deg', '0deg'],
  });

  const frontAnimatedStyle = {
    transform: [{ rotateY: frontInterpolate }],
  };

  const backAnimatedStyle = {
    transform: [{ rotateY: backInterpolate }],
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.headerButton} onPress={onClose}>
            <Ionicons name="close" size={28} color={colors.textPrimary} />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle}>Loading...</Text>
          </View>
          <View style={styles.headerButton} />
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading cards...</Text>
        </View>
      </View>
    );
  }

  if (isFinished) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.headerButton} onPress={onClose}>
            <Ionicons name="close" size={28} color={colors.textPrimary} />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle}>Session Complete</Text>
          </View>
          <View style={styles.headerButton} />
        </View>
        <View style={styles.finishedContainer}>
          <Ionicons name="checkmark-circle" size={80} color={colors.success} />
          <Text style={styles.finishedTitle}>
            {stats.reviewed > 0 ? 'Great job!' : 'No cards due'}
          </Text>
          <Text style={styles.finishedSubtitle}>
            {stats.reviewed > 0 
              ? `You reviewed ${stats.reviewed} card${stats.reviewed !== 1 ? 's' : ''}`
              : 'All cards have been reviewed. Check back later!'}
          </Text>
          <View style={styles.statsContainer}>
            <View style={styles.statBox}>
              <Text style={styles.statNumber}>{stats.reviewed}</Text>
              <Text style={styles.statLabel}>Reviewed</Text>
            </View>
            <View style={styles.statBox}>
              <Text style={styles.statNumber}>{cards.length - currentIndex}</Text>
              <Text style={styles.statLabel}>Remaining</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.finishButton} onPress={onClose}>
            <Text style={styles.finishButtonText}>Done</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.restartButton} onPress={loadCards}>
            <Text style={styles.restartButtonText}>Check for Due Cards</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.resetButton} onPress={handleResetAnki}>
            <Ionicons name="refresh" size={18} color={colors.error} />
            <Text style={styles.resetButtonText}>Reset All Cards</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.headerButton} onPress={onClose}>
          <Ionicons name="close" size={28} color={colors.textPrimary} />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>Anki Review</Text>
          <Text style={styles.headerSubtitle}>
            {currentIndex + 1} / {cards.length}
          </Text>
        </View>
        <View style={styles.headerButton} />
      </View>

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View 
          style={[
            styles.progressBar, 
            { width: `${((currentIndex) / cards.length) * 100}%` }
          ]} 
        />
      </View>

      {/* Stats Bar */}
      <View style={styles.statsBar}>
        <View style={styles.statItem}>
          <Ionicons name="time-outline" size={16} color={colors.error} />
          <Text style={[styles.statText, { color: colors.error }]}>{stats.totalDue} due</Text>
        </View>
        <View style={styles.statItem}>
          <Ionicons name="add-circle-outline" size={16} color={colors.primary} />
          <Text style={[styles.statText, { color: colors.primary }]}>{stats.totalNew} new</Text>
        </View>
        <View style={styles.statItem}>
          <Ionicons name="checkmark-circle-outline" size={16} color={colors.success} />
          <Text style={[styles.statText, { color: colors.success }]}>{stats.reviewed} done</Text>
        </View>
      </View>

      {/* Card */}
      <View style={styles.cardContainer}>
        <TouchableOpacity 
          activeOpacity={0.9} 
          onPress={flipCard}
          style={styles.cardTouchable}
        >
          {/* Front of card */}
          <Animated.View style={[styles.card, styles.cardFront, frontAnimatedStyle]}>
            <View style={styles.cardBadge}>
              <Text style={styles.cardBadgeText}>
                {currentCard?.is_new ? 'NEW' : 'REVIEW'}
              </Text>
            </View>
            <Text style={styles.cardQuestion}>{getQuestion()}</Text>
            <Text style={styles.tapHint}>Tap to reveal answer</Text>
          </Animated.View>

          {/* Back of card */}
          <Animated.View style={[styles.card, styles.cardBack, backAnimatedStyle]}>
            <Text style={styles.cardQuestionSmall}>{getQuestion()}</Text>
            <View style={styles.divider} />
            <Text style={styles.cardAnswer}>{getAnswer()}</Text>
            {currentCard?.explanation && (
              <Text style={styles.cardExplanation} numberOfLines={3}>
                {currentCard.explanation}
              </Text>
            )}
          </Animated.View>
        </TouchableOpacity>
      </View>

      {/* Rating Buttons */}
      {showAnswer && (
        <View style={styles.ratingContainer}>
          <Text style={styles.ratingPrompt}>How well did you know this?</Text>
          <View style={styles.ratingButtons}>
            <TouchableOpacity 
              style={[styles.ratingButton, styles.ratingAgain]}
              onPress={() => handleRating(1)}
            >
              <Text style={styles.ratingButtonText}>Again</Text>
              <Text style={styles.ratingSubtext}>&lt;1m</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.ratingButton, styles.ratingHard]}
              onPress={() => handleRating(2)}
            >
              <Text style={styles.ratingButtonText}>Hard</Text>
              <Text style={styles.ratingSubtext}>~{Math.max(1, Math.floor((currentCard?.interval || 0) * 1.2))}d</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.ratingButton, styles.ratingGood]}
              onPress={() => handleRating(3)}
            >
              <Text style={styles.ratingButtonText}>Good</Text>
              <Text style={styles.ratingSubtext}>~{Math.max(1, Math.floor((currentCard?.interval || 0) * (currentCard?.ease_factor || 2.5)))}d</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.ratingButton, styles.ratingEasy]}
              onPress={() => handleRating(4)}
            >
              <Text style={styles.ratingButtonText}>Easy</Text>
              <Text style={styles.ratingSubtext}>~{Math.max(4, Math.floor((currentCard?.interval || 0) * (currentCard?.ease_factor || 2.5) * 1.3))}d</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
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
    fontSize: fontSize.lg,
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
  statsBar: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.lg,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  statText: {
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: colors.textMuted,
    fontSize: fontSize.md,
    marginTop: spacing.md,
  },
  cardContainer: {
    flex: 1,
    padding: spacing.lg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardTouchable: {
    width: '100%',
    maxWidth: 400,
    aspectRatio: 0.7,
  },
  card: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.xl,
    padding: spacing.xl,
    justifyContent: 'center',
    alignItems: 'center',
    backfaceVisibility: 'hidden',
    ...shadows.lg,
  },
  cardFront: {
    backgroundColor: colors.surface,
  },
  cardBack: {
    backgroundColor: colors.backgroundLight,
  },
  cardBadge: {
    position: 'absolute',
    top: spacing.md,
    left: spacing.md,
    backgroundColor: colors.primary + '30',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.sm,
  },
  cardBadgeText: {
    color: colors.primary,
    fontSize: fontSize.xs,
    fontWeight: '700',
    letterSpacing: 1,
  },
  cardQuestion: {
    color: colors.textPrimary,
    fontSize: fontSize.title,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  cardQuestionSmall: {
    color: colors.textSecondary,
    fontSize: fontSize.lg,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  cardHint: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  tapHint: {
    position: 'absolute',
    bottom: spacing.lg,
    color: colors.textMuted,
    fontSize: fontSize.sm,
  },
  divider: {
    width: '80%',
    height: 1,
    backgroundColor: colors.border,
    marginVertical: spacing.md,
  },
  cardAnswer: {
    color: colors.primary,
    fontSize: fontSize.xxxl,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  cardExplanation: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    textAlign: 'center',
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
  },
  ratingContainer: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.xl,
  },
  ratingPrompt: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  ratingButtons: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  ratingButton: {
    flex: 1,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.md,
    alignItems: 'center',
  },
  ratingButtonText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  ratingSubtext: {
    color: colors.textMuted,
    fontSize: fontSize.xs,
    marginTop: 2,
  },
  ratingAgain: {
    backgroundColor: colors.error + '30',
    borderWidth: 1,
    borderColor: colors.error,
  },
  ratingHard: {
    backgroundColor: colors.warning + '30',
    borderWidth: 1,
    borderColor: colors.warning,
  },
  ratingGood: {
    backgroundColor: colors.success + '30',
    borderWidth: 1,
    borderColor: colors.success,
  },
  ratingEasy: {
    backgroundColor: colors.primary + '30',
    borderWidth: 1,
    borderColor: colors.primary,
  },
  finishedContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  finishedTitle: {
    color: colors.textPrimary,
    fontSize: fontSize.xxl,
    fontWeight: 'bold',
    marginTop: spacing.lg,
  },
  finishedSubtitle: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  statsContainer: {
    flexDirection: 'row',
    gap: spacing.xl,
    marginTop: spacing.xl,
  },
  statBox: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    padding: spacing.lg,
    borderRadius: borderRadius.lg,
    minWidth: 100,
  },
  statNumber: {
    color: colors.primary,
    fontSize: fontSize.title,
    fontWeight: 'bold',
  },
  statLabel: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    marginTop: spacing.xs,
  },
  finishButton: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xxl,
    borderRadius: borderRadius.full,
    marginTop: spacing.xl,
  },
  finishButtonText: {
    color: colors.background,
    fontSize: fontSize.lg,
    fontWeight: '600',
  },
  restartButton: {
    marginTop: spacing.md,
    padding: spacing.md,
  },
  restartButtonText: {
    color: colors.primary,
    fontSize: fontSize.md,
  },
  resetButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.lg,
    padding: spacing.md,
    gap: spacing.xs,
  },
  resetButtonText: {
    color: colors.error,
    fontSize: fontSize.md,
  },
});

export default AnkiPracticeScreen;
