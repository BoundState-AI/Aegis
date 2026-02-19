---
name: retro
description: Write a session retrospective to the retro log. Use at the end of any significant session.
allowed-tools: Read, Write, Edit, Glob, Grep
---

Write a session retrospective to `C:\Users\Jnwil\.claude\projects\d--BoundState-boundstate-aegis\memory\session_retros.md`.

Follow the format from CLAUDE.md:

```
## YYYY-MM-DD — [2-5 word summary]
**Built:** what was accomplished
**Wins:** what went well, clever approaches, good catches
**Failures:** what went wrong, time wasted, wrong assumptions
**Lessons:** concrete takeaways for next time (not vague platitudes)
```

Rules:
1. Review the full conversation to identify what was built, what went well, and what went wrong.
2. Be brutally honest. If you made a dumb mistake, say so. If the user caught something you missed, note it.
3. Prepend the new entry at the top (after the `# Session Retrospectives` header) so newest is first.
4. If there are more than 10 entries, trim the oldest ones.
5. If any lesson is durable (will matter in future sessions), also promote it to `C:\Users\Jnwil\.claude\projects\d--BoundState-boundstate-aegis\memory\MEMORY.md` under the "Key Learnings" section.
6. After writing, show the user what you wrote so they can correct anything.
