---
name: obsidian-cli
description: >-
  Interact with Obsidian using the official CLI to read, search, create, and
  manage notes, daily notes, tasks, properties, and more. Use when the user
  wants to query or manipulate vault content via the obsidian command.
allowed-tools: Bash(obsidian:*)
license: MIT
metadata:
  author: lifidea
  version: "1.0.0"
  created: 2026-02-28
---

# Obsidian CLI Skill

The official Obsidian command-line interface allows you to interact with your vault from the terminal — reading notes, searching, managing properties, handling tasks, and more.

## Prerequisites

Verify the CLI is installed and running:

```bash
obsidian --version
obsidian help
```

Requirements:
- **Obsidian v1.12+** (released late 2024)
- **Catalyst license or higher** (Obsidian Sync, Publish, or community support)
- **Obsidian must be running** — the CLI communicates via IPC with a live instance
- **macOS, Windows, or Linux** support

If not installed, download the latest Obsidian installer from https://obsidian.md/download

## Key Concepts

### IPC-Based Communication
The obsidian-cli works by connecting to a **running Obsidian instance** via inter-process communication (IPC). It does not manipulate files directly; all commands are executed through Obsidian's API, ensuring proper handling of plugins, sync, and vault structure.

### File vs Path Parameters
Two ways to target files:

- **`file=<name>`** — Resolves by name like wikilinks. Searches across folders to find the file. More flexible but slower.
  - Example: `obsidian read file="My Note"` (finds the file regardless of folder)
  - Best for: Quick access when you know the filename

- **`path=<path>`** — Exact path from vault root. No searching, just direct access.
  - Example: `obsidian read path="Journal/2026-02-28.md"` (exact path required)
  - Best for: Performance-sensitive operations, when you know the exact location

### Vault Parameter
By default, commands run against the **currently active vault**. Override with:

```bash
obsidian read file="Note" vault="My Vault"
```

### Quoting & Escaping
- **Spaces in values** — Always quote: `name="My Note"` not `name=My Note`
- **Newlines** — Use `\n`: `content="Line 1\nLine 2"`
- **Tabs** — Use `\t`: `content="Column1\tColumn2"`

### Flags vs Parameters
- **Flags** — Boolean options, no value needed: `--verbose`, `--overwrite`, `--inline`
- **Parameters** — Key=value pairs: `file="Name"`, `query="term"`, `limit=10`

## Syntax Guide

### Basic Command Structure

```bash
obsidian <command> [parameter=value...] [--flag...]
```

### Examples

```bash
# Parameters with simple values
obsidian read file="Journal"

# Parameters with spaces (quoted)
obsidian create name="My Daily Note" content="Hello world"

# Multiple parameters
obsidian search query="TODO" path="Projects" limit=10

# Flags
obsidian files folder="Project" --verbose

# Mixed
obsidian create path="Journal/2026-02-28.md" content="Daily note" --open
```

## File Targeting Patterns

### Read a Note by Name
```bash
obsidian read file="Meeting Notes"
```
Searches vault for `Meeting Notes.md` anywhere.

### Read by Exact Path
```bash
obsidian read path="Project/2026-02-28.md"
```
Reads from exact location; faster for known paths.

### Create with Template
```bash
obsidian create name="New Note" template="Daily Note Template"
```

### List Files in Folder
```bash
obsidian files folder="Journal"
```

## Command Reference

Commands are organized by category. Use `obsidian help <command>` for detailed options.

### File Operations

#### read
Read file contents. Returns full text or structured data.

```bash
# Read by name
obsidian read file="My Note"

# Read by path
obsidian read path="Journal/2026-02-28.md"

# Active file (omit file/path params)
obsidian read
```

#### create
Create a new file with optional content and template.

```bash
# Simple creation
obsidian create name="New Note"

# With content
obsidian create name="Daily Note" content="Today's note"

# With template
obsidian create name="Meeting" template="Meeting Template" --open

# With exact path
obsidian create path="Journal/2026-02-28.md" content="..." --overwrite
```

#### append
Add content to end of file.

```bash
obsidian append file="My Note" content="New line"

# Inline (no newline before appended text)
obsidian append file="My Note" content=" continued" --inline
```

