import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createStore } from 'vuex';
import LiveTimer from './LiveTimer.vue';

// --- Mocks ---

// Mock ProjectSelector with capability to trigger create event
vi.mock('../common/ProjectSelector.vue', () => ({
  default: {
    name: 'ProjectSelector',
    props: ['modelValue', 'disabled'],
    emits: ['update:modelValue', 'create-new-project'],
    template: `
            <select
                :value="modelValue"
                :disabled="disabled"
                @change="$emit('update:modelValue', $event.target.value)"
                data-testid="project-selector"
            >
                <option value="create-new">Create New...</option>
                <option value="1">Project Alpha</option>
                <option value="2">Project Beta</option>
            </select>
        `,
    methods: {
      triggerCreate() {
        this.$emit('create-new-project');
      }
    }
  },
}));

vi.mock('../common/DatePicker.vue', () => ({
  default: {
    name: 'DatePicker',
    props: ['modelValue'],
    emits: ['date-selected', 'close'],
    template: '<div data-testid="date-picker"></div>'
  }
}));

vi.mock('../modals/ProjectCreationModal.vue', () => ({
  default: {
    name: 'ProjectCreationModal',
    props: ['isVisible', 'isSaving', 'error'],
    emits: ['close', 'save'],
    template: '<div v-if="isVisible" data-testid="project-creation-modal"></div>'
  }
}));


// --- Store Factory ---

const createMockStore = (initialState = {}) => {
  const defaultState = {
    liveTrack: null,
    projects: {
      1: { id: 1, title: 'Project Alpha' },
      2: { id: 2, title: 'Project Beta' },
    },
    recentTimeEntries: [],
  };

  const state = { ...defaultState, ...(initialState.state?.time || {}) };

  return createStore({
    modules: {
      time: {
        namespaced: true,
        state,
        getters: {
          getLiveTrack: (s) => s.liveTrack,
          getRecentTimeEntries: (s) => s.recentTimeEntries,
          ...(initialState.getters || {})
        },
        actions: {
          updateTrack: vi.fn(),
          updateTimeEntryProject: vi.fn(),
          createProject: vi.fn(),
          ...(initialState.actions || {})
        },
      },
    },
  });
};


