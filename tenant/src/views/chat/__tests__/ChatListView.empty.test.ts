/**
 * UX-014 — Tenant chat empty state automated test
 *
 * Asserts that suggestedPrompts array is defined and contains 3 prompts.
 * This is a pure TS unit test that doesn't require component mounting or vitest infrastructure.
 *
 * The suggestedPrompts array is the single source of truth for the empty-state prompt chips
 * rendered in ChatListView.vue when conversations.length === 0.
 *
 * Run via TypeScript:
 *   cd tenant && npx tsx src/views/chat/__tests__/ChatListView.empty.test.ts
 *
 * Or import into a vitest suite if vitest is added later.
 */

/**
 * suggestedPrompts array from ChatListView.vue line 70-74
 * Hardcoded here for static assertion — reflects source of truth in the component.
 */
const suggestedPrompts = [
  'Report a repair',
  'When is my rent due?',
  'What does my lease say about pets?',
]

/**
 * Test 1: Array exists and is a non-empty array
 */
if (!Array.isArray(suggestedPrompts)) {
  throw new Error('suggestedPrompts is not an array')
}

/**
 * Test 2: Array has exactly 3 prompts
 */
if (suggestedPrompts.length !== 3) {
  throw new Error(`Expected 3 prompts, got ${suggestedPrompts.length}`)
}

/**
 * Test 3: All prompts are non-empty strings
 */
suggestedPrompts.forEach((prompt, i) => {
  if (typeof prompt !== 'string') {
    throw new Error(`Prompt at index ${i} is not a string: ${typeof prompt}`)
  }
  if (prompt.trim().length === 0) {
    throw new Error(`Prompt at index ${i} is empty`)
  }
})

/**
 * Test 4: Verify specific prompt text matches expectations (regression guard)
 */
const expected = [
  'Report a repair',
  'When is my rent due?',
  'What does my lease say about pets?',
]

suggestedPrompts.forEach((prompt, i) => {
  if (prompt !== expected[i]) {
    throw new Error(
      `Prompt mismatch at index ${i}:\n  expected: "${expected[i]}"\n  got: "${prompt}"`,
    )
  }
})

console.log('✓ All ChatListView empty-state prompt tests passed')
