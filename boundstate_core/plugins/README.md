# BoundState Secure Plugin System

## Overview

The BoundState plugin system has been redesigned for security. Plugins are now defined using JSON files instead of Python code to prevent arbitrary code execution vulnerabilities.

## Security Changes

**Old System (DEPRECATED):**
- Python files (`.py`) that could execute arbitrary code
- Security risk: Plugins had full Python runtime access
- No sandboxing or validation

**New System (SECURE):**
- JSON files (`.json`) with declarative rules only
- No code execution
- Validated patterns with ReDoS protection
- Signed plugin support (optional)

## Plugin Format

Plugins must be JSON files with the following structure:

```json
{
    "name": "plugin_name",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "Plugin description",
    "rules": [
        {
            "tag": "TagName",
            "pattern": "\\bregex\\spattern\\b",
            "description": "What this rule matches",
            "case_sensitive": false,
            "priority": 0
        }
    ]
}
```

### Field Descriptions

- `name`: Unique plugin identifier
- `version`: Semantic version (x.y.z)
- `author`: Plugin author name
- `description`: Human-readable description
- `rules`: Array of tagging rules
  - `tag`: Tag to apply when pattern matches
  - `pattern`: Regular expression pattern (JSON-escaped)
  - `description`: Rule description (optional)
  - `case_sensitive`: Whether pattern is case-sensitive (default: true)
  - `priority`: Rule priority for conflict resolution (default: 0)

## Security Features

1. **Pattern Length Limit**: Maximum 500 characters to prevent ReDoS attacks
2. **Rule Count Limit**: Maximum 100 rules per plugin
3. **Dangerous Pattern Detection**: Patterns with catastrophic backtracking potential are rejected
4. **Field Validation**: Only allowed fields are processed
5. **Signature Support**: Optional cryptographic signatures for plugin verification

## Migration Guide

To convert a Python plugin to JSON:

1. Extract the rules from the `get_rules()` function
2. Convert each `(tag, re.compile(...))` tuple to a JSON rule object
3. Escape regex patterns for JSON (double backslashes)
4. Add metadata fields (name, version, author, description)

Example conversion:

**Python (old):**
```python
("Safety", re.compile(r'\b(hazard|risk)\b', re.IGNORECASE))
```

**JSON (new):**
```json
{
    "tag": "Safety",
    "pattern": "\\b(hazard|risk)\\b",
    "case_sensitive": false
}
```

## Available Plugins

- `amentum_rules.json`: Defense and aerospace industry tagging

## Deprecated Files

The following Python plugin files are deprecated and will be removed:
- `amentum_rules.py` (use `amentum_rules.json` instead)

## Creating New Plugins

1. Create a new `.json` file in this directory
2. Follow the plugin format above
3. Test your patterns for validity and performance
4. Avoid patterns that could cause catastrophic backtracking
5. Keep patterns focused and specific

## Plugin Loading

Plugins are automatically loaded when the tagging system initializes. The secure loader will:
1. Only read `.json` files
2. Validate all fields and patterns
3. Compile patterns with protection against ReDoS
4. Log any errors or warnings
5. Skip invalid plugins without affecting the system

For more information, see `boundstate/secure_plugins.py`.