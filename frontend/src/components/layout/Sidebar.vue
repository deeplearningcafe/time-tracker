<template>
  <aside
    class="hidden md:flex bg-[#1e1e1e] text-gray-400 flex-col h-full border-r border-gray-800 font-sans flex-shrink-0 transition-all duration-300 ease-in-out"
    :class="collapsed ? 'w-20' : 'w-64'">
    <!-- Logo / Brand -->
    <div class="h-16 flex items-center border-b border-gray-800 transition-all duration-300"
      :class="collapsed ? 'justify-center px-0' : 'px-6'">
      <div
        class="w-8 h-8 rounded-full bg-pink-500 flex items-center justify-center text-white mr-3 shadow-lg shadow-pink-500/20">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
            clip-rule="evenodd" />
        </svg>
      </div>
      <!-- Hide text when collapsed -->
      <span v-show="!collapsed"
        class="font-bold text-gray-100 tracking-tight text-lg ml-3 whitespace-nowrap overflow-hidden transition-opacity duration-200">
        TimeTracker
      </span>
    </div>

    <!-- Navigation Links -->
    <nav class="flex-1 overflow-y-auto py-6 space-y-4">
      <!-- Track Section -->
      <div>
        <div v-show="!collapsed"
          class="px-6 mb-2 text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap transition-opacity duration-200">
          Track
        </div>
        <router-link :to="{ name: 'timer' }" custom v-slot="{ href, navigate, isActive }">
          <a :href="href" @click="navigate" class="group flex items-center py-3 border-l-4 transition-all duration-200"
            :class="[
              isActive ? 'border-pink-500 bg-gray-800 text-gray-100' : 'border-transparent hover:bg-gray-800/50 hover:text-gray-200',
              collapsed ? 'justify-center px-0' : 'px-6'
            ]" :title="collapsed ? 'Timer' : ''">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3"
              :class="isActive ? 'text-pink-500' : 'text-gray-500 group-hover:text-gray-300'" fill="none"
              viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span v-show="!collapsed" class="font-medium ml-3 whitespace-nowrap overflow-hidden">Timer</span>
          </a>
        </router-link>
      </div>

      <!-- Analyze Section -->
      <div>
        <div v-show="!collapsed"
          class="px-6 mb-2 text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap transition-opacity duration-200">
          Analyze
        </div>
        <router-link to="/summary" custom v-slot="{ href, navigate, isActive }">
          <a :href="href" @click="navigate" class="group flex items-center py-3 border-l-4 transition-all duration-200"
            :class="[
              isActive ? 'border-pink-500 bg-gray-800 text-gray-100' : 'border-transparent hover:bg-gray-800/50 hover:text-gray-200',
              collapsed ? 'justify-center px-0' : 'px-6'
            ]" :title="collapsed ? 'Reports' : ''">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3"
              :class="isActive ? 'text-pink-500' : 'text-gray-500 group-hover:text-gray-300'" fill="none"
              viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span v-show="!collapsed" class="font-medium ml-3 whitespace-nowrap overflow-hidden">Reports</span>
          </a>
        </router-link>
      </div>

      <!-- Manage Section -->
      <div>
        <div v-show="!collapsed"
          class="px-6 mb-2 text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap transition-opacity duration-200">
          Manage
        </div>
        <router-link :to="{ name: 'projects' }" custom v-slot="{ href, navigate, isActive }">
          <a :href="href" @click="navigate" class="group flex items-center py-3 border-l-4 transition-all duration-200"
            :class="[
              isActive ? 'border-pink-500 bg-gray-800 text-gray-100' : 'border-transparent hover:bg-gray-800/50 hover:text-gray-200',
              collapsed ? 'justify-center px-0' : 'px-6'
            ]" :title="collapsed ? 'Projects' : ''">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3"
              :class="isActive ? 'text-pink-500' : 'text-gray-500 group-hover:text-gray-300'" fill="none"
              viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <span v-show="!collapsed" class="font-medium ml-3 whitespace-nowrap overflow-hidden">Projects</span>
          </a>
        </router-link>
        <router-link :to="{ name: 'settings' }" custom v-slot="{ href, navigate, isActive }">
          <a :href="href" @click="navigate" class="group flex items-center py-3 border-l-4 transition-all duration-200"
            :class="[
              isActive ? 'border-pink-500 bg-gray-800 text-gray-100' : 'border-transparent hover:bg-gray-800/50 hover:text-gray-200',
              collapsed ? 'justify-center px-0' : 'px-6'
            ]" :title="collapsed ? 'Settings' : ''">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3"
              :class="isActive ? 'text-pink-500' : 'text-gray-500 group-hover:text-gray-300'" fill="none"
              viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span v-show="!collapsed" class="font-medium ml-3 whitespace-nowrap overflow-hidden">Settings</span>
          </a>
        </router-link>
      </div>
      <!-- Sync Button -->
      <div class="mt-4">
        <button @click="handleSync"
          class="w-full flex items-center py-3 border-l-4 border-transparent hover:bg-gray-800/50 hover:text-gray-200 transition-all duration-200 text-gray-500"
          :class="collapsed ? 'justify-center px-0' : 'px-6'">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3"
            :class="syncStatus === 'syncing' ? 'animate-spin text-blue-500' : ''" fill="none" viewBox="0 0 24 24"
            stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span v-show="!collapsed" class="font-medium ml-3 whitespace-nowrap overflow-hidden">
            {{ syncStatus === 'syncing' ? 'Syncing...' : 'Synchronize' }}
          </span>
        </button>
      </div>
    </nav>

    <!-- Toggle Button -->
    <div class="px-4 pb-4 flex" :class="collapsed ? 'justify-center' : 'justify-end'">
      <button @click="$emit('toggle')"
        class="p-2 rounded-md text-gray-500 hover:text-gray-200 hover:bg-gray-800 focus:outline-none transition-colors"
        :title="collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'">
        <!-- Icon changes direction based on state -->
        <svg v-if="!collapsed" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24"
          stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24"
          stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
        </svg>
      </button>
    </div>

    <!-- User Profile & Logout -->
    <div class="p-4 border-t border-gray-800 bg-[#1e1e1e]">
      <div class="flex items-center rounded-md hover:bg-gray-800 transition-colors group"
        :class="collapsed ? 'justify-center p-0' : 'justify-between p-2'">

        <div class="flex items-center overflow-hidden">
          <div
            class="h-8 w-8 rounded-full bg-gray-700 flex-shrink-0 flex items-center justify-center text-xs font-bold text-gray-300 border border-gray-600">
            {{ userInitials }}
          </div>
          <div v-show="!collapsed" class="ml-3 overflow-hidden">
            <p class="text-sm font-medium text-gray-200 truncate">{{ userName }}</p>
            <p class="text-xs text-gray-500 truncate">{{ userEmail }}</p>
          </div>
        </div>

        <!-- Logout Button -->
        <button v-show="!collapsed" @click="handleLogout"
          class="text-gray-500 hover:text-red-400 p-1 rounded focus:outline-none ml-2" title="Logout">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['toggle']);

const store = useStore();
const router = useRouter();

const user = computed(() => store.state.auth?.user || {});
const syncStatus = computed(() => store.state.data?.syncStatus || 'idle');

const userName = computed(() => user.value.username || 'User');
const userEmail = computed(() => user.value.email || '');
const userInitials = computed(() => {
  const name = userName.value;
  return name ? name.substring(0, 2).toUpperCase() : 'U';
});

const handleLogout = async () => {
  try {
    await store.dispatch('auth/logout');
  } catch (e) {
    console.error("Logout error", e);
  }
  router.push({ name: 'logger' });
};

const handleSync = async () => {
  await store.dispatch('data/syncUpload');
};
</script>
