import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default tseslint.config(
  {
    ignores: [".next/**", "node_modules/**", "dist/**", "build/**"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx,js,jsx}"],
    plugins: {
      "react-hooks": reactHooks,
    },
    languageOptions: {
      parserOptions: {
        ecmaFeatures: { modules: true },
        ecmaVersion: 2022,
        sourceType: "module",
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      // set-state-in-effect — распространённый паттерн загрузки данных в
      // эффектах; понижен до предупреждения, чтобы не блокировать сборку.
      "react-hooks/set-state-in-effect": "warn",
      // purity/immutability — новые экспериментальные правила react-hooks v7,
      // дающие ложные срабатывания на распространённых паттернах (Math.random
      // в useMemo для skeleton, Date.now() в event handlers и т.п.).
      "react-hooks/purity": "warn",
      "react-hooks/immutability": "warn",
      "no-empty": ["error", { allowEmptyCatch: true }],
    },
  },
);