#### prepend
Add content to beginning of file.

```bash
obsidian prepend file="My Note" content="Header\n"

# Inline
obsidian prepend file="My Note" content="[Start] " --inline
```

#### delete
Remove a file (sends to trash by default).

```bash
obsidian delete file="Old Note"

# Permanent deletion
obsidian delete path="Archive/obsolete.md" --permanent
```

#### rename
Change a file's name.

```bash
obsidian rename file="Old Name" name="New Name"
```

#### move
Move file to different folder.

```bash
obsidian move file="Note" to="Archive"

# Move with new name
obsidian move path="Journal/old.md" to="Archive/2025-old.md"
```

#### open
Open file in Obsidian editor.

```bash
obsidian open file="Note"

# Open in new tab
obsidian open file="Note" --newtab
```

### File Information

#### file
Show metadata about a file.

```bash
obsidian file file="My Note"
```

Returns: created date, modified date, size, links, backlinks count.

#### files
List all files in vault (optionally filtered).

```bash
# All files
obsidian files

# By folder
obsidian files folder="Journal"

# By extension
obsidian files ext="md"

# With count
obsidian files folder="Project" --total
```

#### folder
Show folder information.

```bash
obsidian folder path="Journal"

# Specific info
obsidian folder path="Journal" info=files    # Number of files
obsidian folder path="Journal" info=size     # Total size
obsidian folder path="Journal" info=folders  # Number of subfolders
```

#### folders
List folders in vault.

```bash
obsidian folders

# Subfolders only
obsidian folders folder="Archive"

# With count
obsidian folders folder="Journal" --total
```

#### vault
Show vault information.

```bash
obsidian vault                        # All info
obsidian vault info=name              # Vault name
obsidian vault info=path              # Vault folder path
obsidian vault info=files             # Total files
obsidian vault info=size              # Total vault size
```

#### vaults
List all known vaults.

```bash
obsidian vaults

# Verbose (include paths)
obsidian vaults --verbose
```

#### wordcount
Count words and characters in file.

```bash
obsidian wordcount file="Chapter 1"

# Word count only
obsidian wordcount file="Chapter 1" --words

# Character count only
obsidian wordcount file="Chapter 1" --characters
```

### Searching & Navigation

#### search
Full-text search vault.

```bash
# Basic search
obsidian search query="TODO"

# Limited results
obsidian search query="meeting" limit=5

# In folder
obsidian search query="TODO" path="Projects"

# Case sensitive
obsidian search query="MyClass" --case

# JSON output
obsidian search query="bug" format=json
```

#### search:context
Search with matching line context.

```bash
# Show surrounding lines
obsidian search:context query="TODO" path="Journal"

# JSON format
obsidian search:context query="error" format=json
```

#### search:open
Open search dialog in Obsidian.

```bash
obsidian search:open query="TODO"
```

### Links & References

#### links
List outgoing links from a file.

```bash
obsidian links file="My Note"

# Count only
obsidian links file="My Note" --total
```

#### backlinks
List files linking to a target (incoming links).

```bash
obsidian backlinks file="Project Overview"

# Include link counts
obsidian backlinks file="Project Overview" --counts

# Format output
obsidian backlinks file="Project" format=json
```

#### aliases
Show aliases for a file (alternative names).

```bash
obsidian aliases file="Meeting"

# Count aliases
obsidian aliases file="Meeting" --total

# Verbose (include paths)
obsidian aliases file="Meeting" --verbose

# Aliases for active file
obsidian aliases --active
```

#### unresolved
List broken/unresolved links in vault.

```bash
obsidian unresolved

# Count only
obsidian unresolved --total

# Verbose (show source files)
obsidian unresolved --verbose

# JSON format
obsidian unresolved format=json
```

#### deadends
List files with no outgoing links.

```bash
obsidian deadends

# Count
obsidian deadends --total

# Include non-markdown files
obsidian deadends --all
```

#### orphans
List files with no incoming links (not referenced).

```bash
obsidian orphans

# Count
obsidian orphans --total

# Include non-markdown
obsidian orphans --all
```

### Tags

#### tags
List all tags in vault with frequencies.

