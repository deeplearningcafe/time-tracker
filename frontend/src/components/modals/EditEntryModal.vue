<template>
  <div v-if="isVisible" ref="modalRef" data-testid="modal-overlay"
    class="fixed z-50 bg-gray-900 border border-gray-800 rounded-lg shadow-2xl p-6 w-full max-w-md transform transition-opacity duration-200"
    :style="modalStyle" role="dialog" aria-modal="true">
    <!-- Modal Header -->
    <header class="flex justify-between items-center pb-4 border-b
                    border-gray-800 mb-4">
      <h2 data-testid="modal-title" class="text-xl font-bold text-white tracking-tight">
        {{ modalTitle }}
      </h2>
      <button data-testid="close-button" @click="close" class="text-gray-400 hover:text-white transition-colors
                        p-1 rounded-md hover:bg-gray-800">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    </header>

    <!-- Modal Body (Form) -->
    <form @submit.prevent="handleSave" class="space-y-5">
      <!-- Description Field with Suggestions -->
      <div class="relative">
        <label for="description" class="block text-sm font-medium text-gray-400 mb-1">
          Description
        </label>
        <input ref="descriptionInputRef" type="text" id="description" data-testid="description-input"
          v-model="editableTrack.name" class="block w-full bg-gray-800 border border-gray-700
                            rounded-md shadow-sm py-2.5 px-3 text-white
                            placeholder-gray-500 focus:ring-2
                            focus:ring-blue-500 focus:border-transparent
                            transition-all duration-200" placeholder="What are you working on?" autocomplete="off"
          @focus="showSuggestions = true" @blur="handleInputBlur" @keydown="handleKeydown" />

        <!-- Suggestions Dropdown -->
        <ul v-if="shouldShowSuggestions" data-testid="suggestions-list" class="absolute z-50 w-full mt-1 bg-gray-800 border
                            border-gray-700 rounded-md shadow-xl max-h-60
                            overflow-y-auto custom-scrollbar" @mousedown.prevent>
          <li v-for="(entry, index) in filteredSuggestions" :key="entry.id" @click="selectSuggestion(entry)"
            @mouseenter="selectedIndex = index" class="px-4 py-3 cursor-pointer flex justify-between
                                items-center transition-colors duration-150" :class="{
                                  'bg-gray-700': index === selectedIndex,
                                  'hover:bg-gray-700': index !== selectedIndex
                                }">
            <span class="font-medium text-gray-200 truncate mr-2">
              {{ entry.name }}
            </span>
            <span v-if="entry.project" class="text-xs font-bold uppercase tracking-wider
                                    bg-gray-900 text-gray-400 px-2 py-1
                                    rounded border border-gray-700 shrink-0">
              {{ getProjectName(entry.project) }}
            </span>
          </li>
        </ul>
      </div>

      <!-- Project Selector & Duration -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Project Selector -->
        <div>
          <label for="project" class="block text-sm font-medium text-gray-400 mb-1">
            Project
          </label>
          <ProjectSelector id="project" v-model="editableTrack.project" @create-new-project="openProjectModal" />
          <ProjectCreationModal :is-visible="isProjectModalVisible" :is-saving="isSaving" :error="creationError"
            @close="closeProjectModal" @save="saveNewProject" />
        </div>

        <!-- Duration -->
        <div>
          <label for="duration" class="block text-sm font-medium text-gray-400 mb-1">
            Duration
          </label>
          <input type="text" id="duration" data-testid="duration-input" v-model="editableDuration" class="block w-full bg-gray-800 border border-gray-700
                   rounded-md shadow-sm py-2 px-3 text-white font-mono
                   focus:ring-2 focus:ring-blue-500
                   focus:border-transparent" @focus="onDurationFocus" @blur="onDurationBlur"
            @keydown.enter="$event.target.blur()" />
        </div>
      </div>

      <!-- Time Inputs -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label for="start-time" class="block text-sm font-medium text-gray-400 mb-1">
            Start Time
          </label>
          <input type="datetime-local" id="start-time" data-testid="start-time" v-model="startTimeLocal" class="block w-full bg-gray-800 border border-gray-700
                                rounded-md shadow-sm py-2 px-3 text-white
                                focus:ring-2 focus:ring-blue-500
                                focus:border-transparent" />
        </div>
        <div>
          <label for="end-time" class="block text-sm font-medium text-gray-400 mb-1">
            End Time
          </label>
          <input type="datetime-local" id="end-time" data-testid="end-time" v-model="endTimeLocal" class="block w-full bg-gray-800 border border-gray-700
                                rounded-md shadow-sm py-2 px-3 text-white
                                focus:ring-2 focus:ring-blue-500
                                focus:border-transparent" />
        </div>
      </div>

      <!-- Validation Error -->
      <div v-if="validationError" class="min-h-[1.25rem]">
        <p data-testid="error-message" class="text-sm text-red-400 flex items-center gap-1">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ validationError }}
        </p>
      </div>

      <!-- Modal Footer -->
      <footer class="flex justify-between items-center pt-5 mt-2
                        border-t border-gray-800">
        <div>
          <button v-if="isEditMode" type="button" data-testid="delete-button" @click="handleDelete" class="px-4 py-2 text-sm font-medium text-red-400
                                hover:text-red-300 hover:bg-red-900/30
                                rounded-md transition-colors">
            Delete Entry
          </button>
        </div>
        <div class="flex gap-3">
          <button type="button" @click="close" class="px-4 py-2 text-sm font-medium text-gray-300
                                bg-gray-800 border border-gray-700 rounded-md
                                hover:bg-gray-700 transition-colors">
            Cancel
          </button>
          <button type="submit" data-testid="save-button" :disabled="!isFormValid" class="px-6 py-2 text-sm font-medium text-white
                                bg-blue-600 rounded-md hover:bg-blue-500
                                disabled:bg-gray-700 disabled:text-gray-500
                                disabled:cursor-not-allowed transition-all
                                shadow-lg shadow-blue-900/20">
            {{ isEditMode ? 'Update Entry' : 'Save Entry' }}
          </button>
        </div>
      </footer>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import ProjectSelector from '../common/ProjectSelector.vue';
