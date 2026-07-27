---
name: codex-config
description: Use when the user is editing OpenAI Codex CLI configuration (codex.md, AGENTS.md for Codex, or codex.config.json).
---

## When to Use This Skill

Activate when the user wants to:
- Create or edit `codex.md` or `AGENTS.md` for Codex CLI
- Configure Codex CLI behavior
- Set up project instructions for Codex
- Modify Codex configuration files

## Key Configuration Files

- **codex.md** - Project instructions for Codex CLI
- **AGENTS.md** - Shared agent instructions (works with Codex)
- **codex.config.json** - Codex-specific configuration

## codex.md Format

```markdown
# Project Instructions for Codex

## Code Style
- TypeScript strict mode
- Functional components only

## Rules
- Never use `any` type
- Always handle errors explicitly
- Write tests for new features

## File Structure
- src/components/ - React components
- src/lib/ - Utilities
- src/types/ - TypeScript types
```

## AGENTS.md (Shared)

Can be shared across tools (opencode, codex):
```markdown
## Project Overview
Brief description of the project.

## Development Rules
- Use pnpm for package management
- Run `pnpm typecheck` before commits
- Follow conventional commits
```

## Best Practices

- Keep instructions concise and enforceable
- Use AGENTS.md for cross-tool shared rules
- Use codex.md for Codex-specific behavior
- Include file path conventions
