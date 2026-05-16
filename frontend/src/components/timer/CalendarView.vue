<template>
  <div class="flex bg-black text-gray-300 calendar-grid-container" :style="calendarStyle">
    <!-- Time Axis: Padded to align with the new header -->
    <div class="w-16 flex-shrink-0 pt-10">
      <div v-for="hour in 24" :key="hour" class="relative h-[var(--hour-height)] text-right pr-2 text-xs text-gray-300">

        <!-- 00 minute mark -->
        <span class="absolute top-0 right-2 -translate-y-1/2 bg-black px-1 z-10 font-medium">
          {{ formatTimeLabel(hour - 1, 0) }}
        </span>

        <!-- 15 minute mark -->
        <span v-if="showQuarterHours"
          class="absolute top-[25%] right-2 -translate-y-1/2 bg-black px-1 z-10 text-gray-400">
          {{ formatTimeLabel(hour - 1, 15) }}
        </span>

        <!-- 30 minute mark -->
        <span v-if="showHalfHours" class="absolute top-[50%] right-2 -translate-y-1/2 bg-black px-1 z-10 text-gray-400">
          {{ formatTimeLabel(hour - 1, 30) }}
        </span>

        <!-- 45 minute mark -->
        <span v-if="showQuarterHours"
          class="absolute top-[75%] right-2 -translate-y-1/2 bg-black px-1 z-10 text-gray-400">
          {{ formatTimeLabel(hour - 1, 45) }}
        </span>
      </div>
    </div>

    <!-- Main Content Area: Contains Header and Grid -->
    <div class="flex-grow flex flex-col">
      <!-- Header: Renders day names and dates -->
      <div class="flex h-10 border-b border-gray-700 sticky top-0 z-20 bg-black items-center px-4">
        <!-- Today Tracker (Left) -->
        <div class="w-32 text-gray-400 font-mono text-sm font-bold">
          {{ formattedTodayTotal }}
        </div>

        <!-- Day Names (Centered) -->
        <div class="flex-grow flex">
          <div v-for="day in daysInView" :key="day.getTime()" class="flex-1 text-center">
            <div class="text-xs text-blue-400">{{ getDayName(day) }}</div>
            <div class="text-lg font-bold" :class="{ 'text-blue-400': isToday(day) }">
              {{ day.getDate() }}
            </div>
          </div>
        </div>

        <!-- Right Spacer -->
        <div class="w-32"></div>
      </div>


      <!-- Grid: Container for all day columns -->
      <div ref="gridRef" class="relative flex-grow flex" @mousedown="handleGridMouseDown">
        <!-- Day Columns: Each column has padding for track spacing -->
        <div v-for="day in daysInView" :key="day.getTime()" class="relative flex-1 border-l border-gray-700 px-1">
          <!-- Background Grid Lines for each column -->
          <div v-for="hour in 24" :key="hour" class="relative h-[var(--hour-height)] flex flex-col">
            <template v-if="showQuarterHours">
              <div class="flex-1 border-b border-dashed border-gray-700/70"></div>
              <div class="flex-1 border-b border-dashed border-gray-700"></div>
              <div class="flex-1 border-b border-dashed border-gray-700/70"></div>
              <div class="flex-1 border-b border-gray-700"></div>
            </template>
            <template v-else-if="showHalfHours">
              <div class="flex-1 border-b border-dashed border-gray-700"></div>
              <div class="flex-1 border-b border-gray-700"></div>
            </template>
            <template v-else>
              <div class="flex-1 border-b border-gray-700"></div>
            </template>
          </div>

          <TimeTrackBlock v-for="track in tracksByDay.get(formatDateKey(day)) || []"
            :key="track.id + '-' + track._segmentStart.getTime()" :track="track" :top="timeToY(track._segmentStart)"
            :height="calculateHeight(track._segmentStart, track._segmentEnd)" :left="track.uiLeft"
            :width="track.uiWidth"
            :is-moving="(isMovingTrack && movingTrackId === track.id) || (isResizing && resizingTrackSnapshot?.id === track.id)"
            @track-mousedown="handleTrackMouseDown" @resize-mousedown="handleResizeMouseDown" />
        </div>

        <!-- Current Time Indicator -->
        <CurrentTimeIndicator v-if="currentTime && todayColumnIndex !== -1" :top="timeToY(currentTime)"
          :style="currentTimeIndicatorStyle" />

        <!-- New Entry Dragging Visual -->
        <div v-if="isDragging" class="absolute bg-white/20 rounded-lg pointer-events-none" :style="newEntryStyle"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useStore } from 'vuex';
