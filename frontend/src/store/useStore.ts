import { create } from 'zustand';
import type {
  Shot,
  CompilationResult,
  CompilationStatus,
  AIMessage,
  Selections,
} from '../types';

interface AppState {
  // Story data
  storySlug: string;
  shots: Shot[];
  selectedShotIds: Set<number>;
  
  // Compilation state
  compilationJobId: string | null;
  compilationStatus: CompilationStatus | null;
  compilationResult: CompilationResult | null;
  aiMessages: AIMessage[];
  
  // UI state
  isCompiling: boolean;
  uploadProgress: number;
  
  // Actions
  setStorySlug: (slug: string) => void;
  setShots: (shots: Shot[]) => void;
  setSelectedShotIds: (ids: Set<number>) => void;
  setCompilationJobId: (jobId: string | null) => void;
  setCompilationStatus: (status: CompilationStatus | null) => void;
  setCompilationResult: (result: CompilationResult | null) => void;
  addAIMessage: (message: AIMessage) => void;
  clearAIMessages: () => void;
  setIsCompiling: (isCompiling: boolean) => void;
  setUploadProgress: (progress: number) => void;
  reset: () => void;
  
  // Computed getters
  getSelectedShots: () => Shot[];
  getShotById: (id: number) => Shot | undefined;
  isShotSelected: (id: number) => boolean;
}

const useStore = create<AppState>((set, get) => ({
  // Initial state
  storySlug: '',
  shots: [],
  selectedShotIds: new Set(),
  compilationJobId: null,
  compilationStatus: null,
  compilationResult: null,
  aiMessages: [],
  isCompiling: false,
  uploadProgress: 0,
  
  // Actions
  setStorySlug: (slug) => set({ storySlug: slug }),
  
  setShots: (shots) => set({ shots }),
  
  setSelectedShotIds: (ids) => set({ selectedShotIds: ids }),
  
  setCompilationJobId: (jobId) => set({ compilationJobId: jobId }),
  
  setCompilationStatus: (status) => set({ compilationStatus: status }),
  
  setCompilationResult: (result) => {
    set({ compilationResult: result });
    
    // Update selected shot IDs from result
    if (result?.final_selections) {
      const selections = result.final_selections as Selections;
      const selectedIds = new Set(
        selections.selections.map((s) => s.shot_id)
      );
      set({ selectedShotIds: selectedIds });
    }
  },
  
  addAIMessage: (message) =>
    set((state) => ({
      aiMessages: [...state.aiMessages, message],
    })),
  
  clearAIMessages: () => set({ aiMessages: [] }),
  
  setIsCompiling: (isCompiling) => set({ isCompiling }),
  
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  
  reset: () =>
    set({
      storySlug: '',
      shots: [],
      selectedShotIds: new Set(),
      compilationJobId: null,
      compilationStatus: null,
      compilationResult: null,
      aiMessages: [],
      isCompiling: false,
      uploadProgress: 0,
    }),
  
  // Computed getters
  getSelectedShots: () => {
    const { shots, selectedShotIds } = get();
    return shots.filter((shot) => selectedShotIds.has(shot.shot_id));
  },
  
  getShotById: (id) => {
    const { shots } = get();
    return shots.find((shot) => shot.shot_id === id);
  },
  
  isShotSelected: (id) => {
    const { selectedShotIds } = get();
    return selectedShotIds.has(id);
  },
}));

export default useStore;
