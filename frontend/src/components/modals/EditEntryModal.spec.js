import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createStore } from 'vuex';
import EditEntryModal from './EditEntryModal.vue';

// 1. Mock the composable used in setup()
vi.mock('../composables/useProjectCreation', () => ({
  useProjectCreation: () => ({
    isProjectModalVisible: { value: false },
    isSaving: { value: false },
    creationError: { value: null },
    openProjectModal: vi.fn(),
    saveNewProject: vi.fn(),
  })
}));

// 2. Stub for ProjectSelector
const ProjectSelectorStub = {
  template: '<div data-testid="project-selector-stub"></div>',
  props: ['modelValue'],
  emits: ['update:modelValue', 'create-new-project'],
};

// 3. Stub for ProjectCreationModal
const ProjectCreationModalStub = {
  template: '<div data-testid="project-creation-modal-stub"></div>',
  props: ['isVisible', 'isSaving', 'error'],
};

const MOCK_PROJECTS = [
  { id: 1, title: 'Project Alpha', color: '#ff0000' },
  { id: 2, title: 'Project Beta', color: '#00ff00' },
];

const MOCK_RECENT_ENTRIES = [
  { id: 10, name: 'Recent Task 1', project: 1 },
  { id: 11, name: 'Recent Task 2', project: 2 },
];

// Normalized state for lookups
const MOCK_TIME_ENTRIES = {
  10: { id: 10, name: 'Recent Task 1', project: 1 },
  11: { id: 11, name: 'Recent Task 2', project: 2 },
  101: { id: 101, name: 'Existing Task', project: 1 },
};

const INITIAL_TIMES = {
  start_time: new Date('2025-10-01T09:00:00Z'),
  end_time: new Date('2025-10-01T10:00:00Z'),
};

const MOCK_TRACK = {
  id: 101,
  time_entry: 101,
  start_time: '2025-10-02T14:00:00Z',
  end_time: '2025-10-02T15:30:00Z',
};

// --- Store Factory ---

const createMockStore = () => {
  return createStore({
    modules: {
      time: {
        namespaced: true,
        getters: {
          getAllProjects: () => MOCK_PROJECTS,
          getRecentTimeEntries: () => MOCK_RECENT_ENTRIES,
          getProjectById: () => (id) => MOCK_PROJECTS.find(p => p.id === id),
          getTimeEntryById: () => (id) => MOCK_TIME_ENTRIES[id],
        },
        actions: {
          fetchProjects: vi.fn(),
        },
      },
    },
  });
};

const mountComponent = (props, store) => {
  return mount(EditEntryModal, {
    props,
    global: {
      plugins: [store],
      stubs: {
        ProjectSelector: ProjectSelectorStub,
        ProjectCreationModal: ProjectCreationModalStub,
      },
    },
  });
};


