# RikaiOS UX Principles

> Experience principles for all interfaces.

---

## Core Experience

**Stillness and clarity.** Marie Kondo for your digital life.

The user should feel:
- In control, not overwhelmed
- Informed, not bombarded
- Assisted, not replaced

---

## Design Principles

### 1. Proactive, Not Intrusive

Tama surfaces insights without being asked, but:
- Knows when to stay silent
- Never interrupts urgently unless truly urgent
- Presents, doesn't push

**Good:** "By the way, you mentioned X last week — seems related to what you're working on."

**Bad:** "ALERT: I found a connection! Click here now!"

### 2. Transparency Over Magic

Users should understand:
- Where their data is stored
- What the agent knows about them
- Why a suggestion was made
- What's being shared in federation

**Good:** "I suggested this because you mentioned [X] on [date]."

**Bad:** "Here's a suggestion." (no explanation)

### 3. Permission by Default

- Never act without permission for consequential actions
- Always show what will be shared before sharing
- Make it easy to revoke access

**Good:** "Should I book this? Here's what I'll send: [preview]"

**Bad:** "I booked it for you!"

### 4. Progressive Disclosure

- Start simple, reveal complexity on demand
- Dashboard shows overview, drill down for details
- CLI for power users, GUI for casual use

---

## Interface Guidelines

### Dashboard
- Mind map visualization of context
- Insights surface without cluttering
- Clean, minimal, breathable

### CLI
- Fast, keyboard-driven
- Tab completion for entities
- Rich output with colors and formatting

### Agent Responses
- Concise by default
- Expand on request
- Cite sources when referencing context

---

## Interaction Patterns

### Proactive Suggestions
```
Tama: "You have a meeting with Sarah tomorrow.
       Last time you discussed the Q3 budget.
       Want me to pull up your notes?"

User: "Yes" / "No" / "Tell me more"
```

### Federation Sharing
```
Tama: "Alex's agent is requesting access to your
       'Project Alpha' context. They can see:
       - Project timeline
       - Your meeting notes
       - Shared documents

       Grant access?"

User: [Review details] → "Allow" / "Deny" / "Customize"
```

### Agent Actions
```
Tama: "Your son has soccer on Tuesday.
       Should I book the usual slot at Main Field?

       Action: Book 4pm-5pm, Main Field, $25

       [Confirm] [Edit] [Cancel]"
```

---

## Accessibility

- Keyboard navigation for all interfaces
- Screen reader support for dashboard
- Voice interface planned for hands-free use
- High contrast mode available

---

## Error Handling

- Never show raw errors to users
- Explain what went wrong in plain language
- Suggest next steps
- Log technical details for debugging

**Good:** "Couldn't connect to your calendar. Check your Google account is still linked in Settings."

**Bad:** "Error: OAuth token expired. Code: 401"

---

*The agent should feel like a calm, competent assistant — not a demanding notification machine.*
