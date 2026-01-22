import apiClient from './client';

export const userService = {
  async updateApiKey(apiKey: string): Promise<{ success: boolean; error?: string }> {
    try {
      await apiClient.post('/api/me/api-key', { api_key: apiKey });
      return { success: true };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to save API key',
      };
    }
  },

  async deleteApiKey(): Promise<{ success: boolean; error?: string }> {
    try {
      await apiClient.delete('/api/me/api-key');
      return { success: true };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to delete API key',
      };
    }
  },
};

export default userService;
