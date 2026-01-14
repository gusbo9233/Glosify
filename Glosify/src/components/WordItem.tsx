import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius } from '../utils/theme';
import { Word } from '../types';

interface WordItemProps {
  word: Word;
  index: number;
  isPlaying?: boolean;
  isSelected?: boolean;
  onPress: () => void;
  onLemmaPress: () => void;
  onToggleSelect?: () => void;
  onMorePress?: () => void;
  sourceLanguage?: string; // To determine which is the Slavic word
  targetLanguage?: string;
}

const WordItem: React.FC<WordItemProps> = ({
  word,
  index,
  isPlaying = false,
  isSelected = false,
  onPress,
  onLemmaPress,
  onToggleSelect,
  onMorePress,
  sourceLanguage,
  targetLanguage,
}) => {
  // Determine which is the Slavic word (lemma is typically the source language word)
  // For now, assume lemma is the Slavic word if target is Slavic, otherwise source is Slavic
  const slavicLanguages = ['Polish', 'Ukrainian', 'Russian', 'Czech', 'Slovak', 'Bulgarian', 'Serbian', 'Croatian', 'Slovenian'];
  const isTargetSlavic = targetLanguage && slavicLanguages.includes(targetLanguage);
  const isSourceSlavic = sourceLanguage && slavicLanguages.includes(sourceLanguage);
  
  // The Slavic word is the lemma if source is Slavic, or if we're learning Slavic (target is Slavic)
  // For simplicity, we'll show lemma as the "artist" (Slavic word) at the bottom
  const showLemmaAsArtist = isSourceSlavic || (isTargetSlavic && !isSourceSlavic);
  return (
    <TouchableOpacity
      style={[styles.container, isPlaying && styles.containerPlaying]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      {/* Checkbox */}
      <TouchableOpacity
        style={styles.checkboxContainer}
        onPress={(e) => {
          e.stopPropagation();
          onToggleSelect?.();
        }}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        {isSelected ? (
          <Ionicons name="checkbox" size={20} color={colors.primary} />
        ) : (
          <Ionicons name="square-outline" size={20} color={colors.textMuted} />
        )}
      </TouchableOpacity>

      {/* Track Number / Playing Indicator */}
      <View style={styles.indexContainer}>
        {isPlaying ? (
          <Ionicons name="volume-high" size={14} color={colors.primary} />
        ) : (
          <Text style={styles.index}>{index + 1}</Text>
        )}
      </View>

      {/* Word Info */}
      <View style={styles.infoContainer}>
        <Text
          style={[styles.translation, isPlaying && styles.textPlaying]}
          numberOfLines={1}
        >
          {word.translation}
        </Text>
        <TouchableOpacity 
          onPress={(e) => {
            e.stopPropagation();
            onLemmaPress();
          }}
          activeOpacity={0.7}
        >
          <Text style={styles.lemma} numberOfLines={1}>
            {word.lemma}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Properties Badge */}
      {word.properties && Object.keys(word.properties).length > 0 && (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>
            {Object.keys(word.properties).length}
          </Text>
        </View>
      )}

      {/* Variants Count */}
      {word.variants && word.variants.length > 0 && (
        <View style={styles.variantsCount}>
          <Ionicons name="git-branch-outline" size={14} color={colors.textMuted} />
          <Text style={styles.variantsText}>{word.variants.length}</Text>
        </View>
      )}

      {/* More Options */}
      <TouchableOpacity
        style={styles.moreButton}
        onPress={(e) => {
          e.stopPropagation();
          onMorePress?.();
        }}
      >
        <Ionicons name="ellipsis-horizontal" size={18} color={colors.textMuted} />
      </TouchableOpacity>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: borderRadius.sm,
  },
  containerPlaying: {
    backgroundColor: colors.backgroundLighter,
  },
  checkboxContainer: {
    padding: spacing.xs,
    marginRight: spacing.xs,
  },
  indexContainer: {
    width: 32,
    alignItems: 'center',
  },
  index: {
    color: colors.textMuted,
    fontSize: fontSize.md,
  },
  infoContainer: {
    flex: 1,
    marginLeft: spacing.sm,
  },
  translation: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '500',
  },
  textPlaying: {
    color: colors.primary,
  },
  lemma: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginTop: 4,
    fontWeight: '400',
  },
  badge: {
    backgroundColor: colors.backgroundLighter,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: borderRadius.full,
    marginRight: spacing.sm,
  },
  badgeText: {
    color: colors.textMuted,
    fontSize: fontSize.xs,
  },
  variantsCount: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginRight: spacing.sm,
  },
  variantsText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
  },
  moreButton: {
    padding: spacing.xs,
  },
});

export default WordItem;