import TimeTrackBlock from './TimeTrackBlock.vue';
import CurrentTimeIndicator from './CurrentTimeIndicator.vue';


// --- Store ---
const store = useStore();
const hourHeight = computed(() => store.getters['ui/getHourHeight']);
const currentDate = computed(() => store.getters['ui/getCurrentDate']);
const viewType = computed(() => store.getters['ui/getViewType']);

const currentTime = ref(new Date());
const emit = defineEmits(['request-create-track', 'select-track', 'update-track-times']);

// --- Lifecycle Hooks ---
let timeUpdateInterval = null;

onMounted(() => {
  // Update currentTime every 3 seconds
  timeUpdateInterval = setInterval(() => {
    currentTime.value = new Date();
  }, 3000);
});

onUnmounted(() => {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
  }
});

// --- Constants ---
const GRID_RESOLUTION_MINUTES = 15;
const SNAP_MINUTES = 1;
const MIN_DURATION_MINUTES = 5;

// --- State ---
const gridRef = ref(null);
const gridBounds = ref(null);
const pixelsPerMinute = ref(0);

// Drag Creation State
const isDragging = ref(false);
const dragStartCoords = ref({ x: 0, y: 0 });
const dragCurrentCoords = ref({ x: 0, y: 0 });
const dragStartDayIndex = ref(0);

// Move Track State
const isMovingTrack = ref(false);
const movingTrackId = ref(null);
const movingTrackSnapshot = ref(null);
const moveStartParams = ref(null);

// Resize Track
const isResizing = ref(false);
const resizingTrackSnapshot = ref(null);
const resizingEdge = ref(null); // 'start' or 'end'
const resizeStartParams = ref(null);


watch(hourHeight, (newHeight) => {
  if (newHeight > 0) {
    pixelsPerMinute.value = newHeight / 60;
  }
}, { immediate: true });

// --- Computed Properties ---
const daysInView = computed(() => {
  const date = new Date(currentDate.value);
  if (viewType.value === 'day') {
    return [date];
  }
  const week = store.getters['ui/getWeek'];
  return week;
});

const showHalfHours = computed(() => hourHeight.value >= 72);
const showQuarterHours = computed(() => hourHeight.value >= 144);

// --- Layout Algorithm ---
const computeDayLayout = (tracks, currentT, maxWidthPct) => {
  if (!tracks.length) return [];

  tracks.sort((a, b) => {
    const startA = a._segmentStart.getTime();
    const startB = b._segmentStart.getTime();
    if (startA !== startB) return startA - startB;
    const endA = a._segmentEnd.getTime();
    const endB = b._segmentEnd.getTime();
    return (endB - startB) - (endA - startA);
  });

  const processed = tracks.map(t => ({
    ...t,
    _start: t._segmentStart.getTime(),
    _end: t._segmentEnd.getTime(),
    _col: 0
  }));

  // Cluster Detection & Column Packing
  let cluster = [];
  let clusterEnd = 0;

  const layoutCluster = (group) => {
    if (!group.length) return;
    const columns = [];
    group.forEach(track => {
      let placed = false;
      // Try to place in an existing column
      for (let i = 0; i < columns.length; i++) {
        if (columns[i] <= track._start) {
          columns[i] = track._end;
          track._col = i;
          placed = true;
          break;
        }
      }
      // If no fit, create a new column
      if (!placed) {
        columns.push(track._end);
        track._col = columns.length - 1;
      }
    });
    const widthPct = maxWidthPct / columns.length;
    group.forEach(track => {
      track.uiLeft = `${track._col * widthPct}%`;
      track.uiWidth = `calc(${widthPct}% - 1px)`;
    });
  };

  for (const track of processed) {
    // If this track starts after the current cluster ends, the cluster is done.
    if (cluster.length > 0 && track._start >= clusterEnd) {
      layoutCluster(cluster);
      cluster = [];
      clusterEnd = 0;
    }
    cluster.push(track);
    if (track._end > clusterEnd) clusterEnd = track._end;
  }
  layoutCluster(cluster);
  return processed;
};

