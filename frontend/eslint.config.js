import globals from 'globals';
import pluginJs from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import pluginVitest from '@vitest/eslint-plugin';

export default [
    {
        // Apply this configuration to all JavaScript and Vue files.
        files: ['**/*.js', '**/*.vue'],
        languageOptions: {
            globals: {
                ...globals.browser, // Standard browser globals
                ...globals.node, // Node.js globals for config files
            },
        },
    },

    // Base ESLint recommended rules
    pluginJs.configs.recommended,

    // Vue.js recommended rules for Vue 3
    ...pluginVue.configs['flat/recommended'],

    // Vitest plugin configuration for test files
    {
        ...pluginVitest.configs.recommended,
        files: ['src/**/__tests__/*'],
    },

    // Custom rule overrides can go here
    {
        rules: {
            // Example: enforce 4-space indentation for better readability
            'vue/html-indent': ['error', 4],
            'indent': ['error', 4],
        },
    },
];