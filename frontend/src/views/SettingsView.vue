<template>
  <div class="min-h-screen bg-black text-gray-300 p-6 flex flex-col items-center overflow-y-auto">
    <div class="max-w-3xl w-full space-y-10 mt-10">
      <!-- Header -->
      <div class="text-center sm:text-left border-b border-gray-800 pb-6">
        <h1 class="text-4xl font-extrabold text-white tracking-tight">
          Data Portability
        </h1>
        <p class="mt-3 text-gray-400 text-lg">
          Manage your data. Export your history or import backups to restore your state.
        </p>
      </div>

      <!-- Export Section -->
      <div
        class="bg-gray-900/50 p-8 rounded-2xl border border-gray-800 shadow-lg backdrop-blur-sm transition-all hover:border-gray-700">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
          <div class="flex-1">
            <h2 class="text-2xl font-bold text-white flex items-center gap-2">
              <svg class="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
              </svg>
              Export Data
            </h2>
            <p class="text-gray-400 mt-2 leading-relaxed text-sm">
              Download a JSON file containing your projects, time entries, and tracks. You can export all your data or
              filter by a specific year.
            </p>
          </div>
          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
            <select v-model="selectedYear"
              class="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 outline-none">
              <option value="all">All Data</option>
              <option v-for="year in availableYears" :key="year" :value="year">
                {{ year }}
              </option>
            </select>
            <button @click="handleExport" :disabled="isExporting"
              class="px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md flex-shrink-0 flex justify-center items-center gap-2">
              <span v-if="isExporting">Exporting...</span>
              <span v-else>Download</span>
            </button>
          </div>
        </div>
        <!-- Export Error Message -->
        <div v-if="exportStatus === 'error'"
          class="mt-4 p-3 bg-red-900/20 border border-red-900/50 rounded-lg flex items-center gap-3 text-red-400">
          <span class="text-sm font-medium">Failed to export data. Please try again later.</span>
        </div>
      </div>

      <!-- Import Section -->
      <div
        class="bg-gray-900/50 p-8 rounded-2xl border border-gray-800 shadow-lg backdrop-blur-sm transition-all hover:border-gray-700">
        <h2 class="text-2xl font-bold text-white flex items-center gap-2 mb-4">
          <svg class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path>
          </svg>
          Import Data
        </h2>

        <!-- Info Alert -->
        <div class="bg-blue-900/10 border-l-4 border-blue-500 p-4 rounded-r-lg mb-6">
          <div class="flex items-start">
            <div class="ml-3">
              <h3 class="text-sm font-medium text-blue-400">Import Information</h3>
              <div class="mt-1 text-sm text-blue-300/80">
                <p>Importing data will <strong>merge</strong> the uploaded files with your current local data. Existing
                  records will be updated if the imported data is newer, without deleting your history.</p>
              </div>
            </div>
          </div>
        </div>


        <!-- Drop Zone -->
        <div
          class="border-2 border-dashed rounded-xl transition-all duration-300 cursor-pointer relative group flex flex-col"
          :class="[dropZoneClasses, selectedFiles.length > 0 ? 'p-4' : 'p-10']" @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false" @drop.prevent="handleDrop" @click="triggerFileInput">

          <input type="file" ref="fileInputRef" class="hidden" accept=".json,.csv" multiple @change="handleFileSelect">

          <!-- Loading Overlay -->
          <div v-if="isImporting"
            class="absolute inset-0 bg-gray-900/90 backdrop-blur-sm flex flex-col items-center justify-center z-10 rounded-xl">
            <div class="text-blue-400 font-semibold text-lg animate-pulse">Processing Import...</div>
          </div>

          <!-- Files Selected State -->
          <div v-if="selectedFiles.length > 0" class="flex flex-col h-full" @click.stop>
            <div class="flex justify-between items-center mb-3">
              <h3 class="text-md font-medium text-white">
                {{ selectedFiles.length }} File{{ selectedFiles.length > 1 ? 's' : '' }} Selected
              </h3>
              <button @click="clearFiles"
                class="text-xs text-red-400 hover:text-red-300 bg-red-400/10 px-3 py-1 rounded-md transition-colors"
                :disabled="isImporting">
                Clear All
              </button>
            </div>

            <!-- SCROLLABLE AREA -->
            <ul class="text-left space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
              <li v-for="(file, index) in selectedFiles" :key="index"
                class="flex justify-between items-center bg-gray-800/80 p-3 rounded-lg border border-gray-700">
                <div class="flex items-center gap-3 overflow-hidden">
                  <div class="truncate">
                    <p class="text-sm font-medium text-gray-200 truncate">{{ file.name }}</p>
                    <p class="text-xs text-gray-500">{{ (file.size / 1024).toFixed(2) }} KB</p>
                  </div>
                </div>
                <button @click="removeFile(index)"
                  class="text-gray-500 hover:text-red-400 p-1 rounded-full hover:bg-gray-700 transition-colors"
                  :disabled="isImporting">
                  ✕
                </button>
              </li>
            </ul>

            <button @click="triggerFileInput"
              class="text-xs text-blue-400 hover:text-blue-300 mt-3 block w-full border border-dashed border-gray-600 rounded-lg py-2 hover:bg-gray-800 transition-colors">
              + Add more files
            </button>
          </div>

          <!-- Empty State -->
          <div v-else class="py-6 text-center">
            <p class="text-gray-200 font-semibold text-lg">
              Drag & drop JSON or CSV files here
            </p>
            <p class="text-sm text-gray-500 mt-2">or click to browse your computer</p>
          </div>
        </div>

        <!-- Import Actions & Status -->
        <div class="mt-8">
          <!-- Status Messages (Error/Success) -->
          <div v-if="importStatus === 'error'"
            class="mb-5 p-4 bg-red-900/20 border-l-4 border-red-500 rounded-r-lg text-red-400 text-sm">
            <strong class="block mb-1 text-red-300">Import Failed</strong>
            {{ importError || 'An error occurred during import.' }}
          </div>

          <div v-if="importStatus === 'success'"
            class="mb-5 p-4 bg-green-900/20 border-l-4 border-green-500 rounded-r-lg text-green-400 text-sm flex justify-between items-center">
            <span><strong>Success!</strong> Data imported successfully.</span>
            <button @click="resetImportStatus" class="text-green-500 hover:text-green-300 text-xl">&times;</button>
          </div>

          <div class="flex justify-end">
            <button @click="handleImport" :disabled="selectedFiles.length === 0 || isImporting"
              class="px-8 py-3 rounded-lg font-bold transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              :class="[
                selectedFiles.length > 0 && !isImporting
                  ? 'bg-green-600 hover:bg-green-500 text-white'
                  : 'bg-gray-800 text-gray-500 border border-gray-700'
              ]">
              {{ isImporting ? 'Importing Data...' : 'Start Import' }}
            </button>
          </div>
        </div>
      </div>

      <div
        class="bg-gray-900/50 p-8 rounded-2xl border border-gray-800 shadow-lg backdrop-blur-sm transition-all hover:border-gray-700">
        <h2 class="text-2xl font-bold text-white flex items-center gap-2 mb-4">
          <svg class="w-6 h-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15">
            </path>
          </svg>
          Cloud Synchronization
        </h2>
        <div class="flex items-center justify-between">
          <div class="pr-6">
            <h3 class="text-lg font-medium text-gray-200">Enable Rclone Sync</h3>
            <p class="text-gray-400 text-sm mt-1">
              Automatically synchronize your data with the cloud on startup. Disabling this will eliminate the sync
              delay and is recommended if you share the database locally.
            </p>
          </div>
          <div class="flex items-center">
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="isSyncEnabled" @change="toggleSync" class="sr-only peer">
              <div
                class="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600">
              </div>
            </label>
          </div>
        </div>
      </div>

      <!-- Danger Zone Section -->
      <div
        class="bg-gray-900/50 p-8 rounded-2xl border border-red-900/50 shadow-lg backdrop-blur-sm transition-all hover:border-red-700/50 mt-10">
        <h2 class="text-2xl font-bold text-red-500 flex items-center gap-2 mb-4">
          <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z">
            </path>
          </svg>
          Danger Zone
        </h2>

        <!-- Warning Alert -->
        <div class="bg-red-900/10 border-l-4 border-red-500 p-4 rounded-r-lg mb-6">
          <div class="flex items-start">
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-400">Warning: Destructive Action</h3>
              <div class="mt-1 text-sm text-red-300/80">
                <p>This action will <strong>permanently delete</strong> all your projects, time entries, and tracks.
                  This cannot be undone.</p>
              </div>
            </div>
          </div>
        </div>

        <div v-if="deleteStatus === 'error'"
          class="mb-5 p-4 bg-red-900/20 border-l-4 border-red-500 rounded-r-lg text-red-400 text-sm">
          <strong class="block mb-1 text-red-300">Deletion Failed</strong>
          {{ deleteError || 'An error occurred during deletion.' }}
        </div>

        <div v-if="deleteStatus === 'success'"
          class="mb-5 p-4 bg-green-900/20 border-l-4 border-green-500 rounded-r-lg text-green-400 text-sm">
          <strong>Success!</strong> All data has been deleted.
        </div>

        <div class="flex justify-end">
          <button @click="handleDeleteAll" :disabled="isDeleting"
            class="px-8 py-3 rounded-lg font-bold transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 bg-red-600 hover:bg-red-500 text-white">
            <span v-if="isDeleting">Deleting Data...</span>
            <span v-else>Delete All My Data</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import { getCookie, setCookie } from '../utils/cookies';

