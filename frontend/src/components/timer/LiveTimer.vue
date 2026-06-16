<template>
  <div class="flex items-center justify-between w-full p-3 bg-black
            border-b border-gray-800 text-gray-300 gap-6">
    <!-- Left Section: Input and Project Selector -->
    <div class="flex items-center flex-grow gap-4">
      <!-- Description Input & Suggestions -->
      <div class="relative flex-grow">
        <input type="text" v-model="description" placeholder="What are you working on?" class="w-full p-2 bg-gray-900 border border-gray-700
                        rounded-md text-white placeholder-gray-400
                        focus:outline-none focus:ring-2 focus:ring-blue-500" :disabled="isTimerRunning"
          @focus="showSuggestions = true" @blur="showSuggestions = false" />
        <ul v-if="shouldShowSuggestions" data-testid="suggestions-list" class="absolute z-40 w-full mt-1 bg-gray-900 border
                        border-gray-700 rounded-md shadow-lg max-h-60
                        overflow-y-auto" @mousedown.prevent>
          <li v-for="entry in filteredSuggestions" :key="entry.id" @click="selectSuggestion(entry)"
            class="px-4 py-2 cursor-pointer hover:bg-gray-800">
            <span class="font-semibold text-white">
              {{ entry.name }}
            </span>
            <span class="text-sm text-gray-400 ml-2">
              - {{ projects[entry.project].title || 'No Project' }}
            </span>
          </li>
        </ul>
      </div>

      <!-- Project Selector -->
      <div class="flex-shrink-0">
        <ProjectSelector v-model="selectedProjectId" :disabled="isTimerRunning"
          @create-new-project="openProjectModal" />
      </div>
    </div>

    <!-- Right Section: Timer and Controls -->
    <div class="flex items-center flex-shrink-0 gap-4">
      <!-- Timer Display & DatePicker -->
      <div class="relative flex items-center gap-2">
        <input type="text" v-model="editableDuration"
          class="w-24 text-xl font-mono text-white text-right bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-blue-500 rounded cursor-text"
          data-testid="timer-duration" @focus="onTimerFocus" @blur="onTimerBlur" @keydown.enter="$event.target.blur()"
          :disabled="!isTimerRunning" />

        <!-- Calendar Icon Toggle -->
        <button v-if="isTimerRunning" @click="toggleDatePicker"
          class="text-gray-400 hover:text-white focus:outline-none" title="Select Start Date"
          data-testid="DatePicker-button">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </button>
        <DatePicker v-if="isDatePickerVisible" :model-value="liveTrackStartTime" @date-selected="handleDateUpdate"
          @close="closeDatePicker" class="absolute top-full right-0 mt-2 z-40" />
      </div>

      <!-- Start/Stop Button -->
      <div>
        <button @click="handleStartStop" class="px-6 py-2 text-white font-semibold rounded-md
                        transition-colors focus:outline-none
                        focus-visible:ring-2 focus-visible:ring-offset-2
                        focus-visible:ring-blue-500
                        focus-visible:ring-offset-black" :class="isTimerRunning
                          ? 'bg-red-600 hover:bg-red-700'
                          : 'bg-blue-600 hover:bg-blue-700'" data-testid="timer-button">
          {{ isTimerRunning ? 'Stop' : 'Start' }}
        </button>
      </div>
    </div>
  </div>
  <ProjectCreationModal :is-visible="isProjectModalVisible" :is-saving="isSaving" :error="creationError"
    @close="closeProjectModal" @save="saveNewProject" />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useStore } from 'vuex';
import ProjectSelector from '../common/ProjectSelector.vue';
import DatePicker from '../common/DatePicker.vue';
import { useProjectCreation } from '../../composables/useProjectCreation';
import ProjectCreationModal from '../modals/ProjectCreationModal.vue';

const emit = defineEmits(['request-start-live-timer', 'request-stop-live-timer', 'update-track-times']);

const store = useStore();

// --- STATE ---
const draftDescription = ref('');
const draftSelectedProjectId = ref(null);
const showSuggestions = ref(false);
const duration = ref(0);
const isDatePickerVisible = ref(false);
let timerInterval = null;

