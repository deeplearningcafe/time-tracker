<template>
  <div class="flex flex-col h-full w-full">
    <LiveTimer @request-start-live-timer="handleStartLiveTimer" @request-stop-live-timer="handleStopLiveTimer"
      @update-track-times="handleUpdateTrackTimes" />
    <CalendarToolbar />
    <div ref="scrollContainer" class="flex-grow overflow-y-auto relative">
      <CalendarView @request-create-track="handleRequestCreateTrack" @select-track="handleSelectTrack"
        @update-track-times="handleUpdateTrackTimes" />
    </div>
    <EditEntryModal :is-visible="isModalVisible" :track="selectedTrack" :initial-times="newTrackTimes"
      :position="modalPosition" :is-saving="isSaving" @save="handleSaveTrack" @delete="handleDeleteTrack"
      @close="handleCloseModal" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';

import LiveTimer from '../components/timer/LiveTimer.vue';
import CalendarToolbar from '../components/timer/CalendarToolbar.vue';
import CalendarView from '../components/timer/CalendarView.vue';
import EditEntryModal from '../components/modals/EditEntryModal.vue';

const store = useStore();
const router = useRouter();

// --- Internal State ---
const isModalVisible = ref(false);
const selectedTrack = ref(null);
const newTrackTimes = ref(null);
const isSaving = ref(false);
// Reference to the scrollable DOM element
const scrollContainer = ref(null);

// --- Mouse Position Tracking for Modal ---
const modalPosition = ref({ x: 0, y: 0 });

const updateMousePosition = (e) => {
  modalPosition.value = { x: e.clientX, y: e.clientY };
};

// --- Computed Properties from Store ---
const isAuthenticated = computed(() => store.getters['auth/isAuthenticated']);

// Need hourHeight to calculate scroll positions for zoom
const hourHeight = computed(() => store.getters['ui/getHourHeight']);

// --- Constants ---
// The visual height of the header in CalendarView (h-10 = 40px)
const HEADER_OFFSET_PX = 40;

// --- Scroll & Focus Logic ---

/**
 * Calculates the scrollTop value needed to center a specific time in the viewport.
 * @param {number} minutesFromMidnight - The time to center (e.g., 12:00 = 720).
 * @param {number} containerHeight - The visible height of the scroll container.
 * @param {number} currentHourHeight - The current zoom level (px/hour).
 */
const getScrollTopForMinutes = (minutesFromMidnight, containerHeight, currentHourHeight) => {
  const pxPerMinute = currentHourHeight / 60;
  // The grid starts after the header.
  const timeY = (minutesFromMidnight * pxPerMinute) + HEADER_OFFSET_PX;
  const targetScroll = timeY - (containerHeight / 2);
  return Math.max(0, targetScroll);
};

/**
 * Calculates which time (in minutes) is currently at the vertical center of the viewport.
 */
const getCenterTimeMinutes = (scrollTop, containerHeight, currentHourHeight) => {
  const centerPx = scrollTop + (containerHeight / 2);
  const gridPx = centerPx - HEADER_OFFSET_PX;
  const pxPerMinute = currentHourHeight / 60;
  return gridPx / pxPerMinute;
};


// --- Data Fetching & Error Handling ---

/**
 * Centralized error handling function to dispatch errors to the UI store.
 * @param {Error} error - The error object from a catch block.
 * @param {string} context - A user-friendly context for the error message.
 */
const handleError = (error, context) => {
  console.error(`${context}:`, error);
  const message = error.response?.data?.message || `An error occurred.`;
  store.dispatch('ui/setGlobalError', { message: `${context}: ${message}` });
};

// The dateRange computed property from uiStore provides the ISO strings.
const fetchTracks = async () => {
  if (!isAuthenticated.value) return;
  try {
    // always fetch the full week to support the persistent week timer
    const week = store.getters['ui/getWeek'];
    const startDate = new Date(week[0]);
    startDate.setHours(0, 0, 0, 0);

    const endDate = new Date(week[6]);
    endDate.setHours(23, 59, 59, 999);

    await store.dispatch('time/fetchRangeData', {
      startDate: startDate.toISOString(),
      endDate: endDate.toISOString()
    });
  } catch (error) {
    handleError(error, 'Failed to fetch time data');
  }
};



// --- Lifecycle Hooks ---
onMounted(async () => {
  window.addEventListener('mouseup', updateMousePosition);

  fetchTracks();
  store.dispatch('time/fetchProjects');
  store.dispatch('time/fetchRecentTimeEntries');
  store.dispatch('time/fetchLiveTrack');

  await nextTick();
  if (scrollContainer.value && hourHeight.value) {
    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    const containerH = scrollContainer.value.clientHeight;

    scrollContainer.value.scrollTop = getScrollTopForMinutes(currentMinutes, containerH, hourHeight.value);
  }
});

onUnmounted(() => {
  window.removeEventListener('mouseup', updateMousePosition);
});

// When the zoom level changes, we want to keep the same time focused in the center.
watch(hourHeight, async (newHeight, oldHeight) => {
  if (!scrollContainer.value) return;

  const container = scrollContainer.value;
  const containerH = container.clientHeight;
  const currentScroll = container.scrollTop;

  const centerMinutes = getCenterTimeMinutes(currentScroll, containerH, oldHeight);

  await nextTick();

  container.scrollTop = getScrollTopForMinutes(centerMinutes, containerH, newHeight);
});

const currentWeekStart = computed(() => {
  const week = store.getters['ui/getWeek'];
  return week[0].toISOString();
});
watch(currentWeekStart, fetchTracks, { immediate: false });

// Redirects to login if the user is not authenticated.
watch(
  isAuthenticated,
  (isAuth) => {
    if (!isAuth) {
      router.push({ name: 'logger' });
    }
  },
  { immediate: true }
);

// --- Modal Management ---
const handleCloseModal = () => {
  isModalVisible.value = false;
  selectedTrack.value = null;
  newTrackTimes.value = null;
};

// --- Event Handlers from Children ---

const handleRequestCreateTrack = (payload) => {
  selectedTrack.value = null;
  newTrackTimes.value = payload;
  isModalVisible.value = true;
};

const handleSelectTrack = (track) => {
  newTrackTimes.value = null;
  selectedTrack.value = { ...track };
  isModalVisible.value = true;
};

const handleSaveTrack = async (trackData) => {
  isSaving.value = true;
  try {
    console.log("inside handleSaveTrack, ", trackData)
    const action = selectedTrack.value ? 'time/updateTrack' : 'time/createTrack';
    await store.dispatch(action, { trackData });
    handleCloseModal();
  } catch (error) {
    handleError(error, 'Failed to save track');
    // On error, the modal remains open for the user to correct.
  } finally {
    isSaving.value = false;
  }
};

const handleDeleteTrack = async (trackId) => {
  isSaving.value = true;
  try {
    await store.dispatch('time/deleteTrack', { trackId });
    handleCloseModal();
  } catch (error) {
    handleError(error, 'Failed to delete track');
  } finally {
    isSaving.value = false;
  }
};

const handleUpdateTrackTimes = async (trackData) => {
  try {
    await store.dispatch('time/updateTrack', { trackData });
  } catch (error) {
    handleError(error, 'Failed to move track');
  }
};

const handleStartLiveTimer = (payload) => {
  store.dispatch('time/startNewLiveTrack', {
    name: payload.name,
    project: payload.project,
  });
};

const handleStopLiveTimer = (payload) => {
  store.dispatch('time/stopTimer', { track: payload.track.value });
};
</script>
