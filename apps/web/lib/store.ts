import { create } from "zustand";
import type { DraftParams, CalculateResponse, UploadResponse } from "./types";

interface HydrostaticsState {
  // Hull upload state
  hullFile: File | null;
  hullUpload: UploadResponse | null;
  isUploading: boolean;
  uploadError: string | null;

  // Input parameters
  draftParams: DraftParams;
  waterDensity: number;

  // Calculation results
  results: CalculateResponse | null;
  isCalculating: boolean;
  calculateError: string | null;

  // Actions
  setHullFile: (file: File | null) => void;
  setHullUpload: (upload: UploadResponse | null) => void;
  setUploading: (v: boolean) => void;
  setUploadError: (e: string | null) => void;

  setDraftParams: (dp: Partial<DraftParams>) => void;
  setWaterDensity: (d: number) => void;

  setResults: (r: CalculateResponse | null) => void;
  setCalculating: (v: boolean) => void;
  setCalculateError: (e: string | null) => void;

  reset: () => void;
}

const initialDraftParams: DraftParams = {
  initial_draft: 0.5,
  final_draft: 5.0,
  increment: 0.25,
  design_draft: null,
};

export const useHydrostaticsStore = create<HydrostaticsState>((set) => ({
  hullFile: null,
  hullUpload: null,
  isUploading: false,
  uploadError: null,

  draftParams: initialDraftParams,
  waterDensity: 1.025,

  results: null,
  isCalculating: false,
  calculateError: null,

  setHullFile: (file) => set({ hullFile: file }),
  setHullUpload: (upload) => set({ hullUpload: upload }),
  setUploading: (v) => set({ isUploading: v }),
  setUploadError: (e) => set({ uploadError: e }),

  setDraftParams: (dp) =>
    set((state) => ({ draftParams: { ...state.draftParams, ...dp } })),
  setWaterDensity: (d) => set({ waterDensity: d }),

  setResults: (r) => set({ results: r }),
  setCalculating: (v) => set({ isCalculating: v }),
  setCalculateError: (e) => set({ calculateError: e }),

  reset: () =>
    set({
      hullFile: null,
      hullUpload: null,
      results: null,
      uploadError: null,
      calculateError: null,
    }),
}));