// Editable timer state
const editableDuration = ref('');
const isEditingTimer = ref(false);

// --- COMPUTED PROPERTIES ---
const liveTrack = computed(() => store.getters['time/getLiveTrack']);
const projects = computed(() => store.state.time.projects);
const recentTimeEntries = computed(() => store.getters['time/getRecentTimeEntries']);
const isTimerRunning = computed(() => !!liveTrack.value);

/**
 * Centralized logic to find the TimeEntry object associated with the
 * current live track.
 * 1. Checks both `time_entry_id` (TDD) and `time_entry` (DRF default) properties.
 * 2. Searches in `recentTimeEntries`.
 */
const activeTimeEntry = computed(() => {
  if (!liveTrack.value) return null;

  const entryId = liveTrack.value.time_entry;
  if (!entryId) return null;

  return recentTimeEntries.value.find(e => e.id === entryId);
});

const description = computed({
  get() {
    if (liveTrack.value) {
      // If NOT found, fallback to draft to prevent blank input.
      return activeTimeEntry.value ? activeTimeEntry.value.name : draftDescription.value;
    }
    return draftDescription.value;
  },
  set(value) {
    if (!liveTrack.value) {
      draftDescription.value = value;
    }
  }
});

const selectedProjectId = computed({
  get() {
    if (liveTrack.value) {
      const timeEntry = recentTimeEntries.value.find(
        (entry) => entry.id === liveTrack.value.time_entry
      );
      // Return the project ID if found, otherwise return null.
      return timeEntry ? timeEntry.project : null;
    }
    return draftSelectedProjectId.value;
  },
  set(value) {
    if (!liveTrack.value) {
      draftSelectedProjectId.value = value;
    }
  }
});

/**
 * Provides the start_time of the live track as a Date object,
 * which is the expected type for the DatePicker's modelValue prop.
 */
const liveTrackStartTime = computed(() => {
  return liveTrack.value ? new Date(liveTrack.value.start_time) : new Date();
});

const filteredSuggestions = computed(() => {
  if (!description.value) {
    // take top 10 recent ones
    return recentTimeEntries.value.slice(0, 10);
  }
  const searchTerm = description.value.toLowerCase();
  return recentTimeEntries.value.filter(entry =>
    entry.name.toLowerCase().includes(searchTerm)
  );
});

const shouldShowSuggestions = computed(() => {
  // Suggestions should not show if a timer is already running.
  return !isTimerRunning.value
    && showSuggestions.value
    && filteredSuggestions.value.length > 0;
});

/**
 * Formats the local `duration` ref into a readable HH:MM:SS string.
 * This is a computed property for clean separation of state and presentation.
 */
const formattedDuration = computed(() => {
  const totalSeconds = duration.value;
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);
  const pad = (num) => num.toString().padStart(2, '0');
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
});

watch(formattedDuration, (newVal) => {
  if (!isEditingTimer.value) {
    editableDuration.value = newVal;
  }
}, { immediate: true });

// --- METHODS ---
const {
  isProjectModalVisible,
  isSaving,
  creationError,
  openProjectModal,
  closeProjectModal,
  saveNewProject,
} = useProjectCreation((newProject) => {
  selectedProjectId.value = newProject.id;
});

/**
 * Toggles the visibility of the DatePicker.
 * The picker should only be shown if a timer is currently running.
 */
const toggleDatePicker = () => {
  if (isTimerRunning.value) {
    isDatePickerVisible.value = !isDatePickerVisible.value;
  }
};

const onTimerFocus = () => {
  isEditingTimer.value = true;
};

/**
 * Parses the custom user input and updates the track's start time.
 * Handles cases like "00:3" -> "00:30:00" and "123" -> "12:00:00".
 */
