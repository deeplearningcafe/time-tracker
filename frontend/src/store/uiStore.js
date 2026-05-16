
// Defines the pixel height for each zoom level.
const HOUR_HEIGHTS = [36, 72, 144, 192, 276, 348, 492, 636, 1200];
const ZOOM_LEVEL_DEFAULT = 4;

export const uiStore = {
  namespaced: true,
  state: () => ({
    currentDate: new Date(),
    viewType: 'day', // 'day' | 'week'
    globalError: null,
    zoomLevel: ZOOM_LEVEL_DEFAULT,
    numZoomLevels: HOUR_HEIGHTS.length,
  }),
  getters: {
    getCurrentDate: (state) => state.currentDate,
    getViewType: (state) => state.viewType,
    getZoomLevel: (state) => state.zoomLevel,
    getMaxZoomLevel: (state) => state.numZoomLevels - 1,
    getHourHeight: (state) => {
      return HOUR_HEIGHTS[state.zoomLevel] || HOUR_HEIGHTS[2];
    },

    getDateRange: (state) => {
      const start = new Date(state.currentDate);
      start.setHours(0, 0, 0, 0);

      if (state.viewType === 'day') {
        const end = new Date(start);
        end.setHours(23, 59, 59, 999);
        return { startDate: start, endDate: end };
      } else {
        // Week View: Default Start on Sunday
        const dayOfWeek = start.getDay(); // 0=Sunday, 6=Saturday
        start.setDate(start.getDate() - dayOfWeek);

        const end = new Date(start);
        end.setDate(start.getDate() + 6);
        end.setHours(23, 59, 59, 999);
        return { startDate: start, endDate: end };
      }
    },

    getWeek: (state) => {
      const week = [];
      const date = new Date(state.currentDate);
      const dayOfWeek = date.getDay();
      const diff = date.getDate() - dayOfWeek;
      const sunday = new Date(date.setDate(diff));

      for (let i = 0; i < 7; i++) {
        const nextDay = new Date(sunday);
        nextDay.setDate(sunday.getDate() + i);
        week.push(nextDay);
      }
      return week;
    },

    getShortcutRange: () => (shortcut, referenceDate = new Date()) => {
      let start = new Date(referenceDate);
      let end = new Date(referenceDate);
      let type = 'day';

      start.setHours(0, 0, 0, 0);
      end.setHours(23, 59, 59, 999);

      switch (shortcut) {
        case 'today':
          break;
        case 'yesterday':
          start.setDate(start.getDate() - 1);
          end.setDate(end.getDate() - 1);
          break;
        case 'thisWeek':
          start.setDate(start.getDate() - start.getDay());
          end.setDate(start.getDate() + 6);
          type = 'week';
          break;
        case 'lastWeek':
          start.setDate(start.getDate() - start.getDay() - 7);
          end.setDate(start.getDate() + 6);
          type = 'week';
          break;
        case 'thisMonth':
          start.setDate(1);
          end = new Date(start.getFullYear(), start.getMonth() + 1, 0);
          end.setHours(23, 59, 59, 999);
          type = 'month';
          break;
        case 'lastMonth':
          start = new Date(start.getFullYear(), start.getMonth() - 1, 1);
          end = new Date(start.getFullYear(), start.getMonth() + 1, 0);
          end.setHours(23, 59, 59, 999);
          type = 'month';
          break;
        case 'thisQuarter':
          const q = Math.floor(start.getMonth() / 3);
          start = new Date(start.getFullYear(), q * 3, 1);
          end = new Date(start.getFullYear(), q * 3 + 3, 0);
          end.setHours(23, 59, 59, 999);
          type = 'quarter';
          break;
        case 'thisYear':
          start = new Date(start.getFullYear(), 0, 1);
          end = new Date(start.getFullYear(), 11, 31);
          end.setHours(23, 59, 59, 999);
          type = 'year';
          break;
        case 'lastYear':
          start = new Date(start.getFullYear() - 1, 0, 1);
          end = new Date(start.getFullYear(), 11, 31);
          end.setHours(23, 59, 59, 999);
          type = 'year';
          break;
        case 'prev90Days':
          start.setDate(start.getDate() - 89);
          type = 'custom';
          break;
      }
      console.log("inside getShortcutRange", shortcut, start, end, type);
      return { startDate: start, endDate: end, type: type };
    },

    getAdjacentRange: () => (currentRange, direction) => {
      const start = new Date(currentRange.startDate);
      const end = new Date(currentRange.endDate);
      const type = currentRange.type;

      if (type === 'week') {
        start.setDate(start.getDate() + direction * 7);
        end.setDate(end.getDate() + direction * 7);
      } else if (type === 'month') {
        start.setDate(1);
        start.setMonth(start.getMonth() + direction);
        end.setFullYear(start.getFullYear(), start.getMonth() + 1, 0);
      } else if (type === 'quarter') {
        start.setDate(1);
        start.setMonth(start.getMonth() + direction * 3);
        end.setFullYear(start.getFullYear(), start.getMonth() + 3, 0);
      } else if (type === 'year') {
        start.setDate(1);
        start.setMonth(0);
        start.setFullYear(start.getFullYear() + direction);
        end.setFullYear(start.getFullYear(), 11, 31);
      } else {
        // custom range shift by its exact length
        const diff = end.getTime() - start.getTime();
        const days = Math.round(diff / (1000 * 3600 * 24)) + 1;
        start.setDate(start.getDate() + direction * days);
        end.setDate(end.getDate() + direction * days);
      }

      start.setHours(0, 0, 0, 0);
      end.setHours(23, 59, 59, 999);
      return { startDate: start, endDate: end, type };
    }
  },
  mutations: {
    SET_CURRENT_DATE(state, newDate) {
      state.currentDate = newDate;
    },
    SET_VIEW_TYPE(state, type) {
      state.viewType = type;
    },
    SET_GLOBAL_ERROR(state, message) {
      state.globalError = message;
    },
    CLEAR_GLOBAL_ERROR(state) {
      state.globalError = null;
    },
    SET_ZOOM_LEVEL(state, level) {
      if (level >= 0 && level <= HOUR_HEIGHTS.length) {
        state.zoomLevel = level;
      }
    },
  },
  actions: {
    setDate({ commit }, { newDate }) {
      commit('SET_CURRENT_DATE', newDate);
    },
    setViewType({ commit }, { type }) {
      commit('SET_VIEW_TYPE', type);
    },
    setGlobalError({ commit }, { message }) {
      commit('SET_GLOBAL_ERROR', message);
    },
    changeZoom({ commit, state }, direction) {
      commit('SET_ZOOM_LEVEL', state.zoomLevel + direction);
    },
  },
};