import { useProjectCreation } from '../../composables/useProjectCreation';
import ProjectCreationModal from './ProjectCreationModal.vue';

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  track: { type: Object, default: null },
  initialTimes: { type: Object, default: null },
  isSaving: { type: Boolean, default: false },
  position: { type: Object, default: () => ({ x: 0, y: 0 }) }
});

const emit = defineEmits(['save', 'delete', 'close']);
const store = useStore();

// --- State ---
const editableTrack = ref({});
const showSuggestions = ref(false);
const selectedIndex = ref(-1); // For keyboard navigation
const descriptionInputRef = ref(null);

const modalRef = ref(null);
const modalStyle = ref({ opacity: 0 });

const calculatePosition = () => {
  if (!modalRef.value) return;
  const rect = modalRef.value.getBoundingClientRect();
  const { innerWidth, innerHeight } = window;

  // Default positioning: slightly bottom right of the click
  let top = props.position.y + 15;
  let left = props.position.x + 15;

  if (left + rect.width > innerWidth) {
    left = props.position.x - rect.width - 15;
  }
  if (top + rect.height > innerHeight) {
    top = props.position.y - rect.height - 15;
  }

  left = Math.max(10, left);
  top = Math.max(10, top);

  modalStyle.value = {
    top: `${top}px`,
    left: `${left}px`,
    opacity: 1
  };
};

const handleClickOutside = (event) => {
  // Close the modal if the user clicks outside of it
  if (props.isVisible && modalRef.value && !modalRef.value.contains(event.target)) {
    close();
  }
};

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside);
});

