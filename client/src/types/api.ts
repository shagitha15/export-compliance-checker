export interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  data: T;
  meta?: {
    requestId?: string;
    timestamp?: string;
  };
}

export interface HealthComponents {
  database: boolean;
  vector_db: boolean;
  ai_service?: boolean;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  timestamp: string;
  components?: HealthComponents;
  database?: boolean;
  vectorDb?: boolean;
}
