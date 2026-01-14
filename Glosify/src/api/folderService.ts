import apiClient from './client';
import { Folder } from '../types';

export interface FolderListResponse {
  folders: Folder[];
}

export const folderService = {
  // Get all folders for the logged-in user
  async getFolders(): Promise<Folder[]> {
    try {
      const response = await apiClient.get('/api/folders');
      return response.data.folders || [];
    } catch (error) {
      console.error('Error fetching folders:', error);
      throw error;
    }
  },

  // Create a new folder
  async createFolder(name: string, parentId?: number): Promise<Folder> {
    try {
      const response = await apiClient.post('/api/folders', { 
        name,
        parent_id: parentId 
      });
      return response.data.folder;
    } catch (error) {
      console.error('Error creating folder:', error);
      throw error;
    }
  },

  // Delete a folder
  async deleteFolder(folderId: number): Promise<void> {
    try {
      await apiClient.delete(`/api/folder/${folderId}`);
    } catch (error) {
      console.error('Error deleting folder:', error);
      throw error;
    }
  },

  // Update a folder
  async updateFolder(folderId: number, updates: { name?: string; parent_id?: number | null }): Promise<Folder> {
    try {
      const response = await apiClient.put(`/api/folder/${folderId}`, updates);
      return response.data.folder;
    } catch (error) {
      console.error('Error updating folder:', error);
      throw error;
    }
  },

  // Move a quiz to a folder
  async moveQuizToFolder(quizId: number, folderId: number | null): Promise<void> {
    try {
      await apiClient.post(`/api/quiz/${quizId}/move`, { 
        folder_id: folderId 
      });
    } catch (error) {
      console.error('Error moving quiz to folder:', error);
      throw error;
    }
  },
};

export default folderService;
