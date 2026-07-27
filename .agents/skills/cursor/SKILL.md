---
name: cursor-config
description: Use when the user is editing Cursor configuration files (.cursorrules, .cursor/settings.json, .cursor/mcp.json) or Cursor-specific project settings.
---

## When to Use This Skill

Activate when the user wants to:
- Create or edit `.cursorrules` files
- Configure Cursor MCP servers in `.cursor/mcp.json`
- Modify Cursor settings (`.cursor/settings.json`)
- Set up project rules or AI instructions for Cursor

## Key Configuration Files

- **.cursorrules** - AI behavior rules at project root
- **.cursor/mcp.json** - MCP server configuration
- **.cursor/settings.json** - Cursor editor settings

## .cursorrules Format

Plain markdown/text file at project root:
```
# Project Rules

## Code Style
- Use TypeScript strict mode
- Prefer functional components

## Architecture
- Next.js App Router
- Tailwind CSS for styling
```

## MCP Configuration

`.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": {}
    }
  }
}
```

## Best Practices

- Keep .cursorrules focused and specific
- Use section headers for organization
- Include only enforceable rules
- Test rules by asking Cursor to generate code
