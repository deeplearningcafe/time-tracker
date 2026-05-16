import axiosInstance from '../api/axios';

export const authStore = {
  namespaced: true,
  state: () => ({
    accessToken: null,
    refreshToken: null,
    user: null,
    status: 'idle', // 'idle' | 'loading' | 'success' | 'error'
  }),
  getters: {
    isAuthenticated: (state) => !!state.accessToken,
    authStatus: (state) => state.status,
  },
  mutations: {
    SET_TOKENS(state, { access, refresh }) {
      state.accessToken = access;
      state.refreshToken = refresh;
    },
    SET_USER(state, user) {
      state.user = user;
    },
    SET_AUTH_STATUS(state, status) {
      state.status = status;
    },
    CLEAR_AUTH(state) {
      state.accessToken = null;
      state.refreshToken = null;
      state.user = null;
    },
  },
  actions: {
    async login({ commit, dispatch }, credentials) {
      commit('SET_AUTH_STATUS', 'loading');
      try {
        const tokenResponse = await axiosInstance.post(
          '/token/',
          credentials
        );
        const tokens = tokenResponse.data;
        console.log("Tokens fetched")
        commit('SET_TOKENS', tokens);

        localStorage.setItem('authTokens', JSON.stringify(tokens));

        axiosInstance.defaults.headers.common['Authorization'] =
          `Bearer ${tokens.access}`;

        await dispatch('fetchUser');
        commit('SET_AUTH_STATUS', 'success');
      } catch (error) {
        commit('SET_AUTH_STATUS', 'error');
        dispatch('logout');
        throw error;
      }
    },
    async fetchUser({ commit }) {
      try {
        const userResponse = await axiosInstance.get('/users/me/');
        commit('SET_USER', userResponse.data);
      } catch (error) {
        console.error("Failed to fetch user:", error);
        dispatch('logout');
        throw error;
      }
    },
    logout({ commit }) {
      commit('CLEAR_AUTH');
      localStorage.removeItem('authTokens');
      delete axiosInstance.defaults.headers.common['Authorization'];
    },
    loadTokens({ commit }) {
      const tokens = localStorage.getItem('authTokens');
      if (tokens) {
        const parsedTokens = JSON.parse(tokens);
        commit('SET_TOKENS', parsedTokens);
        axiosInstance.defaults.headers.common['Authorization'] =
          `Bearer ${parsedTokens.access}`;
      }
    },
    async tryRefreshToken({ state, commit }) {
      if (!state.refreshToken) {
        // No refresh token, logout is the only option.
        dispatch('logout');
        return Promise.reject(new Error("No refresh token."));
      }
      try {
        const response = await axiosInstance.post('/token/refresh/', {
          refresh: state.refreshToken,
        });
        const { access } = response.data;
        const newTokens = { access, refresh: state.refreshToken };

        commit('SET_TOKENS', newTokens);
        localStorage.setItem('authTokens', JSON.stringify(newTokens));
        axiosInstance.defaults.headers.common['Authorization'] =
          `Bearer ${access}`;
        return access;
      } catch (error) {
        commit('CLEAR_AUTH');
        localStorage.removeItem('authTokens');
        throw error;
      }
    },
  },
};
