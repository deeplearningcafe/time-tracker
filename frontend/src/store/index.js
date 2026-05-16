import { createStore } from 'vuex';
import { authStore } from './authStore';
import { uiStore } from './uiStore';
import { timeStore } from './timeStore';
import { dataStore } from './dataStore';

// Creates and configures the main Vuex store for the application.
export const store = createStore({
  modules: {
    auth: authStore,
    ui: uiStore,
    time: timeStore,
    data: dataStore,
  }
});
