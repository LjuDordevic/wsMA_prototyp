from pathlib import Path
from typing import List, Optional, Tuple
import re

class KconfigLine:
    """
    one line
    """
    def __init__(self, raw_text: str, line_number: int):
        self.raw_text = raw_text
        self.line_number = line_number
        self.stripped = raw_text.strip()
        self.indent = len(raw_text) - len(raw_text.lstrip())
        
        # parse line typ
        self.line_type = self._detect_type()
        self.content = self._extract_content()
    
    def _detect_type(self) -> str:
        s = self.stripped
        
        if not s or s.startswith('#'):
            return 'empty'
        elif s.startswith('mainmenu '):
            return 'mainmenu'
        elif s.startswith('menu '):
            return 'menu'
        elif s.startswith('endmenu'):
            return 'endmenu'
        elif s.startswith('comment'):
            return 'comment'
        
        elif s.startswith('config '): 
            return 'config'
        elif s.startswith('menuconfig '):
            return 'menuconfig'
        elif s.startswith('choice'):
            return 'choice'
        elif s.startswith('endchoice'): 
            return 'endchoice'
        elif s.startswith('configdefault '):
            return 'configdefault'      
        elif s.startswith('if '):
            return 'if'
        elif s.startswith('endif'): 
            return 'endif'
        
        elif s.startswith('source '):
            return 'source'
        elif s.startswith('osource '):
            return 'osource'
        elif s.startswith('rsource '):
            return 'rsource'
        elif s.startswith('orsource '):
            return 'orsource' 

        elif s.startswith('bool') or s.startswith('boolean'):
            return 'type_bool'
        elif s.startswith('tristate'):
            return 'type_tristate'
        elif s.startswith('int'):
            return 'type_int'
        elif s.startswith('hex'):
            return 'type_hex'
        elif s.startswith('string'):
            return 'type_string'
        elif s.startswith('def_bool'):
            return 'def_bool'
        elif s.startswith('def_tristate'):
            return 'def_tristate'
        elif s.startswith('def_int'):
            return 'def_int'
        elif s.startswith('def_hex'):
            return 'def_hex'
        elif s.startswith('def_string'):
            return 'def_string'
        
        elif s.startswith('default '): 
            return 'default'
        elif s.startswith('prompt '):
            return 'prompt'
        elif s.startswith('depends on '):
            return 'depends_on'
        elif s.startswith('select '):
            return 'select'
        elif s.startswith('imply '):
            return 'imply'
        elif s.startswith('range '):
            return 'range'
        elif s.startswith('help') or s.startswith('---help---'):
            return 'help'
        elif s.startswith('optional'):
            return 'optional'
        elif s.startswith('visible if '):
            return 'visible if'
        
        elif s.startswith('allnoconfig_y'):
            return 'allnoconfig_y'
        elif s.startswith('defconfig_list'):
            return 'defconfig_list'
        elif s.startswith('option env'):
            return 'option env'
        elif s.startswith('option modules'):
            return 'option modules'

        else:
            return 'other'
    
    def _extract_content(self) -> dict:
        s = self.stripped
        content = {}
        
        if self.line_type == 'config':
            # config SYMBOL_NAME
            match = re.match(r'config\s+(\w+)', s)
            if match:
                content['symbol'] = match.group(1)
        
        elif self.line_type == 'menuconfig':
            # menuconfig SYMBOL_NAME
            match = re.match(r'menuconfig\s+(\w+)', s)
            if match:
                content['symbol'] = match.group(1)

        return content
    
    def __repr__(self):
        return f"KconfigLine({self.line_type}, line={self.line_number}, indent={self.indent})"
