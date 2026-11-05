import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import dashboardService from '../../services/dashboardService';
import { normalizeActivity } from '../../utils/normalizers';

export const fetchDashboardSummary = createAsyncThunk(
  'dashboard/fetchSummary',
  async (_, { rejectWithValue }) => {
    try {
      const data = await dashboardService.getSummary();
      return data;
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to retrieve dashboard metrics.');
    }
  }
);

export const fetchDashboardActivities = createAsyncThunk(
  'dashboard/fetchActivities',
  async (limit = 10, { rejectWithValue }) => {
    try {
      const data = await dashboardService.getActivities(limit);
      return data.map(normalizeActivity);
    } catch (err) {
      return rejectWithValue(err.message || 'Failed to retrieve recent activities.');
    }
  }
);

const initialState = {
  summary: null,
  summaryLoading: false,
  summaryError: null,
  activities: [],
  activitiesLoading: false,
  activitiesError: null,
};

export const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    clearDashboardErrors: (state) => {
      state.summaryError = null;
      state.activitiesError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Summary
      .addCase(fetchDashboardSummary.pending, (state) => {
        state.summaryLoading = true;
        state.summaryError = null;
      })
      .addCase(fetchDashboardSummary.fulfilled, (state, action) => {
        state.summaryLoading = false;
        state.summary = action.payload;
        state.summaryError = null;
      })
      .addCase(fetchDashboardSummary.rejected, (state, action) => {
        state.summaryLoading = false;
        state.summaryError = action.payload || 'Failed to load dashboard metrics.';
      })

      // Activities
      .addCase(fetchDashboardActivities.pending, (state) => {
        state.activitiesLoading = true;
        state.activitiesError = null;
      })
      .addCase(fetchDashboardActivities.fulfilled, (state, action) => {
        state.activitiesLoading = false;
        state.activities = action.payload;
        state.activitiesError = null;
      })
      .addCase(fetchDashboardActivities.rejected, (state, action) => {
        state.activitiesLoading = false;
        state.activitiesError = action.payload || 'Failed to load recent activities.';
      });
  },
});

export const { clearDashboardErrors } = dashboardSlice.actions;

export default dashboardSlice.reducer;
