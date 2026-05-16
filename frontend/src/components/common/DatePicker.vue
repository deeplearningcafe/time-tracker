<template>

  <div ref="datePickerRoot" :class="[
    'bg-gray-900 w-72 p-4',
    inline ? '' : 'absolute z-10 border border-gray-700 rounded-lg shadow-lg'
  ]">
    <!-- Start/Stop Time Inputs -->
    <div v-if="showTimeInputs" class="flex justify-between mb-4">
      <div class="w-1/2 pr-1">
        <label class="text-xs font-bold text-gray-500">START</label>
        <input type="text" v-model="editableStartTime" @blur="applyStartTime" @keydown.enter="$event.target.blur()"
          class="w-full p-2 bg-gray-800 border border-gray-700 rounded-md
                           text-white focus:outline-none focus:ring-1
                           focus:ring-blue-500" />
      </div>
      <div class="w-1/2 pl-1">
        <label class="text-xs font-bold text-gray-500">STOP</label>
        <input type="text" :value="formattedEndTime" class="w-full p-2 bg-gray-800 border border-gray-700 rounded-md
                           text-gray-400 cursor-not-allowed" readonly />
      </div>
    </div>


    <!-- Calendar Header -->
    <div class="flex items-center justify-between mb-2">
      <button @click="prevMonth" data-testid="prev-month-btn" class="p-2 rounded-full hover:bg-gray-800 text-gray-300"
        aria-label="Previous month">
        &lt;
      </button>
      <h3 class="text-sm font-semibold text-white" data-testid="month-year-header">
        {{ monthYearHeader }}
      </h3>
      <button @click="nextMonth" data-testid="next-month-btn" class="p-2 rounded-full hover:bg-gray-800 text-gray-300"
        aria-label="Next month">
        &gt;
      </button>
    </div>

    <!-- Calendar Grid -->
    <div class="grid grid-cols-7 text-center">
      <!-- Weekday Headers -->
      <div v-for="day in weekdays" :key="day" class="text-xs font-bold text-gray-500 mb-1">
        {{ day }}
      </div>

      <!-- Day Cells -->
      <div v-for="(day, index) in calendarGrid" :key="index" :class="[
        'flex items-center justify-center h-8 my-0.5',
        {
          'bg-blue-900/40': day && day.isInSelectedWeek,
          'rounded-l-full': day && ((day.isInSelectedWeek && index % 7 === 0) || day.isRangeStart),
          'rounded-r-full': day && ((day.isInSelectedWeek && index % 7 === 6) || day.isRangeEnd)
        }
      ]">
        <button v-if="day" @click="selectDate(day.day)" :class="[
          'w-8 h-8 text-xs rounded-full transition-colors',
          {
            'bg-blue-600 text-white': day.isSelected || day.isRangeStart || day.isRangeEnd,
            'hover:bg-gray-800 text-gray-300':
              !day.isSelected && !day.isInSelectedWeek && !day.isRangeStart && !day.isRangeEnd,
            'hover:bg-blue-800 text-blue-100':
              (!day.isSelected && day.isInSelectedWeek) || (day.isInRange && !day.isRangeStart && !day.isRangeEnd),
          },
        ]" :aria-selected="day.isSelected || day.isRangeStart || day.isRangeEnd" :aria-label="getDayAriaLabel(day.day)"
          data-testid="day-cell">
          {{ day.day }}
        </button>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useStore } from 'vuex';

const props = defineProps({
  /**
   * The selected date, for v-model binding.
   */
  modelValue: {
    type: Date,
    default: () => new Date(),
  },
  /**
   * Determines whether to highlight a single day or a whole week.
   */
  viewType: {
    type: String,
    default: 'day',
  },
  /**
   * Toggles the visibility of the start/stop time inputs.
   */
  showTimeInputs: {
    type: Boolean,
    default: true,
  },
  /**
   * Removes absolute positioning and shadow for inline embedding.
   */
  inline: {
    type: Boolean,
    default: false,
  },
  mode: {
    type: String,
    default: 'single',
  },
  rangeStart: {
    type: Date,
    default: null,
  },
  rangeEnd: {
    type: Date,
    default: null,
  },
});

const emit = defineEmits(['date-selected', 'close', 'range-selected']);

const store = useStore();

const datePickerRoot = ref(null);
const displayDate = ref(new Date(props.modelValue || Date.now()));
const now = ref(new Date());

const tempRangeStart = ref(null);
const tempRangeEnd = ref(null);

watch(() => props.rangeStart, (val) => { tempRangeStart.value = val; }, { immediate: true });
watch(() => props.rangeEnd, (val) => { tempRangeEnd.value = val; }, { immediate: true });


// Reactive reference to the live track from the Vuex store getters.
const liveTrack = computed(() => store.getters['time/getLiveTrack']);

/**
 * Parses the ISO string into a Date object before formatting.
 */
const formatTime = (dateVal) => {
  if (!dateVal) return '';
  const date = new Date(dateVal);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};


const formattedStartTime = computed(() => {
  return formatTime(liveTrack.value?.start_time);
});
const formattedEndTime = computed(() => {
  // If the track has a defined end time, use it.
  // Otherwise, if it's a running track, use the reactive 'now' value.
  return formatTime(liveTrack.value?.end_time || (liveTrack.value ? now.value : null));
});

const editableStartTime = ref('');

// Sync the local editable start time with the formatted start time
watch(formattedStartTime, (newVal) => {
  editableStartTime.value = newVal;
}, { immediate: true });

/**
 * Parses the user input time and emits the updated date.
 */