// Merges store tracks with active drag/resize snapshots for seamless layout
const tracksByDay = computed(() => {
  const map = new Map();
  daysInView.value.forEach(day => { map.set(formatDateKey(day), []); });
  console.log("inside tracksByDay", daysInView.value)

  const allTracks = { ...store.state.time.timeTracks };

  if (isResizing.value && resizingTrackSnapshot.value) {
    allTracks[resizingTrackSnapshot.value.id] = resizingTrackSnapshot.value;
  } else if (isMovingTrack.value && movingTrackSnapshot.value) {
    allTracks[movingTrackSnapshot.value.id] = movingTrackSnapshot.value;
  }

  const hydrate = store.getters['time/hydrateTrack'];
  const currentT = currentTime.value;


  // Group, Hydrate, and Split Multi-day Tracks
  Object.values(allTracks).forEach(track => {
    if (!track.start_time) return;
    const hydratedTrack = hydrate(track);

    const start = new Date(track.start_time);
    const end = track.end_time ? new Date(track.end_time) : currentT;

    // Fast-path for zero duration
    if (start.getTime() === end.getTime()) {
      const key = formatDateKey(start);
      if (map.has(key)) {
        map.get(key).push({
          ...hydratedTrack,
          _segmentStart: start,
          _segmentEnd: end
        });
      }
      return;
    }

    let currentStart = new Date(start);
    while (currentStart < end) {
      const key = formatDateKey(currentStart);

      const nextDay = new Date(currentStart);
      nextDay.setDate(nextDay.getDate() + 1);
      nextDay.setHours(0, 0, 0, 0);

      const currentEnd = end < nextDay ? end : nextDay;

      if (map.has(key)) {
        map.get(key).push({
          ...hydratedTrack,
          _segmentStart: currentStart,
          _segmentEnd: currentEnd
        });
      }

      currentStart = nextDay;
    }
  });


  const isSingleDay = daysInView.value.length === 1;
  const maxWidthPct = isSingleDay ? 90 : 100;

  map.forEach((tracks, key) => {
    map.set(key, computeDayLayout(tracks, currentT, maxWidthPct));
  });
  return map;
});

const todayColumnIndex = computed(() => {
  const todayKey = formatDateKey(new Date());
  return daysInView.value.findIndex(day => formatDateKey(day) === todayKey);
});

const dayColumnWidth = computed(() => {
  if (!gridRef.value || daysInView.value.length === 0) return 0;
  return gridRef.value.clientWidth / daysInView.value.length;
});

const currentTimeIndicatorStyle = computed(() => {
  if (todayColumnIndex.value === -1 || !dayColumnWidth.value) return {};
  return {
    left: `${todayColumnIndex.value * dayColumnWidth.value}px`,
    width: `${dayColumnWidth.value}px`,
  };
});

const newEntryStyle = computed(() => {
  if (!isDragging.value || !dayColumnWidth.value) return {};
  const startY = Math.min(dragStartCoords.value.y, dragCurrentCoords.value.y);
  const endY = Math.max(dragStartCoords.value.y, dragCurrentCoords.value.y);
  const left = dragStartDayIndex.value * dayColumnWidth.value;

  return {
    top: `${startY}px`,
    height: `${endY - startY}px`,
    left: `${left}px`,
    width: `calc(${dayColumnWidth.value}px - 2px)`,
  };
});

const formattedTodayTotal = computed(() => {
  const s = store.getters['time/dailyTotalDuration'](currentDate.value, currentTime.value);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
});

