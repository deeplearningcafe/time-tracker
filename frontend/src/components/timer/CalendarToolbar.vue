<template>
  <div class="flex flex-col bg-black border-b border-gray-800 pb-2">
    <!-- Row 1: Controls and Week Timer -->
    <div class="flex items-center justify-between p-2 sm:p-3">

      <!-- Center: Navigation + Week Total -->
      <div class="flex space-x-4">
        <div class="flex items-center border border-gray-600 rounded-md
                    text-sm font-medium text-gray-300 relative">
          <button @click="navigate(-1)" data-testid="prev-button" class="p-2 hover:bg-gray-800 rounded-l-md">
            &lt;
          </button>
          <div @click="toggleTimePicker" data-testid="timepicker-button"
            class="px-4 py-2 border-l border-r border-gray-600 cursor-pointer">
            <span data-testid="date-display">{{ formattedDate }}</span>
          </div>
          <button @click="navigate(1)" data-testid="next-button" class="p-2 hover:bg-gray-800 rounded-r-md">
            &gt;
          </button>
          <TimePicker v-if="isTimePickerVisible" :modelValue="currentDate" :viewType="viewType" class="top-full left-0"
            @set-date="handleSetDate" @close="isTimePickerVisible = false" />
        </div>

        <!-- Week Total -->
        <div class="flex items-center text-gray-400 text-sm font-mono">
          <span class="text-[10px] uppercase text-gray-500 mr-2">Week Total</span>
          <span class="font-bold text-gray-300">{{ formattedWeekTotal }}</span>
        </div>
      </div>

      <!-- Right: View Switcher & Zoom -->
      <div class="flex-1 flex justify-end space-x-4">
        <!-- Zoom Controls -->
        <div class="flex items-center border border-gray-600 rounded-md p-1 text-sm space-x-1">
          <button @click="adjustZoom(-1)" :disabled="isMinZoom" :class="zoomButtonStyle(isMinZoom)"
            aria-label="Zoom out" data-testid="zoom-out-button">
            -
          </button>
          <button @click="adjustZoom(1)" :disabled="isMaxZoom" :class="zoomButtonStyle(isMaxZoom)" aria-label="Zoom in"
            data-testid="zoom-in-button">
            +
          </button>
        </div>
        <!-- View Switcher -->
        <div class="flex items-center border border-gray-600 rounded-md p-1 text-sm">
          <button @click="changeView('day')" :class="viewBtnClass(viewType === 'day')"
            :aria-pressed="viewType === 'day'" data-testid="day-view-button">Calendar</button>
          <button @click="changeView('week')" :class="viewBtnClass(viewType === 'week')"
            :aria-pressed="viewType === 'week'" data-testid="week-view-button">List view</button>
        </div>
      </div>
    </div>

    <!-- Row 2: Project Distribution Bar -->
    <div class="w-full h-1.5 flex bg-gray-900">
      <div v-for="item in projectDistribution" :key="item.title"
        class="h-full relative group cursor-pointer transition-opacity hover:opacity-80"
        :style="{ width: item.percentage + '%', backgroundColor: `#${item.color}` }">

        <!-- Hover Tooltip -->
        <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden
                            group-hover:flex flex-col items-center bg-gray-800 text-white text-xs
                            rounded px-2 py-1 z-50 whitespace-nowrap shadow-lg border border-gray-700">
          <span class="font-semibold" :style="{ color: item.color }">{{ item.title }}</span>
          <span class="font-mono mt-0.5">
            {{ formatSeconds(item.seconds) }} &middot; {{ Math.round(item.percentage) }}%
          </span>
          <div class="absolute top-full left-1/2 transform -translate-x-1/2
                                border-4 border-transparent border-t-gray-700"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import TimePicker from '../common/TimePicker.vue';

const VIEW_DAY = 'day';
const VIEW_WEEK = 'week';

const store = useStore();
const zoomLevel = computed(() => store.getters['ui/getZoomLevel']);
const maxZoomLevel = computed(() => store.getters['ui/getMaxZoomLevel'])

// --- State ---
// TODO: use the date range from the ui store instead of manually formating
const currentDate = computed(() => store.getters['ui/getCurrentDate']);
const viewType = computed(() => store.getters['ui/getViewType']);
const week = computed(() => store.getters['ui/getWeek']);

