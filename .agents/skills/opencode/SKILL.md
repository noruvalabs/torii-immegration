---
name: opencode-config
description: Use when the user is editing opencode configuration files (opencode.json, AGENTS.md), MCP server setup, skills, or agent configuration. Do not use for general coding tasks.
---

## When to Use This Skill

Activate when the user wants to:
- Edit `opencode.json` or `opencode.jsonc`
- Configure MCP servers
- Create or edit `AGENTS.md` instructions
- Set up skills, subagents, or plugins
- Modify opencode's own configuration

## Key Configuration Files

- **opencode.json** - Main config at project root
- **AGENTS.md** - Project instructions at root or `~/.config/opencode/AGENTS.md`
- **MCP servers** - Defined in opencode.json under `mcp`

## Common Tasks

### Adding an MCP Server
```json
{
  "mcp": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": {}
    }
  }
}
```

### Agent Configuration
Agents are configured via AGENTS.md with markdown sections. Use frontmatter for metadata:
```markdown
## Agent Name
<!-- description: What this agent does -->
Instructions here...
```

### Skills
Skills live in `~/.agents/skills/<name>/SKILL.md` with frontmatter:
```markdown
---
name: skill-name
description: When to activate this skill
---
Instructions here...
```

## Best Practices

- Keep AGENTS.md concise and actionable
- Use environment variables for secrets in MCP config
- Test MCP servers independently before adding to config
- Use project-level AGENTS.md for repo-specific rules