// --- Methods ---
const formatDateKey = (date) => {
  const d = new Date(date);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Formats the time label dynamically based on the current zoom level
const formatTimeLabel = (hour, minute) => {
  const h = hour === 0 ? 12 : (hour > 12 ? hour - 12 : hour);
  const ampm = hour < 12 ? 'AM' : 'PM';

  if (minute === 0) {
    if (showHalfHours.value) {
      return `${h}:00 ${ampm}`;
    }
    return `${h} ${ampm}`;
  }

  return `${h}:${minute} ${ampm}`;
};


const getDayName = (date) => {
  return date.toLocaleDateString('ja-JP', { weekday: 'short' }).toUpperCase();
};

const isToday = (date) => {
  return formatDateKey(date) === formatDateKey(new Date());
};

const timeToY = (time) => {
  if (!pixelsPerMinute.value) return 0;
  const date = new Date(time);
  const minutes = date.getHours() * 60 + date.getMinutes();
  return minutes * pixelsPerMinute.value;
};

const calculateHeight = (start, end) => {
  if (!pixelsPerMinute.value) return 0;
  const startDate = new Date(start);
  const endDate = end ? new Date(end) : currentTime.value;
  const durationMinutes = (endDate - startDate) / (1000 * 60);
  return durationMinutes * pixelsPerMinute.value;
};

const yToTime = (y, selectedDate) => {
  if (!pixelsPerMinute.value) return new Date(this.currentDate);
  let minutes = y / pixelsPerMinute.value;
  minutes = Math.round(minutes / GRID_RESOLUTION_MINUTES) *
    GRID_RESOLUTION_MINUTES;

  const newDate = new Date(selectedDate);
  newDate.setHours(Math.floor(minutes / 60), minutes % 60, 0, 0);
  return newDate;
};

// --- Event Handlers: Drag to Create ---
const handleGridMouseDown = (event) => {
  console.log('--- handleGridMouseDown FIRED ---');
  // Prevent starting a drag on right-click
  if (event.button !== 0) return;

  gridBounds.value = gridRef.value?.getBoundingClientRect() ?? null;
  if (!gridBounds.value || !dayColumnWidth.value) return;

  isDragging.value = true;
  const x = event.clientX - gridBounds.value.left;
  const y = event.clientY - gridBounds.value.top;

  dragStartCoords.value = { x, y };
  dragCurrentCoords.value = { x, y };
  // Determine and store the day index at the beginning of the drag.
  dragStartDayIndex.value = Math.floor(x / dayColumnWidth.value);

  if (dragStartDayIndex.value >= daysInView.value.length) {
    dragStartDayIndex.value = Math.max(0, daysInView.value.length - 1);
  }

  window.addEventListener('mousemove', handleGridMouseMove);
  window.addEventListener('mouseup', handleGridMouseUp);
};

const handleGridMouseMove = (event) => {
  if (!isDragging.value || !gridBounds.value) return;
  dragCurrentCoords.value = {
    x: event.clientX - gridBounds.value.left,
    y: event.clientY - gridBounds.value.top,
  };
};

const handleGridMouseUp = (event) => {
  console.log('--- handleMouseUp FIRED ---');
  window.removeEventListener('mousemove', handleGridMouseMove);
  window.removeEventListener('mouseup', handleGridMouseUp);

  if (!isDragging.value || !gridBounds.value) return;
  isDragging.value = false;

  const finalY = event.clientY - gridBounds.value.top;
  const startY = Math.min(dragStartCoords.value.y, finalY);
  const endY = Math.max(dragStartCoords.value.y, finalY);

  if (Math.abs(endY - startY) < 5) return; // Ignore simple clicks

  const selectedDate = daysInView.value[dragStartDayIndex.value];
  if (!selectedDate) return;

  const startTime = yToTime(startY, selectedDate);
  const endTime = yToTime(endY, selectedDate);

  if (endTime > startTime) emit('request-create-track', { start_time: startTime, end_time: endTime });
};

// --- Event Handlers: Drag to Move ---
const handleTrackMouseDown = (e, track) => {
  isMovingTrack.value = true;
  movingTrackId.value = track.id;
  movingTrackSnapshot.value = { ...track };

  gridBounds.value = gridRef.value?.getBoundingClientRect() ?? null;

  moveStartParams.value = {
    x: e.clientX,
    y: e.clientY,
    startTime: new Date(track.start_time).getTime(),
    // Explicitly preserves null. It does NOT fallback to currentTime.
    endTime: track.end_time ? new Date(track.end_time).getTime() : null,
  };

  window.addEventListener('mousemove', handleTrackMouseMove);
  window.addEventListener('mouseup', handleTrackMouseUp);
};

const handleTrackMouseMove = (e) => {
  if (!isMovingTrack.value) return;

  const deltaY = e.clientY - moveStartParams.value.y;
  const deltaMinutes = deltaY / pixelsPerMinute.value;

  // This preserves the original offset (e.g. 12:22 -> 12:27)
  const snappedDeltaMinutes = Math.round(deltaMinutes / SNAP_MINUTES) * SNAP_MINUTES;

  // Horizontal Drag (Day changing)
  let dayDelta = 0;
  if (gridBounds.value && dayColumnWidth.value && daysInView.value.length > 1) {
    const startX = moveStartParams.value.x - gridBounds.value.left;
    const currentX = e.clientX - gridBounds.value.left;

    const startCol = Math.floor(startX / dayColumnWidth.value);
    const currentCol = Math.floor(currentX / dayColumnWidth.value);

    const clampedStartCol = Math.max(0, Math.min(daysInView.value.length - 1, startCol));
    const clampedCurrentCol = Math.max(0, Math.min(daysInView.value.length - 1, currentCol));

    dayDelta = clampedCurrentCol - clampedStartCol;
  }

  const totalDeltaMs = (snappedDeltaMinutes * 60000) + (dayDelta * 24 * 60 * 60 * 1000);

  const newStart = new Date(moveStartParams.value.startTime + totalDeltaMs);
  movingTrackSnapshot.value.start_time = newStart.toISOString();

  if (moveStartParams.value.endTime) {
    const newEnd = new Date(moveStartParams.value.endTime + totalDeltaMs);
    movingTrackSnapshot.value.end_time = newEnd.toISOString();
  }

};

const handleTrackMouseUp = (e) => {
  window.removeEventListener('mousemove', handleTrackMouseMove);
  window.removeEventListener('mouseup', handleTrackMouseUp);
  console.log("Inside handleTrackMouseUp", movingTrackSnapshot.value)
  if (!isMovingTrack.value) return;

  const distY = Math.abs(e.clientY - moveStartParams.value.y);
  const distX = Math.abs(e.clientX - moveStartParams.value.x);
  const wasDrag = distY > 5 || distX > 5;

  if (wasDrag) {
    // this event calls directly the update tracks
    emit('update-track-times', movingTrackSnapshot.value);
  } else {
    // this event opens the edit entry modal
    emit('select-track', movingTrackSnapshot.value);
  }

  isMovingTrack.value = false;
  movingTrackId.value = null;
  movingTrackSnapshot.value = null;
};

// --- Drag to Resize ---
const handleResizeMouseDown = (e, track, edge) => {
  isResizing.value = true;
  resizingEdge.value = edge;
  resizingTrackSnapshot.value = { ...track };

  const effectiveEndTime = track.end_time
    ? new Date(track.end_time).getTime()
    : currentTime.value.getTime();

  resizeStartParams.value = {
    y: e.clientY,
    startTime: new Date(track.start_time).getTime(),
    endTime: effectiveEndTime,
    isLive: !track.end_time
  };

  window.addEventListener('mousemove', handleResizeMouseMove);
  window.addEventListener('mouseup', handleResizeMouseUp);
};

const handleResizeMouseMove = (e) => {
  if (!isResizing.value) return;

  const deltaY = e.clientY - resizeStartParams.value.y;
  const deltaMinutes = deltaY / pixelsPerMinute.value;
  const snappedDeltaMinutes = Math.round(deltaMinutes / SNAP_MINUTES) * SNAP_MINUTES;
  const deltaMs = snappedDeltaMinutes * 60000;
  const minDurationMs = MIN_DURATION_MINUTES * 60000;

  if (resizingEdge.value === 'start') {
    let newStart = resizeStartParams.value.startTime + deltaMs;

    const maxStart = resizeStartParams.value.endTime - minDurationMs;
    if (newStart > maxStart) newStart = maxStart;

    if (resizeStartParams.value.isLive && newStart > currentTime.value.getTime()) {
      newStart = currentTime.value.getTime();
    }

    resizingTrackSnapshot.value.start_time = new Date(newStart).toISOString();

  } else {
    let newEnd = resizeStartParams.value.endTime + deltaMs;

    const minEnd = resizeStartParams.value.startTime + minDurationMs;
    if (newEnd < minEnd) newEnd = minEnd;

    // TODO: don't allow live tracks end time to be changed, if the user wants to
    // modify the end time, first stop it and then updated it
    resizingTrackSnapshot.value.end_time = new Date(newEnd).toISOString();
  }
};

const handleResizeMouseUp = (e) => {
  window.removeEventListener('mousemove', handleResizeMouseMove);
  window.removeEventListener('mouseup', handleResizeMouseUp);
  if (!isResizing.value) return;

  if (resizeStartParams.value.isLive) {
    resizingTrackSnapshot.value.end_time = null;
  }

  emit('update-track-times', resizingTrackSnapshot.value);

  isResizing.value = false;
  resizingTrackSnapshot.value = null;
  resizeStartParams.value = null;
  resizingEdge.value = null;
};


const calendarStyle = computed(() => ({
  '--hour-height': `${hourHeight.value}px`,
  '--half-hour-height': `${hourHeight.value / 2}px`,
  '--quarter-hour-height': `${hourHeight.value / 4}px`,
}));
</script>

<style scoped>
.calendar-grid-container {
  --hour-height: 48px;
  --half-hour-height: calc(var(--hour-height) / 2);
  --quarter-hour-height: calc(var(--hour-height) / 4);
}
</style>
