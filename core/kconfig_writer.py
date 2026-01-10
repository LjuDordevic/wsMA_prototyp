from pathlib import Path
from typing import List, Optional
import re

class KconfigLine:
    """
    one line
    """
    def __init__(self, raw_text: str, line_number: int, line_type: str = None):
        self.raw_text = raw_text
        self.line_number = line_number
        self.stripped = raw_text.strip()
        self.indent = len(raw_text) - len(raw_text.lstrip())
        
        # parse line typ
        self.line_type = self._detect_type()
        self.content = self._extract_content()
    
    # all keywords 
    def _detect_type(self) -> str:
        s = self.stripped
        source_keyword_pattern = r'^(source|osource|rsource|orsource)\s+["\']'
        # because Kconfiglib can read these for backward compatibility
        grsource_keyword_pattern = r'^(grsource)\s+["\']'   # orsource
        gsource_keyword_pattern = r'^(gsource)\s+["\']'     # osource
        source_match = re.match(source_keyword_pattern, s)
        grsource_match= re.match(grsource_keyword_pattern, s)
        gsource_match = re.match(gsource_keyword_pattern, s)
        inline_prompt_choice_pattern = r'\s*(bool|tristate)\s+"([^"]*)"'
        inline_prompt_choice_match = re.match(inline_prompt_choice_pattern, s)
        
        if not s:
            return 'empty'
        elif re.match(r'^#\s+\w+', s):
            return 'commented'
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
            if re.match(r'^choice\s+\w+', s):
                return 'named_choice'
            else:
                return 'choice'
        elif s.startswith('endchoice'): 
            return 'endchoice'
        elif s.startswith('configdefault '):
            return 'configdefault'      
        elif re.match(r'^if\s+[A-Za-z0-9_-]+$', s):
            return 'if'
        elif s.startswith('endif'): 
            return 'endif'
        elif source_match:
            return source_match.group(1)
        elif grsource_match:
            return 'orsource'
        elif gsource_match:
            return 'osource'
        elif inline_prompt_choice_match:
            return 'inline_prompt_choice'
        elif re.match(r'^\s*(bool|boolean)\s*$', s):
            return 'type_bool'
        elif re.match(r'^\s*(tristate)\s*$', s):
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
        
        elif s.startswith('option env'):
            return 'option env'
        elif s.startswith('option allnoconfig_y'):
            return 'allnoconfig_y'
        elif s.startswith('option defconfig_list'):
            return 'defconfig_list'        
        elif s.startswith('option modules'):
            return 'option modules'
        elif s.startswith('modules'):
            return 'modules'
        elif s.startswith('warning'):
            return 'warning'
        elif s.startswith('set '):
            return 'set'
        elif s.startswith('set default '):
            return 'set_default'
        else:
            return 'other'
    
    def _extract_content(self) -> dict:
        line_stripped = self.stripped
        content = {}

        if self.line_type == 'empty':
            return
        
        if self.line_type == 'comment':
            return

        if self.line_type == 'config':
            match = re.match(r'config\s+(\w+)', line_stripped)
            if match:
                content['symbol'] = match.group(1)

        if self.line_type == 'menuconfig':
            match = re.match(r'menuconfig\s+(\w+)', line_stripped)
            if match:
                content['symbol'] = match.group(1)

        elif self.line_type == 'configdefault':
            match = re.match(r'configdefault\s+(\w+)', line_stripped)
            if match:
                content['symbol'] = match.group(1)
        
        elif self.line_type == 'default':
            rest = line_stripped[len("default"):].strip()
            split_rest = rest.split(' if ', 1)
            content['value'] = split_rest[0].strip()
            content['condition'] = split_rest[1].strip() if len(split_rest) > 1 else None
        
        elif self.line_type.startswith('def_'):
            def_keyword = self.line_type                    # == def_bool, def_int, def_hex, def_string
            rest = line_stripped[len(def_keyword):].strip() # == value + if <expr>
            #print('def_keyword: ' + def_keyword)
            #print('rest: ' + rest)

            _keyword = def_keyword.split('_', 1)
            content['_keyword'] = _keyword[1].strip()       # save after _: bool, string, hex, int 
            #print(f"_keyword: {_keyword}")
            #print(_keyword[1])  

            split_rest = rest.split(' if ', 1)              # split one time
            #print(f"split_rest: {split_rest}")
            content['default_value'] = split_rest[0].strip()
            content['condition'] = split_rest[1].strip() if len(split_rest) > 1 else None
        
        elif self.line_type == 'option env':
            content['env'] = line_stripped.split('"')[1]

        elif self.line_type == 'prompt':
            content['prompt_text'] = line_stripped.split('"')[1]

        elif self.line_type == 'inline_prompt_choice':
            match = re.match(r'\s*(bool|tristate)\s+"([^"]*)"', line_stripped)
            content['inline_typ'] = match.group(1)
            content['prompt_text'] = match.group(2)


        elif self.line_type == 'named_choice':
            match = re.match(r'^choice\s+(\w+)', line_stripped)
            content['name'] = match.group(1)
        return content
    
    def __repr__(self):
        return f"KconfigLine({self.line_type}, line={self.line_number}, indent={self.indent})"

class KconfigReader:
    def __init__(self, spec_version: str):
        self.spec_version = spec_version.upper()
    
    def read_file(self, file_path: Path) -> List[KconfigLine]:
        """
        read file -> give list of lines 
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Kconfig file not found: {file_path}")
        
        lines = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, raw_line in enumerate(f, start=1):
                raw_line = raw_line.rstrip('\n\r')
                kconfig_line = KconfigLine(raw_line, line_num)
                lines.append(kconfig_line)
        print(f"\n")
        print(f"Reader found: {len(lines)} lines in {str(file_path)}")
        return lines
    
    def read_single_line(self, file_path: Path, line_number: int) -> List[KconfigLine]:
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for current_line_num, raw_line in enumerate(f, start=1):
                    if current_line_num == line_number:
                        raw_line = raw_line.rstrip('\n\r')       
                        kconfig_line = KconfigLine(raw_line, line_number)
                        return kconfig_line
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
        
        return None

class KconfigWriter:   
    def __init__(self, spec_version: str):
        self.spec_version = spec_version.upper()
    
    def write(self, lines: List[KconfigLine], output_path: Path):
        """
        write lines -> output file
        """        
        with open(output_path, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line.raw_text + '\n') # add EOL 
                 
        print(f"        Done writting {len(lines)} lines in {output_path}")
