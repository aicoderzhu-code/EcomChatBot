import apiClient from './client';
import { ApiResponse } from '@/types';

export interface PlaygroundChatRequest {
  message: string;
  model_config_id?: number | null;
  system_prompt?: string | null;
  use_rag?: boolean;
  rag_top_k?: number;
  conversation_history?: { role: string; content: string }[];
}

export interface PlaygroundChatResponse {
  response: string;
  model: string;
  provider: string;
  input_tokens: number;
  output_tokens: number;
  response_time_ms: number;
  used_rag: boolean;
  rag_sources?: { title: string; score: number; chunk_preview: string }[] | null;
}

export const playgroundApi = {
  chat: async (request: PlaygroundChatRequest): Promise<ApiResponse<PlaygroundChatResponse>> => {
    const response = await apiClient.post<ApiResponse<PlaygroundChatResponse>>(
      '/playground/chat',
      request,
    );
    return response.data;
  },
};
