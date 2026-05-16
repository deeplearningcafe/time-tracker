<template>
  <div
    class="flex flex-col md:flex-row items-center justify-between p-4 bg-gray-900 border-b border-gray-800 gap-4 sticky top-0 z-10">
    <!-- Date Navigation Control -->
    <div class="flex items-center border border-gray-600 rounded-md
                text-sm font-medium text-gray-300 relative">
      <button @click="$emit('range-change', -1)" class="p-2 hover:bg-gray-800 rounded-l-md transition-colors
                    focus:outline-none focus-visible:ring-2
                    focus-visible:ring-blue-500
                    focus-visible:ring-offset-2
                    focus-visible:ring-offset-black" aria-label="Previous period">
        &lt;
      </button>

      <div @click="toggleTimePicker" class="px-4 py-2 border-l border-r border-gray-600
                    cursor-pointer hover:bg-gray-800 transition-colors
                    focus:outline-none focus-visible:ring-2
                    focus-visible:ring-blue-500
                    focus-visible:ring-offset-2
                    focus-visible:ring-offset-black">
        <span>{{ formattedRange }}</span>
      </div>

      <button @click="$emit('range-change', 1)" class="p-2 hover:bg-gray-800 rounded-r-md transition-colors
                    focus:outline-none focus-visible:ring-2
                    focus-visible:ring-blue-500
                    focus-visible:ring-offset-2
                    focus-visible:ring-offset-black" aria-label="Next period">
        &gt;
      </button>

      <TimePicker v-if="isTimePickerVisible" :modelValue="currentDate" :rangeStart="props.dateRange.startDate"
        :rangeEnd="props.dateRange.endDate" callerType="report" class="top-full left-0" @set-range="handleSetRange"
        @close="isTimePickerVisible = false" />
    </div>

    <!-- Filters -->
    <div class="flex flex-col sm:flex-row items-center space-y-2 sm:space-y-0 sm:space-x-3 w-full md:w-auto">
      <div class="relative w-full sm:w-48">
        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
        </span>
        <input v-model="searchText" type="text" placeholder="Filter description..."
          class="bg-black text-sm text-gray-200 pl-10 pr-3 py-2 rounded border border-gray-800 focus:outline-none focus:border-blue-500 w-full transition-colors placeholder-gray-600"
          @input="emitFilters" />
      </div>

      <div class="relative w-full sm:w-48">
        <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z">
            </path>
          </svg>
        </span>
        <input v-model="projectText" type="text" placeholder="Filter project..."
          class="bg-black text-sm text-gray-200 pl-10 pr-3 py-2 rounded border border-gray-800 focus:outline-none focus:border-blue-500 w-full transition-colors placeholder-gray-600"
          @input="emitFilters" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useStore } from 'vuex';
import TimePicker from '../common/TimePicker.vue';

const props = defineProps({
  dateRange: { type: Object, required: true },
});

const emit = defineEmits(['range-change', 'filter-change', 'set-range']);

const store = useStore();
const searchText = ref('');
const projectText = ref('');
const isTimePickerVisible = ref(false);

const currentDate = computed(() => store.state.ui.currentDate);

const formattedRange = computed(() => {
  const start = props.dateRange.startDate;
  const end = props.dateRange.endDate;
  const type = props.dateRange.type;

  if (type === 'month') {
    return start.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  } else if (type === 'year') {
    return start.getFullYear().toString();
  } else if (type === 'quarter') {
    const q = Math.floor(start.getMonth() / 3) + 1;
    return `Q${q} ${start.getFullYear()}`;
  }

  const startMonth = start.toLocaleDateString(undefined, { month: 'short' });
  const endMonth = end.toLocaleDateString(undefined, { month: 'short' });
  if (startMonth === endMonth) {
    return `${startMonth} ${start.getDate()} – ${end.getDate()}, ${end.getFullYear()}`;
  }
  return `${startMonth} ${start.getDate()} – ${endMonth} ${end.getDate()}, ${end.getFullYear()}`;

});

const toggleTimePicker = () => {
  isTimePickerVisible.value = !isTimePickerVisible.value;
};
const handleSetRange = (date) => {
  emit('set-range', date);
};
const emitFilters = () => {
  emit('filter-change', {
    text: searchText.value,
    project: projectText.value || null
  });
};
</script>
