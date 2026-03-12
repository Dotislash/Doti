import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UiState {
  isSidebarOpen: boolean;
  chatSpacing: 'compact' | 'relaxed';
  toggleSidebar: () => void;
  setChatSpacing: (spacing: 'compact' | 'relaxed') => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      isSidebarOpen: true,
      chatSpacing: 'relaxed',
      toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
      setChatSpacing: (spacing) => set({ chatSpacing: spacing }),
    }),
    {
      name: 'doti-ui-storage',
    }
  )
);