describe('EditEntryModal.vue', () => {
  let store;

  beforeEach(() => {
    store = createMockStore();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('General Rendering', () => {
    it('does not render when isVisible is false', () => {
      const wrapper = mountComponent({ isVisible: false }, store);
      expect(wrapper.find('[data-testid="modal-overlay"]').exists()).toBe(false);
    });

    it('renders when isVisible is true', () => {
      const wrapper = mountComponent({ isVisible: true }, store);
      expect(wrapper.find('[data-testid="modal-overlay"]').exists()).toBe(true);
    });

    it('emits a "close" when close button is clicked', async () => {
      const wrapper = mountComponent({ isVisible: true }, store);
      await wrapper.find('[data-testid="close-button"]').trigger('click');
      expect(wrapper.emitted()).toHaveProperty('close');
    });
  });

  describe('Create Mode', () => {
    let wrapper;
    beforeEach(() => {
      wrapper = mountComponent({
        isVisible: true,
        track: null,
        initialTimes: INITIAL_TIMES,
      }, store);
    });

    it('initializes with blank form and correct title', () => {
      expect(wrapper.find('[data-testid="modal-title"]').text()).toBe('Create Time Entry');
      expect(wrapper.find('[data-testid="description-input"]').element.value).toBe('');
      // Delete button should not exist in create mode
      expect(wrapper.find('[data-testid="delete-button"]').exists()).toBe(false);
    });

    it('emits a "save" event with new track data', async () => {
      await wrapper.find('[data-testid="description-input"]').setValue('New Task');

      await wrapper.findComponent(ProjectSelectorStub).vm.$emit('update:modelValue', 2);

      await wrapper.find('form').trigger('submit');

      expect(wrapper.emitted('save')).toBeTruthy();
      const payload = wrapper.emitted('save')[0][0];

      expect(payload.name).toBe('New Task');
      expect(payload.project).toBe(2);
      expect(payload.start_time).toEqual(INITIAL_TIMES.start_time);
      expect(payload.end_time).toEqual(INITIAL_TIMES.end_time);

    });
  });

  describe('Edit Mode', () => {
    let wrapper;
    beforeEach(() => {
      wrapper = mountComponent({
        isVisible: true,
        track: MOCK_TRACK,
      }, store);
    });

    it('initializes with existing data and correct title', () => {
      expect(wrapper.find('[data-testid="modal-title"]').text()).toBe('Edit Time Entry');

      expect(wrapper.find('[data-testid="description-input"]').element.value).toBe('Existing Task');

      expect(wrapper.findComponent(ProjectSelectorStub).props('modelValue')).toBe(1);

      expect(wrapper.find('[data-testid="delete-button"]').exists()).toBe(true);
    });

    it('emits a "save" with updated data', async () => {
      await wrapper.find('[data-testid="description-input"]').setValue('Updated Task Name');

      await wrapper.find('form').trigger('submit');

      const payload = wrapper.emitted('save')[0][0];
      expect(payload.id).toBe(MOCK_TRACK.id);
      expect(payload.name).toBe('Updated Task Name');
      // Project should remain 1 as we didn't change it
      expect(payload.project).toBe(1);
    });

    it('emits "delete" when delete button is clicked and confirmed', async () => {
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

      await wrapper.find('[data-testid="delete-button"]').trigger('click');

      expect(confirmSpy).toHaveBeenCalled();
      expect(wrapper.emitted('delete')).toBeTruthy();
      expect(wrapper.emitted('delete')[0][0]).toBe(MOCK_TRACK.id);
    });

    it('does not emit "delete" if cancelled', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);

      await wrapper.find('[data-testid="delete-button"]').trigger('click');

      expect(wrapper.emitted('delete')).toBeFalsy();
    });
  });


  describe('Suggestions Logic', () => {
    let wrapper;
    beforeEach(() => {
      wrapper = mountComponent({
        isVisible: true,
        initialTimes: INITIAL_TIMES,
      }, store);
    });

    it('shows suggestions on input focus', async () => {
      const input = wrapper.find('[data-testid="description-input"]');
      await input.trigger('focus');

      const list = wrapper.find('[data-testid="suggestions-list"]');
      expect(list.exists()).toBe(true);
      expect(list.findAll('li').length).toBe(2); // We have 2 recent entries
    });

    it('filters suggestions by name', async () => {
      const input = wrapper.find('[data-testid="description-input"]');
      await input.trigger('focus');
      await input.setValue('Recent Task 1'); // Matches ID 10

      const list = wrapper.find('[data-testid="suggestions-list"]');
      const items = list.findAll('li');
      expect(items.length).toBe(1);
      expect(items[0].text()).toContain('Recent Task 1');
    });

    it('fills form when a suggestion is selected', async () => {
      const input = wrapper.find('[data-testid="description-input"]');
      await input.trigger('focus');

      const list = wrapper.find('[data-testid="suggestions-list"]');
      await list.findAll('li')[0].trigger('click');

      expect(input.element.value).toBe('Recent Task 1');

      expect(wrapper.findComponent(ProjectSelectorStub).props('modelValue')).toBe(1);

      expect(wrapper.find('[data-testid="suggestions-list"]').exists()).toBe(false);
    });
  });

  describe('Validation Logic', () => {
    let wrapper;
    beforeEach(() => {
      wrapper = mountComponent({
        isVisible: true,
        initialTimes: INITIAL_TIMES,
      }, store);
    });

    it('disables save button if project is not selected', async () => {
      // Description is empty, Project is null
      expect(wrapper.find('[data-testid="save-button"]').attributes('disabled')).toBeDefined();

      await wrapper.find('[data-testid="description-input"]').setValue('Some Task');

      // Still disabled because project is null
      expect(wrapper.find('[data-testid="save-button"]').attributes('disabled')).toBeDefined();
    });

    it('enables save button when all fields are valid', async () => {
      await wrapper.find('[data-testid="description-input"]').setValue('Some Task');
      await wrapper.findComponent(ProjectSelectorStub).vm.$emit('update:modelValue', 1);

      expect(wrapper.find('[data-testid="save-button"]').attributes('disabled')).toBeUndefined();
    });

    it('shows error and prevents save if end time < start time', async () => {
      // Make form otherwise valid
      await wrapper.find('[data-testid="description-input"]').setValue('Some Task');
      await wrapper.findComponent(ProjectSelectorStub).vm.$emit('update:modelValue', 1);

      // Set invalid times
      const startInput = wrapper.find('[data-testid="start-time"]');
      const endInput = wrapper.find('[data-testid="end-time"]');

      // 10:00
      await startInput.setValue('2025-10-01T10:00');
      // 09:00
      await endInput.setValue('2025-10-01T09:00');

      // Try submit
      await wrapper.find('form').trigger('submit');

      expect(wrapper.emitted('save')).toBeFalsy();
      expect(wrapper.find('[data-testid="error-message"]').text()).toContain('End time must be after start time');
    });
  });

  describe('Duration Logic', () => {
    let wrapper;
    beforeEach(() => {
      // MOCK_TRACK has start: 14:00:00Z, end: 15:30:00Z (Duration: 01:30:00)
      wrapper = mountComponent({
        isVisible: true,
        track: MOCK_TRACK,
      }, store);
    });

    it('initializes with the correctly formatted duration', () => {
      const durationInput = wrapper.find('[data-testid="duration-input"]');
      expect(durationInput.element.value).toBe('01:30:00');
    });

    it('updates start_time when duration is changed', async () => {
      const durationInput = wrapper.find('[data-testid="duration-input"]');

      await durationInput.trigger('focus');
      await durationInput.setValue('02:00:00');
      await durationInput.trigger('blur');

      // Submit form to check the emitted payload
      await wrapper.find('form').trigger('submit');
      const payload = wrapper.emitted('save')[0][0];

      // End time is 15:30:00Z, minus 2 hours duration = 13:30:00Z
      expect(payload.start_time).toEqual(new Date('2025-10-02T13:30:00Z'));
      // End time should remain unchanged
      expect(payload.end_time).toEqual(new Date('2025-10-02T15:30:00Z'));
    });

    it('handles overflow parsing correctly', async () => {
      const durationInput = wrapper.find('[data-testid="duration-input"]');

      await durationInput.trigger('focus');
      await durationInput.setValue('00:150:00');
      await durationInput.trigger('blur');

      expect(durationInput.element.value).toBe('02:30:00');

      await wrapper.find('form').trigger('submit');
      const payload = wrapper.emitted('save')[0][0];

      // End time is 15:30:00Z, minus 2h 30m duration = 13:00:00Z
      expect(payload.start_time).toEqual(new Date('2025-10-02T13:00:00Z'));
    });

    it('enforces a minimum duration of 1 minute', async () => {
      const durationInput = wrapper.find('[data-testid="duration-input"]');

      await durationInput.trigger('focus');
      // Set to 10 seconds, which is below the 1 min minimum
      await durationInput.setValue('00:00:10');
      await durationInput.trigger('blur');

      // Visually normalizes to 00:01:00
      expect(durationInput.element.value).toBe('00:01:00');

      await wrapper.find('form').trigger('submit');
      const payload = wrapper.emitted('save')[0][0];

      // End time is 15:30:00Z, minus 1 minute minimum = 15:29:00Z
      expect(payload.start_time).toEqual(new Date('2025-10-02T15:29:00Z'));
    });
  });
});
