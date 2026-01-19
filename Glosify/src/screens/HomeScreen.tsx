import React, { useState, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius, shadows } from '../utils/theme';
import { useApp } from '../context/AppContext';
import { Quiz, Folder } from '../types';
import quizService from '../api/quizService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const isTablet = SCREEN_WIDTH > 768;

interface HomeScreenProps {
  onQuizPress: (quiz: Quiz) => void;
  onStartAnkiPress: (quiz: Quiz, mode: 'words' | 'sentences') => void;
  onExplorePress: () => void;
}

// Helper to get all quizzes including those in nested folders
const getAllQuizzesFromFolders = (folderList: Folder[]): Quiz[] => {
  let allQuizzes: Quiz[] = [];
  for (const folder of folderList) {
    allQuizzes = [...allQuizzes, ...folder.quizzes];
    allQuizzes = [...allQuizzes, ...getAllQuizzesFromFolders(folder.subfolders)];
  }
  return allQuizzes;
};

const HomeScreen: React.FC<HomeScreenProps> = ({ 
  onQuizPress,
  onStartAnkiPress,
  onExplorePress,
}) => {
  const { quizzes, folders, user } = useApp();
  
  // Get all quizzes (root level + from all folders)
  const allQuizzes = useMemo(
    () => [...quizzes, ...getAllQuizzesFromFolders(folders)],
    [quizzes, folders]
  );
  const [ankiStats, setAnkiStats] = useState<{
    total_due: number;
    total_new: number;
    total_due_words: number;
    total_due_sentences: number;
    quizzes_with_due: Array<{
      id: number;
      name: string;
      due_words: number;
      due_sentences: number;
    }>;
  } | null>(null);
  const [loadingAnki, setLoadingAnki] = useState(true);

  // Fetch Anki statistics
  const ankiStatsKey = useMemo(
    () =>
      allQuizzes
        .map(
          (quiz) =>
            `${quiz.id}:${quiz.words?.length || 0}:${quiz.sentences?.length || 0}`
        )
        .join('|'),
    [allQuizzes]
  );

  useEffect(() => {
    const fetchAnkiStats = async () => {
      try {
        const stats = await quizService.getAnkiStats();
        setAnkiStats(stats);
      } catch (error) {
        console.error('Failed to fetch Anki stats:', error);
      } finally {
        setLoadingAnki(false);
      }
    };

    if (allQuizzes.length > 0) {
      fetchAnkiStats();
    } else {
      setLoadingAnki(false);
    }
  }, [ankiStatsKey, allQuizzes.length]);

  // Calculate statistics
  const totalQuizzes = allQuizzes.length;
  const totalWords = allQuizzes.reduce((sum, quiz) => sum + (quiz.words?.length || 0), 0);
  const totalSentences = allQuizzes.reduce((sum, quiz) => sum + (quiz.sentences?.length || 0), 0);
  const recentQuizzes = [...allQuizzes]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 6);

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Welcome Section */}
      <View style={styles.welcomeSection}>
        <View style={styles.welcomeHeader}>
          <View style={styles.welcomeTextContainer}>
            <Text style={styles.welcomeTitle}>Welcome back{user ? `, ${user.username}` : ''}!</Text>
            <Text style={styles.welcomeSubtitle}>
              Continue learning with your vocabulary quizzes
            </Text>
          </View>
          <TouchableOpacity
            style={styles.exploreButton}
            onPress={onExplorePress}
          >
            <Ionicons name="globe" size={20} color={colors.primary} />
            <Text style={styles.exploreButtonText}>Explore</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Statistics Cards */}
      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <View style={styles.statIcon}>
            <Ionicons name="book" size={24} color={colors.primary} />
          </View>
          <View style={styles.statContent}>
            <Text style={styles.statValue}>{totalQuizzes}</Text>
            <Text style={styles.statLabel}>Quizzes</Text>
          </View>
        </View>

        <View style={styles.statCard}>
          <View style={styles.statIcon}>
            <Ionicons name="text" size={24} color={colors.primary} />
          </View>
          <View style={styles.statContent}>
            <Text style={styles.statValue}>{totalWords}</Text>
            <Text style={styles.statLabel}>Words</Text>
          </View>
        </View>

        <View style={styles.statCard}>
          <View style={styles.statIcon}>
            <Ionicons name="document-text" size={24} color={colors.primary} />
          </View>
          <View style={styles.statContent}>
            <Text style={styles.statValue}>{totalSentences}</Text>
            <Text style={styles.statLabel}>Sentences</Text>
          </View>
        </View>
      </View>

      {/* Anki Statistics */}
      {loadingAnki ? (
        <View style={styles.ankiSection}>
          <ActivityIndicator size="small" color={colors.primary} />
        </View>
      ) : ankiStats && (ankiStats.total_due > 0 || ankiStats.total_new > 0) && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>📚 Anki Review</Text>
          </View>
          <View style={styles.ankiCard}>
            <View style={styles.ankiStatRow}>
              <View style={styles.ankiStatItem}>
                <Ionicons name="flash" size={20} color={colors.warning} />
                <View style={styles.ankiStatContent}>
                  <Text style={styles.ankiStatValue}>{ankiStats.total_due}</Text>
                  <Text style={styles.ankiStatLabel}>Due Cards</Text>
                </View>
              </View>
              <View style={styles.ankiStatItem}>
                <Ionicons name="star" size={20} color={colors.primary} />
                <View style={styles.ankiStatContent}>
                  <Text style={styles.ankiStatValue}>{ankiStats.total_new}</Text>
                  <Text style={styles.ankiStatLabel}>New Cards</Text>
                </View>
              </View>
            </View>
            {ankiStats.quizzes_with_due.length > 0 && (
              <View style={styles.quizzesWithDue}>
                <Text style={styles.quizzesWithDueTitle}>Quizzes with due cards:</Text>
                {ankiStats.quizzes_with_due.slice(0, 3).map((quiz) => (
                  <TouchableOpacity
                    key={quiz.id}
                    style={styles.quizWithDueItem}
                    onPress={() => {
                      const foundQuiz = allQuizzes.find(q => q.id === quiz.id);
                      if (foundQuiz) {
                        const defaultMode = quiz.due_words > 0 ? 'words' : 'sentences';
                        onStartAnkiPress(foundQuiz, defaultMode);
                      }
                    }}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.quizWithDueName}>{quiz.name}</Text>
                    <View style={styles.quizWithDueBadges}>
                      {quiz.due_words > 0 && (
                        <TouchableOpacity
                          style={styles.dueBadge}
                          onPress={() => {
                            const foundQuiz = allQuizzes.find(q => q.id === quiz.id);
                            if (foundQuiz) onStartAnkiPress(foundQuiz, 'words');
                          }}
                          activeOpacity={0.8}
                        >
                          <Text style={styles.dueBadgeText}>{quiz.due_words} words</Text>
                        </TouchableOpacity>
                      )}
                      {quiz.due_sentences > 0 && (
                        <TouchableOpacity
                          style={styles.dueBadge}
                          onPress={() => {
                            const foundQuiz = allQuizzes.find(q => q.id === quiz.id);
                            if (foundQuiz) onStartAnkiPress(foundQuiz, 'sentences');
                          }}
                          activeOpacity={0.8}
                        >
                          <Text style={styles.dueBadgeText}>{quiz.due_sentences} sentences</Text>
                        </TouchableOpacity>
                      )}
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </View>
        </View>
      )}

      {/* Recent Quizzes Section */}
      {recentQuizzes.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Quizzes</Text>
            <TouchableOpacity>
              <Text style={styles.seeAllText}>See all</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.quizzesGrid}>
            {recentQuizzes.map((quiz) => (
              <TouchableOpacity
                key={quiz.id}
                style={styles.quizCard}
                onPress={() => onQuizPress(quiz)}
                activeOpacity={0.7}
              >
                <View style={styles.quizCardIcon}>
                  <Ionicons name="book" size={32} color={colors.primary} />
                </View>
                <Text style={styles.quizCardName} numberOfLines={2}>
                  {quiz.name}
                </Text>
                <View style={styles.quizCardMeta}>
                  <Text style={styles.quizCardMetaText}>
                    {quiz.words?.length || 0} words
                  </Text>
                  {quiz.source_language && quiz.target_language && (
                    <Text style={styles.quizCardMetaText}>
                      {quiz.source_language} → {quiz.target_language}
                    </Text>
                  )}
                </View>
                {quiz.processing_status === 'processing' && (
                  <View style={styles.processingBadge}>
                    <Ionicons name="sync" size={12} color={colors.warning} />
                    <Text style={styles.processingText}>Processing</Text>
                  </View>
                )}
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* Empty State */}
      {totalQuizzes === 0 && (
        <View style={styles.emptyState}>
          <Ionicons name="book-outline" size={64} color={colors.textMuted} />
          <Text style={styles.emptyTitle}>No quizzes yet</Text>
          <Text style={styles.emptySubtitle}>
            Create your first quiz to start learning!
          </Text>
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  welcomeSection: {
    padding: spacing.xl,
    paddingTop: spacing.xxl,
  },
  welcomeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  welcomeTextContainer: {
    flex: 1,
  },
  welcomeTitle: {
    fontSize: fontSize.xxxl,
    fontWeight: 'bold',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  welcomeSubtitle: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
  },
  exploreButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.primary + '20',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: borderRadius.md,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  exploreButtonText: {
    color: colors.primary,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  statsContainer: {
    flexDirection: 'row',
    paddingHorizontal: spacing.xl,
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  statCard: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    ...shadows.md,
  },
  statIcon: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.md,
    backgroundColor: colors.primary + '20',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.md,
  },
  statContent: {
    flex: 1,
  },
  statValue: {
    fontSize: fontSize.xxl,
    fontWeight: 'bold',
    color: colors.textPrimary,
  },
  statLabel: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  section: {
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: fontSize.xl,
    fontWeight: 'bold',
    color: colors.textPrimary,
  },
  seeAllText: {
    fontSize: fontSize.sm,
    color: colors.primary,
    fontWeight: '600',
  },
  quizzesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  quizCard: {
    width: isTablet ? (SCREEN_WIDTH - spacing.xl * 2 - spacing.md * 2) / 3 : (SCREEN_WIDTH - spacing.xl * 2 - spacing.md) / 2,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    ...shadows.md,
    position: 'relative',
  },
  quizCardIcon: {
    width: 56,
    height: 56,
    borderRadius: borderRadius.md,
    backgroundColor: colors.primary + '20',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  quizCardName: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
    minHeight: 40,
  },
  quizCardMeta: {
    gap: spacing.xs,
  },
  quizCardMetaText: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
  processingBadge: {
    position: 'absolute',
    top: spacing.sm,
    right: spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.warning + '20',
    paddingHorizontal: spacing.xs,
    paddingVertical: 4,
    borderRadius: borderRadius.sm,
  },
  processingText: {
    fontSize: fontSize.xs,
    color: colors.warning,
    fontWeight: '600',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xxl * 2,
    paddingHorizontal: spacing.xl,
  },
  emptyTitle: {
    fontSize: fontSize.xl,
    fontWeight: 'bold',
    color: colors.textPrimary,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  emptySubtitle: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  ankiSection: {
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.xl,
    alignItems: 'center',
    paddingVertical: spacing.md,
  },
  ankiCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    ...shadows.md,
  },
  ankiStatRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  ankiStatItem: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  ankiStatContent: {
    flex: 1,
  },
  ankiStatValue: {
    fontSize: fontSize.xl,
    fontWeight: 'bold',
    color: colors.textPrimary,
  },
  ankiStatLabel: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    marginTop: 2,
  },
  quizzesWithDue: {
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  quizzesWithDueTitle: {
    fontSize: fontSize.sm,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  quizWithDueItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.sm,
    marginBottom: spacing.xs,
  },
  quizWithDueName: {
    fontSize: fontSize.sm,
    fontWeight: '500',
    color: colors.textPrimary,
    flex: 1,
  },
  quizWithDueBadges: {
    flexDirection: 'row',
    gap: spacing.xs,
  },
  dueBadge: {
    backgroundColor: colors.warning + '20',
    paddingHorizontal: spacing.xs,
    paddingVertical: 2,
    borderRadius: borderRadius.sm,
  },
  dueBadgeText: {
    fontSize: fontSize.xs,
    color: colors.warning,
    fontWeight: '600',
  },
});

export default HomeScreen;
