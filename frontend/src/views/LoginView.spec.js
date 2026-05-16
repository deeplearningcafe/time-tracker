import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createStore } from 'vuex';
import { createRouter, createWebHistory } from 'vue-router';

import LoginView from './LoginView.vue';

/**
 * Factory function to create a mock Vuex store. Using a factory ensures
 * that each test gets a fresh, isolated store instance, preventing state
 * leakage between tests.
 * @param {object} options - Configuration for the mock store.
 * @param {boolean} options.isAuthenticated - Initial authentication state.
 * @param {string} options.authStatus - Initial status ('idle', 'loading', 'error').
 * @param {Function} options.mockLogin - A mock for the login action.
 * @param {Function} options.mockLogout - A mock for the logout action.
 * @returns {Store} A Vuex store instance.
 */
const createMockStore = ({
  isAuthenticated = false,
  authStatus = 'idle',
  mockLogin,
  mockLogout,
}) => {
  const authModule = {
    namespaced: true,
    state: {
      accessToken: isAuthenticated ? 'fake-token' : null,
      user: isAuthenticated ? { username: 'testuser' } : null,
      status: authStatus,
    },
    getters: {
      isAuthenticated: (state) => !!state.accessToken,
    },
    actions: {
      login: mockLogin || vi.fn(),
      logout: mockLogout || vi.fn(),
    },
  };

  return createStore({
    modules: {
      auth: authModule,
    },
  });
};

/**
 * Factory function to create a Vue Router instance for testing navigation
 * and redirects within the component.
 * @returns {Router} A Vue Router instance.
 */
const createMockRouter = () => {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/timer', component: { template: '<div>Timer Page</div>' } },
    ],
  });
};

describe('LoginView.vue', () => {
  let router;

  beforeEach(() => {
    router = createMockRouter();
  });

  describe('when user is not authenticated', () => {
    it('renders the login form correctly', async () => {
      const store = createMockStore({ isAuthenticated: false });
      router.push('/login');
      await router.isReady();

      const wrapper = mount(LoginView, {
        global: { plugins: [store, router] },
      });

      expect(wrapper.find('input[type="text"]').exists()).toBe(true);
      expect(wrapper.find('input[type="password"]').exists()).toBe(true);
      expect(wrapper.find('button[type="submit"]').text()).toBe('Login');
      expect(wrapper.find('.logout-button').exists()).toBe(false);
    });

    it('dispatches login action and redirects on success', async () => {
      const mockLogin = vi.fn().mockResolvedValue();
      const store = createMockStore({ mockLogin });
      router.push('/timer');
      await router.isReady();
      router.push('/login');
      await router.isReady();

      const wrapper = mount(LoginView, {
        global: { plugins: [store, router] },
      });

      await wrapper.find('input[type="text"]').setValue('testuser');
      await wrapper.find('input[type="password"]').setValue('password');
      await wrapper.find('form').trigger('submit.prevent');

      expect(mockLogin).toHaveBeenCalledTimes(1);
      expect(mockLogin).toHaveBeenCalledWith(expect.any(Object), {
        username: 'testuser',
        password: 'password',
      });

      await wrapper.vm.$nextTick();

      expect(router.currentRoute.value.path).toBe('/timer');
    });

    it('disables the submit button during login', async () => {
      const store = createMockStore({
        isAuthenticated: false,
        authStatus: 'loading',
      });
      router.push('/login');
      await router.isReady();

      const wrapper = mount(LoginView, {
        global: { plugins: [store, router] },
      });

      const submitButton = wrapper.find('button[type="submit"]');
      expect(submitButton.attributes('disabled')).toBeDefined();
      expect(submitButton.text()).toBe('Logging in...');
    });

    it('displays an error message on failed login', async () => {
      const store = createMockStore({
        isAuthenticated: false,
        authStatus: 'error',
      });
      router.push('/login');
      await router.isReady();

      const wrapper = mount(LoginView, {
        global: { plugins: [store, router] },
      });

      const errorElement = wrapper.find('.error-message');
      expect(errorElement.exists()).toBe(true);
    });
  });

  describe('when user is authenticated', () => {
    it('redirects to /timer on mount', async () => {
      const store = createMockStore({ isAuthenticated: true });
      router.push('/login');

      mount(LoginView, {
        global: { plugins: [store, router] },
      });

      await router.isReady();

      expect(router.currentRoute.value.path).toBe('/timer');
    });

    it('displays user info and handles logout', async () => {
      const mockLogout = vi.fn();
      const store = createMockStore({ isAuthenticated: true, mockLogout });

      const push = vi.fn();
      router.push = push;

      const wrapper = mount(LoginView, {
        global: { plugins: [store, router] },
      });

      expect(push).toHaveBeenCalledWith('/timer');

      expect(wrapper.find('.welcome-message').text())
        .toContain('Welcome, testuser');
      expect(wrapper.find('.logout-button').exists()).toBe(true);
      expect(wrapper.find('form').exists()).toBe(false);

      await wrapper.find('.logout-button').trigger('click');

      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
  });
});
