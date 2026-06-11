<template>
  <!-- Main Container -->
  <div class="flex h-screen w-full bg-black text-gray-300 font-sans overflow-hidden">
    <!-- Sidebar Component -->
    <Sidebar v-if="showSidebar" :collapsed="isSidebarCollapsed" @toggle="isSidebarCollapsed = !isSidebarCollapsed" />
    <main class="flex-1 flex flex-col min-w-0 relative bg-black">
      <div v-if="isStartupSyncing" class="flex h-full items-center justify-center text-xl text-blue-500">
        Synchronizing with cloud...
      </div>
      <RouterView v-else />
    </main>
  </div>
</template>

<script setup>
import { watch, onMounted, ref, computed } from 'vue';
import { useStore } from 'vuex';
import { RouterView, useRoute } from 'vue-router';
import Sidebar from './components/layout/Sidebar.vue';

const store = useStore();
const route = useRoute();

// State for sidebar toggle
const isSidebarCollapsed = ref(false);
const showSidebar = ref(false);

const isStartupSyncing = computed(() => store.state.data.syncStatus === 'startup_syncing');

onMounted(async () => {
  store.dispatch('auth/loadTokens');

  if (store.getters['auth/isAuthenticated']) {
    try {
      await store.dispatch('auth/fetchUser');

      await store.dispatch('data/checkStartupSync');

      await store.dispatch('time/fetchProjects');
    } catch (error) {
      console.log("Initial session validation failed.");
      console.error(error)
    }
  }
});

watch(
  [() => route.name, () => store.getters['auth/isAuthenticated']],
  ([routeName, isAuthenticated]) => {
    // Sidebar should be hidden if:
    // 1. The route explicitly says so (e.g., login page) via meta field
    // 2. The user is not authenticated
    const shouldHide = route.meta?.hideSidebar || false;

    showSidebar.value = isAuthenticated && !shouldHide;
  },
  { immediate: true }
);

</script>
