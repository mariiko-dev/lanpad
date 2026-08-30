import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["node_modules", "../src/lanpad/web"] },
  ...tseslint.configs.recommended,
);
