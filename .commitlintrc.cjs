// =============================================================================================================================
// Commitlint Configuration
// =============================================================================================================================
//
// Enforces conventional commit message format for better project history.
//
// COMMIT FORMAT:
// <type>[optional scope]: <description>
//
// [optional body]
//
// [optional footer(s)]
//
// EXAMPLES:
// feat: add user authentication system
// fix(api): resolve memory leak in data processing
// docs: update installation instructions
// feat!: remove deprecated login endpoint
// chore(deps): bump lodash from 4.17.19 to 4.17.21
//
// Subject is enforced lower-case, EXCEPT for content wrapped in backticks so
// identifiers can appear verbatim:
//   fix(consumer): allow `KafkaConsumer` bootstrap overrides
//
// BREAKING CHANGES:
// Use ! after type/scope or include "BREAKING CHANGE:" in footer
//
// =============================================================================================================================

const subjectCaseAllowBackticks = parsed => {
  if (!parsed.subject) return [true];
  const stripped = parsed.subject.replace(/`[^`]*`/g, "");
  if (stripped === stripped.toLowerCase()) return [true];
  return [false, "subject must be lower-case (wrap identifiers in `backticks` to allow caps)"];
};

module.exports = {
  extends: ["@commitlint/config-conventional"],
  plugins: [
    {
      rules: {
        "subject-case-allow-backticks": subjectCaseAllowBackticks,
      },
    },
  ],
  rules: {
    "type-enum": [2, "always", ["feat", "fix", "docs", "style", "refactor", "perf", "test", "chore", "ci", "build", "revert"]],
    "type-empty": [2, "never"],
    "type-case": [2, "always", "lower-case"],
    "subject-empty": [2, "never"],
    // Built-in subject-case is disabled in favor of the backtick-aware rule below.
    "subject-case": [0],
    "subject-case-allow-backticks": [2, "always"],
    "subject-max-length": [2, "always", 72],
    "subject-min-length": [2, "always", 3],
    "subject-full-stop": [2, "never", "."],
    "header-max-length": [2, "always", 100],
    "body-max-line-length": [2, "always", 100],
    "body-leading-blank": [1, "always"],
    "footer-leading-blank": [1, "always"],
  },
};