// --- Computed Properties ---
const isEditMode = computed(() => !!props.track?.id);
const modalTitle = computed(() => isEditMode.value ? 'Edit Time Entry' : 'Create Time Entry');
const recentTimeEntries = computed(() => store.getters['time/getRecentTimeEntries']);

// Helper to display project name in suggestions
const getProjectName = (projectId) => {
  const project = store.getters['time/getProjectById'](projectId);
  return project ? project.title : 'Unknown';
};

// --- Validation Logic ---
const isDescriptionValid = computed(() =>
  (editableTrack.value.name || '').trim() !== ''
);
const isProjectSelected = computed(() => !!editableTrack.value.project);

const isTimeIntervalValid = computed(() => {
  const start = editableTrack.value.start_time;
  const end = editableTrack.value.end_time;
  // Ensure both are valid Date objects before comparing
  return start instanceof Date && end instanceof Date && end > start;
});

const isFormValid = computed(() =>
  isDescriptionValid.value && isTimeIntervalValid.value && isProjectSelected.value
);

const validationError = computed(() => {
  if (!isTimeIntervalValid.value) {
    return 'End time must be after start time.';
  }
  return null;
});

const filteredSuggestions = computed(() => {
  const currentName = editableTrack.value.name || '';

  // If input is empty, show most recent unique entries (limit 5)
  if (!currentName.trim()) {
    return recentTimeEntries.value.slice(0, 5);
  }
  const searchTerm = currentName.toLowerCase();
  return recentTimeEntries.value
    .filter(entry => entry.name.toLowerCase().includes(searchTerm))
    .slice(0, 5);
});

const shouldShowSuggestions = computed(() => {
  return showSuggestions.value && filteredSuggestions.value.length > 0;
});

// --- Methods ---
const selectSuggestion = (entry) => {
  editableTrack.value.name = entry.name;
  editableTrack.value.project = entry.project;
  showSuggestions.value = false;
  selectedIndex.value = -1;
};

const handleInputBlur = () => {
  setTimeout(() => {
    showSuggestions.value = false;
  }, 150);
};

/**
 * Handles keyboard navigation within the description input
 */
const handleKeydown = (e) => {
  if (!shouldShowSuggestions.value) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    selectedIndex.value = (selectedIndex.value + 1) % filteredSuggestions.value.length;
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    selectedIndex.value =
      (selectedIndex.value - 1 + filteredSuggestions.value.length) % filteredSuggestions.value.length;
  } else if (e.key === 'Enter') {
    if (selectedIndex.value >= 0) {
      e.preventDefault();
      selectSuggestion(filteredSuggestions.value[selectedIndex.value]);
    }
    // If no selection, let the default form submit happen
  } else if (e.key === 'Escape') {
    showSuggestions.value = false;
  }
};

// Reset selection when suggestions change
watch(filteredSuggestions, () => {
  selectedIndex.value = -1;
});

// --- Duration Logic ---
const isEditingDuration = ref(false);
const editableDuration = ref('');

