import { createRouter, createWebHistory } from 'vue-router'
import { store } from '../store/index.js';
import TimerView from '../views/TimerView.vue'
import LoginView from '../views/LoginView.vue'
import SettingsView from '../views/SettingsView.vue'
import SummaryView from '../views/SummaryView.vue';
import ProjectsView from '../views/ProjectsView.vue';

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    {
      path: '/',
      name: 'timer',
      component: TimerView,
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'logger',
      component: LoginView,
      meta: { hideSidebar: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/summary',
      name: 'summary',
      component: SummaryView,
      meta: { requiresAuth: true },
    },
    {
      path: '/projects',
      name: 'projects',
      component: ProjectsView,
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to, from, next) => {
  const isAuthenticated = store.getters['auth/isAuthenticated'];

  // If the route requires authentication and the user is not logged in
  if (to.meta.requiresAuth && !isAuthenticated) {
    // Redirect them to the login page
    next({ name: 'logger' });
  } else {
    // Otherwise, allow them to proceed
    next();
  }
});

export default router