```bash
obsidian tags

# For specific file
obsidian tags file="My Note"

# By path
obsidian tags path="Journal"

# With counts
obsidian tags --counts

# Sort by count
obsidian tags --counts sort=count

# JSON format
obsidian tags format=json

# Tags for active file
obsidian tags --active
```

#### tag
Get info about a specific tag.

```bash
obsidian tag name=meeting

# Count only
obsidian tag name=meeting --total

# List files with tag
obsidian tag name=work --verbose
```

### Tasks & Checklists

#### tasks
List all tasks in vault.

```bash
obsidian tasks

# Incomplete tasks
obsidian tasks --todo

# Completed tasks
obsidian tasks --done

# By file
obsidian tasks file="My Note"

# By path
obsidian tasks path="Journal"

# By status (e.g., "x" for done, "-" for in progress)
obsidian tasks status="-"

# Verbose (group by file with line numbers)
obsidian tasks --verbose

# JSON format
obsidian tasks format=json

# Tasks from daily note
obsidian tasks --daily
```

#### task
Show or update a single task.

```bash
# Show task at line 5 in Journal/2026-02-28.md
obsidian task ref="Journal/2026-02-28.md:5"

# Toggle task status
obsidian task ref="Journal/2026-02-28.md:5" --toggle

# Mark as done
obsidian task ref="Journal/2026-02-28.md:5" --done

# Mark as incomplete
obsidian task ref="Journal/2026-02-28.md:5" --todo

# Set custom status (e.g., in progress)
obsidian task file="My Note" line=3 status="-"
```

### Properties & Metadata

#### properties
List all properties in vault with usage counts.

```bash
obsidian properties

# Properties for specific file
obsidian properties file="My Note"

# By path
obsidian properties path="Journal"

# With counts
obsidian properties --counts

# Count specific property
obsidian properties name=category --total

# Sort by count
obsidian properties sort=count

# YAML format
obsidian properties format=yaml

# JSON format
obsidian properties format=json

# Properties for active file
obsidian properties --active
```

#### property:set
Set a property on a file.

```bash
obsidian property:set name=category value=work file="My Note"

# With type (auto-inferred if not specified)
obsidian property:set name=priority value=high file="Task" type=text

# List type
obsidian property:set name=tags value="work,urgent" file="Note" type=list

# Number type
obsidian property:set name=wordcount value=1500 file="Article" type=number

# Checkbox
obsidian property:set name=reviewed value=true file="Document" type=checkbox

# Date
obsidian property:set name=deadline value=2026-03-01 file="Task" type=date
```

#### property:read
Get a property value from a file.

```bash
obsidian property:read name=category file="My Note"

# By path
obsidian property:read name=priority path="Tasks/urgent.md"
```

#### property:remove
Delete a property from a file.

```bash
obsidian property:remove name=draft file="Article"

# By path
obsidian property:remove name=status path="Archive/old.md"
```

### Templates

#### templates
List all templates in vault.

```bash
obsidian templates

# Count
obsidian templates --total
```

#### template:read
Read template content (useful for understanding what template will insert).

```bash
obsidian template:read name="Daily Note"

# Resolve variables
obsidian template:read name="Daily Note" --resolve title="2026-02-28"
```

#### template:insert
Insert template into active file.

```bash
obsidian template:insert name="Daily Note"
```

### Bookmarks

#### bookmarks
List all bookmarks.

```bash
obsidian bookmarks

# Count
obsidian bookmarks --total

# Verbose (show types)
obsidian bookmarks --verbose

# JSON format
obsidian bookmarks format=json
```

#### bookmark
Add a bookmark.

```bash
# Bookmark a file
obsidian bookmark file="Journal/2026-02-28.md"

# Bookmark a section
obsidian bookmark file="Project Overview" subpath="Goals"

# Bookmark a folder
obsidian bookmark folder="Archive"

# Bookmark a search
obsidian bookmark search="TODO"

# Bookmark a URL
obsidian bookmark url="https://example.com" title="My Site"
```

### Bases (Database-like Tables)

#### bases
List all base files in vault.

```bash
obsidian bases
```

#### base:views
List views in a base.

```bash
obsidian base:views file="Contacts"

# By path
obsidian base:views path="Databases/Projects.md"
```

