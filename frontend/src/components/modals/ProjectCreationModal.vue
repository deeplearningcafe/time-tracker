<template>
  <div v-if="isVisible" class="fixed inset-0 bg-black bg-opacity-60 flex items-center
            justify-center z-50" @click.self="close">
    <div class="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md
                mx-4">
      <!-- Modal Header -->
      <header class="flex justify-between items-center pb-4 border-b
                    border-gray-700">
        <h2 class="text-xl font-semibold text-gray-100">
          {{ isEditMode ? 'Edit project' : 'Create new project' }}
        </h2>
        <button @click="close" class="text-gray-400 hover:text-white transition-colors" aria-label="Close modal">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </header>

      <!-- Modal Body (Form) -->
      <form @submit.prevent="handleSave" class="mt-4 space-y-4">
        <div>
          <label for="project-name" class="block text-sm font-medium text-gray-300">
            Project name
          </label>
          <input type="text" id="project-name" v-model="projectName" class="mt-1 block w-full bg-gray-700 border
                            border-gray-600 rounded-md shadow-sm py-2 px-3
                            text-gray-100 focus:ring-blue-500
                            focus:border-blue-500" placeholder="Enter project name" />
        </div>

        <div>
          <label for="project-color" class="block text-sm font-medium text-gray-300">
            Project color
          </label>
          <div class="mt-1 flex items-center gap-3">
            <input type="color" id="project-color" v-model="projectColor" class="w-10 h-10 p-1 bg-gray-700 border
                                border-gray-600 rounded-md cursor-pointer" />
            <span class="font-mono text-gray-400">
              {{ projectColor }}
            </span>
          </div>
        </div>

        <p v-if="error" class="text-sm text-red-400">
          {{ error }}
        </p>

        <!-- Modal Footer -->
        <footer class="flex justify-end items-center pt-4 mt-4
                        border-t border-gray-700 gap-2">
          <button type="button" @click="close" class="px-4 py-2 text-sm font-medium text-gray-200
                            bg-gray-600 rounded-md hover:bg-gray-500
                            transition-colors">
            Cancel
          </button>
          <button type="submit" :disabled="!isFormValid" class="px-4 py-2 text-sm font-medium text-white
                            bg-blue-600 rounded-md hover:bg-blue-700
                            disabled:bg-gray-500
                            disabled:cursor-not-allowed transition-colors">
            {{ isEditMode ? 'Save changes' : 'Create project' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  isVisible: { type: Boolean, default: false },
  isSaving: { type: Boolean, default: false },
  error: { type: String, default: null },
  project: { type: Object, default: null },
});

const emit = defineEmits(['save', 'close']);

const defaultColor = '#4f46e5';

const projectName = ref('');
const projectColor = ref(defaultColor);

const isEditMode = computed(() => !!props.project);
const isFormValid = computed(() => projectName.value.trim() !== '');

function close() {
  emit('close');
}

function handleSave() {
  if (!isFormValid.value) return;
  const payload = {
    title: projectName.value,
    color: projectColor.value.slice(1),
  };

  if (isEditMode.value) {
    payload.id = props.project.id;
  }

  emit('save', payload);
}

watch(() => props.isVisible, (newVal) => {
  if (newVal) {
    if (props.project) {
      projectName.value = props.project.title;
      projectColor.value = '#' + props.project.color;
    } else {
      projectName.value = '';
      projectColor.value = defaultColor;
    }
  }
});
</script>
