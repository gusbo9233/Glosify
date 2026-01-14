import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Modal,
  Dimensions,
  Picker,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius, shadows } from '../utils/theme';
import { useApp } from '../context/AppContext';
import { Quiz, Folder } from '../types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const SIDEBAR_WIDTH = Math.min(280, SCREEN_WIDTH * 0.35);

interface SidebarProps {
  onClose?: () => void;
  onQuizSelect?: () => void;
  onHomeClick?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onClose, onQuizSelect, onHomeClick }) => {
  const { quizzes, folders, selectedQuiz, selectQuiz, createQuiz, deleteQuiz, createFolder, deleteFolder, toggleFolderExpanded, moveQuizToFolder, logout, user } = useApp();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false);
  const [showDeleteFolderModal, setShowDeleteFolderModal] = useState(false);
  const [showMoveQuizModal, setShowMoveQuizModal] = useState(false);
  const [quizToDelete, setQuizToDelete] = useState<Quiz | null>(null);
  const [quizToMove, setQuizToMove] = useState<Quiz | null>(null);
  const [folderToDelete, setFolderToDelete] = useState<number | null>(null);
  const [newQuizName, setNewQuizName] = useState('');
  const [newQuizSourceLanguage, setNewQuizSourceLanguage] = useState<string>('');
  const [newQuizTargetLanguage, setNewQuizTargetLanguage] = useState<string>('');
  const [newQuizPrompt, setNewQuizPrompt] = useState('');
  const [showSourceLanguageDropdown, setShowSourceLanguageDropdown] = useState(false);
  const [showTargetLanguageDropdown, setShowTargetLanguageDropdown] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [parentFolderId, setParentFolderId] = useState<number | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  
  const sourceLanguages = ['English', 'Swedish'];
  const targetLanguages = ['Polish', 'Ukrainian'];

  const filteredQuizzes = quizzes.filter(q =>
    q.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateQuiz = async () => {
    if (newQuizName.trim()) {
      await createQuiz(
        newQuizName.trim(),
        newQuizSourceLanguage.trim() || undefined,
        newQuizTargetLanguage.trim() || undefined,
        newQuizPrompt.trim() || undefined
      );
      setNewQuizName('');
      setNewQuizSourceLanguage('');
      setNewQuizTargetLanguage('');
      setNewQuizPrompt('');
      setShowSourceLanguageDropdown(false);
      setShowTargetLanguageDropdown(false);
      setShowCreateModal(false);
    }
  };

  const handleSelectQuiz = async (quiz: Quiz) => {
    await selectQuiz(quiz);
    onQuizSelect?.(); // Notify parent to switch to quiz screen
    onClose?.();
  };

  const handleDeleteClick = (e: any, quiz: Quiz) => {
    e.stopPropagation();
    setQuizToDelete(quiz);
    setShowDeleteModal(true);
  };

  const handleMoveQuizClick = (e: any, quiz: Quiz) => {
    e.stopPropagation();
    setQuizToMove(quiz);
    setShowMoveQuizModal(true);
  };

  const handleMoveToFolder = async (folderId: number | null) => {
    if (quizToMove) {
      try {
        await moveQuizToFolder(quizToMove.id, folderId);
        setShowMoveQuizModal(false);
        setQuizToMove(null);
      } catch (error) {
        console.error('Failed to move quiz:', error);
      }
    }
  };

  // Helper to get all folders as a flat list for selection
  const getAllFoldersFlat = (folderList: Folder[], result: Array<{id: number | null, name: string, depth: number}> = [], depth: number = 0): Array<{id: number | null, name: string, depth: number}> => {
    // Add "Root" option at the beginning
    if (depth === 0) {
      result.push({ id: null, name: 'Root (No folder)', depth: 0 });
    }
    folderList.forEach(folder => {
      result.push({ id: folder.id, name: folder.name, depth });
      getAllFoldersFlat(folder.subfolders, result, depth + 1);
    });
    return result;
  };

  const handleConfirmDelete = async () => {
    if (quizToDelete) {
      await deleteQuiz(quizToDelete.id);
      setShowDeleteModal(false);
      setQuizToDelete(null);
    }
  };

  const handleCreateFolder = async () => {
    if (newFolderName.trim()) {
      try {
        await createFolder(newFolderName.trim(), parentFolderId);
        setNewFolderName('');
        setParentFolderId(undefined);
        setShowCreateFolderModal(false);
      } catch (error) {
        console.error('Failed to create folder:', error);
        // Could show error message to user here
      }
    }
  };

  const handleDeleteFolder = (folderId: number) => {
    setFolderToDelete(folderId);
    setShowDeleteFolderModal(true);
  };

  const handleConfirmDeleteFolder = async () => {
    if (folderToDelete) {
      try {
        await deleteFolder(folderToDelete);
        setShowDeleteFolderModal(false);
        setFolderToDelete(null);
      } catch (error) {
        console.error('Failed to delete folder:', error);
        // Could show error message to user here
        setShowDeleteFolderModal(false);
        setFolderToDelete(null);
      }
    }
  };

  // Recursive component to render folder tree
  const renderFolderTree = (folderList: Folder[], depth: number = 0) => {
    return folderList.map(folder => (
      <View key={folder.id}>
        <TouchableOpacity
          style={[styles.folderItem, { paddingLeft: spacing.md + (depth * spacing.md) }]}
          onPress={() => toggleFolderExpanded(folder.id)}
        >
          <Ionicons
            name={folder.isExpanded ? 'chevron-down' : 'chevron-forward'}
            size={16}
            color={colors.textMuted}
            style={styles.folderChevron}
          />
          <Ionicons name="folder" size={18} color={colors.textSecondary} />
          <Text style={styles.folderName} numberOfLines={1}>
            {folder.name}
          </Text>
          <TouchableOpacity
            style={styles.folderActions}
            onPress={(e) => {
              e.stopPropagation();
              handleDeleteFolder(folder.id);
            }}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="trash-outline" size={16} color={colors.textMuted} />
          </TouchableOpacity>
        </TouchableOpacity>
        {folder.isExpanded && (
          <View>
            {renderFolderTree(folder.subfolders, depth + 1)}
            {folder.quizzes.map(quiz => (
              <TouchableOpacity
                key={quiz.id}
                style={[
                  styles.quizItem,
                  { paddingLeft: spacing.md + ((depth + 1) * spacing.md) },
                  selectedQuiz?.id === quiz.id && styles.quizItemSelected,
                ]}
                onPress={() => handleSelectQuiz(quiz)}
              >
                <View style={styles.quizIcon}>
                  <Ionicons name="book" size={20} color={colors.textSecondary} />
                </View>
                <View style={styles.quizInfo}>
                  <Text
                    style={[
                      styles.quizName,
                      selectedQuiz?.id === quiz.id && styles.quizNameSelected,
                    ]}
                    numberOfLines={1}
                  >
                    {quiz.name}
                  </Text>
                  <Text style={styles.quizMeta}>
                    {quiz.words?.length || 0} words
                  </Text>
                </View>
                <TouchableOpacity
                  style={styles.deleteButton}
                  onPress={(e) => handleDeleteClick(e, quiz)}
                  hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                >
                  <Ionicons name="trash-outline" size={18} color={colors.textMuted} />
                </TouchableOpacity>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>
    ));
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.logoContainer}
          onPress={onHomeClick}
          activeOpacity={0.7}
        >
          <Ionicons name="book" size={28} color={colors.primary} />
          <Text style={styles.logoText}>Glosify</Text>
        </TouchableOpacity>
        {onClose && (
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={24} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>

      {/* Search */}
      <View style={styles.searchContainer}>
        <Ionicons name="search" size={18} color={colors.textMuted} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search quizzes..."
          placeholderTextColor={colors.textMuted}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      {/* Create New Quiz Buttons */}
      <TouchableOpacity
        style={styles.createButton}
        onPress={() => setShowCreateModal(true)}
      >
        <Ionicons name="add-circle" size={20} color={colors.textPrimary} />
        <Text style={styles.createButtonText}>Create Quiz</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.createButton, styles.folderButton]}
        onPress={() => setShowCreateFolderModal(true)}
      >
        <Ionicons name="folder-outline" size={20} color={colors.primary} />
        <Text style={[styles.createButtonText, styles.folderButtonText]}>📁 New Folder</Text>
      </TouchableOpacity>

      {/* Folders and Quizzes List */}
      <ScrollView style={styles.quizzesList} showsVerticalScrollIndicator={false}>
        <Text style={styles.sectionTitle}>YOUR QUIZZES</Text>
        {folders.length > 0 && renderFolderTree(folders)}
        {filteredQuizzes.length === 0 && folders.length === 0 ? (
          <Text style={styles.emptyText}>No quizzes yet</Text>
        ) : (
          filteredQuizzes.map(quiz => (
            <TouchableOpacity
              key={quiz.id}
              style={[
                styles.quizItem,
                selectedQuiz?.id === quiz.id && styles.quizItemSelected,
              ]}
              onPress={() => handleSelectQuiz(quiz)}
            >
              <View style={styles.quizIcon}>
                <Ionicons name="book" size={20} color={colors.textSecondary} />
              </View>
              <View style={styles.quizInfo}>
                <Text
                  style={[
                    styles.quizName,
                    selectedQuiz?.id === quiz.id && styles.quizNameSelected,
                  ]}
                  numberOfLines={1}
                >
                  {quiz.name}
                </Text>
                <Text style={styles.quizMeta}>
                  {quiz.words?.length || 0} words
                </Text>
              </View>
              {quiz.processing_status !== 'completed' && (
                <View style={styles.processingIndicator}>
                  <Ionicons name="time" size={14} color={colors.warning} />
                </View>
              )}
              <View style={styles.quizActions}>
                <TouchableOpacity
                  style={styles.actionButton}
                  onPress={(e) => handleMoveQuizClick(e, quiz)}
                  hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                >
                  <Ionicons name="folder-outline" size={18} color={colors.textMuted} />
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.actionButton}
                  onPress={(e) => handleDeleteClick(e, quiz)}
                  hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                >
                  <Ionicons name="trash-outline" size={18} color={colors.textMuted} />
                </TouchableOpacity>
              </View>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>

      {/* User Section */}
      <View style={styles.userSection}>
        <View style={styles.userInfo}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </Text>
          </View>
          <Text style={styles.username}>{user?.username || 'User'}</Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutButton}>
          <Ionicons name="log-out-outline" size={20} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>

      {/* Create Quiz Modal */}
      <Modal
        visible={showCreateModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowCreateModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Create New Quiz</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Quiz name..."
              placeholderTextColor={colors.textMuted}
              value={newQuizName}
              onChangeText={setNewQuizName}
              autoFocus
            />
            {/* Source Language Dropdown */}
            <View style={[styles.dropdownContainer, { zIndex: showSourceLanguageDropdown ? 100 : 2 }]}>
              <Text style={styles.dropdownLabel}>Source Language</Text>
              <TouchableOpacity
                style={styles.dropdownButton}
                activeOpacity={0.7}
                onPress={() => {
                  setShowSourceLanguageDropdown(!showSourceLanguageDropdown);
                  setShowTargetLanguageDropdown(false);
                }}
              >
                <Text style={[styles.dropdownButtonText, !newQuizSourceLanguage && styles.dropdownPlaceholder]}>
                  {newQuizSourceLanguage || 'Select source language...'}
                </Text>
                <Ionicons
                  name={showSourceLanguageDropdown ? 'chevron-up' : 'chevron-down'}
                  size={20}
                  color={colors.textSecondary}
                />
              </TouchableOpacity>
              {showSourceLanguageDropdown && (
                <View style={[styles.dropdownOptions, { zIndex: 1001 }]}>
                  {sourceLanguages.map((lang) => (
                    <TouchableOpacity
                      key={lang}
                      style={styles.dropdownOption}
                      activeOpacity={0.7}
                      onPress={() => {
                        setNewQuizSourceLanguage(lang);
                        setShowSourceLanguageDropdown(false);
                      }}
                    >
                      <Text style={styles.dropdownOptionText}>{lang}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>

            {/* Target Language Dropdown */}
            <View style={[styles.dropdownContainer, { zIndex: showTargetLanguageDropdown ? 100 : 1 }]}>
              <Text style={styles.dropdownLabel}>Target Language</Text>
              <TouchableOpacity
                style={styles.dropdownButton}
                activeOpacity={0.7}
                onPress={() => {
                  setShowTargetLanguageDropdown(!showTargetLanguageDropdown);
                  setShowSourceLanguageDropdown(false);
                }}
              >
                <Text style={[styles.dropdownButtonText, !newQuizTargetLanguage && styles.dropdownPlaceholder]}>
                  {newQuizTargetLanguage || 'Select target language...'}
                </Text>
                <Ionicons
                  name={showTargetLanguageDropdown ? 'chevron-up' : 'chevron-down'}
                  size={20}
                  color={colors.textSecondary}
                />
              </TouchableOpacity>
              {showTargetLanguageDropdown && (
                <View style={[styles.dropdownOptions, { zIndex: 1001 }]}>
                  {targetLanguages.map((lang) => (
                    <TouchableOpacity
                      key={lang}
                      style={styles.dropdownOption}
                      activeOpacity={0.7}
                      onPress={() => {
                        setNewQuizTargetLanguage(lang);
                        setShowTargetLanguageDropdown(false);
                      }}
                    >
                      <Text style={styles.dropdownOptionText}>{lang}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>
            
            {/* Prompt Field (Optional) */}
            <View style={styles.promptContainer}>
              <Text style={styles.promptLabel}>Prompt (Optional)</Text>
              <Text style={styles.promptHint}>
                Describe what you want to practice (e.g., "Polish verbs 'to have' and 'to be'", "Ukrainian family members")
              </Text>
              <TextInput
                style={[styles.modalInput, styles.promptInput]}
                placeholder="e.g., Polish verbs 'to have' and 'to be'"
                placeholderTextColor={colors.textMuted}
                value={newQuizPrompt}
                onChangeText={setNewQuizPrompt}
                multiline
                textAlignVertical="top"
              />
            </View>
            
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setShowCreateModal(false)}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalCreateButton}
                onPress={handleCreateQuiz}
              >
                <Text style={styles.modalCreateText}>Create</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        visible={showDeleteModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowDeleteModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Delete Quiz</Text>
            <Text style={styles.deleteConfirmText}>
              Are you sure you want to delete "{quizToDelete?.name}"? This action cannot be undone.
            </Text>
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => {
                  setShowDeleteModal(false);
                  setQuizToDelete(null);
                }}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalDeleteButton}
                onPress={handleConfirmDelete}
              >
                <Text style={styles.modalDeleteText}>Delete</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Create Folder Modal */}
      <Modal
        visible={showCreateFolderModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowCreateFolderModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Create New Folder</Text>
              <TextInput
                style={styles.modalInput}
              placeholder="Folder name..."
                placeholderTextColor={colors.textMuted}
              value={newFolderName}
              onChangeText={setNewFolderName}
              autoFocus
              />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => {
                  setShowCreateFolderModal(false);
                  setNewFolderName('');
                  setParentFolderId(undefined);
                }}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalCreateButton}
                onPress={handleCreateFolder}
              >
                <Text style={styles.modalCreateText}>Create</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Delete Folder Confirmation Modal */}
      <Modal
        visible={showDeleteFolderModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowDeleteFolderModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Delete Folder</Text>
            <Text style={styles.deleteConfirmText}>
              Are you sure you want to delete this folder? All subfolders and quizzes inside will be moved to the parent folder.
            </Text>
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => {
                  setShowDeleteFolderModal(false);
                  setFolderToDelete(null);
                }}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalDeleteButton}
                onPress={handleConfirmDeleteFolder}
              >
                <Text style={styles.modalDeleteText}>Delete</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Move Quiz to Folder Modal */}
      <Modal
        visible={showMoveQuizModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowMoveQuizModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Move Quiz</Text>
            <Text style={styles.moveQuizText}>
              Move "{quizToMove?.name}" to:
            </Text>
            <ScrollView style={styles.folderSelectList} showsVerticalScrollIndicator={true}>
              {getAllFoldersFlat(folders).map((folderOption) => (
                <TouchableOpacity
                  key={folderOption.id ?? 'root'}
                  style={[
                    styles.folderOption,
                    { paddingLeft: spacing.md + (folderOption.depth * spacing.md) }
                  ]}
                  onPress={() => handleMoveToFolder(folderOption.id)}
                >
                  <Ionicons 
                    name={folderOption.id === null ? "home-outline" : "folder"} 
                    size={18} 
                    color={colors.textSecondary} 
                  />
                  <Text style={styles.folderOptionText}>{folderOption.name}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => {
                  setShowMoveQuizModal(false);
                  setQuizToMove(null);
                }}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: SIDEBAR_WIDTH,
    backgroundColor: colors.background,
    borderRightWidth: 1,
    borderRightColor: colors.border,
    height: '100%',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: spacing.md,
    paddingTop: spacing.xl,
  },
  logoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  logoText: {
    fontSize: fontSize.xl,
    fontWeight: 'bold',
    color: colors.textPrimary,
  },
  closeButton: {
    padding: spacing.xs,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    margin: spacing.md,
    marginTop: 0,
    paddingHorizontal: spacing.sm,
    gap: spacing.sm,
  },
  searchInput: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: fontSize.md,
    paddingVertical: spacing.sm,
  },
  createButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.md,
    marginHorizontal: spacing.md,
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    marginBottom: spacing.xs,
  },
  createButtonText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  folderButton: {
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: 'transparent',
  },
  folderButtonText: {
    color: colors.primary,
  },
  folderItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.sm,
    borderRadius: borderRadius.sm,
    marginBottom: spacing.xs,
  },
  folderChevron: {
    marginRight: spacing.xs,
  },
  folderName: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '500',
    marginLeft: spacing.sm,
  },
  folderActions: {
    padding: spacing.xs,
    marginLeft: spacing.xs,
  },
  quizzesList: {
    flex: 1,
    paddingHorizontal: spacing.md,
    marginTop: spacing.md,
  },
  sectionTitle: {
    fontSize: fontSize.xs,
    fontWeight: '700',
    color: colors.textMuted,
    letterSpacing: 1,
    marginBottom: spacing.sm,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: spacing.xl,
  },
  quizItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.sm,
    borderRadius: borderRadius.sm,
    marginBottom: spacing.xs,
  },
  quizItemSelected: {
    backgroundColor: colors.backgroundLighter,
  },
  quizIcon: {
    width: 40,
    height: 40,
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.sm,
  },
  quizInfo: {
    flex: 1,
  },
  quizName: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '500',
  },
  quizNameSelected: {
    color: colors.primary,
  },
  quizMeta: {
    color: colors.textMuted,
    fontSize: fontSize.xs,
    marginTop: 2,
  },
  processingIndicator: {
    marginLeft: spacing.sm,
  },
  deleteButton: {
    padding: spacing.xs,
    marginLeft: spacing.xs,
  },
  userSection: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  userInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: borderRadius.full,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: colors.textPrimary,
    fontWeight: 'bold',
    fontSize: fontSize.md,
  },
  username: {
    color: colors.textPrimary,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  logoutButton: {
    padding: spacing.sm,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: colors.overlay,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    width: '80%',
    maxWidth: 400,
  },
  modalTitle: {
    color: colors.textPrimary,
    fontSize: fontSize.xl,
    fontWeight: 'bold',
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  modalInput: {
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.textPrimary,
    fontSize: fontSize.md,
    marginBottom: spacing.md,
  },
  dropdownContainer: {
    marginBottom: spacing.md,
    position: 'relative',
    elevation: 5, // Android shadow
  },
  dropdownLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginBottom: spacing.xs,
    fontWeight: '500',
  },
  dropdownButton: {
    backgroundColor: colors.backgroundLighter,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  dropdownButtonText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
  },
  dropdownPlaceholder: {
    color: colors.textMuted,
  },
  dropdownOptions: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    marginTop: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
    maxHeight: 200,
    elevation: 10, // Android shadow
    ...shadows.lg,
  },
  dropdownOption: {
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  dropdownOptionText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
  },
  promptContainer: {
    marginBottom: spacing.md,
  },
  promptLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginBottom: spacing.xs,
    fontWeight: '500',
  },
  promptHint: {
    color: colors.textMuted,
    fontSize: fontSize.xs,
    marginBottom: spacing.xs,
    fontStyle: 'italic',
  },
  promptInput: {
    minHeight: 80,
    paddingTop: spacing.md,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.sm,
  },
  modalCancelButton: {
    padding: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  modalCancelText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
  },
  modalCreateButton: {
    backgroundColor: colors.primary,
    padding: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: borderRadius.full,
  },
  modalCreateText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  modalCreateButtonDisabled: {
    opacity: 0.5,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  closeModalButton: {
    padding: spacing.xs,
  },
  inputLabel: {
    color: colors.textPrimary,
    fontSize: fontSize.sm,
    fontWeight: '600',
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
  },
  textArea: {
    minHeight: 200,
    paddingTop: spacing.md,
  },
  textAreaSmall: {
    minHeight: 80,
    paddingTop: spacing.md,
  },
  deleteConfirmText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
  modalDeleteButton: {
    backgroundColor: colors.error,
    padding: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: borderRadius.full,
  },
  modalDeleteText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  moveQuizText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  folderSelectList: {
    maxHeight: 300,
    marginBottom: spacing.md,
  },
  folderOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    borderRadius: borderRadius.sm,
    marginBottom: spacing.xs,
    backgroundColor: colors.backgroundLighter,
  },
  folderOptionText: {
    color: colors.textPrimary,
    fontSize: fontSize.md,
    marginLeft: spacing.sm,
  },
});

export default Sidebar;

