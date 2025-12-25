---
description: Keep documentation synced with code changes
---

# Documentation Sync Workflow

Use this workflow when making changes to code or documentation to ensure everything stays synchronized.

## When to Run This Workflow

- After modifying any file in `src/active_flow/`
- After changing parameters in `parameters/*.yml`
- After updating any file in `docs/`

## Steps

### 1. Check Code-Doc Alignment

If you changed **code** in a module, update the corresponding doc:

| Module Changed | Update This Doc |
|----------------|-----------------|
| `src/active_flow/simulation/` | `docs/capsules/simulation.md` |
| `src/active_flow/steady_state_analysis/` | `docs/capsules/steady_state_analysis.md` |
| `src/active_flow/extrema_search/` | `docs/capsules/extrema_search.md` |
| `src/active_flow/hyperuniformity_analysis/` | `docs/capsules/hyperuniformity_analysis.md` |
| `parameters/*.yml` | `docs/capsules/` (parameter tables) |
| Mathematical model changes | `docs/theoretical_background.md` |

### 2. Check for Broken Links

// turbo
Run this command to find any broken doc references:
```bash
grep -r "\.md)" docs/ README.md | grep -v node_modules
```

Verify all linked files exist.

### 3. Update README if Needed

If you added/removed modules or changed the pipeline structure, update:
- Project structure diagram in `README.md`
- Documentation table in `README.md`
- Pipeline description

### 4. Verify Cross-References

Each capsule doc should link to:
- Related modules (previous/next in pipeline)
- `theoretical_background.md` for math details

## Quick Reference: Current Doc Structure

```
docs/
├── theoretical_background.md  ← Math & numerical methods
└── capsules/
    ├── framework.md           ← Architecture overview
    ├── simulation.md          ← PVC solver
    ├── steady_state_analysis.md
    ├── extrema_search.md
    └── hyperuniformity_analysis.md
```

## Tips

- Keep docs concise — link to `theoretical_background.md` for details
- Update parameter tables when YAML files change
- Test that Mermaid diagrams render correctly