const store = useStore();
const fileInputRef = ref(null);
const selectedFiles = ref([]);
const isDragging = ref(false);
const availableYears = ref([]);
const selectedYear = ref('all');

// --- Vuex State Mapping ---
const importStatus = computed(() => store.state.data.importStatus);
const exportStatus = computed(() => store.state.data.exportStatus);
const importError = computed(() => store.state.data.importError);
const deleteStatus = computed(() => store.state.data.deleteStatus);
const deleteError = computed(() => store.state.data.deleteError);

const isExporting = computed(() => exportStatus.value === 'exporting');
const isImporting = computed(() => importStatus.value === 'importing');
const isDeleting = computed(() => deleteStatus.value === 'deleting');

// --- Computed Styles ---
const dropZoneClasses = computed(() => {
  if (isDragging.value) return 'border-blue-500 bg-blue-900/20';
  if (selectedFiles.value.length > 0) return 'border-gray-700 bg-gray-800/20';
  return 'border-gray-600 hover:border-gray-500 hover:bg-gray-800/60';
});

// --- Lifecycle ---
onMounted(async () => {
  availableYears.value = await store.dispatch('data/fetchAvailableYears');
  const syncCookie = getCookie('rclone_sync_enabled');
  isSyncEnabled.value = syncCookie === 'true';
});

