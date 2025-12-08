---
name: obsidian-mermaid
description: Create Obsidian-compatible Mermaid diagrams. Avoid common errors like markdown in labels, use narrow TB layouts for publishing. Use when creating flowcharts, sequence diagrams, or any Mermaid diagrams in markdown files.
allowed-tools:
  - Read
  - Edit
license: MIT
---

# Obsidian Mermaid Diagrams

Create Mermaid diagrams that render correctly in Obsidian and publish without issues.

## When to Use This Skill

Activate when you need to:
- Create flowcharts, sequence diagrams, ER diagrams
- Convert ASCII art to Mermaid
- Fix Mermaid rendering errors in Obsidian

## Critical Rules

### 1. NO Markdown in Labels

**Common Errors**:
```
Node["1. First"]     → "Unsupported markdown: list"
Node["Text<br/>More"] → "Unsupported markdown: heading"
Node["## Header"]    → "Unsupported markdown: heading"
```

**Correct**:
```
Node[First]
Node[Text]
```

**Rule**: Keep labels plain text. Move complex descriptions outside the diagram.

### 2. Use TB Direction (Narrow Width)

**Problem**: `flowchart LR` (left-right) creates wide diagrams that get cut off when published.

```markdown
❌ Gets cut off:
flowchart LR

✅ Fits narrow screens:
flowchart TB
```

**Rule**: Default to `flowchart TB` (top-bottom) unless horizontal layout is essential.

### 3. Keep Labels Short

```markdown
❌ Too long:
Node["This is a very long description that will break layout"]

✅ Short and clear:
Node[Short Label]
```

**Rule**: Labels should be under 15 characters. Add details in text below the diagram.

### 4. Avoid Special Characters in Subgraph Names

```markdown
❌ May cause issues:
subgraph "1. Phase One"
subgraph "Phase: Setup"

✅ Safe:
subgraph Phase_One["Phase One"]
subgraph Setup["Setup Phase"]
```

## Good Examples

### Simple Flowchart
```mermaid
flowchart TB
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[End]
```

### Process Flow with Details Outside
```mermaid
flowchart TB
    Input[Input] --> Process[Process]
    Process --> Output[Output]
```

**Process Details**:
- Input: User data from form
- Process: Validation and transformation
- Output: Saved to database

### Subgraph Example
```mermaid
flowchart TB
    subgraph Frontend["Frontend"]
        UI[UI] --> API[API Call]
    end
    subgraph Backend["Backend"]
        Server[Server] --> DB[Database]
    end
    API --> Server
```

## Bad Examples (Don't Do This)

### Markdown in Labels
```mermaid
flowchart LR
    A["1. Start<br/>with details"] --> B{"2. Decision"}
```
This will show "Unsupported markdown" errors.

### Too Wide
```mermaid
flowchart LR
    A[Very Long Process Name Here] --> B[Another Long Name] --> C[Yet Another] --> D[And More]
```
This gets cut off on mobile and narrow screens.

## Converting ASCII to Mermaid

**ASCII Art**:
```
┌───────┐     ┌───────┐
│ Start │────→│  End  │
└───────┘     └───────┘
```

**Mermaid**:
```mermaid
flowchart TB
    Start[Start] --> End[End]
```

## Quality Checklist

Before completing diagram creation:

- [ ] No `<br/>` tags in node labels
- [ ] No numbered list format (`1.`, `2.`) in labels
- [ ] Using `flowchart TB` direction (not LR)
- [ ] All labels are short (under 15 characters)
- [ ] Complex details moved to text outside diagram
- [ ] No special characters in subgraph names
- [ ] Tested rendering in Obsidian preview
