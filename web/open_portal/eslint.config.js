import pluginVue from 'eslint-plugin-vue'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import tsParser from '@typescript-eslint/parser'
import vueParser from 'vue-eslint-parser'
import prettierPlugin from 'eslint-plugin-prettier'
import globals from 'globals'

export default [
  {
    ignores: ['dist/**', 'node_modules/**', 'src/components.d.ts', 'src/vite-env.d.ts'],
  },
  {
    files: ['**/*.{ts,vue}'],
    plugins: {
      vue: pluginVue,
      '@typescript-eslint': tsPlugin,
      prettier: prettierPlugin,
    },
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: 'latest',
        sourceType: 'module',
        extraFileExtensions: ['.vue'],
      },
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
    },
    rules: {
      ...pluginVue.configs['flat/essential'].rules,
      ...tsPlugin.configs['recommended'].rules,
      'vue/multi-word-component-names': 'off',
      'prettier/prettier': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    },
  },
]
