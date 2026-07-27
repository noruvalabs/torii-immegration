---
name: claude-code-config
description: Use when the user is editing Claude Code configuration (CLAUDE.md, .claude/settings.json, MCP servers for Claude Code, or claude.config.json).
---

## When to Use This Skill

Activate when the user wants to:
- Create or edit `CLAUDE.md` files
- Configure Claude Code MCP servers
- Modify `.claude/settings.json`
- Set up project instructions for Claude Code

## Key Configuration Files

- **CLAUDE.md** - Project instructions (like AGENTS.md for Claude)
- **.claude/settings.json** - Claude Code settings
- **MCP servers** - Configured in settings or via CLI

## CLAUDE.md Format

Markdown file at project root:
```markdown
# Project Instructions

## Code Style
- Use TypeScript with strict mode
- Prefer named exports

## Architecture
- Next.js 14+ App Router
- Server Components by default

## Testing
- Use Vitest for unit tests
- Playwright for E2E
```

## MCP Configuration

Via CLI:
```bash
claude mcp add server-name npx -y package-name
```

Or in `.claude/settings.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"]
    }
  }
}
```

## Best Practices

- Keep CLAUDE.md under 500 lines
- Use clear section headers
- Include concrete examples of preferred patterns
- Reference actual files in the codebase when possible
