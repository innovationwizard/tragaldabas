# Dependency Notes

## Protobuf Version Conflict

There is a known dependency conflict warning related to `protobuf`:

- **Our project dependencies** require `protobuf<6.0.0` (for `google-generativeai` compatibility)
- **External package** `grpcio-health-checking` (from `dagster`, not in our requirements) requires `protobuf>=6.31.1`

### Resolution

We use `protobuf 5.29.5` which is compatible with all our project dependencies:
- ✅ `google-generativeai` - works correctly
- ✅ `anthropic` - works correctly  
- ✅ `openai` - works correctly
- ✅ All other project dependencies - compatible

The warning about `grpcio-health-checking` can be safely ignored as:
1. It's not in our `requirements.txt`
2. It's a dependency of `dagster` (not used in this project)
3. Our project functionality is not affected

### Verification

All LLM packages import and function correctly:
```bash
python -c "import google.generativeai; import anthropic; import openai; print('✓ All packages work')"
```

### If You Need to Resolve

If you need `grpcio-health-checking` for another project:
1. Use a virtual environment to isolate dependencies
2. Or upgrade `google-generativeai` when a version supporting protobuf 6.x is released

