// test_ai.pl — Real AI call from PAPA Lang
// Usage: OPENAI_API_KEY=sk-... pl run examples/test_ai.pl
//    or: ANTHROPIC_API_KEY=sk-ant-... pl run examples/test_ai.pl

print("=== PAPA Lang AI Engine Test ===")
print("")

// Show configured providers
let providers = ai.models()
print("Config: " + providers)
print("")

// Simple ask
print("Asking AI: 'What is 2+2?'...")
let answer = ai.ask("What is 2+2? Answer with just the number.")
print("AI says: " + answer)
print("")

// Ask with specific model (if you have the key)
// let code = ai.ask("Write hello world in Python. Only code, no explanation.", "anthropic/claude-sonnet-4-20250514")
// print("Claude says: " + code)

print("=== AI Engine Test Complete ===")
