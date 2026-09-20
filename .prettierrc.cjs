// =============================================================================================================================
// prettier config
// =============================================================================================================================

const config = {
  printWidth: 128,
  tabWidth: 2,
  useTabs: false,
  semi: true,
  singleQuote: false,
  quoteProps: "as-needed",
  trailingComma: "es5",
  bracketSpacing: true,
  arrowParens: "avoid",
  // See: https://github.com/prettier/prettier/issues/15388
  plugins: [require.resolve("prettier-plugin-toml")],
  overrides: [
    {
      files: "*.toml",
      options: {
        tabWidth: 4,
      },
    },
    {
      files: "*.md",
      options: {
        tabWidth: 4,
      },
    },
  ],
};

module.exports = config;