const formattedDuration = computed(() => {
  const start = editableTrack.value.start_time;
  const end = editableTrack.value.end_time;
  if (!(start instanceof Date) || !(end instanceof Date)) return '00:00:00';

  const totalSeconds = Math.max(0, Math.floor((end.getTime() - start.getTime()) / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);

  const pad = (num) => num.toString().padStart(2, '0');
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
});

watch(formattedDuration, (newVal) => {
  if (!isEditingDuration.value) {
    editableDuration.value = newVal;
  }
}, { immediate: true });

const onDurationFocus = () => {
  isEditingDuration.value = true;
};

const onDurationBlur = () => {
  isEditingDuration.value = false;
  let input = editableDuration.value.trim();
  const parts = input.split(':');
  const parsedParts = [];

  for (let i = 0; i < 3; i++) {
    if (i < parts.length) {
      let part = parts[i].replace(/\D/g, '');

      if (part.length === 1) part = part + '0'; // Pad right with zero (e.g., "3" becomes "30")
      if (part.length === 0) part = '0';
      parsedParts.push(part);
    } else {
      parsedParts.push('0');
    }
  }

  const hours = parseInt(parsedParts[0], 10);
  const minutes = parseInt(parsedParts[1], 10);
  const seconds = parseInt(parsedParts[2], 10);

  let totalSeconds = hours * 3600 + minutes * 60 + seconds;

  // Enforce minimum duration of 1 minute (60 seconds)
  if (totalSeconds < 60) {
    totalSeconds = 60;
  }

  const end = editableTrack.value.end_time;
  if (end instanceof Date) {
    const newStart = new Date(end.getTime() - totalSeconds * 1000);
    editableTrack.value.start_time = newStart;

    const normHours = Math.floor(totalSeconds / 3600);
    const normMinutes = Math.floor((totalSeconds % 3600) / 60);
    const normSeconds = Math.floor(totalSeconds % 60);
    const pad = (num) => num.toString().padStart(2, '0');

    editableDuration.value = `${pad(normHours)}:${pad(normMinutes)}:${pad(normSeconds)}`;
  }

};

// --- Date Handling for datetime-local input ---
function dateToLocalISOString(date) {
  if (!(date instanceof Date) || isNaN(date)) return '';
  // These methods get the date/time components in the user's local timezone
  const pad = (num) => num.toString().padStart(2, '0');
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

const startTimeLocal = computed({
  get() {
    return dateToLocalISOString(editableTrack.value.start_time);
  },
  set(newValue) {
    editableTrack.value.start_time = new Date(newValue);
  }
});

const endTimeLocal = computed({
  get() {
    return dateToLocalISOString(editableTrack.value.end_time);
  },
  set(newValue) {
    editableTrack.value.end_time = new Date(newValue);
  }
});

// --- State Initialization ---
const createBlankTrack = () => ({
  name: '',
  project: null,
  start_time: props.initialTimes?.start_time || new Date(),
  end_time: props.initialTimes?.end_time || new Date(),
});

function initializeTrack() {
  if (isEditMode.value) {
    const timeEntry = store.getters['time/getTimeEntryById'](props.track.time_entry);

    const end_time = props.track.end_time ? new Date(props.track.end_time) : new Date();

    editableTrack.value = {
      id: props.track.id,
      start_time: new Date(props.track.start_time),
      end_time: end_time,
      name: timeEntry ? timeEntry.name : '',
      project: timeEntry ? timeEntry.project : null,
    };
  } else {
    editableTrack.value = createBlankTrack();
  }
}

// --- Event Handlers ---
function close() { emit('close'); }

const {
  isProjectModalVisible,
  isSaving,
  creationError,
  openProjectModal,
  closeProjectModal,
  saveNewProject,
} = useProjectCreation((newProject) => {
  editableTrack.value.project = newProject.id;
});

function handleSave() {
  if (!isFormValid.value) return;
  const payload = { ...editableTrack.value };

  // Ensure live tracks remain live after editing.
  if (props.track && !props.track.end_time) {
    payload.end_time = null;
  }

  emit('save', payload);
}

function handleDelete() {
  if (confirm('Are you sure you want to delete this entry?')) {
    emit('delete', props.track.id);
  }
}

// --- Lifecycle Hooks ---
// Initialize track data and focus input when modal opens
watch(() => props.isVisible, (newVal) => {
  if (newVal) {
    modalStyle.value = { opacity: 0 };
    initializeTrack();
    document.addEventListener('mousedown', handleClickOutside);

    nextTick(() => {
      calculatePosition();
    });
  } else {
    showSuggestions.value = false;
    document.removeEventListener('mousedown', handleClickOutside);
  }
}, { immediate: true });
</script>

<style scoped>
/* Custom scrollbar for the suggestion list to match the dark theme */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #1f2937;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #4b5563;
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #6b7280;
}
</style>
