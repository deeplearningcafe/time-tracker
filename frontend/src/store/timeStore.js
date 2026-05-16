import axiosInstance from '../api/axios';

// Helper to merge new items into an existing dictionary state
// This preserves existing keys that are not in the new list.
const mergeToState = (stateDict, newItems) => {
  newItems.forEach(item => {
    stateDict[item.id] = item;
  });
};

export const timeStore = {
  namespaced: true,
  state: () => ({
    // Normalized State: Objects keyed by ID for O(1) access
    projects: {},
    projectDurations: {},
    timeEntries: {},
    timeTracks: {},

    recentTimeEntryIds: [],

    liveTrackId: null,
    summaryData: null,

    status: {
      projects: 'idle',
      tracks: 'idle',
      summary: 'idle',
      entries: 'idle',
      entryCreation: 'idle',
    },
  }),
  getters: {
    getProjectById: (state) => (id) => state.projects[id],
    getTimeEntryById: (state) => (id) => state.timeEntries[id],
    getTimeTrackById: (state) => (id) => state.timeTracks[id],
    getAllProjects: (state) => Object.values(state.projects),
    getAllProjectsDurations: (state) => state.projectDurations,

    // --- Hydration Helper ---
    // Combines Track + Entry + Project into a single object for the View
    hydrateTrack: (state) => (track) => {
      if (!track) return null;
      const entry = state.timeEntries[track.time_entry];
      const project = entry ? state.projects[entry.project] : null;
      console.log("inside hydrateTrack for track, with entry and project, ", track, entry, project)
      return {
        ...track,
        name: entry ? entry.name : '',
        project: entry ? entry.project : null,
        project_title: project ? project.title : 'No Project',
        project_color: project ? project.color : '#808080',
      };
    },

    // Filter raw tracks first, then hydrate only the matches.
    tracksForDate: (state) => (date) => {
      const targetDate = new Date(date);
      targetDate.setHours(0, 0, 0, 0);
      const nextDay = new Date(targetDate);
      nextDay.setDate(nextDay.getDate() + 1);

      const matchingTracks = [];

      for (const track of Object.values(state.timeTracks)) {
        if (!track.start_time) continue;
        const start = new Date(track.start_time);
        const end = track.end_time ? new Date(track.end_time) : new Date();

        // Standard overlap condition
        if (start < nextDay && end > targetDate) {
          matchingTracks.push(getters.hydrateTrack(track));
        }
      }
      return matchingTracks.sort(
        (a, b) => new Date(a.start_time) - new Date(b.start_time)
      );
    },
    getLiveTrack: (state, getters) => {
      if (!state.liveTrackId) return null;
      return getters.hydrateTrack(state.timeTracks[state.liveTrackId]);
    },

    hasLiveTrack: (state) => !!state.liveTrackId,

    getRecentTimeEntries: (state) => {
      return state.recentTimeEntryIds
        .map(id => state.timeEntries[id])
        .filter(Boolean);
    },
    /**
     * Calculates duration in seconds for a track within a specific window.
     * Clips start/end times to the provided range.
     */
    getTrackDurationInRange: () => (track, startRange, endRange, now) => {
      const trackStart = new Date(track.start_time);
      const trackEnd = track.end_time ? new Date(track.end_time) : now;

      const effectiveStart = Math.max(trackStart, startRange);
      const effectiveEnd = Math.min(trackEnd, endRange);

      if (effectiveEnd > effectiveStart) {
        return (effectiveEnd - effectiveStart) / 1000;
      }
      return 0;
    },

    /**
     * Returns total seconds tracked for a specific day.
     */
    dailyTotalDuration: (state, getters) => (date, now = new Date()) => {
      const start = new Date(date);
      start.setHours(0, 0, 0, 0);
      const end = new Date(start);
      end.setDate(start.getDate() + 1);

      return Object.values(state.timeTracks).reduce((acc, track) => {
        return acc + getters.getTrackDurationInRange(
          track, start, end, now
        );
      }, 0);
    },

    /**
     * Returns total seconds tracked for the current week.
     */
    weeklyTotalDuration: (state, getters) => (week, now = new Date()) => {
      if (!week || week.length === 0) return 0;
      const start = new Date(week[0]);
      start.setHours(0, 0, 0, 0);
      const end = new Date(week[6]);
      end.setHours(23, 59, 59, 999);

      return Object.values(state.timeTracks).reduce((acc, track) => {
        return acc + getters.getTrackDurationInRange(
          track, start, end, now
        );
      }, 0);
    },

    /**
     * Computes project distribution for a day.
     * Returns array of { project_title, project_color, percentage, seconds }
     */
    dailyProjectDistribution: (state, getters) => (date, now = new Date()) => {
      const start = new Date(date);
      start.setHours(0, 0, 0, 0);
      const end = new Date(start);
      end.setDate(start.getDate() + 1);

      const distribution = {};
      let totalSeconds = 0;

      Object.values(state.timeTracks).forEach(track => {
        const dur = getters.getTrackDurationInRange(track, start, end, now);
        if (dur <= 0) return;

        const hydrated = getters.hydrateTrack(track);
        const pId = hydrated.project || 'no-project';

        if (!distribution[pId]) {
          distribution[pId] = {
            title: hydrated.project_title,
            color: hydrated.project_color,
            seconds: 0
          };
        }
        distribution[pId].seconds += dur;
        totalSeconds += dur;
      });

      return Object.values(distribution).map(item => ({
        ...item,
        percentage: (item.seconds / totalSeconds) * 100
      })).sort((a, b) => b.seconds - a.seconds);
    },
  },
  mutations: {
    SET_STATUS(state, { entity, status }) {
      state.status[entity] = status;
    },

    UPSERT_PROJECTS(state, projects) {
      const list = Array.isArray(projects) ? projects : [projects];
      mergeToState(state.projects, list);
    },
    UPSERT_TIME_ENTRIES(state, entries) {
      const list = Array.isArray(entries) ? entries : [entries];
      mergeToState(state.timeEntries, list);
    },
    UPSERT_TIME_TRACKS(state, tracks) {
      const list = Array.isArray(tracks) ? tracks : [tracks];
      mergeToState(state.timeTracks, list);
    },
    REMOVE_TIME_TRACK(state, trackId) {
      delete state.timeTracks[trackId];
      if (state.liveTrackId === trackId) {
        state.liveTrackId = null;
      }
    },
    SET_RECENT_TIME_ENTRY_IDS(state, ids) {
      state.recentTimeEntryIds = ids;
    },
    SET_LIVE_TRACK_ID(state, id) {
      state.liveTrackId = id;
    },
    SET_SUMMARY_DATA(state, data) {
      state.summaryData = data;
    },
    RESET_STATE(state) {
      state.projects = {};
      state.timeEntries = {};
      state.timeTracks = {};
      state.recentTimeEntryIds = [];
      state.liveTrackId = null;
      state.summaryData = null;

      Object.keys(state.status).forEach(key => {
        state.status[key] = 'idle';
      });
    },
    REMAP_TIME_ENTRY_FOR_TRACKS(state, { oldId, newId }) {
      Object.values(state.timeTracks).forEach(track => {
        if (track.time_entry === oldId) {
          track.time_entry = newId;
        }
      });
      delete state.timeEntries[oldId];
    },
    SET_PROJECT_DURATIONS(state, durations) {
      state.projectDurations = durations;
    },
  },
  actions: {
    async fetchProjects({ commit }) {
      commit('SET_STATUS', { entity: 'projects', status: 'loading' });
      try {
        const response = await axiosInstance.get('/projects/');
        commit('UPSERT_PROJECTS', response.data);
        commit('SET_STATUS', { entity: 'projects', status: 'success' });
      } catch (error) {
        commit('SET_STATUS', { entity: 'projects', status: 'error' });
      }
    },

    async fetchTimeEntries({ commit }, { startDate, endDate } = {}) {
      commit('SET_STATUS', { entity: 'entries', status: 'loading' });
      try {
        const params = {};
        if (startDate && endDate) {
          params.start_date = startDate;
          params.end_date = endDate;
        }
        const response = await axiosInstance.get('/time-entries/', { params });
        commit('UPSERT_TIME_ENTRIES', response.data);
        commit('SET_STATUS', { entity: 'entries', status: 'success' });
      } catch (error) {
        commit('SET_STATUS', { entity: 'entries', status: 'error' });
      }
    },

    async fetchRecentTimeEntries({ commit }) {
      try {
        const response = await axiosInstance.get('/time-entries/recent/');
        commit('UPSERT_TIME_ENTRIES', response.data);
        commit('SET_RECENT_TIME_ENTRY_IDS', response.data.map(e => e.id));
      } catch (error) {
        console.error("Failed to fetch recent entries", error);
      }
    },
    async fetchTimeTracks({ commit }, { startDate, endDate }) {
      commit('SET_STATUS', { entity: 'tracks', status: 'loading' });
      try {
        const response = await axiosInstance.get('/time-tracks/', {
          params: { start_date: startDate, end_date: endDate },
        });

        commit('UPSERT_TIME_TRACKS', response.data);
        commit('SET_STATUS', { entity: 'tracks', status: 'success' });
      } catch (error) {
        commit('SET_STATUS', { entity: 'tracks', status: 'error' });
      }
    },
    // Fetches both TimeTracks AND TimeEntries for a specific date range.
    async fetchRangeData({ dispatch }, { startDate, endDate }) {
      await Promise.all([
        dispatch('fetchTimeTracks', { startDate, endDate }),
        dispatch('fetchTimeEntries', { startDate, endDate })
      ]);
    },
    async fetchLiveTrack({ commit }) {
      try {
        const response = await axiosInstance.get('/time-tracks/live');
        const data = response.data;
        if (data && data.id) {
          commit('UPSERT_TIME_TRACKS', [data]);
          commit('SET_LIVE_TRACK_ID', data.id);
        } else {
          commit('SET_LIVE_TRACK_ID', null);
        }
      } catch (error) {
        console.error("Failed to fetch live track", error);
      }
    },
    /**
     * Ensures a TimeEntry exists for the given name and project.
     * Checks local state first to avoid unnecessary API calls.
     */
    async ensureTimeEntry({ commit, state }, { name, project }) {
      const existingEntry = Object.values(state.timeEntries).find(
        e => e.name === name && e.project === project
      );

      if (existingEntry) {
        return existingEntry;
      }

      const response = await axiosInstance.post('/time-entries/', {
        name: name,
        project: project
      });

      commit('UPSERT_TIME_ENTRIES', response.data);
      return response.data;
    },

    async createTrack({ commit, dispatch }, { trackData }) {
      // Resolve TimeEntry ID, it creates new time entry if needed
      const timeEntry = await dispatch('ensureTimeEntry', {
        name: trackData.name,
        project: trackData.project
      });
      const payload = {
        time_entry: timeEntry.id,
        start_time: trackData.start_time,
        end_time: trackData.end_time,
      };

      const response = await axiosInstance.post('/time-tracks/', payload);
      commit('UPSERT_TIME_TRACKS', response.data);
      return response.data;
    },
    async startNewLiveTrack({ commit, dispatch }, { name, project }) {
      commit('SET_STATUS', { entity: 'entryCreation', status: 'loading' });
      try {
        console.log("Inside startNewLiveTrack", name, project)
        const timeEntry = await dispatch('ensureTimeEntry', {
          name,
          project,
        });

        const response = await axiosInstance.post('/time-tracks/', {
          time_entry: timeEntry.id,
          start_time: new Date().toISOString(),
          end_time: null,
        });

        commit('UPSERT_TIME_TRACKS', response.data);
        commit('SET_LIVE_TRACK_ID', response.data.id);
        commit('SET_STATUS', { entity: 'entryCreation', status: 'success' });
      } catch (error) {
        const message = error.response?.data?.message ||
          error.response?.data?.error ||
          'An unknown error occurred during startNewLiveTrack.';
        console.error("Failed to start new live track:", message, ": ", error);
        commit('SET_STATUS', { entity: 'entryCreation', status: 'error' });
        throw error;
      }
    },
    async updateTrack({ dispatch, commit, state }, { trackData }) {
      const currentTrack = state.timeTracks[trackData.id];
      if (!currentTrack) return;
      console.log("inside update track with current track", currentTrack)

      let timeEntryId = currentTrack?.time_entry;

      const timeEntry = await dispatch('ensureTimeEntry', {
        name: trackData.name,
        project: trackData.project
      });
      timeEntryId = timeEntry.id;

      const payload = {
        id: trackData.id,
        time_entry: timeEntryId,
        start_time: trackData.start_time,
        end_time: trackData.end_time,
      };

      const response = await axiosInstance.put(
        `/time-tracks/${trackData.id}/`,
        payload
      );
      commit('UPSERT_TIME_TRACKS', response.data);
      return response.data;
    },
    async deleteTrack({ commit }, { trackId }) {
      await axiosInstance.delete(`/time-tracks/${trackId}/`);
      commit('REMOVE_TIME_TRACK', trackId);
    },
    async stopTimer({ state, commit }) {
      if (state.liveTrackId) {
        const track = state.timeTracks[state.liveTrackId];
        if (!track) return;

        const payload = {
          ...track,
          end_time: new Date().toISOString(),
        };

        commit('UPSERT_TIME_TRACKS', payload);
        commit('SET_LIVE_TRACK_ID', null);

        try {
          const response = await axiosInstance.put(`/time-tracks/${track.id}/`, payload);
          commit('UPSERT_TIME_TRACKS', response.data);
        } catch (e) {
          console.error("Failed to stop timer", e);
        }
      }
    },
    async updateTimeEntryProject({ commit }, { timeEntryId, projectId }) {
      try {
        // Use PATCH to update only the project field on the backend.
        await axiosInstance.patch(
          `/time-entries/${timeEntryId}/`,
          { project: projectId }
        );

        commit('UPSERT_TIME_ENTRIES', [{ id: timeEntryId, project: projectId }]);
      } catch (error) {
        console.error("Failed to update time entry project:", error);
        throw error;
      }
    },
    async fetchSummary({ commit }, { startDate, endDate }) {
      commit('SET_STATUS', { entity: 'summary', status: 'loading' });
      try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        const response = await axiosInstance.get('/summary/', {
          params: {
            start_date: startDate,
            end_date: endDate,
            timezone: timezone
          },
        });

        commit('SET_SUMMARY_DATA', response.data);
        commit('SET_STATUS', { entity: 'summary', status: 'success' });
      } catch (error) {
        const message = error.response?.data?.message ||
          error.response?.data?.error ||
          'An unknown error occurred during fetchSummary.';
        console.error("Failed to fetch summary data:", message, ": ", error);
        commit('SET_STATUS', { entity: 'summary', status: 'error' });
      }
    },
    async fetchProjectDurations({ commit }) {
      try {
        const response = await axiosInstance.get('/projects/durations/');
        commit('SET_PROJECT_DURATIONS', response.data);
      } catch (error) {
        console.error("Failed to fetch project durations", error);
      }
    },
    async createProject({ commit }, projectData) {
      try {
        const response = await axiosInstance.post('/projects/', projectData);
        commit('UPSERT_PROJECTS', response.data);
        return response.data;
      } catch (error) {
        console.error("Failed to create project:", error.response?.data);
        throw error;
      }
    },
    async updateProject({ commit }, projectData) {
      try {
        const response = await axiosInstance.put(
          `/projects/${projectData.id}/`,
          projectData
        );
        commit('UPSERT_PROJECTS', response.data);
        return response.data;
      } catch (error) {
        console.error("Failed to update project:", error.response?.data);
        throw error;
      }
    },
    resetState({ commit }) {
      commit('RESET_STATE');
    },
  },
};
