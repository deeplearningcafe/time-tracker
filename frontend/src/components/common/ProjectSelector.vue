<template>
  <div class="relative w-48" ref="selectorRoot">
    <button type="button" @click="toggleDropdown" :disabled="disabled" :aria-expanded="isOpen" aria-haspopup="listbox"
      class="flex items-center justify-between w-full px-3 py-2
                bg-gray-700 border border-gray-600 rounded-md text-left
                text-gray-100 focus:outline-none focus:ring-2
                focus:ring-blue-500 disabled:bg-gray-800
                disabled:cursor-not-allowed">
      <span class="flex items-center">
        <span v-if="selectedProject" class="w-3 h-3 rounded-full mr-2" :style="{
          backgroundColor: `#${selectedProject.color}` || '#000000'
        }"></span>
        <span :class="{ 'text-gray-400': !selectedProject }">
          {{ selectedProject ? selectedProject.title : 'No Project' }}
        </span>
      </span>
      <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
      </svg>
    </button>

    <div v-if="isOpen" class="absolute z-40 w-full mt-1 bg-gray-800 rounded-md shadow-lg
                border border-gray-700">
      <div class="p-2">
        <input ref="searchInput" type="text" v-model="searchTerm" @keydown.enter.prevent
          placeholder="Search by project..." class="w-full px-2 py-1 bg-gray-700 border
                        border-gray-600 rounded-md text-gray-100" />
      </div>
      <ul class="py-1 max-h-60 overflow-y-auto" role="listbox" tabindex="-1">
        <li @click="selectProject(null)" role="option" :aria-selected="modelValue === null" class="flex items-center px-4 py-2 text-sm cursor-pointer
                        text-gray-100 hover:bg-blue-600">
          <span class="w-3 h-3 rounded-full mr-2 bg-gray-400"></span>
          No Project
        </li>
        <li v-for="project in filteredProjects" :key="project.id" :ref="(el) => setProjectRef(el, project.id)"
          @click="selectProject(project.id)" role="option" :aria-selected="modelValue === project.id" class="flex items-center px-4 py-2 text-sm cursor-pointer
                        text-gray-100 hover:bg-blue-600">
          <span class="w-3 h-3 rounded-full mr-2" :style="{ backgroundColor: `#${project.color}` || '#000000' }"></span>
          {{ project.title }}
        </li>
      </ul>
      <div class="border-t border-gray-700">
        <button @click="handleCreateNew" class="w-full text-left px-4 py-2 text-sm text-blue-400
                        hover:bg-blue-500/10 hover:text-blue-300
                        transition-colors">
          + Create a new project
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useStore } from 'vuex';

// --- PROPS & EMITS ---

const props = defineProps({
  modelValue: {
    type: [Number, String, null],
    default: null,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:modelValue', 'create-new-project']);

// --- STATE ---

const store = useStore();
const selectorRoot = ref(null);
const searchInput = ref(null);
const isOpen = ref(false);
const searchTerm = ref('');
const projectRefs = ref({});

// --- COMPUTED PROPERTIES ---
const allProjects = computed(() => store.getters['time/getAllProjects']);

/**
 * Finds the full project object based on the v-model ID.
 * NOTE: The `color` property used in the template is a UI enhancement
 * and is not present in the original TDDOC data model. This would
 * need to be added to the `Project` model in the backend.
 */
const selectedProject = computed(() => {
  if (props.modelValue === null) {
    return null;
  }
  return store.getters['time/getProjectById'](props.modelValue);
});

const filteredProjects = computed(() => {
  if (!searchTerm.value) {
    return allProjects.value;
  }
  const lowerCaseSearch = searchTerm.value.toLowerCase();
  return allProjects.value.filter(project =>
    project.title.toLowerCase().includes(lowerCaseSearch)
  );
});

// --- METHODS ---

const setProjectRef = (el, id) => {
  if (el) projectRefs.value[id] = el;
};

const toggleDropdown = async () => {
  if (!props.disabled) {
    isOpen.value = !isOpen.value;
    if (isOpen.value) {
      await nextTick();
      searchInput.value?.focus();

      // Scroll to selected project using the ref map
      if (props.modelValue && projectRefs.value[props.modelValue]) {
        projectRefs.value[props.modelValue].scrollIntoView({ block: 'nearest' });
      }

    }
  }
};

const selectProject = (projectId) => {
  emit('update:modelValue', projectId);
  isOpen.value = false;
  searchTerm.value = '';
};

const handleCreateNew = () => {
  emit('create-new-project');
  isOpen.value = false;
};

const handleClickOutside = (event) => {
  if (selectorRoot.value && !selectorRoot.value.contains(event.target)) {
    isOpen.value = false;
  }
};

// --- LIFECYCLE HOOKS ---

onMounted(() => { document.addEventListener('mousedown', handleClickOutside); });
onUnmounted(() => { document.removeEventListener('mousedown', handleClickOutside); });
</script>
