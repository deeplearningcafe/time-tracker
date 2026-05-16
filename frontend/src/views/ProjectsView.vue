<template>
  <div class="flex flex-col h-full w-full bg-[#1e1e1e] text-gray-200 overflow-y-auto">
    <div class="p-6 max-w-7xl mx-auto w-full">
      <!-- Header -->
      <div class="flex justify-between items-center mb-6 border-b border-gray-800 pb-4">
        <h1 class="text-2xl font-bold text-gray-100">Projects</h1>
        <button @click="openCreateModal"
          class="px-4 py-2 bg-pink-600 hover:bg-pink-500 text-white rounded-md font-medium transition-colors">
          + New project
        </button>
      </div>

      <!-- Table -->
      <div class="bg-[#2a2a2a] rounded-lg border border-gray-800 shadow-sm overflow-hidden">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-[#1e1e1e] border-b border-gray-800 text-xs uppercase tracking-wider text-gray-500">
              <th class="p-4 font-medium w-1/2">Project</th>
              <th class="p-4 font-medium">Created At</th>
              <th class="p-4 font-medium text-right">Total Time</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="project in projects" :key="project.id" @click="openEditModal(project)"
              class="border-b border-gray-800/50 hover:bg-[#333333] cursor-pointer transition-colors group">
              <td class="p-4 flex items-center">
                <span class="w-3 h-3 rounded-full mr-3 border border-black/20"
                  :style="{ backgroundColor: '#' + project.color }"></span>
                <span class="font-medium text-gray-200 group-hover:text-white">{{ project.title }}</span>
              </td>
              <td class="p-4 text-gray-400 text-sm">
                {{ formatDate(project.created_at) }}
              </td>
              <td class="p-4 text-right font-mono text-gray-300">
                {{ formatDuration(projectDurations[project.id] || 0) }}
              </td>
            </tr>
            <tr v-if="projects.length === 0">
              <td colspan="3" class="p-8 text-center text-gray-500">
                No projects found.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Reused Modal -->
    <ProjectCreationModal :is-visible="isModalVisible" :is-saving="isSaving" :error="modalError"
      :project="selectedProject" @close="closeModal" @save="saveProject" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useStore } from 'vuex';
import ProjectCreationModal from '../components/modals/ProjectCreationModal.vue';

const store = useStore();
const projects = computed(() => store.getters['time/getAllProjects']);
const projectDurations = computed(() => store.getters['time/getAllProjectsDurations']);

const isModalVisible = ref(false);
const isSaving = ref(false);
const modalError = ref(null);
const selectedProject = ref(null);

onMounted(() => {
  store.dispatch('time/fetchProjects');
  store.dispatch('time/fetchProjectDurations');
});

const formatDuration = (totalSeconds) => {
  const hours = totalSeconds / 3600;
  return `${hours.toFixed(2)} h`;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric'
  });
};

const openCreateModal = () => {
  selectedProject.value = null;
  modalError.value = null;
  isModalVisible.value = true;
};

const openEditModal = (project) => {
  selectedProject.value = project;
  modalError.value = null;
  isModalVisible.value = true;
};

const closeModal = () => {
  isModalVisible.value = false;
  selectedProject.value = null;
};

const saveProject = async (projectData) => {
  isSaving.value = true;
  modalError.value = null;
  try {
    if (selectedProject.value) {
      await store.dispatch('time/updateProject', projectData);
    } else {
      await store.dispatch('time/createProject', projectData);
    }
    closeModal();
  } catch (error) {
    modalError.value = error.response?.data?.message || 'An error occurred.';
  } finally {
    isSaving.value = false;
  }
};
</script>
