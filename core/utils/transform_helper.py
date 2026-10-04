from pathlib import Path
from typing import List, Optional, Tuple
from core.context.context import ExtParserContext

class TransformHelperUtils:

    def create_extended_condition(self, original_condition, deps_ext) -> str:
        conditions = []
        
        if original_condition:
            conditions.append(original_condition)
        
        for dep in deps_ext:
            if dep not in conditions:
                conditions.append(dep)

        return " && ".join(conditions) if conditions else ""
 
    def extract_dependencies(self, dep_element) -> list[str]:
        dependencies = []
        
        if hasattr(dep_element, 'name'):
            return [dep_element.name]
        
        if isinstance(dep_element, tuple):
            for item in dep_element:
                if hasattr(item, 'name'):
                    dependencies.append(item.name)
                elif isinstance(item, tuple):
                    dependencies.extend(self._extract_dependencies(item))
        
        return dependencies
  
    def extract_value(self, d_value) -> str | int | float | None:
        if d_value is None:
            return None
        #print(f"xx {d_value}")

        if hasattr(d_value, "value"):
            v = getattr(d_value, "value")
            if isinstance(v, (str, int, float)):
                #print(f"1 {d_value}")
                return v
    
        if hasattr(d_value, "str_value"):
            try:
                return d_value.str_value()
            except Exception: # not callable
                #print(f"2 {d_value}")
                pass

        if hasattr(d_value, "name"):
            #print(f"3 {d_value}")
            return getattr(d_value, "name")
        
        if isinstance(d_value, tuple):
                #print(f"4 {d_value}")
                return str("expr")

        # 5) Fallback: string representation
        return str(d_value)

    def get_last_config(self, ext_sym_def: List[Tuple]) -> Optional[Tuple]:
        last_config = None
        for entry in ext_sym_def:
            if not entry[3]:
                last_config = entry
        return last_config      

    def get_cd_entries(self, sym_def_list: List[Tuple]) -> List[Tuple[Tuple[str, int], List[str]]]:
        cd_entries = []
    
        for entry in sym_def_list:
            # entry[3] is_configdefault Flag
            # entry[4] defaults_list
            if entry[3]:  # True = configdefault
                defaults_list = entry[4]
             
                for default_entry in defaults_list:
                    loc = default_entry.get('loc')
                    deps_ext = default_entry.get('deps_ext', [])
                    
                    if loc:  
                        cd_entries.append((loc, deps_ext))
        
        return cd_entries

    def get_transformed_config_defaults(self, cd_entries, reader, project_dir: Path) -> List:
        from core.kconfig_writer import KconfigLine
        transformed_lines = []
        
        print("transform all extracted <default lines> from conifgdefaults - add them together")

        for loc, deps_ext in cd_entries:
            # transfom path from loc 
            file_path, line_number = loc
            full_path = project_dir / Path(file_path)
            print(f"    default line entry: {loc} --> {full_path}")
                    
            # Read the specific line for default line of configdefault_entry
            line_entry = reader.read_single_line(full_path, line_number)
            
            if line_entry is None:
                print(f"Warning: Could not read line {line_number} from {file_path}")
                continue

            # Check if content exists
            if line_entry.content is None:
                print(f"Warning: Line {line_number} from {file_path} has no content")
                continue
            
            # build if <...>
            content = line_entry.content or {}
            cond_full = self.create_extended_condition(content.get('condition'), deps_ext)
            
            # build line
            indent_str = " " * line_entry.indent
            line_value = line_entry.content.get('value')

            if cond_full:
                transformed_content = f"{indent_str}default {line_value} && {cond_full}"
            else:
                transformed_content = f"{indent_str}default {line_value}"
            
            default_line = KconfigLine(transformed_content, line_number)
            transformed_lines.append(default_line)
        
        print("print transformed lines")
        for line in transformed_lines:
            print(f"\n    {line}")
            if line.line_type != 'empty' and line.line_type != 'other':
                print(f"        -> Content: {line.content}")
        
        return transformed_lines
                     
    def if_block_contains_only_configdefault(self, lines, if_start_indx) -> bool:
        i = if_start_indx + 1
        has_configdefault = False
        nested_level = 1  
    
        while i < len(lines):
            line = lines[i]

            if line.line_type == 'if':
                nested_level += 1
                i += 1
                continue
            
            if line.line_type == 'endif':
                nested_level -= 1
                if nested_level == 0:
                    return has_configdefault
                i += 1
                continue
            
            if line.line_type in ['empty', 'comment']:
                i += 1
                continue
            
            if line.line_type == 'configdefault':
                has_configdefault = True
                i += 1
                while i < len(lines) and lines[i].indent > line.indent:
                    i += 1
                continue
            
            if line.line_type not in ['empty', 'comment', 'configdefault', 'endif']:
                return False
            
            i += 1
        
        return has_configdefault

    def skip_if_block(self, lines, if_start_index) -> int:
        if_indent = lines[if_start_index].indent
        i = if_start_index + 1
        nested_level = 1  

        while i < len(lines):
            line = lines[i]

            if line.line_type == 'if' and line.indent >= if_indent:
                nested_level += 1
            
            elif line.line_type == 'endif' and line.indent == if_indent:
                nested_level -= 1
                if nested_level == 0:
                    return i + 1  # index after endif
            
            i += 1

        return i

    def remove_consecutive_empty_lines(self, lines):
        """
        transformation of configdefault can leave some unwanted empty lines,
        so this function removes them 
        """
        cleaned = []
        previous_line_empty = False
        removed_nr = 0
        previous_len = len(lines)
        for line in lines:
            if line.line_type == 'empty':        # looking at empty line, so 
                if previous_line_empty:
                    removed_nr += 1
                    continue                     # skip this empty line, go check the next one           
                previous_line_empty = True       # if previous line wasn't empty, than set a flag on this one 
            else:
                previous_line_empty = False      # the line we are looking at it's not empty, so set the flag

            cleaned.append(line)
        
        # this lines are already counted through self.stats.file_skipped_bc_configdefault
        self.stats.file_removed_consecutive_empty_lines = previous_len - len(cleaned)
        #print(f"{self.stats.file_removed_consecutive_empty_lines} = {previous_len} - {len(cleaned)}")
        return cleaned
