import axiosInstance from '../api/axios';

export const dataStore = {
  namespaced: true,
  state: () => ({
    importStatus: 'idle', // 'idle' | 'importing' | 'success' | 'error'
    exportStatus: 'idle',
    syncStatus: 'idle',
    importError: null,
  }),
  mutations: {
    SET_IMPORT_STATUS(state, status) {
      state.importStatus = status;
    },
    SET_EXPORT_STATUS(state, status) {
      state.exportStatus = status;
    },
    SET_SYNC_STATUS(state, status) {
      state.syncStatus = status;
    },
    SET_IMPORT_ERROR(state, error) {
      state.importError = error;
    },
  },
  actions: {
    async fetchAvailableYears() {
      try {
        const response = await axiosInstance.get('/data/available-years/');
        return response.data;
      } catch (error) {
        console.error("Failed to fetch available years:", error);
        return [];
      }
    },
    async exportData({ commit }, payload = {}) {
      commit('SET_EXPORT_STATUS', 'exporting');
      try {
        const year = payload.year;
        const url = year && year !== 'all'
          ? `/data/export/?year=${year}`
          : '/data/export/';

        const response = await axiosInstance.get(url, {
          responseType: 'blob',
        });

        // Create a temporary link to trigger the file download
        const urlBlob = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = urlBlob;
        const filename = year && year !== 'all'
          ? `time_tracker_export_${year}.json`
          : 'time_tracker_export.json';

        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        commit('SET_EXPORT_STATUS', 'success');
      } catch (error) {
        console.error("Export failed:", error);

        if (error.response && error.response.data instanceof Blob) {
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const errorData = JSON.parse(reader.result);
              console.error("Backend export error:", errorData);
            } catch (e) { /* ignore parse error */ }
          };
          reader.readAsText(error.response.data);
        }

        commit('SET_EXPORT_STATUS', 'error');
      }
    },
    async importData({ commit, dispatch, rootGetters }, { files }) {
      commit('SET_IMPORT_STATUS', 'importing');
      commit('SET_IMPORT_ERROR', null);

      const formData = new FormData();
      // Append all selected files to the form payload
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      try {
        await axiosInstance.post('/data/import-data/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        commit('SET_IMPORT_STATUS', 'success');

        await dispatch('time/resetState', null, { root: true });

        const dateRange = rootGetters['ui/getDateRange'];
        await Promise.all([
          dispatch('time/fetchProjects', null, { root: true }),
          dispatch('time/fetchRangeData', {
            startDate: dateRange.startDate,
            endDate: dateRange.endDate
          }, { root: true }),
        ]);
      } catch (error) {
        commit('SET_IMPORT_STATUS', 'error');
        const message = error.response?.data?.message ||
          error.response?.data?.error ||
          'An unknown error occurred during import.';
        commit('SET_IMPORT_ERROR', message);
      }
    },

    async syncUpload({ commit }) {
      commit('SET_SYNC_STATUS', 'syncing');
      try {
        await axiosInstance.post('/sync/trigger_upload/');
        commit('SET_SYNC_STATUS', 'success');
        setTimeout(() => commit('SET_SYNC_STATUS', 'idle'), 2000);
      } catch (error) {
        const message = error.response?.data?.message ||
          error.response?.data?.error ||
          'An unknown error occurred during import.';
        commit('SET_IMPORT_ERROR', message);
        console.error("Manual sync failed:", message, " : ", error);
        commit('SET_SYNC_STATUS', 'error');
      }
    },
    async checkStartupSync({ commit, dispatch, rootGetters }) {
      commit('SET_SYNC_STATUS', 'startup_syncing');
      try {
        const response = await axiosInstance.post('/sync/startup_check/');
        if (response.data.status === 'downloaded') {
          console.log("New data synced from drive. Reloading state.");
          // Data changed, reload everything
          const dateRange = rootGetters['ui/getDateRange'];
          await dispatch('time/fetchProjects', null, { root: true });
          await dispatch('time/fetchRangeData', {
            startDate: dateRange.startDate,
            endDate: dateRange.endDate
          }, { root: true });
          await dispatch('time/fetchRecentTimeEntries', {}, { root: true });
          await dispatch('time/fetchLiveTrack', {}, { root: true });

        }
      } catch (error) {
        const message = error.response?.data?.message ||
          error.response?.data?.error ||
          'An unknown error occurred during import.';
        console.error("Manual sync failed:", message, " : ", error);
      } finally {
        commit('SET_SYNC_STATUS', 'idle');
      }
    },
  },
};
