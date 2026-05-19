<template>
  <div ref="timePickerRoot" class="absolute z-50 mt-2 flex bg-gray-900 border border-gray-700
               rounded-lg shadow-xl overflow-hidden">

    <!-- Left Sidebar Shortcuts -->
    <div class="w-36 bg-gray-800 border-r border-gray-700 flex flex-col py-2 overflow-y-auto max-h-96">
      <template v-if="callerType === 'timer'">
        <button @click="selectShortcut('today')" :class="shortcutClass('today')">Today</button>
        <button @click="selectShortcut('yesterday')" :class="shortcutClass('yesterday')">Yesterday</button>
        <button @click="selectShortcut('thisWeek')" :class="shortcutClass('thisWeek')">This week</button>
        <button @click="selectShortcut('lastWeek')" :class="shortcutClass('lastWeek')">Last week</button>
      </template>
      <template v-else>
        <button @click="selectShortcut('thisWeek')" :class="shortcutClass('thisWeek')">This week</button>
        <button @click="selectShortcut('lastWeek')" :class="shortcutClass('lastWeek')">Last week</button>
        <button @click="selectShortcut('thisMonth')" :class="shortcutClass('thisMonth')">This month</button>
        <button @click="selectShortcut('lastMonth')" :class="shortcutClass('lastMonth')">Last month</button>
        <button @click="selectShortcut('thisQuarter')" :class="shortcutClass('thisQuarter')">This quarter</button>
        <button @click="selectShortcut('prev90Days')" :class="shortcutClass('prev90Days')">Prev 90 days</button>
        <button @click="selectShortcut('thisYear')" :class="shortcutClass('thisYear')">This year</button>
        <button @click="selectShortcut('lastYear')" :class="shortcutClass('lastYear')">Last year</button>
      </template>
    </div>

    <!-- Right Calendar -->
    <div class="p-0">
      <DatePicker :modelValue="modelValue" :viewType="viewType" :showTimeInputs="false" :inline="true"
        :mode="callerType === 'report' ? 'range' : 'single'" :rangeStart="rangeStart" :rangeEnd="rangeEnd"
        @date-selected="onDateSelected" @range-selected="onRangeSelected" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import DatePicker from './DatePicker.vue';

const store = useStore();

const props = defineProps({
  modelValue: {
    type: Date,
    required: true
  },
  viewType: {
    type: String,
    default: 'day'
  },
  callerType: {
    type: String,
    default: 'timer'
  },
  rangeStart: {
    type: Date,
    default: null
  },
  rangeEnd: {
    type: Date,
    default: null
  }

});

const emit = defineEmits(['set-date', 'set-range', 'close']);
const timePickerRoot = ref(null);

const handleOutsideClick = (event) => {
  if (timePickerRoot.value && !timePickerRoot.value.contains(event.target)) {
    emit('close');
  }
};

onMounted(() => {
  document.addEventListener('mousedown', handleOutsideClick);
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleOutsideClick);
});

// emit only the date as the uiStore will handle the week
// computation from the date
const onDateSelected = (date) => {
  emit('set-date', { date, viewType: props.viewType });
  emit('close');
};

const onRangeSelected = ({ start, end }) => {
  emit('set-range', {
    startDate: start, endDate: end,
    apiEndDate: new Date(end.getTime() + 1),
    type: 'custom'
  });
  emit('close');
};

const selectShortcut = (shortcut) => {
  const range = store.getters['ui/getShortcutRange'](shortcut);

  if (props.callerType === 'timer') {
    emit('set-date', { date: range.startDate, viewType: range.type });
  } else {
    console.log("inside selectShortcut of time picker", range, shortcut);
    emit('set-range', range);
  }
  emit('close');
};

const isActiveShortcut = (shortcut) => {
  if (props.callerType === 'report') {
    return false;
  }

  const now = new Date();
  const d = props.modelValue;

  const isSameDay = (d1, d2) =>
    d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate();

  const isSameWeek = (d1, d2) => {
    const start1 = new Date(
      d1.getFullYear(), d1.getMonth(), d1.getDate() - d1.getDay()
    );
    const start2 = new Date(
      d2.getFullYear(), d2.getMonth(), d2.getDate() - d2.getDay()
    );
    return start1.getTime() === start2.getTime();
  };

  if (shortcut === 'today') {
    return props.viewType === 'day' && isSameDay(d, now);
  }
  if (shortcut === 'yesterday') {
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    return props.viewType === 'day' && isSameDay(d, yesterday);
  }
  if (shortcut === 'thisWeek') {
    return props.viewType === 'week' && isSameWeek(d, now);
  }
  if (shortcut === 'lastWeek') {
    const lastWeek = new Date(now);
    lastWeek.setDate(lastWeek.getDate() - 7);
    return props.viewType === 'week' && isSameWeek(d, lastWeek);
  }
  return false;
};

const shortcutClass = (shortcut) => {
  const base = 'text-left px-4 py-2 text-sm transition-colors m-1 rounded-md';
  if (isActiveShortcut(shortcut)) {
    return `${base} bg-blue-900/40 text-blue-400 font-medium`;
  }
  return `${base} text-gray-300 hover:bg-gray-700 hover:text-white`;
};
</script>
