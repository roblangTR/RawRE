import axios from 'axios';
import type {
  Shot,
  StoryStats,
  CompilationRequest,
  CompilationResult,
  CompilationStatus,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 900000, // 15 minutes timeout for large batch operations
});

// Story and shots API
export const api = {
  // Get shots for a story
  getShots: async (storySlug: string): Promise<Shot[]> => {
    const response = await apiClient.get(`/api/stories/${storySlug}/shots`);
    return response.data.shots || [];
  },

  // Get story statistics
  getStoryStats: async (storySlug: string): Promise<StoryStats> => {
    const response = await apiClient.get(`/api/stories/${storySlug}/stats`);
    return response.data;
  },

  // Get shot details
  getShot: async (shotId: number): Promise<Shot> => {
    const response = await apiClient.get(`/api/shots/${shotId}`);
    return response.data.shot;
  },

  // Start compilation
  startCompilation: async (request: CompilationRequest): Promise<{ job_id: string }> => {
    const response = await apiClient.post('/api/edits/generate', {
      story_slug: request.story_slug,
      brief: request.brief,
      target_duration: request.target_duration,
      max_iterations: request.max_iterations || 3,
    });
    return response.data;
  },

  // Get compilation status
  getCompilationStatus: async (jobId: string): Promise<CompilationStatus> => {
    const response = await apiClient.get(`/api/edits/${jobId}/status`);
    return {
      job_id: response.data.job_id,
      status: response.data.status,
      current_iteration: response.data.current_iteration || 0,
      max_iterations: response.data.max_iterations || 3,
      progress: response.data.progress || 0,
      message: response.data.message || '',
      current_agent: response.data.current_agent,
    };
  },

  // Get compilation result
  getCompilationResult: async (jobId: string): Promise<CompilationResult | null> => {
    const response = await apiClient.get(`/api/edits/${jobId}/status`);
    if (response.data.status === 'complete' && response.data.result) {
      return response.data.result;
    }
    return null;
  },

  // Upload videos
  uploadVideos: async (
    files: File[],
    storySlug: string,
    onProgress?: (progress: number) => void
  ): Promise<{ job_id: string; story_slug: string }> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await apiClient.post(`/api/videos/upload?story_slug=${storySlug}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    
    return response.data;
  },

  // Get ingestion status
  getIngestionStatus: async (jobId: string): Promise<{
    success: boolean;
    job: {
      status: string;
      progress: number;
      total_files: number;
      processed_files: number;
      total_shots: number;
      errors: string[];
    };
  }> => {
    const response = await apiClient.get(`/api/ingestion/${jobId}/status`);
    return response.data;
  },

  // Download EDL
  downloadEDL: async (jobId: string): Promise<Blob> => {
    const response = await apiClient.get(`/api/edits/${jobId}/export/edl`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Download FCPXML
  downloadFCPXML: async (jobId: string): Promise<Blob> => {
    const response = await apiClient.get(`/api/edits/${jobId}/export/fcpxml`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string }> => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

// WebSocket connection for real-time updates
export const createWebSocket = (jobId: string): WebSocket => {
  const wsUrl = API_BASE_URL.replace('http', 'ws');
  return new WebSocket(`${wsUrl}/ws/edits/${jobId}`);
};

export default api;