const applyStartTime = () => {
  if (!liveTrack.value) return;
  const timeStr = editableStartTime.value.trim();

  const match = timeStr.match(/^(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?$/i);

  if (match) {
    let hours = parseInt(match[1], 10);
    const minutes = parseInt(match[2], 10);
    const ampm = match[3] ? match[3].toUpperCase() : null;

    if (ampm === 'PM' && hours < 12) hours += 12;
    if (ampm === 'AM' && hours === 12) hours = 0;

    const newDate = new Date(liveTrack.value.start_time);
    newDate.setHours(hours, minutes, 0, 0);
    emit('date-selected', newDate);
  } else {
    // Revert to original if the format is invalid
    editableStartTime.value = formattedStartTime.value;
  }
};

const monthYearHeader = computed(() => {
  return displayDate.value.toLocaleString('default', {
    month: 'long',
    year: 'numeric',
  });
});

const calendarGrid = computed(() => {
  const year = displayDate.value.getFullYear();
  const month = displayDate.value.getMonth();
  const firstDayOfMonth = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const grid = [];

  const selectedDate = props.modelValue || new Date();
  const selectedYear = selectedDate.getFullYear();
  const selectedMonth = selectedDate.getMonth();
  const selectedDateNum = selectedDate.getDate();

  // Calculate week boundaries for week highlighting
  const dayOfWeek = selectedDate.getDay();
  const weekStart = new Date(
    selectedYear, selectedMonth, selectedDateNum - dayOfWeek
  );
  const weekEnd = new Date(
    selectedYear, selectedMonth, selectedDateNum + (6 - dayOfWeek)
  );
  weekStart.setHours(0, 0, 0, 0);
  weekEnd.setHours(23, 59, 59, 999);

  for (let i = 0; i < firstDayOfMonth; i++) {
    grid.push(null);
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const currentCellDate = new Date(year, month, day);
    const isSelected =
      props.modelValue &&
      currentCellDate.getFullYear() === selectedYear &&
      currentCellDate.getMonth() === selectedMonth &&
      currentCellDate.getDate() === selectedDateNum;

    const isInSelectedWeek =
      props.modelValue &&
      props.viewType === 'week' &&
      currentCellDate >= weekStart &&
      currentCellDate <= weekEnd;

    let isRangeStart = false;
    let isRangeEnd = false;
    let isInRange = false;

    if (props.mode === 'range') {
      const start = tempRangeStart.value;
      const end = tempRangeEnd.value;

      const cellTime = currentCellDate.getTime();
      if (start && cellTime === new Date(start.getFullYear(), start.getMonth(), start.getDate()).getTime()) {
        isRangeStart = true;
      }
      if (end && cellTime === new Date(end.getFullYear(), end.getMonth(), end.getDate()).getTime()) {
        isRangeEnd = true;
      }
      if (start && end && currentCellDate >= start && currentCellDate <= end) {
        isInRange = true;
      }
    }
    grid.push({ day, isSelected, isInSelectedWeek, isRangeStart, isRangeEnd, isInRange });
  }

  return grid;
});


const prevMonth = () => {
  const newMonth = displayDate.value.getMonth() - 1;
  displayDate.value = new Date(displayDate.value.setMonth(newMonth));
};

const nextMonth = () => {
  const newMonth = displayDate.value.getMonth() + 1;
  displayDate.value = new Date(displayDate.value.setMonth(newMonth));
};

const selectDate = (day) => {
  const newSelectedDate = new Date(displayDate.value);
  newSelectedDate.setDate(day);

  if (props.mode === 'range') {
    newSelectedDate.setHours(0, 0, 0, 0);
    // reset/start range
    if (!tempRangeStart.value || (tempRangeStart.value && tempRangeEnd.value)) {
      tempRangeStart.value = newSelectedDate;
      tempRangeEnd.value = null;
    } else {
      // end date selection
      if (newSelectedDate < tempRangeStart.value) {
        tempRangeEnd.value = tempRangeStart.value;
        tempRangeStart.value = newSelectedDate;
      } else {
        tempRangeEnd.value = newSelectedDate;
      }
      const end = new Date(tempRangeEnd.value);
      end.setHours(23, 59, 59, 999);
      emit('range-selected', { start: tempRangeStart.value, end });
    }
  } else {
    if (props.modelValue) {
      newSelectedDate.setHours(props.modelValue.getHours());
      newSelectedDate.setMinutes(props.modelValue.getMinutes());
      newSelectedDate.setSeconds(props.modelValue.getSeconds());
      newSelectedDate.setMilliseconds(props.modelValue.getMilliseconds());
    }
    emit('date-selected', newSelectedDate);
  }
};

const getDayAriaLabel = (day) => {
  const date = new Date(displayDate.value);
  date.setDate(day);
  return `Select ${date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })}`;
};

let timerInterval = null;

const handleOutsideClick = (event) => {
  if (props.inline) return; // TimePicker will handle its own outside click
  if (datePickerRoot.value && !datePickerRoot.value.contains(event.target)) {
    emit('close');
  }
};

onMounted(() => {
  document.addEventListener('mousedown', handleOutsideClick);
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleOutsideClick);
  if (timerInterval) {
    clearInterval(timerInterval);
  }
});

watch(liveTrack, (currentTrack) => {
  // If there is a running track (no end_time)
  if (currentTrack && !currentTrack.end_time) {
    // and the interval isn't already running, start it.
    if (!timerInterval) {
      timerInterval = setInterval(() => {
        now.value = new Date();
      }, 1000);
    }
  } else {
    // If there is no running track, ensure the interval is cleared.
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }
}, { immediate: true });

watch(() => props.modelValue, (newDate) => {
  if (newDate) {
    // Sync the calendar view to the new date's month and year.
    displayDate.value = new Date(newDate);
  }
});

const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
</script>
