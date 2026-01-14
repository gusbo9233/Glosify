import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  FlatList,
  Dimensions,
  ActivityIndicator,
  Modal,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { colors, spacing, fontSize, borderRadius, shadows } from '../utils/theme';
import { useApp } from '../context/AppContext';
import WordItem from '../components/WordItem';
import SentenceItem from '../components/SentenceItem';
import PlayButton from '../components/PlayButton';
import { Word, Sentence, Variant } from '../types';
import quizService from '../api/quizService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const isTablet = SCREEN_WIDTH > 768;

interface QuizDetailScreenProps {
  onWordPress: (word: Word) => void;
  onStartPractice: (selectedWordIds: Set<number>) => void;
  onStartAnkiPractice: () => void;
}

const QuizDetailScreen: React.FC<QuizDetailScreenProps> = ({
  onWordPress,
  onStartPractice,
  onStartAnkiPractice,
}) => {
  const { quizzes, selectedQuiz, practiceSettings, updatePracticeSettings, addWordToQuiz, importTextToQuiz, importImageToQuiz, selectQuiz } = useApp();
  const [showAddWord, setShowAddWord] = useState(false);
  const [newLemma, setNewLemma] = useState('');
  const [newTranslation, setNewTranslation] = useState('');
  const [selectedWordIds, setSelectedWordIds] = useState<Set<number>>(new Set());
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const lemmaInputRef = useRef<TextInput>(null);
  const translationInputRef = useRef<TextInput>(null);
  const [showWordMenu, setShowWordMenu] = useState(false);
  const [menuWord, setMenuWord] = useState<Word | null>(null);
  const [showEditWordModal, setShowEditWordModal] = useState(false);
  const [editLemma, setEditLemma] = useState('');
  const [editTranslation, setEditTranslation] = useState('');
  const [showCopyModal, setShowCopyModal] = useState(false);
  
  // Text import state
  const [importContent, setImportContent] = useState('');
  const [importContext, setImportContext] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [pollIntervalRef, setPollIntervalRef] = useState<NodeJS.Timeout | null>(null);

  const words = selectedQuiz?.words || [];
  const sentences = selectedQuiz?.sentences || [];
  const [selectedSentenceIds, setSelectedSentenceIds] = useState<Set<number>>(new Set());
  
  // Create expanded list for variants mode (words + all variants)
  type ListItem = {
    type: 'word' | 'variant';
    id: string; // 'word-{id}' or 'variant-{id}'
    word: Word;
    variant?: Variant;
    index: number;
  };
  
  const listItems = useMemo((): ListItem[] => {
    if (practiceSettings.mode === 'variants') {
      const items: ListItem[] = [];
      let globalIndex = 0;
      
      words.forEach((word) => {
        // Add base word
        items.push({
          type: 'word',
          id: `word-${word.id}`,
          word,
          index: globalIndex++,
        });
        
        // Add all variants
        word.variants?.forEach((variant) => {
          items.push({
            type: 'variant',
            id: `variant-${variant.id}`,
            word,
            variant,
            index: globalIndex++,
          });
        });
      });
      
      return items;
    } else {
      // Normal mode: just words
      return words.map((word, index) => ({
        type: 'word' as const,
        id: `word-${word.id}`,
        word,
        index,
      }));
    }
  }, [words, practiceSettings.mode]);

  // Update isImporting based on quiz processing status
  useEffect(() => {
    if (selectedQuiz?.processing_status === 'pending' || selectedQuiz?.processing_status === 'processing') {
      setIsImporting(true);
    } else if (selectedQuiz?.processing_status === 'completed' || 
               selectedQuiz?.processing_status === 'error' ||
               selectedQuiz?.processing_status === 'cancelled') {
      setIsImporting(false);
    }
  }, [selectedQuiz?.processing_status]);

  // Cleanup poll interval on unmount or quiz change
  useEffect(() => {
    return () => {
      if (pollIntervalRef) {
        clearInterval(pollIntervalRef);
      }
    };
  }, [pollIntervalRef]);

  // Initialize all words/sentences as selected when quiz changes
  useEffect(() => {
    if (words.length > 0) {
      setSelectedWordIds(new Set(words.map(w => w.id)));
    }
    if (sentences.length > 0) {
      setSelectedSentenceIds(new Set(sentences.map(s => s.id)));
    }
  }, [selectedQuiz?.id]);

  // Update selection when words are added
  useEffect(() => {
    if (words.length > 0) {
      setSelectedWordIds(prev => {
        const newSet = new Set(prev);
        words.forEach(word => {
          if (!newSet.has(word.id)) {
            newSet.add(word.id);
          }
        });
        return newSet;
      });
    }
  }, [words.length]);

  const handleToggleWord = (wordId: number) => {
    setSelectedWordIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(wordId)) {
        newSet.delete(wordId);
      } else {
        newSet.add(wordId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    setSelectedWordIds(new Set(words.map(w => w.id)));
  };

  const handleDeselectAll = () => {
    setSelectedWordIds(new Set());
  };

  const handleToggleSentence = (sentenceId: number) => {
    setSelectedSentenceIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sentenceId)) {
        newSet.delete(sentenceId);
      } else {
        newSet.add(sentenceId);
      }
      return newSet;
    });
  };

  const handleSelectAllSentences = () => {
    setSelectedSentenceIds(new Set(sentences.map(s => s.id)));
  };

  const handleDeselectAllSentences = () => {
    setSelectedSentenceIds(new Set());
  };

  const handleStartPractice = () => {
    // PracticeScreen will use the selectedQuiz and mode to determine what to practice
    // For sentences mode, it will use all sentences from the quiz
    // For words/variants mode, it will use selectedWordIds
    onStartPractice(selectedWordIds);
  };

  if (!selectedQuiz) {
    return (
      <View style={styles.emptyContainer}>
        <Ionicons name="musical-notes-outline" size={80} color={colors.textMuted} />
        <Text style={styles.emptyTitle}>Select a quiz</Text>
        <Text style={styles.emptySubtitle}>
          Choose a quiz from the sidebar to start learning
        </Text>
      </View>
    );
  }

  const handleAddWord = () => {
    const lemma = newLemma.trim();
    const translation = newTranslation.trim();
    
    if (!lemma && !translation) {
      return; // Don't add if both fields are empty
    }
    
    // Clear fields immediately for smooth UX
    setNewLemma('');
    setNewTranslation('');
    
    // Add word in background (non-blocking, allows multiple concurrent additions)
    addWordToQuiz(selectedQuiz.id, lemma, translation)
      .then(() => {
        // Word added successfully, quiz will auto-refresh
      })
      .catch((error) => {
        console.error('Failed to add word:', error);
        // Show error popup
        const errorMsg = error?.response?.data?.error || error?.message || 'Failed to add word. Please try again.';
        setErrorMessage(`${lemma || translation}: ${errorMsg}`);
      });
    
    // Auto-focus the lemma input for next word
    setTimeout(() => {
      lemmaInputRef.current?.focus();
    }, 100);
  };

  const openWordMenu = (word: Word) => {
    setMenuWord(word);
    setShowWordMenu(true);
  };

  const closeWordMenu = () => {
    setShowWordMenu(false);
  };

  const handleEditWord = () => {
    if (!menuWord) return;
    setEditLemma(menuWord.lemma);
    setEditTranslation(menuWord.translation);
    setShowEditWordModal(true);
    setShowWordMenu(false);
  };

  const handleSaveWordEdit = async () => {
    if (!menuWord) return;
    try {
      await quizService.updateWord(menuWord.id, editLemma.trim(), editTranslation.trim());
      // Refresh quiz to show updates
      if (selectedQuiz) {
        const updatedQuiz = await quizService.getQuizDetail(selectedQuiz.id);
        await selectQuiz({ ...selectedQuiz, ...updatedQuiz.quiz });
      }
      setShowEditWordModal(false);
    } catch (error) {
      console.error('Failed to update word:', error);
      setErrorMessage('Failed to update word. Please try again.');
    }
  };

  const handleDeleteWord = async () => {
    if (!menuWord) return;
    try {
      await quizService.deleteWord(menuWord.id);
      // Refresh quiz to remove deleted word
      if (selectedQuiz) {
        const updatedQuiz = await quizService.getQuizDetail(selectedQuiz.id);
        await selectQuiz({ ...selectedQuiz, ...updatedQuiz.quiz });
      }
      setShowWordMenu(false);
    } catch (error) {
      console.error('Failed to delete word:', error);
      setErrorMessage('Failed to delete word. Please try again.');
    }
  };

  const handleCopyWord = () => {
    setShowCopyModal(true);
    setShowWordMenu(false);
  };

  const handleCopyToQuiz = async (targetQuizId: number) => {
    if (!menuWord) return;
    try {
      await quizService.copyWordToQuiz(menuWord.id, targetQuizId);
      setShowCopyModal(false);
    } catch (error) {
      console.error('Failed to copy word:', error);
      setErrorMessage('Failed to copy word. Please try again.');
    }
  };

  const handleImportText = async () => {
    if (importContent.trim() && selectedQuiz) {
      setIsImporting(true);
      try {
        // Language is auto-detected by backend based on text content (Cyrillic = Slavic, Latin = English/Swedish)
        await importTextToQuiz(
          selectedQuiz.id,
          selectedQuiz.target_language || 'Ukrainian', // Pass as hint, backend will auto-detect from text
          importContent.trim(),
          importContext.trim() || undefined
        );
        
        // Poll for progress updates
        let pollInterval: NodeJS.Timeout | null = null;
        pollInterval = setInterval(async () => {
          try {
            // Reload the quiz to get updated processing status
            const updatedQuiz = await quizService.getQuizDetail(selectedQuiz.id);
            
            // Update the selected quiz with new status
            await selectQuiz({ ...selectedQuiz, ...updatedQuiz.quiz });
            
            // Check if processing is complete, cancelled, or errored
            if (updatedQuiz.quiz.processing_status === 'completed' || 
                updatedQuiz.quiz.processing_status === 'error' ||
                updatedQuiz.quiz.processing_status === 'cancelled') {
              if (pollInterval) clearInterval(pollInterval);
              setPollIntervalRef(null);
              setIsImporting(false);
              if (updatedQuiz.quiz.processing_status !== 'cancelled') {
                setImportContent('');
                setImportContext('');
              }
            }
          } catch (error) {
            console.error('Error polling quiz status:', error);
            if (pollInterval) clearInterval(pollInterval);
            setPollIntervalRef(null);
            setIsImporting(false);
          }
        }, 1000); // Poll every second
        
        setPollIntervalRef(pollInterval);
        
        // Timeout after 5 minutes
        setTimeout(() => {
          if (pollInterval) clearInterval(pollInterval);
          setPollIntervalRef(null);
          setIsImporting(false);
        }, 300000);
      } catch (error) {
        console.error('Failed to import text:', error);
        setIsImporting(false);
      }
    }
  };

  const handleCancelProcessing = async () => {
    if (!selectedQuiz || !isImporting) return;
    
    try {
      await quizService.cancelProcessing(selectedQuiz.id);
      
      // Clear polling interval
      if (pollIntervalRef) {
        clearInterval(pollIntervalRef);
        setPollIntervalRef(null);
      }
      
      // Reload quiz to get updated status
      const updatedQuiz = await quizService.getQuizDetail(selectedQuiz.id);
      await selectQuiz({ ...selectedQuiz, ...updatedQuiz.quiz });
      
      setIsImporting(false);
    } catch (error) {
      console.error('Failed to cancel processing:', error);
      setErrorMessage('Failed to cancel processing. Please try again.');
    }
  };

  const handlePickImage = async () => {
    if (!selectedQuiz) return;

    // Request permissions
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      setErrorMessage('Permission to access photos is required.');
      return;
    }

    // Launch image picker
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.8,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      processImage(result.assets[0].base64);
    }
  };

  const handleTakePhoto = async () => {
    if (!selectedQuiz) return;

    // On web, camera access is not available, so use file picker instead
    if (Platform.OS === 'web') {
      handlePickImage();
      return;
    }

    // Request camera permissions
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      setErrorMessage('Permission to access camera is required.');
      return;
    }

    // Launch camera
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      quality: 0.8,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      processImage(result.assets[0].base64);
    }
  };

  const processImage = async (imageBase64: string) => {
    if (!selectedQuiz) return;

    setIsImporting(true);
    try {
      await importImageToQuiz(
        selectedQuiz.id,
        imageBase64,
        importContext.trim() || undefined
      );

      // Poll for progress updates
      let pollInterval: NodeJS.Timeout | null = null;
      pollInterval = setInterval(async () => {
        try {
          const updatedQuiz = await quizService.getQuizDetail(selectedQuiz.id);
          await selectQuiz({ ...selectedQuiz, ...updatedQuiz.quiz });

          if (updatedQuiz.quiz.processing_status === 'completed' || 
              updatedQuiz.quiz.processing_status === 'error' ||
              updatedQuiz.quiz.processing_status === 'cancelled') {
            if (pollInterval) clearInterval(pollInterval);
            setPollIntervalRef(null);
            setIsImporting(false);
            if (updatedQuiz.quiz.processing_status !== 'cancelled') {
              setImportContext('');
            }
          }
        } catch (error) {
          console.error('Error polling quiz status:', error);
          if (pollInterval) clearInterval(pollInterval);
          setPollIntervalRef(null);
          setIsImporting(false);
        }
      }, 1000);

      setPollIntervalRef(pollInterval);

      // Timeout after 5 minutes
      setTimeout(() => {
        if (pollInterval) clearInterval(pollInterval);
        setPollIntervalRef(null);
        setIsImporting(false);
      }, 300000);
    } catch (error) {
      console.error('Failed to import image:', error);
      setIsImporting(false);
      setErrorMessage('Failed to process image. Please try again.');
    }
  };

  return (
    <View style={styles.container}>
      {/* Header Section - Spotify-style gradient */}
      <View style={styles.header}>
        <View style={styles.headerGradient}>
          {/* Quiz Cover */}
          <View style={styles.coverArt}>
            <Ionicons name="book" size={40} color={colors.textSecondary} />
          </View>

          {/* Quiz Info */}
          <View style={styles.headerInfo}>
            <Text style={styles.quizLabel}>
              QUIZ
            </Text>
            <Text style={styles.quizTitle} numberOfLines={2}>
              {selectedQuiz.name}
            </Text>
            <Text style={styles.quizMeta}>
              {words.length} words • Created{' '}
              {new Date(selectedQuiz.created_at).toLocaleDateString()}
            </Text>
          </View>
        </View>

        {/* Action Buttons */}
        <View style={styles.actions}>
          <PlayButton
            size="large"
            onPress={handleStartPractice}
            isPlaying={false}
          />

          <TouchableOpacity
            style={[
              styles.shuffleButton,
              practiceSettings.shuffle && styles.shuffleButtonActive,
            ]}
            onPress={() => updatePracticeSettings({ shuffle: !practiceSettings.shuffle })}
          >
            <Ionicons
              name="shuffle"
              size={24}
              color={practiceSettings.shuffle ? colors.primary : colors.textSecondary}
            />
          </TouchableOpacity>

          {/* Anki Mode Button */}
          <TouchableOpacity
            style={styles.ankiButton}
            onPress={onStartAnkiPractice}
          >
            <Ionicons
              name="flash"
              size={20}
              color={colors.warning}
            />
            <Text style={styles.ankiButtonText}>Anki</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.optionButton}
            onPress={() => setShowAddWord(!showAddWord)}
          >
            <Ionicons
              name={showAddWord ? 'close' : 'add'}
              size={24}
              color={colors.textSecondary}
            />
          </TouchableOpacity>

          {/* Direction Selector */}
          <View style={styles.directionButtonsInline}>
            <TouchableOpacity
              style={[
                styles.directionButtonInline,
                practiceSettings.direction === 'forward' && styles.directionButtonActive,
              ]}
              onPress={() => updatePracticeSettings({ direction: 'forward' })}
            >
              <Ionicons 
                name="arrow-forward" 
                size={14} 
                color={practiceSettings.direction === 'forward' ? colors.background : colors.textSecondary} 
              />
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.directionButtonInline,
                practiceSettings.direction === 'reverse' && styles.directionButtonActive,
              ]}
              onPress={() => updatePracticeSettings({ direction: 'reverse' })}
            >
              <Ionicons 
                name="arrow-back" 
                size={14} 
                color={practiceSettings.direction === 'reverse' ? colors.background : colors.textSecondary} 
              />
            </TouchableOpacity>
          </View>

          {/* Select/Deselect All */}
          <View style={styles.selectionButtonsInline}>
            <TouchableOpacity
              style={styles.selectionButtonInline}
              onPress={practiceSettings.mode === 'sentences' ? handleSelectAllSentences : handleSelectAll}
            >
              <Ionicons name="checkmark-circle-outline" size={18} color={colors.textSecondary} />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.selectionButtonInline}
              onPress={practiceSettings.mode === 'sentences' ? handleDeselectAllSentences : handleDeselectAll}
            >
              <Ionicons name="close-circle-outline" size={18} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>
        </View>
      </View>

      {/* Add Word Form */}
      {showAddWord && (
        <View style={styles.addWordFormContainer}>
          <ScrollView 
            style={styles.addWordFormScroll}
            contentContainerStyle={styles.addWordFormContent}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={true}
            nestedScrollEnabled={true}
          >
            <Text style={styles.sectionLabel}>Add Word Manually</Text>
            <TextInput
              ref={lemmaInputRef}
              style={styles.addWordInput}
              placeholder={selectedQuiz?.source_language || "Word (lemma)"}
              placeholderTextColor={colors.textMuted}
              value={newLemma}
              onChangeText={setNewLemma}
              returnKeyType="next"
              onSubmitEditing={() => {
                // Focus translation field when Enter is pressed
                translationInputRef.current?.focus();
              }}
            />
            <TextInput
              ref={translationInputRef}
              style={styles.addWordInput}
              placeholder={selectedQuiz?.target_language || "Translation"}
              placeholderTextColor={colors.textMuted}
              value={newTranslation}
              onChangeText={setNewTranslation}
              returnKeyType="done"
              onSubmitEditing={handleAddWord}
            />
            <TouchableOpacity 
              style={styles.addWordButton}
              onPress={handleAddWord}
              activeOpacity={0.7}
              disabled={false}
            >
              <Text style={styles.addWordButtonText}>Add Word</Text>
            </TouchableOpacity>
            
            {/* Paste Text Section */}
            <View style={styles.pasteSection}>
              <Text style={styles.sectionLabel}>📋 Or Paste Text</Text>
              <Text style={styles.pasteDescription}>
                Paste any text - lyrics, word lists, textbook excerpts, etc. AI will extract vocabulary automatically.
                {selectedQuiz?.source_language && (
                  <Text style={styles.languageHint}>
                    {'\n'}Using {selectedQuiz.source_language} → {selectedQuiz.target_language || 'translation'}
                  </Text>
                )}
              </Text>
              <TextInput
                style={[styles.importInput, styles.textArea]}
                placeholder="Paste your text here..."
                placeholderTextColor={colors.textMuted}
                value={importContent}
                onChangeText={setImportContent}
                multiline
                textAlignVertical="top"
                scrollEnabled={false}
              />
              <TextInput
                style={[styles.importInput, styles.textAreaSmall]}
                placeholder="Context (optional) - e.g., 'This is a love song', 'Medical terminology'..."
                placeholderTextColor={colors.textMuted}
                value={importContext}
                onChangeText={setImportContext}
                multiline
                textAlignVertical="top"
                scrollEnabled={false}
              />
              
              {/* Import Button */}
              <TouchableOpacity
                style={[styles.importButton, isImporting && styles.importButtonDisabled]}
                onPress={handleImportText}
                disabled={isImporting || !importContent.trim()}
              >
                <Text style={styles.importButtonText}>
                  {isImporting ? 'Processing...' : '🚀 Import Words from Text'}
                </Text>
              </TouchableOpacity>

              {/* Image/Camera Import Section */}
              <View style={styles.imageImportSection}>
                <Text style={styles.sectionLabel}>📷 Or Scan from Image</Text>
                <Text style={styles.pasteDescription}>
                  {Platform.OS === 'web' 
                    ? 'Select an image of text (textbook page, notes, etc.)'
                    : 'Take a photo or select an image of text (textbook page, notes, etc.)'}
                </Text>
                <View style={styles.imageButtonRow}>
                  {Platform.OS !== 'web' && (
                    <TouchableOpacity
                      style={[styles.imageButton, isImporting && styles.importButtonDisabled]}
                      onPress={handleTakePhoto}
                      disabled={isImporting}
                    >
                      <Ionicons name="camera" size={24} color={colors.background} />
                      <Text style={styles.imageButtonText}>Take Photo</Text>
                    </TouchableOpacity>
                  )}
                  <TouchableOpacity
                    style={[
                      styles.imageButton, 
                      Platform.OS === 'web' ? styles.imageButtonFullWidth : styles.imageButtonSecondary, 
                      isImporting && styles.importButtonDisabled
                    ]}
                    onPress={handlePickImage}
                    disabled={isImporting}
                  >
                    <Ionicons name="images" size={24} color={Platform.OS === 'web' ? colors.background : colors.primary} />
                    <Text style={[
                      styles.imageButtonText, 
                      Platform.OS === 'web' ? {} : styles.imageButtonTextSecondary
                    ]}>
                      {Platform.OS === 'web' ? 'Choose Image' : 'Choose Photo'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
              
              {/* Progress Indicator */}
              {isImporting && selectedQuiz?.processing_message && (
                <View style={styles.progressContainer}>
                  <View style={styles.progressBar}>
                    <View style={[styles.progressFill, { width: '100%' }]} />
                  </View>
                  <View style={styles.progressRow}>
                    <Text style={styles.progressText}>
                      {selectedQuiz.processing_message}
                    </Text>
                    <TouchableOpacity
                      style={styles.cancelButton}
                      onPress={handleCancelProcessing}
                    >
                      <Ionicons name="close-circle" size={20} color={colors.error} />
                      <Text style={styles.cancelButtonText}>Cancel</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </View>
          </ScrollView>
        </View>
      )}

      {/* Practice Mode Options */}
      <View style={styles.modeOptions}>
        <Text style={styles.modeLabel}>Practice Mode:</Text>
        <View style={styles.modeButtons}>
          {(['words', 'variants', 'sentences'] as const).map(mode => (
            <TouchableOpacity
              key={mode}
              style={[
                styles.modeButton,
                practiceSettings.mode === mode && styles.modeButtonActive,
              ]}
              onPress={() => updatePracticeSettings({ mode })}
            >
              <Text
                style={[
                  styles.modeButtonText,
                  practiceSettings.mode === mode && styles.modeButtonTextActive,
                ]}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Selection Info */}
      <View style={styles.selectionInfoRow}>
        <Text style={styles.selectionInfo}>
          {practiceSettings.mode === 'sentences' 
            ? `${selectedSentenceIds.size} of ${sentences.length} selected`
            : practiceSettings.mode === 'variants'
            ? `${selectedWordIds.size} of ${words.length} words selected (${listItems.length} items total)`
            : `${selectedWordIds.size} of ${words.length} selected`}
        </Text>
      </View>

      {/* Words/Sentences List */}
      <View style={styles.wordsSection}>
        <View style={styles.wordsHeader}>
          <Text style={styles.columnHeader}>#</Text>
          <Text style={[styles.columnHeader, { flex: 1 }]}>TITLE</Text>
          <Ionicons name="time-outline" size={16} color={colors.textMuted} />
        </View>

        {practiceSettings.mode === 'sentences' ? (
          <FlatList
            data={sentences}
            keyExtractor={(item) => item.id.toString()}
            renderItem={({ item, index }) => (
              <SentenceItem
                sentence={item}
                index={index}
                isSelected={selectedSentenceIds.has(item.id)}
                onPress={() => {}}
                onToggleSelect={() => handleToggleSentence(item.id)}
              />
            )}
            ListEmptyComponent={
              <View style={styles.emptyWords}>
                <Text style={styles.emptyWordsText}>
                  No sentences in this quiz yet.
                </Text>
              </View>
            }
            showsVerticalScrollIndicator={false}
          />
        ) : (
          <FlatList
            data={listItems}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => {
              if (item.type === 'variant' && item.variant) {
                // Render variant as a word-like item
                const variantWord: Word = {
                  ...item.word,
                  lemma: item.variant.value,
                  translation: item.variant.translation,
                };
                return (
                  <View style={styles.variantItemContainer}>
                    <View style={styles.variantIndent} />
                    <WordItem
                      word={variantWord}
                      index={item.index}
                      isSelected={selectedWordIds.has(item.word.id)}
                      onPress={() => {}}
                      onLemmaPress={() => onWordPress(item.word)}
                      onMorePress={() => openWordMenu(item.word)}
                      onToggleSelect={() => handleToggleWord(item.word.id)}
                      sourceLanguage={selectedQuiz?.source_language}
                      targetLanguage={selectedQuiz?.target_language}
                    />
                  </View>
                );
              } else {
                // Render regular word
                return (
                  <WordItem
                    word={item.word}
                    index={item.index}
                    isSelected={selectedWordIds.has(item.word.id)}
                    onPress={() => {}}
                    onLemmaPress={() => onWordPress(item.word)}
                    onMorePress={() => openWordMenu(item.word)}
                    onToggleSelect={() => handleToggleWord(item.word.id)}
                    sourceLanguage={selectedQuiz?.source_language}
                    targetLanguage={selectedQuiz?.target_language}
                  />
                );
              }
            }}
            ListEmptyComponent={
              <View style={styles.emptyWords}>
                <Text style={styles.emptyWordsText}>
                  No words in this quiz yet.
                </Text>
                <TouchableOpacity
                  style={styles.addFirstWord}
                  onPress={() => setShowAddWord(true)}
                >
                  <Ionicons name="add" size={20} color={colors.primary} />
                  <Text style={styles.addFirstWordText}>Add your first word</Text>
                </TouchableOpacity>
              </View>
            }
            showsVerticalScrollIndicator={false}
          />
        )}
      </View>

      {/* Error Modal */}
      <Modal
        visible={errorMessage !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setErrorMessage(null)}
      >
        <View style={styles.errorModalOverlay}>
          <View style={styles.errorModalContent}>
            <View style={styles.errorModalHeader}>
              <Ionicons name="alert-circle" size={24} color={colors.error} />
              <Text style={styles.errorModalTitle}>Error Adding Word</Text>
            </View>
            <Text style={styles.errorModalText}>{errorMessage}</Text>
            <TouchableOpacity
              style={styles.errorModalButton}
              onPress={() => setErrorMessage(null)}
            >
              <Text style={styles.errorModalButtonText}>OK</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
      
      {/* Word Actions Menu */}
      <Modal
        visible={showWordMenu}
        transparent
        animationType="fade"
        onRequestClose={closeWordMenu}
      >
        <TouchableOpacity style={styles.menuOverlay} onPress={closeWordMenu}>
          <View style={styles.menuContent}>
            <Text style={styles.menuTitle}>Word Actions</Text>
            <TouchableOpacity style={styles.menuItem} onPress={handleEditWord}>
              <Ionicons name="create-outline" size={20} color={colors.textPrimary} />
              <Text style={styles.menuItemText}>Edit Word</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.menuItem} onPress={handleCopyWord}>
              <Ionicons name="copy-outline" size={20} color={colors.textPrimary} />
              <Text style={styles.menuItemText}>Add to Another Quiz</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.menuItem, styles.menuItemDanger]} onPress={handleDeleteWord}>
              <Ionicons name="trash-outline" size={20} color={colors.error} />
              <Text style={[styles.menuItemText, styles.menuItemTextDanger]}>Remove from Quiz</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Edit Word Modal */}
      <Modal
        visible={showEditWordModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowEditWordModal(false)}
      >
        <View style={styles.menuOverlay}>
          <View style={styles.editModalContent}>
            <Text style={styles.menuTitle}>Edit Word</Text>
            <TextInput
              style={styles.addWordInput}
              placeholder="Word (lemma)"
              placeholderTextColor={colors.textMuted}
              value={editLemma}
              onChangeText={setEditLemma}
            />
            <TextInput
              style={styles.addWordInput}
              placeholder="Translation"
              placeholderTextColor={colors.textMuted}
              value={editTranslation}
              onChangeText={setEditTranslation}
            />
            <View style={styles.editModalButtons}>
              <TouchableOpacity
                style={styles.editModalCancel}
                onPress={() => setShowEditWordModal(false)}
              >
                <Text style={styles.editModalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.editModalSave}
                onPress={handleSaveWordEdit}
              >
                <Text style={styles.editModalSaveText}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Copy Word Modal */}
      <Modal
        visible={showCopyModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowCopyModal(false)}
      >
        <View style={styles.menuOverlay}>
          <View style={styles.copyModalContent}>
            <Text style={styles.menuTitle}>Add to Another Quiz</Text>
            <ScrollView style={styles.copyList} showsVerticalScrollIndicator={false}>
              {quizzes.filter(q => q.id !== selectedQuiz?.id).length === 0 ? (
                <Text style={styles.emptyCopyText}>No other quizzes available.</Text>
              ) : (
                quizzes
                  .filter(q => q.id !== selectedQuiz?.id)
                  .map((quiz) => (
                    <TouchableOpacity
                      key={quiz.id}
                      style={styles.copyItem}
                      onPress={() => handleCopyToQuiz(quiz.id)}
                    >
                      <Text style={styles.copyItemText}>{quiz.name}</Text>
                      <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                    </TouchableOpacity>
                  ))
              )}
            </ScrollView>
            <TouchableOpacity
              style={styles.editModalCancel}
              onPress={() => setShowCopyModal(false)}
            >
              <Text style={styles.editModalCancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
    padding: spacing.xl,
  },
  emptyTitle: {
    color: colors.textPrimary,
    fontSize: fontSize.xxl,
    fontWeight: 'bold',
    marginTop: spacing.lg,
  },
  emptySubtitle: {
    color: colors.textMuted,
    fontSize: fontSize.md,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  header: {
    backgroundColor: colors.backgroundLight,
    paddingBottom: spacing.sm,
  },
  headerGradient: {
    flexDirection: isTablet ? 'row' : 'column',
    alignItems: isTablet ? 'flex-end' : 'center',
    padding: spacing.md,
    paddingTop: spacing.lg,
    gap: spacing.md,
  },
  coverArt: {
    width: isTablet ? 120 : 100,
    height: isTablet ? 120 : 100,
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    ...shadows.lg,
  },
  headerInfo: {
    flex: isTablet ? 1 : undefined,
    alignItems: isTablet ? 'flex-start' : 'center',
  },
  quizLabel: {
    color: colors.textPrimary,
    fontSize: fontSize.xs,
    fontWeight: '700',
    letterSpacing: 1,
  },
  quizTitle: {
    color: colors.textPrimary,
    fontSize: isTablet ? fontSize.title : fontSize.xxxl,
    fontWeight: 'bold',
    marginTop: spacing.xs,
    textAlign: isTablet ? 'left' : 'center',
  },
  quizMeta: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginTop: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
    flexWrap: 'wrap',
  },
  shuffleButton: {
    padding: spacing.sm,
  },
  shuffleButtonActive: {
    // Active state
  },
  ankiButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.warning + '20',
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
    borderRadius: borderRadius.md,
    borderWidth: 1,
    borderColor: colors.warning,
  },
  ankiButtonText: {
    color: colors.warning,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  optionButton: {
    padding: spacing.sm,
  },
  addWordFormContainer: {
    backgroundColor: colors.surface,
    margin: spacing.md,
    borderRadius: borderRadius.md,
    height: Math.min(Dimensions.get('window').height * 0.5, 500), // Reduced height to give more room for words
    flexDirection: 'column',
    overflow: 'hidden',
  },
  addWordFormScroll: {
    flex: 1,
  },
  addWordFormContent: {
    padding: spacing.md,
    paddingBottom: 200, // Large padding to ensure full button visibility when scrolled
    gap: spacing.sm,
    flexGrow: 1,
  },
  addWordForm: {
    backgroundColor: colors.surface,
    padding: spacing.md,
    margin: spacing.md,
    borderRadius: borderRadius.md,
    gap: spacing.sm,
  },
  addWordInput: {
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.textPrimary,
    fontSize: fontSize.md,
  },
  addWordButton: {
    backgroundColor: colors.primary,
    borderRadius: borderRadius.full,
    padding: spacing.md,
    alignItems: 'center',
  },
  addWordButtonText: {
    color: colors.background,
    fontWeight: '600',
    fontSize: fontSize.md,
  },
  errorModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorModalContent: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    width: '80%',
    maxWidth: 400,
  },
  errorModalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  errorModalTitle: {
    color: colors.textPrimary,
    fontSize: fontSize.lg,
    fontWeight: '600',
  },
  errorModalText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    marginBottom: spacing.lg,
    lineHeight: 20,
  },
  errorModalButton: {
    backgroundColor: colors.primary,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
  },
  errorModalButtonText: {
    color: colors.background,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  menuContent: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    width: '100%',
    maxWidth: 400,
  },
  menuTitle: {
    color: colors.textPrimary,
    fontSize: fontSize.lg,
    fontWeight: '600',
    marginBottom: spacing.md,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.sm,
  },
  menuItemText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
  },
  menuItemDanger: {
    marginTop: spacing.xs,
  },
  menuItemTextDanger: {
    color: colors.error,
  },
  editModalContent: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    width: '100%',
    maxWidth: 400,
  },
  editModalButtons: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  editModalCancel: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  editModalCancelText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
  },
  editModalSave: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: borderRadius.full,
  },
  editModalSaveText: {
    color: colors.background,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  copyModalContent: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    width: '100%',
    maxWidth: 400,
    maxHeight: '80%',
  },
  copyList: {
    marginBottom: spacing.md,
  },
  copyItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  copyItemText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    flex: 1,
  },
  emptyCopyText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    textAlign: 'center',
    paddingVertical: spacing.md,
  },
  modeOptions: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    paddingHorizontal: spacing.lg,
    gap: spacing.md,
  },
  selectionInfo: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
  },
  modeLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
  },
  modeButtons: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  modeButton: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.full,
    backgroundColor: colors.backgroundLighter,
  },
  modeButtonActive: {
    backgroundColor: colors.primary,
  },
  modeButtonText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
  },
  modeButtonTextActive: {
    color: colors.background,
    fontWeight: '600',
  },
  directionButtonsInline: {
    flexDirection: 'row',
    gap: spacing.xs,
    marginLeft: spacing.sm,
  },
  directionButtonInline: {
    padding: spacing.xs,
    borderRadius: borderRadius.sm,
    backgroundColor: colors.backgroundLighter,
    minWidth: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  directionButtonActive: {
    backgroundColor: colors.primary,
  },
  selectionButtonsInline: {
    flexDirection: 'row',
    gap: spacing.xs,
    marginLeft: spacing.sm,
  },
  selectionButtonInline: {
    padding: spacing.xs,
    borderRadius: borderRadius.sm,
  },
  selectionInfoRow: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xs,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  wordsSection: {
    flex: 1,
    paddingHorizontal: spacing.md,
  },
  wordsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    gap: spacing.md,
  },
  columnHeader: {
    color: colors.textMuted,
    fontSize: fontSize.xs,
    fontWeight: '600',
    letterSpacing: 1,
    width: 32,
  },
  emptyWords: {
    alignItems: 'center',
    paddingVertical: spacing.xxl,
  },
  emptyWordsText: {
    color: colors.textMuted,
    fontSize: fontSize.md,
  },
  variantItemContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  variantIndent: {
    width: spacing.md,
    borderLeftWidth: 2,
    borderLeftColor: colors.primary + '40',
    marginRight: spacing.xs,
  },
  addFirstWord: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
    padding: spacing.md,
  },
  addFirstWordText: {
    color: colors.primary,
    fontSize: fontSize.md,
    fontWeight: '500',
  },
  sectionLabel: {
    color: colors.textPrimary,
    fontSize: fontSize.sm,
    fontWeight: '600',
    marginBottom: spacing.sm,
    marginTop: spacing.md,
  },
  pasteSection: {
    marginTop: spacing.lg,
    paddingTop: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  pasteDescription: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    marginBottom: spacing.md,
    lineHeight: 20,
  },
  languageHint: {
    color: colors.primary,
    fontWeight: '500',
  },
  importInput: {
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.textPrimary,
    fontSize: fontSize.md,
    marginBottom: spacing.sm,
  },
  textArea: {
    minHeight: 180,
    paddingTop: spacing.md,
  },
  textAreaSmall: {
    minHeight: 60,
    paddingTop: spacing.md,
  },
  importButtonContainer: {
    padding: spacing.md,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  importButton: {
    backgroundColor: colors.primary,
    borderRadius: borderRadius.full,
    padding: spacing.md,
    paddingVertical: spacing.lg,
    alignItems: 'center',
    marginTop: spacing.md,
    marginBottom: spacing.sm,
    minHeight: 50,
  },
  importButtonDisabled: {
    opacity: 0.5,
  },
  importButtonText: {
    color: colors.background,
    fontWeight: '600',
    fontSize: fontSize.md,
  },
  imageImportSection: {
    marginTop: spacing.lg,
    paddingTop: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  imageButtonRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  imageButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    backgroundColor: colors.primary,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    paddingVertical: spacing.lg,
  },
  imageButtonSecondary: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: colors.primary,
  },
  imageButtonFullWidth: {
    flex: 1,
  },
  imageButtonText: {
    color: colors.background,
    fontWeight: '600',
    fontSize: fontSize.md,
  },
  imageButtonTextSecondary: {
    color: colors.primary,
  },
  progressContainer: {
    marginTop: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
  },
  progressBar: {
    height: 6,
    backgroundColor: colors.border,
    borderRadius: borderRadius.full,
    overflow: 'hidden',
    marginBottom: spacing.sm,
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.primary,
    borderRadius: borderRadius.full,
  },
  progressRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  progressText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    flex: 1,
  },
  cancelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  cancelButtonText: {
    color: colors.error,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
});

export default QuizDetailScreen;

