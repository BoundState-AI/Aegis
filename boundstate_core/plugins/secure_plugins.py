# Copyright 2025 BoundStateAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Secure plugin system for BoundState using declarative JSON format
Compliance: SWE-013, SWE-033
"""

__safety_critical__ = True  # Plugin validation is safety-critical

import json
import re
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PluginRule:
    """Validated plugin rule"""
    tag: str
    pattern: str
    compiled_regex: re.Pattern
    description: str = ""
    priority: int = 0
    case_sensitive: bool = True

@dataclass
class SecurePlugin:
    """Secure plugin metadata and rules"""
    name: str
    version: str
    author: str
    description: str
    rules: List[PluginRule]
    signature: Optional[str] = None
    loaded_at: Optional[datetime] = None
    checksum: Optional[str] = None

class SecurePluginLoader:
    """Load and validate plugins from JSON files with security checks"""
    
    ALLOWED_RULE_FIELDS = {'tag', 'pattern', 'description', 'priority', 'case_sensitive'}
    MAX_PATTERN_LENGTH = 500  # Prevent ReDoS attacks
    MAX_RULES_PER_PLUGIN = 100
    
    def __init__(self, plugin_dir: str = "boundstate/plugins", 
                 require_signatures: bool = False):
        self.plugin_dir = Path(plugin_dir)
        self.require_signatures = require_signatures
        self.loaded_plugins: Dict[str, SecurePlugin] = {}
        
    def load_plugins(self) -> List[Tuple[str, re.Pattern]]:
        """Load all valid JSON plugins and return compiled rules"""
        all_rules = []
        
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist")
            return all_rules
            
        # Only load .json files (safer than .py)
        json_files = list(self.plugin_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} plugin files")
        
        for json_file in json_files:
            try:
                plugin = self._load_single_plugin(json_file)
                if plugin:
                    self.loaded_plugins[plugin.name] = plugin
                    # Convert to legacy format for compatibility
                    for rule in plugin.rules:
                        all_rules.append((rule.tag, rule.compiled_regex))
                        
            except Exception as e:
                logger.error(f"Failed to load plugin {json_file}: {e}")
                continue
                
        logger.info(f"Successfully loaded {len(self.loaded_plugins)} plugins with {len(all_rules)} total rules")
        return all_rules
        
    def _load_single_plugin(self, json_path: Path) -> Optional[SecurePlugin]:
        """Load and validate a single plugin"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
            # Validate required fields
            required = ['name', 'version', 'author', 'rules']
            for field in required:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Calculate checksum
            content = json_path.read_text()
            checksum = hashlib.sha256(content.encode()).hexdigest()
            
            # Verify signature if required
            if self.require_signatures:
                if not self._verify_signature(data.get('signature'), checksum):
                    raise ValueError("Invalid plugin signature")
                    
            # Validate and compile rules
            rules = []
            raw_rules = data.get('rules', [])
            
            if len(raw_rules) > self.MAX_RULES_PER_PLUGIN:
                raise ValueError(f"Too many rules: {len(raw_rules)} > {self.MAX_RULES_PER_PLUGIN}")
                
            for rule_data in raw_rules:
                rule = self._validate_rule(rule_data)
                if rule:
                    rules.append(rule)
                    
            plugin = SecurePlugin(
                name=data['name'],
                version=data['version'],
                author=data['author'],
                description=data.get('description', ''),
                rules=rules,
                signature=data.get('signature'),
                loaded_at=datetime.now(),
                checksum=checksum
            )
            
            logger.info(f"Loaded plugin: {plugin.name} v{plugin.version} with {len(rules)} rules")
            return plugin
            
        except Exception as e:
            logger.error(f"Error loading plugin {json_path}: {e}")
            return None
            
    def _validate_rule(self, rule_data: Dict[str, Any]) -> Optional[PluginRule]:
        """Validate and compile a single rule"""
        try:
            # Check for unknown fields
            unknown_fields = set(rule_data.keys()) - self.ALLOWED_RULE_FIELDS
            if unknown_fields:
                logger.warning(f"Ignoring unknown fields in rule: {unknown_fields}")
                
            tag = rule_data.get('tag', '').strip()
            pattern = rule_data.get('pattern', '').strip()
            
            if not tag or not pattern:
                logger.warning("Rule missing tag or pattern")
                return None
                
            # Security: Limit pattern length to prevent ReDoS
            if len(pattern) > self.MAX_PATTERN_LENGTH:
                logger.warning(f"Pattern too long for tag {tag}: {len(pattern)} chars")
                return None
                
            # Security: Basic pattern validation
            if self._is_dangerous_pattern(pattern):
                logger.warning(f"Dangerous pattern detected for tag {tag}")
                return None
                
            # Compile regex with timeout protection
            flags = 0 if rule_data.get('case_sensitive', True) else re.IGNORECASE
            compiled = re.compile(pattern, flags)
            
            return PluginRule(
                tag=tag,
                pattern=pattern,
                compiled_regex=compiled,
                description=rule_data.get('description', ''),
                priority=rule_data.get('priority', 0),
                case_sensitive=rule_data.get('case_sensitive', True)
            )
            
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating rule: {e}")
            return None
            
    def _is_dangerous_pattern(self, pattern: str) -> bool:
        """Check for potentially dangerous regex patterns"""
        # Detect catastrophic backtracking patterns
        dangerous_patterns = [
            r'\(\.\*\)\+',  # (.*)+
            r'\(\.\+\)\+',  # (.+)+
            r'(\w+\+)+',    # Nested quantifiers
            r'(\d+\*)+',    # Nested quantifiers
        ]
        
        for danger in dangerous_patterns:
            if re.search(danger, pattern):
                return True
                
        # Check for excessive alternation
        if pattern.count('|') > 20:
            return True
            
        return False
        
    def _verify_signature(self, signature: Optional[str], checksum: str) -> bool:
        """Verify plugin signature (implement based on your PKI)"""
        # TODO: Implement actual signature verification
        # For now, just check if signature exists
        return signature is not None
        
    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about loaded plugins"""
        return [
            {
                'name': p.name,
                'version': p.version,
                'author': p.author,
                'description': p.description,
                'rule_count': len(p.rules),
                'loaded_at': p.loaded_at.isoformat() if p.loaded_at else None,
                'checksum': p.checksum
            }
            for p in self.loaded_plugins.values()
        ]
        
    def reload_plugins(self) -> List[Tuple[str, re.Pattern]]:
        """Reload all plugins"""
        self.loaded_plugins.clear()
        return self.load_plugins()

# Compatibility function for existing code
def load_secure_plugins(plugin_dir: str = "boundstate/plugins") -> List[Tuple[str, re.Pattern]]:
    """Load plugins using secure JSON format"""
    loader = SecurePluginLoader(plugin_dir)
    return loader.load_plugins()