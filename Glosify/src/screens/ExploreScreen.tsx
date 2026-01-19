import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
  FlatList,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius, shadows } from '../utils/theme';
import { useApp } from '../context/AppContext';
import { Quiz } from '../types';
import quizService from '../api/quizService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const isTablet = SCREEN_WIDTH > 768;

interface ExploreScreenProps {
  onQuizPress: (quiz: Quiz) => void;
  onBack: () => void;
}

const ExploreScreen: React.FC<ExploreScreenProps> = ({ 
  onQuizPress,
  onBack,
}) => {
  const { user } = useApp();
  const [publicQuizzes, setPublicQuizzes] = useState<Quiz[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [subscribingQuizId, setSubscribingQuizId] = useState<number | null>(null);
  const [subscribedQuizIds, setSubscribedQuizIds] = useState<Set<number>>(new Set());
  const [copyingQuizId, setCopyingQuizId] = useState<number | null>(null);

  useEffect(() => {
    loadPublicQuizzes();
  }, []);

  const loadPublicQuizzes = async () => {
    setIsLoading(true);
    try {
      const quizzes = await quizService.getPublicQuizzes();
      setPublicQuizzes(quizzes);
    } catch (error) {
      console.error('Failed to load public quizzes:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubscribe = async (quiz: Quiz) => {
    if (subscribingQuizId || subscribedQuizIds.has(quiz.id)) return;
    
    setSubscribingQuizId(quiz.id);
    try {
      await quizService.subscribeToQuiz(quiz.id);
      setSubscribedQuizIds(prev => new Set(prev).add(quiz.id));
      // Reload folders to show the new subscription
      // The parent component should handle this
    } catch (error: any) {
      console.error('Failed to subscribe to quiz:', error);
      if (error?.response?.status === 400 && error?.response?.data?.quiz_id) {
        // Already subscribed
        setSubscribedQuizIds(prev => new Set(prev).add(quiz.id));
      }
    } finally {
      setSubscribingQuizId(null);
    }
  };

  const handleCopy = async (quiz: Quiz) => {
    if (copyingQuizId) return;
    
    setCopyingQuizId(quiz.id);
    try {
      await quizService.copyQuiz(quiz.id);
      // Reload folders to show the new copy
      // The parent component should handle this
    } catch (error: any) {
      console.error('Failed to copy quiz:', error);
    } finally {
      setCopyingQuizId(null);
    }
  };

  const renderQuizItem = ({ item }: { item: Quiz }) => {
    const isSubscribed = subscribedQuizIds.has(item.id);
    const isSubscribing = subscribingQuizId === item.id;
    const isCopying = copyingQuizId === item.id;
    // Hide copy/subscribe buttons if the quiz belongs to the current user
    const isOwnQuiz = item.user_id === user?.id;
    
    return (
      <View style={styles.quizCard}>
        <TouchableOpacity
          style={styles.quizCardContent}
          onPress={() => onQuizPress(item)}
          activeOpacity={0.7}
        >
          <View style={styles.quizCardHeader}>
            <View style={styles.quizCardIcon}>
              <Ionicons name="book" size={24} color={colors.primary} />
            </View>
            <View style={styles.quizCardInfo}>
              <Text style={styles.quizCardName} numberOfLines={2}>
                {item.name}
              </Text>
              <View style={styles.quizCardMeta}>
                {item.source_language && item.target_language && (
                  <Text style={styles.quizCardLanguage}>
                    {item.source_language} → {item.target_language}
                  </Text>
                )}
                <Text style={styles.quizCardStats}>
                  {item.word_count || 0} words
                  {item.sentence_count ? ` • ${item.sentence_count} sentences` : ''}
                </Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </View>
        </TouchableOpacity>
        {!isOwnQuiz && (
          <View style={styles.quizActions}>
            <TouchableOpacity
              style={[styles.actionButton, styles.copyButton]}
              onPress={() => handleCopy(item)}
              disabled={isCopying}
            >
              {isCopying ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <>
                  <Ionicons name="copy-outline" size={16} color={colors.primary} />
                  <Text style={styles.actionButtonText}>Copy</Text>
                </>
              )}
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionButton, styles.subscribeButton, isSubscribed && styles.subscribeButtonSubscribed]}
              onPress={() => handleSubscribe(item)}
              disabled={isSubscribing || isSubscribed}
            >
              {isSubscribing ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : isSubscribed ? (
                <>
                  <Ionicons name="checkmark" size={16} color={colors.primary} />
                  <Text style={styles.actionButtonText}>Subscribed</Text>
                </>
              ) : (
                <>
                  <Ionicons name="add" size={16} color={colors.primary} />
                  <Text style={styles.actionButtonText}>Subscribe</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>
    );
  };

  if (isLoading) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={onBack}>
            <Ionicons name="arrow-back" size={24} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Explore</Text>
          <View style={styles.backButton} />
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={onBack}>
          <Ionicons name="arrow-back" size={24} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Explore</Text>
        <View style={styles.backButton} />
      </View>

      {publicQuizzes.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Ionicons name="globe-outline" size={80} color={colors.textMuted} />
          <Text style={styles.emptyTitle}>No Public Quizzes</Text>
          <Text style={styles.emptySubtitle}>
            There are no public quizzes available yet.
          </Text>
        </View>
      ) : (
        <FlatList
          data={publicQuizzes}
          renderItem={renderQuizItem}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          ListHeaderComponent={
            <View style={styles.headerSection}>
              <Text style={styles.sectionTitle}>Public Quizzes</Text>
              <Text style={styles.sectionSubtitle}>
                Discover quizzes shared by the community
              </Text>
            </View>
          }
        />
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
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    paddingTop: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: fontSize.xl,
    fontWeight: 'bold',
    color: colors.textPrimary,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptyTitle: {
    fontSize: fontSize.xl,
    fontWeight: 'bold',
    color: colors.textPrimary,
    marginTop: spacing.lg,
  },
  emptySubtitle: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  listContent: {
    padding: spacing.md,
  },
  headerSection: {
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    fontSize: fontSize.xxl,
    fontWeight: 'bold',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  sectionSubtitle: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
  },
  quizCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    marginBottom: spacing.md,
    ...shadows.small,
  },
  quizCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
  },
  quizCardIcon: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.md,
    backgroundColor: colors.primary + '20',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.md,
  },
  quizCardInfo: {
    flex: 1,
  },
  quizCardName: {
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  quizCardMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: spacing.sm,
  },
  quizCardLanguage: {
    fontSize: fontSize.sm,
    color: colors.primary,
    fontWeight: '500',
  },
  quizCardStats: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
  },
  quizActions: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.primary + '20',
    flex: 1,
  },
  copyButton: {
    borderRightWidth: 1,
    borderRightColor: colors.border,
  },
  subscribeButton: {
    // Inherits from actionButton
  },
  subscribeButtonSubscribed: {
    backgroundColor: colors.primary + '10',
  },
  actionButtonText: {
    fontSize: fontSize.sm,
    fontWeight: '600',
    color: colors.primary,
  },
});

export default ExploreScreen;
