"use client";

import { create } from "zustand";

interface CrossHighlightState {
  hoveredFieldKey: string | null;
  selectedRuleId: string | null;
  setHoveredField: (key: string | null) => void;
  setSelectedRule: (id: string | null) => void;
  clear: () => void;
}

export const useCrossHighlight = create<CrossHighlightState>((set) => ({
  hoveredFieldKey: null,
  selectedRuleId: null,
  setHoveredField: (key) => set({ hoveredFieldKey: key }),
  setSelectedRule: (id) =>
    set((s) => ({ selectedRuleId: s.selectedRuleId === id ? null : id })),
  clear: () => set({ hoveredFieldKey: null, selectedRuleId: null }),
}));
