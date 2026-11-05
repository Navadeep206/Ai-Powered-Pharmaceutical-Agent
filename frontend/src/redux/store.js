import { configureStore } from '@reduxjs/toolkit';
import appReducer from './slices/appSlice';
import investigationReducer from './slices/investigationSlice';
import dashboardReducer from './slices/dashboardSlice';

export const store = configureStore({
  reducer: {
    app: appReducer,
    investigations: investigationReducer,
    dashboard: dashboardReducer,
  },
  devTools: typeof process !== 'undefined' ? process.env.NODE_ENV !== 'production' : true,
});

export default store;