describe('LiveTimer.vue', () => {
  const mountComponent = (store) => {
    return mount(LiveTimer, {
      global: {
        plugins: [store],
      },
    });
  };

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Idle State (No Timer Running)', () => {
    let store;

    beforeEach(() => {
      store = createMockStore({
        state: { time: { liveTrack: null } }
      });
    });

    it('renders correctly with empty inputs', () => {
      const wrapper = mountComponent(store);
      const input = wrapper.find('input[type="text"]');
      const button = wrapper.find('button');
      const selector = wrapper.findComponent({ name: 'ProjectSelector' });

      expect(input.element.value).toBe('');
      expect(input.attributes('placeholder')).toBe('What are you working on?');
      expect(button.text()).toBe('Start');
      expect(button.classes()).toContain('bg-blue-600');
      expect(selector.props('disabled')).toBe(false);
    });

    it('emits "request-start-live-timer" with valid input', async () => {
      const wrapper = mountComponent(store);

      await wrapper.find('input[type="text"]').setValue('New Task');
      await wrapper.findComponent({ name: 'ProjectSelector' }).vm.$emit('update:modelValue', '1');

      await wrapper.find('button').trigger('click');

      expect(wrapper.emitted('request-start-live-timer')).toHaveLength(1);
      expect(wrapper.emitted('request-start-live-timer')[0][0]).toEqual({
        name: 'New Task',
        project: '1'
      });
    });

    it('does NOT emit start event if description is missing', async () => {
      const wrapper = mountComponent(store);

      await wrapper.findComponent({ name: 'ProjectSelector' }).vm.$emit('update:modelValue', '1');
      await wrapper.find('button').trigger('click');

      expect(wrapper.emitted('request-start-live-timer')).toBeFalsy();
    });

    it('does NOT emit start event if project is missing', async () => {
      const wrapper = mountComponent(store);

      await wrapper.find('input[type="text"]').setValue('New Task');
      await wrapper.find('button').trigger('click');

      expect(wrapper.emitted('request-start-live-timer')).toBeFalsy();
    });

    it('opens ProjectCreationModal when ProjectSelector emits create event', async () => {
      const wrapper = mountComponent(store);

      expect(wrapper.find('[data-testid="project-creation-modal"]').exists()).toBe(false);

      const selector = wrapper.findComponent({ name: 'ProjectSelector' });
      selector.vm.triggerCreate();
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="project-creation-modal"]').exists()).toBe(true);
    });
  });

  describe('Running State (Timer Active)', () => {
    let store;
    const startTime = new Date('2025-01-01T10:00:00Z');
    const matchingEntry = {
      id: 50,
      name: 'Active Task',
      project: 1
    };
    const runningTrack = {
      id: 101,
      time_entry: 50,
      start_time: startTime.toISOString(),
      end_time: null,
      project: { id: 1, name: "test project" }
    };

    beforeEach(() => {
      vi.useFakeTimers();
      // Set system time to 5 seconds after start
      vi.setSystemTime(new Date(startTime.getTime() + 5000));

      store = createMockStore({
        state: {
          time: {
            liveTrack: runningTrack,
            recentTimeEntries: [matchingEntry]
          }
        }
      });
    });

    it('displays active entry name and disables inputs', () => {
      const wrapper = mountComponent(store);

      const input = wrapper.find('input[type="text"]');
      const selector = wrapper.findComponent({ name: 'ProjectSelector' });
      const button = wrapper.find('[data-testid="timer-button"]');

      expect(input.element.value).toBe('Active Task');
      expect(input.attributes('disabled')).toBeDefined();
      expect(selector.props('disabled')).toBe(true);
      expect(button.text()).toBe('Stop');
      expect(button.classes()).toContain('bg-red-600');
    });

    it('displays and updates duration', async () => {
      const wrapper = mountComponent(store);
      await wrapper.vm.$nextTick();

      const timer = wrapper.find('[data-testid="timer-duration"]');
      expect(timer.element.value).toBe('00:00:05');

      // Advance 2 seconds
      vi.advanceTimersByTime(2000);
      await wrapper.vm.$nextTick();

      expect(timer.element.value).toBe('00:00:07');
    });

    it('emits "request-stop-live-timer" on stop click', async () => {
      const wrapper = mountComponent(store);
      await wrapper.find('[data-testid="timer-button"]').trigger('click');

      expect(wrapper.emitted('request-stop-live-timer')).toHaveLength(1);
      expect(wrapper.emitted('request-stop-live-timer')[0][0]).toEqual({
        track: runningTrack
      });
    });

    it('toggles DatePicker on timer button click', async () => {
      const wrapper = mountComponent(store);
      const timer = wrapper.find('[data-testid="DatePicker-button"]');

      // Open
      await timer.trigger('click');
      expect(wrapper.findComponent({ name: 'DatePicker' }).exists()).toBe(true);

      // Close
      await timer.trigger('click');
      expect(wrapper.findComponent({ name: 'DatePicker' }).exists()).toBe(false);
    });

    it('dispatches "time/updateTrack" when DatePicker selects date', async () => {
      const wrapper = mountComponent(store);
      const dispatchSpy = vi.spyOn(store, 'dispatch');

      await wrapper.find('[data-testid="DatePicker-button"]').trigger('click');

      const newDate = new Date('2025-01-01T09:00:00Z');
      const picker = wrapper.findComponent({ name: 'DatePicker' });
      picker.vm.$emit('date-selected', newDate);

      // LiveTimer preserves the original hours, minutes, and seconds
      const expectedDate = new Date(newDate);
      const originalStart = new Date(runningTrack.start_time);
      expectedDate.setHours(
        originalStart.getHours(),
        originalStart.getMinutes(),
        originalStart.getSeconds(),
        originalStart.getMilliseconds()
      );

      expect(dispatchSpy).toHaveBeenCalledWith('time/updateTrack', {
        trackData: {
          ...runningTrack,
          start_time: expectedDate.toISOString()
        }
      });

      await wrapper.vm.$nextTick();
      expect(wrapper.findComponent({ name: 'DatePicker' }).exists()).toBe(false);
    });
  });

  describe('Suggestions Logic', () => {
    let store;
    const recentEntries = [
      { id: 1, name: 'Task A', project: 1 },
      { id: 2, name: 'Task B', project: 2 },
      { id: 3, name: 'Backend testing', project: 2 },
      { id: 4, name: 'API Design', project: 2 },
      { id: 5, name: 'Database schema', project: 2 },
      { id: 6, name: 'Component styling', project: 1 },
      { id: 7, name: 'Documentation writing', project: 1 },
      { id: 8, name: 'Deployment setup', project: 2 },
      { id: 9, name: 'User authentication flow', project: 1 },
      { id: 10, name: 'Code review', project: 2 },
      { id: 11, name: 'Frontend development', project: 1 },
      { id: 12, name: 'Frontend bug fixes', project: 1 },
    ];

    beforeEach(() => {
      store = createMockStore({
        state: {
          time: {
            liveTrack: null,
            recentTimeEntries: recentEntries
          }
        }
      });
    });

    it('shows suggestions on focus', async () => {
      const wrapper = mountComponent(store);
      const input = wrapper.find('input[type="text"]');

      expect(wrapper.find('[data-testid="suggestions-list"]').exists()).toBe(false);

      await input.trigger('focus');
      expect(wrapper.find('[data-testid="suggestions-list"]').exists()).toBe(true);

      const items = wrapper.findAll('[data-testid="suggestions-list"] li');
      expect(items).toHaveLength(10);
    });

    it('filters suggestions based on input', async () => {
      const wrapper = mountComponent(store);
      const input = wrapper.find('input[type="text"]');

      await input.trigger('focus');
      await input.setValue('Task A');

      const items = wrapper.findAll('[data-testid="suggestions-list"] li');
      expect(items).toHaveLength(1);
      expect(items[0].text()).toContain('Task A');
    });

    it('populates fields when suggestion is clicked', async () => {
      const wrapper = mountComponent(store);
      const input = wrapper.find('input[type="text"]');

      await input.trigger('focus');
      await input.setValue('Task'); // show both

      const items = wrapper.findAll('[data-testid="suggestions-list"] li');
      // Click "Task B" (index 1)
      await items[1].trigger('click');

      expect(input.element.value).toBe('Task B');

      const selector = wrapper.findComponent({ name: 'ProjectSelector' });
      expect(selector.props('modelValue')).toBe(2);

      expect(wrapper.find('[data-testid="suggestions-list"]').exists()).toBe(false);
    });

    it('shows recent history (unfiltered) when input is cleared', async () => {
      const wrapper = mountComponent(store);
      const input = wrapper.find('input[type="text"]');

      await input.trigger('focus');
      await input.setValue('Task A');
      expect(wrapper.findAll('[data-testid="suggestions-list"] li')).toHaveLength(1);

      await input.setValue('');
      // Should show all recent (slice -10)
      expect(wrapper.findAll('[data-testid="suggestions-list"] li')).toHaveLength(10);
    });

    it('does not show suggestions if no match is found', async () => {
      const wrapper = mountComponent(store);
      const input = wrapper.find('input[type="text"]');

      await input.trigger('focus');
      await input.setValue('NonExistentTask');
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-testid="suggestions-list"]').exists())
        .toBe(false);
    });
  });
});