const onTimerBlur = () => {
  isEditingTimer.value = false;
  let input = editableDuration.value.trim();
  const parts = input.split(':');
  const parsedParts = [];

  for (let i = 0; i < 3; i++) {
    if (i < parts.length) {
      let part = parts[i].replace(/\D/g, '');
      if (part.length > 2) part = part.substring(0, 2);
      if (part.length === 1) part = part + '0';
      if (part.length === 0) part = '00';
      parsedParts.push(part);
    } else {
      parsedParts.push('00');
    }
  }

  editableDuration.value = parsedParts.join(':');

  const hours = parseInt(parsedParts[0], 10);
  const minutes = parseInt(parsedParts[1], 10);
  const seconds = parseInt(parsedParts[2], 10);

  const totalSeconds = hours * 3600 + minutes * 60 + seconds;

  if (liveTrack.value) {
    const now = new Date();
    const newStartTime = new Date(now.getTime() - totalSeconds * 1000);

    const updatedTrack = {
      ...liveTrack.value,
      start_time: newStartTime.toISOString()
    };

    emit('update-track-times', updatedTrack);
  }
};

/**
 * Handles the date-selected event from the DatePicker.
 * It dispatches an action to update the running track with the new date.
 * @param {Date} newDate - The new date selected by the user.
 */
const handleDateUpdate = (newDate) => {
  if (!liveTrack.value) return;

  // Preserve the original hours, minutes, and seconds
  const originalStart = new Date(liveTrack.value.start_time);
  const updatedStart = new Date(newDate);
  updatedStart.setHours(originalStart.getHours(), originalStart.getMinutes(), originalStart.getSeconds(), originalStart.getMilliseconds());

  const updatedTrack = {
    ...liveTrack.value,
    start_time: updatedStart.toISOString(),
  };

  store.dispatch('time/updateTrack', { trackData: updatedTrack });

  isDatePickerVisible.value = false;
};

// Closes the DatePicker component when it emits the 'close' event.
const closeDatePicker = () => {
  isDatePickerVisible.value = false;
};


const handleStartStop = () => {
  if (isTimerRunning.value) {
    emit('request-stop-live-timer', { track: liveTrack.value });
    description.value = '';
    selectedProjectId.value = null;
  } else {
    if (description.value && selectedProjectId.value) {
      emit('request-start-live-timer', {
        name: description.value,
        project: selectedProjectId.value,
      });
    }
    else {
      console.log("No name or no project id", description.value, selectedProjectId.value)
    }
  }
};

const selectSuggestion = (entry) => {
  description.value = entry.name;
  selectedProjectId.value = entry.project;
  showSuggestions.value = false;
  handleStartStop();
};

// --- LIFECYCLE & WATCHERS ---

onUnmounted(() => {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
});

watch(liveTrack, (newTrack) => {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }

  if (newTrack && newTrack.start_time) {
    const startTime = new Date(newTrack.start_time).getTime();

    const updateDuration = () => {
      const now = Date.now();
      duration.value = Math.max(0, Math.floor((now - startTime) / 1000));

      const name = activeTimeEntry.value?.name || draftDescription.value || 'Tracking';
      const projId = activeTimeEntry.value?.project || draftSelectedProjectId.value;
      const projName = projId ? projects.value[projId]?.title : '';
      document.title = `${formattedDuration.value} - ${name}${projName ? ' - ' + projName : ''} | Time Tracker`;
    };

    updateDuration();
    timerInterval = setInterval(updateDuration, 1000);

    if (activeTimeEntry.value) {
      draftDescription.value = '';
      draftSelectedProjectId.value = null;
    }
  } else {
    // No timer is running, so reset the counter display.
    duration.value = 0;
    document.title = 'Time Tracker';
  }
}, { immediate: true });

watch(activeTimeEntry, (newEntry) => {
  if (newEntry && isTimerRunning.value) {
    draftDescription.value = '';
    draftSelectedProjectId.value = null;
  }
});

/**
 * Watches for changes to the selected project ID. If a timer is
 * running and the project has changed, it dispatches an action to
 * update the project for the current time entry.
 */
watch(selectedProjectId, (newProjectId) => {
  if (
    isTimerRunning.value &&
    newProjectId &&
    newProjectId !== liveTrack.value?.project &&
    liveTrack.value.time_entry
  ) {
    console.log("update live timer project disabled")
  }
});

</script>
