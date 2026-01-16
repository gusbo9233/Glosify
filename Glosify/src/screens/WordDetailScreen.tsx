import React, { useMemo, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Dimensions,
  TextInput,
  Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius, shadows } from '../utils/theme';
import { useApp } from '../context/AppContext';
import quizService from '../api/quizService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface WordDetailScreenProps {
  onBack: () => void;
}

const WordDetailScreen: React.FC<WordDetailScreenProps> = ({ onBack }) => {
  const { selectedWord, selectWord } = useApp();
  const [isEditing, setIsEditing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const editState = useMemo(() => {
    if (!selectedWord) return null;
    return {
      lemma: selectedWord.lemma,
      translation: selectedWord.translation,
      example_sentence: selectedWord.example_sentence || '',
      explanation: selectedWord.explanation || '',
      variants: (selectedWord.variants || []).map((variant) => ({
        id: variant.id,
        value: variant.value,
        translation: variant.translation,
        tags: variant.tags || {},
      })),
    };
  }, [selectedWord]);

  const [editLemma, setEditLemma] = useState(editState?.lemma || '');
  const [editTranslation, setEditTranslation] = useState(editState?.translation || '');
  const [editExample, setEditExample] = useState(editState?.example_sentence || '');
  const [editExplanation, setEditExplanation] = useState(editState?.explanation || '');
  const [editVariants, setEditVariants] = useState(editState?.variants || []);

  const enterEditMode = () => {
    if (!editState) return;
    setEditLemma(editState.lemma);
    setEditTranslation(editState.translation);
    setEditExample(editState.example_sentence);
    setEditExplanation(editState.explanation);
    setEditVariants(editState.variants);
    setIsEditing(true);
  };

  const handleAddVariant = () => {
    setEditVariants((prev) => [
      ...prev,
      { id: undefined, value: '', translation: '', tags: {} },
    ]);
  };

  const handleRemoveVariant = (index: number) => {
    setEditVariants((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateVariant = (index: number, field: string, value: string) => {
    setEditVariants((prev) =>
      prev.map((variant, i) =>
        i === index ? { ...variant, [field]: value } : variant
      )
    );
  };

  const handleSave = async () => {
    if (!selectedWord) return;
    try {
      const variantsPayload = editVariants.map((variant) => ({
        id: variant.id, // Include ID so backend can preserve tags
        value: variant.value.trim(),
        translation: variant.translation.trim(),
        // Don't send tags - they're read-only and will be preserved by backend
      }));

      const updatedWord = await quizService.updateWord(selectedWord.id, {
        lemma: editLemma.trim(),
        translation: editTranslation.trim(),
        example_sentence: editExample.trim() || null,
        explanation: editExplanation.trim() || null,
        // Don't send properties or tags - they're read-only
        variants: variantsPayload,
      });

      await selectWord(updatedWord);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update word:', error);
      setErrorMessage('Failed to update word. Please check your JSON formats.');
    }
  };

  if (!selectedWord) {
    return null;
  }

  const properties = selectedWord.properties || {};
  const variants = selectedWord.variants || [];

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Back Button */}
      <TouchableOpacity style={styles.backButton} onPress={onBack}>
        <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
        <Text style={styles.backText}>Back</Text>
      </TouchableOpacity>

      {/* Header - Artist style */}
      <View style={styles.header}>
        <View style={styles.headerActions}>
          <TouchableOpacity
            style={styles.editButton}
            onPress={isEditing ? handleSave : enterEditMode}
          >
            <Ionicons
              name={isEditing ? 'save-outline' : 'create-outline'}
              size={18}
              color={colors.textPrimary}
            />
            <Text style={styles.editButtonText}>{isEditing ? 'Save' : 'Edit'}</Text>
          </TouchableOpacity>
          {isEditing && (
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => setIsEditing(false)}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
          )}
        </View>
        <View style={styles.avatarLarge}>
          <Text style={styles.avatarText}>
            {selectedWord.lemma.charAt(0).toUpperCase()}
          </Text>
        </View>

        <View style={styles.verifiedBadge}>
          <Ionicons name="checkmark-circle" size={16} color={colors.primary} />
          <Text style={styles.verifiedText}>Verified Word</Text>
        </View>

        {!isEditing ? (
          <>
        <Text style={styles.lemma}>{selectedWord.lemma}</Text>
        <Text style={styles.translation}>{selectedWord.translation}</Text>
          </>
        ) : (
          <View style={styles.editHeaderFields}>
            <TextInput
              style={styles.editInput}
              placeholder="Lemma"
              placeholderTextColor={colors.textMuted}
              value={editLemma}
              onChangeText={setEditLemma}
            />
            <TextInput
              style={styles.editInput}
              placeholder="Translation"
              placeholderTextColor={colors.textMuted}
              value={editTranslation}
              onChangeText={setEditTranslation}
            />
          </View>
        )}
      </View>

      {/* Example Sentence */}
      {(!isEditing && selectedWord.example_sentence) && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Example</Text>
          <View style={styles.exampleCard}>
            <Ionicons name="chatbubble-outline" size={20} color={colors.primary} />
            <Text style={styles.exampleText}>{selectedWord.example_sentence}</Text>
          </View>
        </View>
      )}
      {isEditing && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Example</Text>
          <TextInput
            style={[styles.editInput, styles.textAreaSmall]}
            placeholder="Example sentence"
            placeholderTextColor={colors.textMuted}
            value={editExample}
            onChangeText={setEditExample}
            multiline
            textAlignVertical="top"
          />
        </View>
      )}

      {/* Explanation */}
      {(!isEditing && selectedWord.explanation) && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Explanation</Text>
          <View style={styles.explanationCard}>
            <Ionicons name="information-circle-outline" size={20} color={colors.primary} />
            <Text style={styles.explanationText}>{selectedWord.explanation}</Text>
          </View>
        </View>
      )}
      {isEditing && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Explanation</Text>
          <TextInput
            style={[styles.editInput, styles.textArea]}
            placeholder="Explanation"
            placeholderTextColor={colors.textMuted}
            value={editExplanation}
            onChangeText={setEditExplanation}
            multiline
            textAlignVertical="top"
          />
        </View>
      )}

      {/* Properties - Read-only */}
      {Object.keys(properties).length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Properties</Text>
          <View style={styles.propertiesGrid}>
            {Object.entries(properties).map(([key, value]) => (
              <View key={key} style={styles.propertyCard}>
                <Text style={styles.propertyKey}>{key}</Text>
                <Text style={styles.propertyValue}>{value}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Variants */}
        <View style={styles.section}>
        <View style={styles.variantsHeaderRow}>
          <Text style={styles.sectionTitle}>Variants</Text>
          {isEditing && (
            <TouchableOpacity style={styles.addVariantButton} onPress={handleAddVariant}>
              <Ionicons name="add" size={18} color={colors.background} />
              <Text style={styles.addVariantText}>Add</Text>
            </TouchableOpacity>
          )}
        </View>
        {!isEditing && variants.length > 0 && (
          <Text style={styles.sectionSubtitle}>
            {variants.length} form{variants.length !== 1 ? 's' : ''} available
          </Text>
        )}
        {isEditing && editVariants.length === 0 && (
          <Text style={styles.sectionSubtitle}>No variants yet.</Text>
        )}

        {!isEditing && variants.length > 0 && (
          <View style={styles.variantsList}>
            {variants.map((variant, index) => (
              <View key={variant.id || index} style={styles.variantItem}>
                <View style={styles.variantIndex}>
                  <Text style={styles.variantIndexText}>{index + 1}</Text>
                </View>
                <View style={styles.variantInfo}>
                  <Text style={styles.variantValue}>{variant.value}</Text>
                  <Text style={styles.variantTranslation}>
                    {variant.translation}
                  </Text>
                </View>
                {variant.tags && Object.keys(variant.tags).length > 0 && (
                  <View style={styles.variantTags}>
                    {Object.entries(variant.tags).map(([key, value]) => (
                      <View key={key} style={styles.tag}>
                        <Text style={styles.tagText}>
                          {key}={value}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ))}
          </View>
        )}

        {isEditing && (
          <View style={styles.variantsList}>
            {editVariants.map((variant, index) => (
              <View key={`${variant.id || 'new'}-${index}`} style={styles.editVariantCard}>
                <View style={styles.editVariantRow}>
                  <TextInput
                    style={styles.editVariantInput}
                    placeholder="Variant value"
                    placeholderTextColor={colors.textMuted}
                    value={variant.value}
                    onChangeText={(value) => handleUpdateVariant(index, 'value', value)}
                  />
                  <TextInput
                    style={styles.editVariantInput}
                    placeholder="Translation"
                    placeholderTextColor={colors.textMuted}
                    value={variant.translation}
                    onChangeText={(value) => handleUpdateVariant(index, 'translation', value)}
                  />
                </View>
                {/* Tags - Read-only display */}
                {variant.tags && Object.keys(variant.tags).length > 0 && (
                  <View style={styles.variantTags}>
                    {Object.entries(variant.tags).map(([key, value]) => (
                      <View key={key} style={styles.tag}>
                        <Text style={styles.tagText}>
                          {key}={value}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}
                <TouchableOpacity
                  style={styles.removeVariantButton}
                  onPress={() => handleRemoveVariant(index)}
                >
                  <Ionicons name="trash-outline" size={16} color={colors.error} />
                  <Text style={styles.removeVariantText}>Remove</Text>
                </TouchableOpacity>
              </View>
            ))}
        </View>
      )}
      </View>

      {/* Quick Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Actions</Text>
        <View style={styles.actionsRow}>
          <TouchableOpacity style={styles.actionButton}>
            <Ionicons name="play" size={20} color={colors.textPrimary} />
            <Text style={styles.actionText}>Practice</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Ionicons name="heart-outline" size={20} color={colors.textPrimary} />
            <Text style={styles.actionText}>Favorite</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Ionicons name="share-outline" size={20} color={colors.textPrimary} />
            <Text style={styles.actionText}>Share</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.bottomSpacer} />
      
      <Modal
        visible={errorMessage !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setErrorMessage(null)}
      >
        <View style={styles.errorOverlay}>
          <View style={styles.errorContent}>
            <Text style={styles.errorTitle}>Error</Text>
            <Text style={styles.errorMessage}>{errorMessage}</Text>
            <TouchableOpacity
              style={styles.errorButton}
              onPress={() => setErrorMessage(null)}
            >
              <Text style={styles.errorButtonText}>OK</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    paddingTop: spacing.xl,
    gap: spacing.xs,
  },
  backText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
  },
  header: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.backgroundLight,
  },
  headerActions: {
    alignSelf: 'stretch',
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  editButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.backgroundLighter,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
    borderRadius: borderRadius.full,
  },
  editButtonText: {
    color: colors.textPrimary,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  cancelButton: {
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
  },
  cancelButtonText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
  },
  editHeaderFields: {
    width: '100%',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  editInput: {
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.textPrimary,
    fontSize: fontSize.md,
  },
  textArea: {
    minHeight: 140,
    paddingTop: spacing.md,
  },
  textAreaSmall: {
    minHeight: 80,
    paddingTop: spacing.md,
  },
  avatarLarge: {
    width: 150,
    height: 150,
    borderRadius: 75,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    ...shadows.lg,
  },
  avatarText: {
    fontSize: 60,
    fontWeight: 'bold',
    color: colors.background,
  },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: spacing.md,
  },
  verifiedText: {
    color: colors.primary,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  lemma: {
    fontSize: fontSize.title,
    fontWeight: 'bold',
    color: colors.textPrimary,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  translation: {
    fontSize: fontSize.xl,
    color: colors.textSecondary,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  section: {
    padding: spacing.lg,
  },
  sectionTitle: {
    fontSize: fontSize.lg,
    fontWeight: 'bold',
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  sectionSubtitle: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
  exampleCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
  },
  exampleText: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontStyle: 'italic',
    lineHeight: 22,
  },
  explanationCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
  },
  explanationText: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: fontSize.md,
    lineHeight: 24,
  },
  propertiesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  propertyCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    minWidth: 100,
  },
  propertyKey: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  propertyValue: {
    fontSize: fontSize.md,
    color: colors.textPrimary,
    fontWeight: '600',
    marginTop: spacing.xs,
  },
  variantsList: {
    gap: spacing.sm,
  },
  variantsHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  addVariantButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.full,
  },
  addVariantText: {
    color: colors.background,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  editVariantCard: {
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  editVariantRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  editVariantInput: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.sm,
    color: colors.textPrimary,
    fontSize: fontSize.sm,
  },
  removeVariantButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: spacing.sm,
  },
  removeVariantText: {
    color: colors.error,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  variantItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    gap: spacing.md,
  },
  variantIndex: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.backgroundLighter,
    justifyContent: 'center',
    alignItems: 'center',
  },
  variantIndexText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  variantInfo: {
    flex: 1,
  },
  variantValue: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '500',
  },
  variantTranslation: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginTop: 2,
  },
  variantTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  tag: {
    backgroundColor: colors.backgroundLighter,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: borderRadius.full,
  },
  tagText: {
    color: colors.textMuted,
    fontSize: fontSize.xs,
  },
  actionsRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  actionButton: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
    gap: spacing.sm,
  },
  actionText: {
    color: colors.textPrimary,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  bottomSpacer: {
    height: spacing.xxl,
  },
  errorOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  errorContent: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    width: '100%',
    maxWidth: 400,
  },
  errorTitle: {
    color: colors.textPrimary,
    fontSize: fontSize.lg,
    fontWeight: '600',
    marginBottom: spacing.sm,
  },
  errorMessage: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    marginBottom: spacing.lg,
  },
  errorButton: {
    backgroundColor: colors.primary,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
  },
  errorButtonText: {
    color: colors.background,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
});

export default WordDetailScreen;