#### base:query
Query a base and return filtered results.

```bash
# Query a view
obsidian base:query file="Contacts" view="Active"

# JSON output
obsidian base:query file="Projects" view="2026" format=json

# CSV output
obsidian base:query file="Contacts" view="All" format=csv
```

#### base:create
Create a new record in a base.

```bash
obsidian base:create file="Contacts" view="All" name="John Doe" email="john@example.com"

# With initial content
obsidian base:create file="Projects" view="Active" name="Project X" content="Details..."

# Open after creating
obsidian base:create file="Tasks" view="Backlog" name="Task 1" --open
```

### Publishing

#### publish:status
Check what files have unpublished changes.

```bash
obsidian publish:status

# New files only
obsidian publish:status --new

# Changed files
obsidian publish:status --changed

# Deleted files
obsidian publish:status --deleted

# Count
obsidian publish:status --total
```

#### publish:add
Publish files to Obsidian Publish.

```bash
# Publish specific file
obsidian publish:add file="Project Overview"

# Publish all changed
obsidian publish:add --changed
```

#### publish:remove
Unpublish a file.

```bash
obsidian publish:remove file="Archived Note"

# By path
obsidian publish:remove path="Archive/old.md"
```

#### publish:list
List published files.

```bash
obsidian publish:list

# Count
obsidian publish:list --total
```

#### publish:site
Show Publish site info.

```bash
obsidian publish:site
```

#### publish:open
Open published file in browser.

```bash
obsidian publish:open file="My Article"
```

### Sync & Version History

#### sync:status
Check sync status.

```bash
obsidian sync:status
```

#### sync
Pause or resume sync.

```bash
obsidian sync off   # Pause sync

obsidian sync on    # Resume sync
```

#### sync:history
List version history for a file in sync.

```bash
obsidian sync:history file="My Note"

# Count versions
obsidian sync:history file="My Note" --total
```

#### sync:read
Read a specific sync version.

```bash
obsidian sync:read file="My Note" version=5
```

#### sync:restore
Restore a file to a previous sync version.

```bash
obsidian sync:restore file="My Note" version=3
```

#### sync:deleted
List files deleted in sync.

```bash
obsidian sync:deleted

# Count
obsidian sync:deleted --total
```

#### sync:open
Open sync history UI.

```bash
obsidian sync:open file="My Note"
```

#### history
List local file history versions.

```bash
obsidian history file="My Note"

# By path
obsidian history path="Journal/2026-02-28.md"
```

#### history:read
Read a local history version.

```bash
obsidian history:read file="My Note" version=2
```

#### history:restore
Restore from local history.

```bash
obsidian history:restore file="My Note" version=1
```

#### diff
Compare local and sync versions.

```bash
obsidian diff file="My Note"

# Diff specific versions
obsidian diff file="My Note" from=1 to=5

# Filter by source
obsidian diff file="My Note" filter=local
obsidian diff file="My Note" filter=sync
```

### Plugins

#### plugins
List all installed plugins.

```bash
obsidian plugins

# Core plugins only
obsidian plugins filter=core

# Community plugins
obsidian plugins filter=community

# Include versions
obsidian plugins --versions

# JSON format
obsidian plugins format=json
```

#### plugins:enabled
List enabled plugins.

```bash
obsidian plugins:enabled

# By type
obsidian plugins:enabled filter=core
```

#### plugin
Get info about a plugin.

```bash
obsidian plugin id=dataview
```

#### plugin:enable
Enable a plugin.

```bash
obsidian plugin:enable id=dataview
```

#### plugin:disable
Disable a plugin.

```bash
obsidian plugin:disable id=templater
```

#### plugin:install
Install a community plugin.

```bash
# Install and enable
obsidian plugin:install id=obsidian-git --enable

# Just install
obsidian plugin:install id=dataview
```

#### plugin:uninstall
Remove a plugin.

```bash
obsidian plugin:uninstall id=templater
```

#### plugin:reload
Reload a plugin (development use).

```bash
obsidian plugin:reload id=my-plugin
```

#### plugins:restrict
Toggle restricted mode.

```bash
obsidian plugins:restrict on    # Enable restricted mode

obsidian plugins:restrict off   # Disable restricted mode
```

