import { apiClient } from './apiClient';
import { API_ENDPOINTS } from '../constants/apiEndpoints';
import { HealthStatus, ApiResponse } from '../types/api';

export const healthService = {
  async checkHealth(): Promise<ApiResponse<HealthStatus>> {
    return apiClient<HealthStatus>(API_ENDPOINTS.HEALTH);
  },
};
