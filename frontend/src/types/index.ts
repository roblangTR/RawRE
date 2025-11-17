// Shot data types (matches API response format)
export interface Shot {
  id: number;
  storySlug: string;
  filepath: string;
  timecode: {
    in: string;
    out: string;
  };
  duration: number; // milliseconds
  shotType?: string | null;
  transcript?: string;
  description?: string;
  hasFace: number | boolean;
  hasSpeech: boolean;
  thumbnailUrl: string;
  gemini_shot_type?: string;
  gemini_shot_size?: string;
  gemini_subjects?: string[];
  relevance_score?: number;
}

// Beat structure
export interface Beat {
  beat_number: number;
  description: string;
  requirements: string[];
  target_duration: number;
  shot_types?: string[];
}

// Plan structure
export interface Plan {
  beats: Beat[];
  planned_duration: number;
  narrative_arc: string;
}

// Shot selection
export interface ShotSelection {
  beat_number: number;
  shot_id: number;
  reasoning: string;
  duration_ms: number;
}

// Selections result
export interface Selections {
  selections: ShotSelection[];
  total_shots: number;
  total_duration: number;
  beat_durations: Record<number, number>;
}

// Verification issue
export interface Issue {
  severity: 'high' | 'medium' | 'low';
  category: string;
  description: string;
  suggestion?: string;
}

// Verification result
export interface Verification {
  approved: boolean;
  overall_score: number;
  scores: {
    narrative_flow: number;
    brief_compliance: number;
    technical_quality: number;
    broadcast_standards: number;
  };
  issues: Issue[];
  high_severity_issues: Issue[];
  medium_severity_issues: Issue[];
  low_severity_issues: Issue[];
  strengths: string[];
  recommendations: string[];
}

// Compilation iteration
export interface CompilationIteration {
  iteration: number;
  plan: Plan;
  selections: Selections;
  verification: Verification;
  approved: boolean;
  error?: string;
}

// Compilation result
export interface CompilationResult {
  story_slug: string;
  brief: string;
  target_duration: number;
  constraints?: Record<string, any>;
  iterations: CompilationIteration[];
  final_plan: Plan | null;
  final_selections: Selections | null;
  final_verification: Verification | null;
  approved: boolean;
  start_time: string;
  end_time: string | null;
  duration_seconds: number | null;
}

// Compilation request
export interface CompilationRequest {
  story_slug: string;
  brief: string;
  target_duration: number;
  constraints?: Record<string, any>;
  max_iterations?: number;
  min_verification_score?: number;
}

// Compilation status
export interface CompilationStatus {
  job_id: string;
  status: 'pending' | 'planning' | 'picking' | 'verifying' | 'complete' | 'failed';
  current_iteration: number;
  max_iterations: number;
  current_agent?: 'planner' | 'picker' | 'verifier';
  message?: string;
  progress: number; // 0-100
}

// AI feedback message
export interface AIMessage {
  timestamp: string;
  agent: 'planner' | 'picker' | 'verifier' | 'system';
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

// Story stats
export interface StoryStats {
  story_slug: string;
  total_shots: number;
  total_duration_s: number;
  shot_type_counts: Record<string, number>;
  has_data: boolean;
}

// Upload progress
export interface UploadProgress {
  file: string;
  progress: number; // 0-100
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error';
  message?: string;
}