### Themes

#### themes
List installed themes.

```bash
obsidian themes

# Include versions
obsidian themes --versions
```

#### theme
Get current theme or info about a theme.

```bash
obsidian theme                  # Show active theme

obsidian theme name=Obsidian    # Info about a theme
```

#### theme:set
Set active theme.

```bash
obsidian theme:set name=Obsidian

# Back to default
obsidian theme:set name=""
```

#### theme:install
Install community theme.

```bash
obsidian theme:install name="Minimal" --enable

# Just install
obsidian theme:install name="Things"
```

#### theme:uninstall
Remove theme.

```bash
obsidian theme:uninstall name="Minimal"
```

### Snippets (CSS)

#### snippets
List CSS snippets.

```bash
obsidian snippets
```

#### snippets:enabled
List enabled snippets.

```bash
obsidian snippets:enabled
```

#### snippet:enable
Enable a CSS snippet.

```bash
obsidian snippet:enable name="hide-metadatablock"
```

#### snippet:disable
Disable a CSS snippet.

```bash
obsidian snippet:disable name="custom-colors"
```

### Commands & Hotkeys

#### commands
List all available Obsidian command IDs.

```bash
obsidian commands

# Filter by prefix
obsidian commands filter=editor
```

#### command
Execute an Obsidian command.

```bash
obsidian command id=editor:save-file
```

#### hotkeys
List hotkeys (keyboard shortcuts).

```bash
obsidian hotkeys

# Verbose (show if custom or default)
obsidian hotkeys --verbose

# Include all (even commands without hotkeys)
obsidian hotkeys --all

# Count
obsidian hotkeys --total
```

#### hotkey
Get hotkey for a specific command.

```bash
obsidian hotkey id=editor:save-file --verbose
```

### Workspaces

#### workspaces
List saved workspaces.

```bash
obsidian workspaces

# Count
obsidian workspaces --total
```

#### workspace
Show workspace tree.

```bash
obsidian workspace

# Include workspace item IDs
obsidian workspace --ids
```

#### workspace:save
Save current layout as a workspace.

```bash
obsidian workspace:save name="Writing"

obsidian workspace:save name="Development"
```

#### workspace:load
Load a saved workspace.

```bash
obsidian workspace:load name="Writing"
```

#### workspace:delete
Delete a saved workspace.

```bash
obsidian workspace:delete name="Old Workspace"
```

### Tabs & Windows

#### tabs
List open tabs.

```bash
obsidian tabs

# Include tab IDs
obsidian tabs --ids
```

#### tab:open
Open a new tab.

```bash
obsidian tab:open file="Journal/2026-02-28.md"

# Specific group
obsidian tab:open group=main-group file="Note"

# View type
obsidian tab:open view=search
```

### Utility & Navigation

#### open
Open a file in editor (same as `open` in File Operations).

```bash
obsidian open file="Note"
```

#### random
Open a random note.

```bash
obsidian random

# From folder
obsidian random folder="Journal"

# In new tab
obsidian random --newtab
```

#### random:read
Read a random note.

```bash
obsidian random:read

# From folder
obsidian random:read folder="Ideas"
```

#### recents
List recently opened files.

```bash
obsidian recents

# Count
obsidian recents --total
```

#### outline
Show headings in a file.

```bash
obsidian outline file="Project Plan"

# Tree format (default)
obsidian outline file="Project Plan" format=tree

# Markdown format
obsidian outline file="Project Plan" format=md

# JSON format
obsidian outline file="Project Plan" format=json

# Count only
obsidian outline file="Project Plan" --total
```

#### reload
Reload the vault.

```bash
obsidian reload
```

#### restart
Restart Obsidian completely.

```bash
obsidian restart
```

#### version
Show Obsidian version.

```bash
obsidian version
```

### Developer Tools

#### dev:screenshot
Take a screenshot of Obsidian UI.

```bash
obsidian dev:screenshot path=screenshot.png
```

#### dev:console
Show captured console messages.

```bash
obsidian dev:console

# Filter by level
obsidian dev:console level=error

# Clear buffer
obsidian dev:console --clear

# Limit output
obsidian dev:console limit=20
```

#### dev:errors
Show captured errors.

