import { ref } from 'vue';
import { useStore } from 'vuex';

/**
 * A Vue Composable to manage the state and logic for the project creation modal.
 * This centralizes the logic, making it reusable and keeping components clean.
 *
 * @param {Function} onProjectCreated - An optional callback function that
 * receives the new project and is executed upon successful creation.
 */
export function useProjectCreation(onProjectCreated) {
  const store = useStore();

  const isProjectModalVisible = ref(false);
  const isSaving = ref(false);
  const creationError = ref(null);

  const openProjectModal = () => {
    creationError.value = null;
    isProjectModalVisible.value = true;
  };

  const closeProjectModal = () => {
    isProjectModalVisible.value = false;
  };

  const saveNewProject = async (projectData) => {
    isSaving.value = true;
    creationError.value = null;
    console.log("Inside saveNewProject", projectData)
    try {
      const newProject = await store.dispatch(
        'time/createProject',
        projectData
      );
      if (onProjectCreated) {
        onProjectCreated(newProject);
      }
      closeProjectModal();
    } catch (error) {
      creationError.value =
        error.response?.data?.message || 'A server error occurred.';
    } finally {
      isSaving.value = false;
    }
  };

  return {
    isProjectModalVisible,
    isSaving,
    creationError,
    openProjectModal,
    closeProjectModal,
    saveNewProject,
  };
}