const isMinZoom = ref(false);
const isMaxZoom = ref(false);
const isTimePickerVisible = ref(false);

const now = ref(new Date());
let ticker = null;

onMounted(() => { ticker = setInterval(() => now.value = new Date(), 3000); });
onUnmounted(() => clearInterval(ticker));

watch([zoomLevel, maxZoomLevel], ([current, max]) => {
  // Zoom levels are 1-based (1 to max).
  // If current is 0 or less, we are at minimum zoom.
  isMinZoom.value = current <= 0;
  // If current is equal to or greater than max, we are at maximum zoom.
  isMaxZoom.value = current >= max;
}, { immediate: true });

// --- Methods ---
const adjustZoom = (direction) => {
  store.dispatch('ui/changeZoom', direction);
};

const projectDistribution = computed(() =>
  store.getters['time/dailyProjectDistribution'](currentDate.value, now.value));

const formattedWeekTotal = computed(() => {
  const seconds = store.getters['time/weeklyTotalDuration'](week.value, now.value);
  return formatSeconds(seconds);
});

const formatSeconds = (s) => {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
};

const viewBtnClass = (active) => `px-4 py-1 rounded-md transition-colors ${active ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-800'}`;

// --- Date Formatting Helpers ---
/**
 * Gets the first day of the week (Sunday) for a given date.
 * @param {Date} d - The input date.
 * @returns {Date} The date of the preceding Sunday.
 */
const getWeekStart = (d) => {
  const date = new Date(d);
  const day = date.getDay(); // 0 for Sunday, 1 for Monday, etc.
  const diff = date.getDate() - day;
  return new Date(date.setDate(diff));
};

/**
 * Gets the last day of the week (Saturday) for a given date.
 * @param {Date} d - The input date.
 * @returns {Date} The date of the following Saturday.
 */
const getWeekEnd = (d) => {
  const startDate = getWeekStart(d);
  const endDate = new Date(startDate);
  endDate.setDate(startDate.getDate() + 6);
  return endDate;
};

// --- Computed Property ---
const formattedDate = computed(() => {
  const date = new Date(currentDate.value);
  const today = new Date();
  const isToday = date.toDateString() === today.toDateString();

  if (viewType.value === VIEW_DAY) {
    if (isToday) {
      return `Today · ${date.toLocaleDateString(
        undefined, { weekday: 'short' }
      )}`;
    }
    return date.toLocaleDateString(undefined, { dateStyle: 'medium' });
  }

  if (viewType.value === VIEW_WEEK) {
    const start = getWeekStart(date);
    const end = getWeekEnd(date);
    const startMonth = start.toLocaleDateString(
      undefined, { month: 'short' }
    );
    const endMonth = end.toLocaleDateString(
      undefined, { month: 'short' }
    );

    // Handle cases where the week spans across two months.
    if (startMonth === endMonth) {
      return `${startMonth} ${start.getDate()} – ${end.getDate()}, ` +
        `${end.getFullYear()}`;
    }
    return `${startMonth} ${start.getDate()} – ${endMonth} ` +
      `${end.getDate()}, ${end.getFullYear()}`;
  }
  return '';
});

const navigate = (direction) => {
  const newDate = new Date(currentDate.value);
  const increment = viewType.value === VIEW_DAY ? 1 : 7;
  newDate.setDate(newDate.getDate() + (direction * increment));
  store.dispatch('ui/setDate', { newDate });
};

const toggleTimePicker = () => {
  isTimePickerVisible.value = !isTimePickerVisible.value;
};

const handleSetDate = ({ date, viewType: newViewType }) => {
  store.dispatch('ui/setDate', { newDate: date });
  if (newViewType && newViewType !== viewType.value) {
    store.dispatch('ui/setViewType', { type: newViewType });
  }
};

const changeView = (type) => {
  if (type !== viewType.value) {
    store.dispatch('ui/setViewType', { type });
  }
};

const zoomButtonStyle = (disabled) => {
  const baseClasses = `px-3 py-1 rounded-md transition-colors
        focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
        focus-visible:ring-offset-2 focus-visible:ring-offset-black`;

  if (disabled) {
    return `${baseClasses} text-gray-500 cursor-not-allowed`;
  }
  return `${baseClasses} text-gray-300 hover:bg-gray-800`;
};
</script>
