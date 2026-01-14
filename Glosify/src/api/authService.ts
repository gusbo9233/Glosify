import apiClient from './client';
import { User, AuthResponse } from '../types';

export const authService = {
  // Login
  async login(username: string, password: string): Promise<AuthResponse> {
    try {
      const response = await apiClient.post('/api/login', {
        username,
        password,
      });
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || 'Login failed',
      };
    }
  },

  // Register
  async register(username: string, password: string): Promise<AuthResponse> {
    try {
      const response = await apiClient.post('/api/register', {
        username,
        password,
      });
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || 'Registration failed',
      };
    }
  },

  // Logout
  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/logout');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  },

  // Check if logged in
  async checkAuth(): Promise<AuthResponse> {
    try {
      const response = await apiClient.get('/api/me');
      return response.data;
    } catch (error) {
      return { success: false };
    }
  },
};

export default authService;