onUnmounted(() => {
  resetImportStatus();
});

// --- Methods ---
const toggleSync = () => {
  setCookie('rclone_sync_enabled', isSyncEnabled.value, 365);
};

const handleExport = () => {
  store.dispatch('data/exportData', { year: selectedYear.value });
};

const triggerFileInput = () => {
  if (fileInputRef.value) fileInputRef.value.click();
};

const resetImportStatus = () => {
  store.commit('data/SET_IMPORT_STATUS', 'idle');
  store.commit('data/SET_IMPORT_ERROR', null);
};

const validateAndAddFiles = (files) => {
  if (!files || files.length === 0) return;
  resetImportStatus();

  files.forEach(file => {
    const fileName = file.name.toLowerCase();
    if (fileName.endsWith('.json') || fileName.endsWith('.csv')) {
      const isDuplicate = selectedFiles.value.some(
        f => f.name === file.name && f.size === file.size
      );
      if (!isDuplicate) selectedFiles.value.push(file);
    } else {
      store.commit('data/SET_IMPORT_ERROR', 'Invalid format. Please upload .json or .csv.');
    }
  });
};

const handleFileSelect = (event) => {
  validateAndAddFiles(Array.from(event.target.files));
  if (fileInputRef.value) fileInputRef.value.value = '';
};

const handleDrop = (event) => {
  isDragging.value = false;
  validateAndAddFiles(Array.from(event.dataTransfer.files));
};

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1);
  if (selectedFiles.value.length === 0) resetImportStatus();
};

const clearFiles = () => {
  selectedFiles.value = [];
  resetImportStatus();
};

const handleImport = async () => {
  if (selectedFiles.value.length === 0) return;

  await store.dispatch('data/importData', { files: selectedFiles.value });

  if (store.state.data.importStatus === 'success') {
    selectedFiles.value = [];
  }
};

const handleDeleteAll = async () => {
  const confirmMsg = "Are you absolutely sure? This will permanently delete all your tracking data.";
  if (!window.confirm(confirmMsg)) return;

  await store.dispatch('data/deleteAllData');
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(31, 41, 55, 0.5);
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #4b5563;
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #6b7280;
}

.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #4b5563 rgba(31, 41, 55, 0.5);
}
</style>
