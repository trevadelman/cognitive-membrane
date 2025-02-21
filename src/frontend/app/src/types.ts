export interface ActivityPattern {
  pattern_type: string;
  start_time: Date;
  end_time: Date;
  intensity: number;
  confidence: number;
  metrics: Record<string, number>;
}

export interface ContextChange {
  timestamp: Date;
  from_context: string;
  to_context: string;
  change_duration: number;
  confidence: number;
}

export interface PerformanceMetrics {
  cpu_usage: number;
  memory_usage: number;
  response_time: number;
  pattern_detection_time: number;
  timestamp: Date;
}
