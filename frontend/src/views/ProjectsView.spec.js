import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createStore } from 'vuex';
import ProjectsView from './ProjectsView.vue';

vi.mock('../components/modals/ProjectCreationModal.vue', () => ({
  default: {
    name: 'ProjectCreationModal',
    props: ['isVisible', 'isSaving', 'error', 'project'],
    template: '<div v-if="isVisible" data-testid="project-modal-mock"></div>',
    emits: ['close', 'save']
  }
}));

describe('ProjectsView.vue', () => {
  let store;
  let actions;

  const mockProjects = [
    { id: 1, title: 'Project A', color: 'ff0000', created_at: '2025-01-01T10:00:00Z' },
    { id: 2, title: 'Project B', color: '00ff00', created_at: '2025-01-02T10:00:00Z' }
  ];
  // 3600s = 1h, 7200s = 2h
  const mockDurations = { 1: 3600, 2: 7200 };

  beforeEach(() => {
    actions = {
      fetchProjects: vi.fn(),
      fetchProjectDurations: vi.fn(),
      createProject: vi.fn(),
      updateProject: vi.fn(),
    };

    store = createStore({
      modules: {
        time: {
          namespaced: true,
          getters: {
            getAllProjects: () => mockProjects,
            getAllProjectsDurations: () => mockDurations,
          },
          actions
        }
      }
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const mountComponent = () => {
    return mount(ProjectsView, {
      global: { plugins: [store] }
    });
  };

  it('fetches projects and durations on mount', () => {
    mountComponent();
    expect(actions.fetchProjects).toHaveBeenCalled();
    expect(actions.fetchProjectDurations).toHaveBeenCalled();
  });

  it('renders projects and their formatted durations', () => {
    const wrapper = mountComponent();
    const rows = wrapper.findAll('tbody tr');

    expect(rows.length).toBe(2);
    expect(rows[0].text()).toContain('Project A');
    expect(rows[0].text()).toContain('1.00 h');
    expect(rows[1].text()).toContain('Project B');
    expect(rows[1].text()).toContain('2.00 h');
  });

  it('opens modal for new project creation', async () => {
    const wrapper = mountComponent();
    await wrapper.find('button').trigger('click'); // "+ New project" button

    const modal = wrapper.findComponent({ name: 'ProjectCreationModal' });
    expect(modal.exists()).toBe(true);
    expect(modal.props('isVisible')).toBe(true);
    expect(modal.props('project')).toBeNull();
  });

  it('opens modal for editing an existing project', async () => {
    const wrapper = mountComponent();
    const rows = wrapper.findAll('tbody tr');

    await rows[0].trigger('click'); // Click first project

    const modal = wrapper.findComponent({ name: 'ProjectCreationModal' });
    expect(modal.exists()).toBe(true);
    expect(modal.props('isVisible')).toBe(true);
    expect(modal.props('project')).toEqual(mockProjects[0]);
  });

  it('dispatches createProject when saving a new project', async () => {
    const wrapper = mountComponent();
    await wrapper.find('button').trigger('click'); // Open create modal

    const newProjectData = { title: 'New Proj', color: '0000ff' };
    const modal = wrapper.findComponent({ name: 'ProjectCreationModal' });
    await modal.vm.$emit('save', newProjectData);

    expect(wrapper.vm.isSaving).toBe(true);
    await flushPromises();

    expect(actions.createProject).toHaveBeenCalledWith(expect.anything(), newProjectData);
    expect(wrapper.vm.isModalVisible).toBe(false);
  });

  it('dispatches updateProject when saving an existing project', async () => {
    const wrapper = mountComponent();
    const rows = wrapper.findAll('tbody tr');
    await rows[0].trigger('click'); // Open edit modal

    const updatedData = { id: 1, title: 'Updated Proj', color: 'ff0000' };
    const modal = wrapper.findComponent({ name: 'ProjectCreationModal' });
    await modal.vm.$emit('save', updatedData);

    await flushPromises();

    expect(actions.updateProject).toHaveBeenCalledWith(expect.anything(), updatedData);
    expect(wrapper.vm.isModalVisible).toBe(false);
  });

  it('handles errors when saving fails', async () => {
    actions.createProject.mockRejectedValueOnce({
      response: { data: { message: 'Save failed' } }
    });

    const wrapper = mountComponent();
    await wrapper.find('button').trigger('click');

    const modal = wrapper.findComponent({ name: 'ProjectCreationModal' });
    await modal.vm.$emit('save', { title: 'Fail Proj' });

    await flushPromises();

    expect(wrapper.vm.modalError).toBe('Save failed');
    expect(wrapper.vm.isModalVisible).toBe(true); // Modal stays open
    expect(wrapper.vm.isSaving).toBe(false);
  });
});
