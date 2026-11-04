import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  appName: 'RootIQ',
  tagline: 'Intelligence Behind Every Investigation.',
  systemStatus: 'operational',
  currentFacility: 'API Plant Alpha - Hyderabad',
  sidebarOpen: true,
  mobileNavOpen: false,
  activeInvestigationId: null,
};

export const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action) => {
      state.sidebarOpen = action.payload;
    },
    toggleMobileNav: (state) => {
      state.mobileNavOpen = !state.mobileNavOpen;
    },
    setMobileNavOpen: (state, action) => {
      state.mobileNavOpen = action.payload;
    },
    setCurrentFacility: (state, action) => {
      state.currentFacility = action.payload;
    },
    setActiveInvestigationId: (state, action) => {
      state.activeInvestigationId = action.payload;
    },
    setSystemStatus: (state, action) => {
      state.systemStatus = action.payload;
    },
  },
});

export const {
  toggleSidebar,
  setSidebarOpen,
  toggleMobileNav,
  setMobileNavOpen,
  setCurrentFacility,
  setActiveInvestigationId,
  setSystemStatus,
} = appSlice.actions;

export default appSlice.reducer;