```bash
obsidian dev:errors

# Clear
obsidian dev:errors --clear
```

#### dev:debug
Attach/detach Chrome DevTools debugger.

```bash
obsidian dev:debug on   # Attach

obsidian dev:debug off  # Detach
```

#### dev:dom
Query DOM elements.

```bash
# Find elements
obsidian dev:dom selector=".cm-editor"

# Get text
obsidian dev:dom selector=".status-bar" --text

# Count matches
obsidian dev:dom selector="button" --total

# Get attribute
obsidian dev:dom selector="a.link" attr=href

# Get CSS property
obsidian dev:dom selector=".title" css=color
```

#### dev:css
Inspect CSS with source locations.

```bash
obsidian dev:css selector=".heading"

# Filter by property
obsidian dev:css selector=".text" prop=color
```

#### dev:cdp
Run Chrome DevTools Protocol command.

```bash
obsidian dev:cdp method=Page.printToPDF params='{"path":"output.pdf"}'
```

#### dev:mobile
Toggle mobile emulation.

```bash
obsidian dev:mobile on   # Enable

obsidian dev:mobile off  # Disable
```

#### devtools
Toggle Electron dev tools.

```bash
obsidian devtools
```

#### eval
Execute JavaScript in Obsidian context.

```bash
obsidian eval code='app.vault.getMarkdownFiles().length'

# Get custom object
obsidian eval code='app.workspace.activeEditor?.file?.name'
```

## Common Patterns for GOBI Vault

### Reading Daily Notes
```bash
# Today's journal
obsidian read file="Journal"

# Specific date
obsidian read path="Journal/2026-02-28.md"
```

### Appending to Journal
```bash
obsidian append file="Journal" content="\n## Reflection\n[Your thoughts]"
```

### Finding Todos
```bash
# All incomplete tasks
obsidian tasks --todo

# TODOs in projects
obsidian search query="TODO" path="Projects"
```

### Getting File Properties
```bash
# Read specific property
obsidian property:read name=tags file="Article"

# All properties on a file
obsidian properties file="My Note"
```

### Searching Your Vault
```bash
# Find by keyword
obsidian search query="machine learning" limit=10

# In specific folder
obsidian search query="meeting" path="Work"

# Case-sensitive
obsidian search query="MyClass" --case
```

### Managing Projects
```bash
# List all project files
obsidian files folder="Projects"

# Get project outline
obsidian outline file="Project X"

# Search project issues
obsidian search query="BUG:" path="Projects/ProjectX"
```

### Working with Tags
```bash
# All tags and their counts
obsidian tags --counts

# Files with tag
obsidian tag name=important --verbose

# Tags in article
obsidian tags file="Article"
```

## Discovering Options

Every command has built-in help. Use `obsidian help` to learn more:

```bash
# List all commands
obsidian help

# Help for specific command
obsidian help read
obsidian help search
obsidian help property:set

# Short help (in command output)
obsidian <command>
```

## Quality Checklist

Before using obsidian CLI commands:

- [ ] Obsidian is running and responding
- [ ] Correct vault targeted (if using `vault=` parameter)
- [ ] File name or path is correct
  - Use `file=` for name-based lookup
  - Use `path=` for exact vault-root paths
- [ ] Parameters quoted if containing spaces
- [ ] Output format appropriate (json/tsv/csv available for most commands)
- [ ] Understand the difference between metadata (properties/tags) and content

## Error Handling

### Common Issues

**"Obsidian is not running"**
- Solution: Start Obsidian before running CLI commands. The CLI requires IPC connection.

**"Vault not found"**
- Solution: Use `obsidian vaults` to list available vaults, then specify `vault="Name"`

**"File not found"** (with `file=` parameter)
- Solution: Verify file exists with `obsidian files`. Consider using `path=` instead for exact match.

**"Permission denied"**
- Solution: Ensure you have read/write permissions in Obsidian vault folder and plugins are not interfering.

### Debug Commands

```bash
# Check vault status
obsidian vault

# List all files
obsidian files --total

# Test search
obsidian search query="test" limit=1

# Check version
obsidian version
```

---

**Next Steps**: Run `obsidian help` to explore specific commands, or use pattern examples above for GOBI vault operations.
