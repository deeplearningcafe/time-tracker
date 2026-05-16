<template>
  <div class="flex items-center justify-center min-h-screen bg-gray-900 text-white">
    <!--
          Authenticated View: If the user is logged in, this section is
          rendered. It provides a welcome message and a logout button.
        -->
    <div v-if="isAuthenticated && user" class="text-center">
      <h1 class="text-2xl mb-4 welcome-message">
        Welcome, {{ user.username }}
      </h1>
      <p class="mb-6">You are already logged in.</p>
      <button @click="handleLogout"
        class="logout-button w-full px-4 py-2 font-bold text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500">
        Logout
      </button>
    </div>

    <!--
          Unauthenticated View: If the user is not logged in, the login form
          is displayed.
        -->
    <div v-else class="w-full max-w-md p-8 space-y-6 bg-gray-800 rounded-lg shadow-lg">
      <h1 class="text-2xl font-bold text-center">Login</h1>
      <form @submit.prevent="handleLogin" class="space-y-6">
        <p v-if="authStatus === 'error'" class="p-3 text-center text-red-200 bg-red-800 rounded-md error-message">
          Login failed. Please check your username and password.
        </p>

        <!-- Username Input -->
        <div>
          <label for="username" class="block mb-2 text-sm font-medium">
            Username
          </label>
          <input type="text" id="username" v-model="username" required
            class="w-full px-3 py-2 text-white bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <!-- Password Input -->
        <div>
          <label for="password" class="block mb-2 text-sm font-medium">
            Password
          </label>
          <input type="password" id="password" v-model="password" required
            class="w-full px-3 py-2 text-white bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <button type="submit" :disabled="authStatus === 'loading'"
          class="w-full px-4 py-2 font-bold text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-500 disabled:cursor-not-allowed">
          {{ authStatus === 'loading' ? 'Logging in...' : 'Login' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useStore } from 'vuex';
import { useRouter, useRoute } from 'vue-router';

const store = useStore();
const router = useRouter();
const route = useRoute();

// --- Component State ---
const username = ref('');
const password = ref('');

// --- Computed Properties---
const isAuthenticated = computed(() => store.getters['auth/isAuthenticated']);
const authStatus = computed(() => store.state.auth.status);
const user = computed(() => store.state.auth.user);

// --- Methods ---

/**
 * Handles the form submission with dynamic redirection.
 * It dispatches the 'login' action. On success, it redirects the user
 * to their originally intended page or to a default page.
 */
const handleLogin = () => {
  store.dispatch('auth/login', {
    username: username.value,
    password: password.value,
  }).then(() => {
    const redirectPath = route.query.redirect || '/';
    router.push(redirectPath);
  }).catch(error => {
    console.error('Login failed:', error);
  });
};

/**
 * Dispatches the 'logout' action. The authStore is responsible for clearing
 * user data and tokens.
 */
const handleLogout = () => {
  store.dispatch('auth/logout');
};

// --- Lifecycle Hooks ---

/**
 * onMounted hook now also checks for a redirect path.
 * If the user is already authenticated, it redirects them away from the
 * login page to their intended destination or the default '/timer' view.
 */
onMounted(() => {
  if (isAuthenticated.value) {
    const redirectPath = route.query.redirect || '/timer';
    router.push(redirectPath);
  }
});
</script>
