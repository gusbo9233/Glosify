import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius } from '../utils/theme';
import { Sentence } from '../types';

interface SentenceItemProps {
  sentence: Sentence;
  index: number;
  isPlaying?: boolean;
  isSelected?: boolean;
  onPress: () => void;
  onToggleSelect?: () => void;
}

const SentenceItem: React.FC<SentenceItemProps> = ({
  sentence,
  index,
  isPlaying = false,
  isSelected = false,
  onPress,
  onToggleSelect,
}) => {
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

      {/* Sentence Info */}
      <View style={styles.infoContainer}>
        <Text
          style={[styles.sentence, isPlaying && styles.textPlaying]}
          numberOfLines={2}
        >
          {sentence.text} - {sentence.translation}
        </Text>
      </View>

      {/* More Options */}
      <TouchableOpacity style={styles.moreButton}>
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
  sentence: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '500',
  },
  textPlaying: {
    color: colors.primary,
  },
  moreButton: {
    padding: spacing.xs,
  },
});

export default SentenceItem;
