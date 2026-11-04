import { configureStore } from '@reduxjs/toolkit';
import appReducer from './slices/appSlice';
import investigationReducer from './slices/investigationSlice';

export const store = configureStore({
  reducer: {
    app: appReducer,
    investigations: investigationReducer,
  },
  devTools: process.env.NODE_ENV !== 'production',
});

export default store;
