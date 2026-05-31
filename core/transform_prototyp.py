from pathlib import Path
from posixpath import join, dirname
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass
from core.utils import ContextBuilder, TransformationStats, write_to_excel
from core.context.context import ExtParserContext
from core.utils.context_builder import ContextBuilder
from glob import iglob

class KconfigTransformer:
    DEF_KEYWORDS = ('def_string', 'def_int', 'def_hex')
    SOURCE_KEYWORDS = ('source', 'osource', 'rsource', 'orsource')

    def __init__(self, source_spec: str):
        self.source_spec = source_spec.upper()  # maybe for some later checks 
        self.context = None
        self.stats = TransformationStats()
        self.processed_choices = set()

    def initialize_context(self, parser_result: dict, log):
        self.context = ContextBuilder().build(parser_result, log)

    def _extract_named_choice_info(self, choice_name: str, log: bool, log_cd_nc_details: bool):
        context = self.context
        choice_infos = context.choice_infos
        choice_definitions = context.choice_definitions
        choice_deps = context.choice_dep    

        if choice_name not in choice_infos:
            return {
            'choice_def': []
            }
        
        default_dependencies_extracted_list = []
        node_dep_extracted_list = []
        if log_cd_nc_details:
            print("------H-----------")
            print(f"context.choice_infos:       {choice_infos}")
            print(f"context.choice_definitions: {choice_definitions}")
            print(f"context.choice_deps:        {choice_deps}\n")
            print(f"choice_deps[{choice_name}]:")
        
        for entry in choice_deps[choice_name]:
            default_tuple = entry['node.defaults']
            if log_cd_nc_details: print(f"node.defaults:   {default_tuple}")
            for default in default_tuple:
                default_dependencies = default[1]
                dependencies = self._extract_dependencies(default_dependencies)
                default_dependencies_extracted_list.append(dependencies)
             
            dep_tuple = entry['node.dep']
            if log_cd_nc_details: print(f"node.dep:        {repr(dep_tuple)}")
            extr_dep_dependencies = self._extract_dependencies(dep_tuple)
            node_dep_extracted_list.append(extr_dep_dependencies)

        if log:
            print(f"def dependencies extr: {default_dependencies_extracted_list}")
            print(f"dep dependencies extr: {node_dep_extracted_list}")
        
        choice_all_dep_list = []
        choice_all_dep_list.append((choice_name, default_dependencies_extracted_list, node_dep_extracted_list))
    
        print()
        return {
            'choice_def': choice_all_dep_list
        }
        
    def _extract_symbol_info(self, context: ExtParserContext, symbol_name: str):
       
        symbol_infos = context.symbol_infos
        symbol_definitions = context.symbol_definitions
        symbol_defaults = context.symbol_defaults

        if symbol_name not in symbol_infos:
            return {
            'sym_def': [],
            'def_dep': []
            }
        
        symbol_definitions_list = []

        if symbol_name in symbol_definitions:
            for location_info in symbol_definitions[symbol_name]: # filter symbol_def for given symbol 
                file = location_info.get('file')
                line = location_info.get('line')
                is_conf_def_flag = location_info.get('is_configdefault')
                node_defaults = location_info.get('node.defaults')
                #node_defs_dep = location_info.get('node.default.dep')
                #node_defs_loc = location_info.get('node.default.loc')
                #symbol_definitions_list.append((symbol_name, file, line, is_conf_def_flag, node_defs, node_defs_dep, node_defs_loc))
                
                """
                Examples of node_defaults entry:
                [(<symbol y, bool, value y, constant>, <symbol y, bool, value y, constant>, ('KconfigZephyrRTOS', 34))]
                --> extracted_node_defaults:
                [{'value_ext': 'y', 'deps_ext': ['y'], 'loc': ('KconfigZephyrRTOS', 34)}]

                [(<symbol y, bool, value y, constant>, (2, <symbol CN, bool, value n, visibility n, direct deps y, KconfigZephyrRTOS:18>, 
                (2, <symbol CY, bool, value n, visibility n, direct deps y, KconfigZephyrRTOS:15>, 
                <symbol ACCC, bool, value y, visibility n, direct deps y, Kconfig3:19>)), ('Kconfig3', 6))]
                --> extracted_node_defaults:
                [{'value_ext': 'y', 'deps_ext': ['CN', 'CY', 'ACCC'], 'loc': ('Kconfig3', 6)}]

                * if deps_exp == y, means ther's no [if <exp>] after default value
                  also deps_exp collects every dependency - form the symbol itself, from if-block, from menu depends on ...
                """
                extracted_node_defaults = []
                for (d_value, d_cond, d_loc) in node_defaults:
                    if_cond_ext = self._extract_dependencies(d_cond)
                    d_value_ext = self._extract_value(d_value)
                    extracted_node_defaults.append({
                        "value_ext": d_value_ext,
                        "deps_ext": if_cond_ext,       
                        "loc": d_loc
                    })
                
                symbol_definitions_list.append((symbol_name, file, line, is_conf_def_flag, extracted_node_defaults))

        #last_config_for_sym = self._get_last_config(symbol_definitions_list)
        #configdefault_entries = self._get_cd_entries(symbol_definitions_list)
        
        default_dependencies_list = []

        for entry in symbol_defaults[symbol_name]:
            default_tuple = entry['sym.default']
            default_location = default_tuple[2]
                
            default_dependencies = default_tuple[1]
            dependencies = self._extract_dependencies(default_dependencies)
                
            default_dependencies_list.append((symbol_name, default_location, dependencies))
            
        return {
            'sym_def' : symbol_definitions_list,
            #'last_config': last_config_for_sym,
            #'configdefaults': configdefault_entries,
            'def_dep' : default_dependencies_list
        }
    
    def _extract_dependencies(self, dep_element):
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

    def _extract_value(self, d_value):
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

    def _get_last_config(self, ext_sym_def: List[Tuple]) -> Optional[Tuple]:
        last_config = None
        for entry in ext_sym_def:
            if not entry[3]:
                last_config = entry
        return last_config      
    
    def _get_cd_entries(self, sym_def_list: List[Tuple]) -> List[Tuple[Tuple[str, int], List[str]]]:
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

    def _get_transformed_config_defaults(self, cd_entries, reader, project_dir: Path) -> List:
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
            cond_full = self._create_extended_condition(content.get('condition'), deps_ext)
            
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

    def _create_extended_condition(self, original_condition, deps_ext) -> str:
        conditions = []
        
        if original_condition:
            conditions.append(original_condition)
        
        for dep in deps_ext:
            if dep not in conditions:
                conditions.append(dep)

        return " && ".join(conditions) if conditions else ""

    def _get_all_source_files(self) -> List[Path]:
        """
        extract Kconfig files, that parser found 
        output: all paths that parser found, 
        these are either relativ to srctree = project_dir
        or are absolut paths "outside of srctree"
        """
        if self.context is None:
            raise RuntimeError("call build_context_from_parser() first")
            
        kconf = self.context.parser_result['kconf']
        files = []
        
        for filename in kconf.kconfig_filenames:
            file_path = Path(filename)
            files.append(file_path)
        print("    get_all_source_files: ")
        for file in files:
            print(f"    parser found: {file}")

        return files    

    def _transform_lines(self, lines: List, current_file: Path, cd_definition_info, choice_definition_info, log_and_check_resolve_glob):
            """
            lines -> from reader 
            """
            len_reader_input = len(lines)
            print(f"start transforming {len(lines)} input lines")
            if self.context is None:
                raise RuntimeError("call build_context_from_parser() first")
            
            result = []             # list for whole output  
            i = 0                   # counter
            current_symbol = None   
            while i < len(lines):
                cd_processed = False
                choice_processed = False
                line = lines[i]
                #print(f"hellooo {line}")     
                #print(f"\n while counter i: {i} given line: {line}")
                
                if line.line_type == 'if':
                    if_contains_only_configdefault = self._if_block_contains_only_configdefault(lines, i)
            
                    if if_contains_only_configdefault:
                        print(f"    Skipping if-endif block (only configdefaults) starting at line {line.line_number}")
                        old_i = i
                        i = self._skip_if_block(lines, i)
                        self.stats.file_skipped_bc_configdefault += (i - old_i)
                        continue

                if line.line_type == 'configdefault':
                    print(f"    Skipping configdefault block starting at line {line.line_number}")
                    self.stats.file_skipped_bc_configdefault += 1 # the configdefault line itself
                    i += 1

                    while i < len(lines) and lines[i].indent > line.indent:
                        print(f"      Skipping line {lines[i].line_number}: {lines[i].line_type}")
                        self.stats.file_skipped_bc_configdefault += 1
                        i += 1
                    # i = 1. line after the block 
                    continue

                if line.line_type == 'named_choice':
                    choice_name = line.content.get('name')
                    
                    if not choice_name or choice_name not in choice_definition_info:
                        pass  
  
                    else:
                        choice_info = choice_definition_info[choice_name]
                        #print(f"choice_definition_info: {choice_definition_info}")
                        #print(f"choice_info {choice_info}")
                        
                        #print(f"    processed_choices before if: {self.PROCESSED_CHOICES}")

                        if choice_name in self.PROCESSED_CHOICES:
                            print(f"    Skipping non-first definition of choice {choice_name} at line {line.line_number}, {current_file}")
                            # Skip until endchoice
                            #print(f"    before_i {i}")
                            self.stats.file_skipped_bc_named_choice += 1 # the choice line itself
                            i += 1
                            while i < len(lines) and lines[i].line_type != 'endchoice':
                                #print(f"        {lines[i]}")
                                self.stats.file_skipped_bc_named_choice += 1
                                i += 1
                            i += 1  # consume endchoice
                            self.stats.file_skipped_bc_named_choice += 1
                            #print(f"    after {i}")
                            #print("helloooend")     
                            continue
                        #print("helloooneu")
                        first_def = self.context.choice_definitions[choice_name][0]
                        first_def_file = self.context.srctree / first_def['file']
                        first_def_line = first_def['line']
                            
                        if (current_file == first_def_file and 
                            line.line_number == first_def_line):
                                
                            print(f"    Found first definition of choice {choice_name} at line {line.line_number}")
                            print(f"    Processing choice transformation")

                            self.PROCESSED_CHOICES.add(choice_name)
                            print(f"    processed_choices now: {self.PROCESSED_CHOICES}")

                            # IF THE FIRST PARAMETER = True, then we log DEBUG info 
                            i = self._transform_named_choice(True, lines, i, choice_info, result, 
                                                lambda l, s, f: self._transform_single_line(l, s, f, log_and_check_resolve_glob))
                            #choice_processed = True
                            continue
                
                if line.line_type == 'choice':
                    i = self._transform_choice(lines, i, result, 
                                                lambda l, s, f: self._transform_single_line(l, s, f, log_and_check_resolve_glob))
                    continue

                if line.line_type in ['config', 'menuconfig']:
                    #print("line is config/ menuconfig")
                    current_symbol = line.content.get('symbol')
                    #print(f"line's symbol: {current_symbol}")
                    
                    if current_symbol and current_symbol in cd_definition_info:
                        cd_info_list = cd_definition_info[current_symbol]
                        #print(f"\ncd_info_list: {cd_info_list}")

                        for cd_entry in cd_info_list:
                            last_config = cd_entry.get('last_config')
                            #print(f"\nlast_config: {last_config}")
                            transformed_entries = cd_entry.get('transformed_entries_list', [])
                            #print(f"transformed_entries: {transformed_entries}")

                            if last_config:
                                last_conf_symbol = last_config[0]
                                last_conf_file = last_config[1]
                                last_conf_line = last_config[2]
                                #print(f"last_conf_symbol: {last_conf_symbol}")
                                #print(f"last_conf_file: {last_conf_file}")
                                #print(f"last_conf_line: {last_conf_line}") 

                                last_conf_full_path = self.context.srctree / last_conf_file
                                #print(f"last_conf_full_path: {last_conf_full_path}")

                                if (current_symbol == last_conf_symbol and 
                                    line.line_number == last_conf_line and 
                                    current_file == last_conf_full_path):
                                    
                                    print(f"    Found matching config for {current_symbol} at line {line.line_number}")
                                    print(f"    Adding {len(transformed_entries)} configdefault entries")
                                    
                                    i = self._transform_cd(lines, i, transformed_entries, result, 
                                                lambda l, s, f: self._transform_single_line(l, s, f, log_and_check_resolve_glob))
                                    #print(f"i = self.transform_cd {i}")
                                    cd_processed = True
                                    break 
                
                if cd_processed:
                    continue

                #print(f"\nget transformed wenn line is not config/menuconfig:")
                transformed = self._transform_single_line(line, current_symbol, current_file, log_and_check_resolve_glob)
                
                #print(f"transformed: {transformed}")
                
                if transformed is None:
                    #print(f"transformed is non i++")
                    i += 1
                    continue
                
                if isinstance(transformed, list):
                    result.extend(transformed) # 1:n (def_bool → bool + default)
                else:
                    result.append(transformed) # 1:1         
                #print(f"after {i} is result: {result}")
                i += 1  # go to the next line
                            
            len_transformed_lines = len(result)
            # EXCEL stats
            #stats = self._log_file_and_reset_count(self.stats.file_source_out_diff, current_file, len_reader_input, len_transformed_lines)
            return result, self.stats.file_source_out_diff, len_reader_input, len_transformed_lines

    def _transform_choice(self, lines: List, current_index: int, result: List, transform_func) -> int:
        from core.kconfig_writer import KconfigLine
        import re

        choice_line = lines[current_index]        
        result.append(choice_line)

        #find endblock 
        end_line = None
        block_end_index = current_index + 1
        while block_end_index < len(lines):
            next_line = lines[block_end_index]   
            if next_line.line_type == 'endchoice':
                # copy this line, so that we can add it at the end of result 
                indent_str = ' ' * (next_line.indent)   
                new_line_text = f'{indent_str}endchoice'
                end_line = KconfigLine(new_line_text, next_line.line_number, line_type='endchoice')
                block_end_index += 1
                break
            block_end_index += 1
        
        # FIND line where first config/if starts
        first_ch_config_idx = None
        for idx in range(current_index + 1, block_end_index):
            if lines[idx].line_type in ['config', 'if']:
                first_ch_config_idx = idx
                break
        
        # CHOICE ATTR
        choice_attr_end = first_ch_config_idx if first_ch_config_idx is not None else block_end_index - 1
        print(f"    current_indx: {current_index + 1} - choice_attr_end: {choice_attr_end}")
        
        idx = current_index + 1
        while idx < choice_attr_end:
            line_item = lines[idx]
            #print(f"dahjskaj {line_item.line_type}")

            # SKIP: type attr (bool/tristate) & optional attr
            if line_item.line_type == 'optional':
                self.stats.file_skip_optional_choice_attr += 1 
                idx += 1
                continue
            if line_item.line_type == 'type_tristate':
                self.stats.file_skip_choice_typ_def_tristate += 1
                idx += 1
                continue
            if line_item.line_type == 'type_bool':
                self.stats.file_skip_choice_typ_def_bool += 1
                idx += 1
                continue
            if line_item.line_type == 'inline_prompt_choice':
                #inline_typ = line_item.content.get('inline_typ', '')
                indent_str = ' ' * line_item.indent
                prompt_text = line_item.content.get('prompt_text', '')
                new_prompt_line = f'{indent_str}prompt "{prompt_text}"'
                modified_line = KconfigLine(new_prompt_line, line_item.line_number)
                result.append(modified_line)
                self.stats.file_changed_inprompt_bc_choice += 1
                idx += 1
                continue

            # everything else: copy/transform as usual (because it's a first definition)
            transformed = transform_func(line_item, None, None)
            if transformed is None:
                idx += 1
                continue

            if isinstance(transformed, list):
                result.extend(transformed)
            else:
                result.append(transformed)  
            
            idx += 1

        # CHOICE ELEMENTS
        while idx < block_end_index - 1 and lines[current_index].line_type != 'endchoice':
            
            line_item = lines[idx]

            # IF CONFIG INSIDE CHOICE is type tristate 
            if line_item.line_type in ('type_tristate', 'inline_prompt_choice'):
                line_item = self._transform_typ_choice_help(line_item)

            # everything else: copy/transform as usual (because it's a first definition)
            transformed = transform_func(line_item, None, None)
            if transformed is None:
                idx += 1
                continue

            if isinstance(transformed, list):
                result.extend(transformed)
            else:
                result.append(transformed)  
            
            idx += 1

        result.append(end_line)

        #print(f"PROCESS choice: {result}")
        return block_end_index

    def _transform_named_choice(self, log_debug: bool, lines: List, current_index: int, choice_info: dict, result: List, transform_func) -> int:
        from core.kconfig_writer import KconfigLine
        
        choice_line = lines[current_index]        
        # save first line without name
        indent_str = ' ' * choice_line.indent
        anonymous_choice = KconfigLine(f'{indent_str}choice', choice_line.line_number, line_type='choice')
        result.append(anonymous_choice)
        
        # EXTEND DEPENDENCIES for depends on & default line -----------------------------------------------------------------
        # WRONG: from parser 
        # Find endchoice index
        end_line = None
        block_end_index = current_index + 1
        while block_end_index < len(lines):
            next_line = lines[block_end_index]   
            if next_line.line_type == 'endchoice':
                # copy this line, so that we can add it at the end of result 
                indent_str = ' ' * (next_line.indent)   
                new_line_text = f'{indent_str}endchoice'
                end_line = KconfigLine(new_line_text, next_line.line_number, line_type='endchoice')
                block_end_index += 1
                break
            block_end_index += 1
        
        # PROCESS: ATTR OF THE FIRST DEFINITION ----------------------------------------------------------------------------------------------
        # Kconfiglib can have menuconfig as choice elements (see wsMA_prototyp/test_dir_/transform_choice_analysis/transform_choice_analysis.log)
        print(f"    process lines until first choice config/if was found") 
        print(f"    current_indx: {current_index + 1} - block endidx {block_end_index}")
        
        # FIND line where first config/if starts ! Kconfiglib allows menuconfig as elements of choice Option
        first_ch_config_idx = None
        for idx in range(current_index + 1, block_end_index):
            if lines[idx].line_type in ['config', 'if', 'menuconfig']:
                first_ch_config_idx = idx
                break
        
        # PROCESS attr of choice ---------------------------------------------------------------------------------------------------- 
        choice_attr_end = first_ch_config_idx if first_ch_config_idx is not None else block_end_index
        print(f"    current_indx: {current_index + 1} - choice_attr_end: {choice_attr_end}")
        # save depends on of first definition -> add them to menuconfigs of the first definition 
        first_depends_on_for_mc = []
        
        for idx in range(current_index + 1, choice_attr_end):
            line_item = lines[idx]

            # SKIP: type attr (bool/tristate) & optional attr
            if line_item.line_type == 'optional':
                self.stats.file_skip_optional_choice_attr += 1 
                continue
            if line_item.line_type == 'type_tristate':
                self.stats.file_skip_choice_typ_def_tristate += 1
                continue
            if line_item.line_type == 'type_bool':
                self.stats.file_skip_choice_typ_def_bool += 1
                continue
            if line_item.line_type == 'inline_prompt_choice': 
                #inline_typ = line_item.content.get('inline_typ') Linux doesn't allow bool "..."
                indent_str = ' ' * (choice_line.indent + 2)
                line_text = line_item.content.get('prompt_text')
                new_prompt_line_text = f'{indent_str}prompt "{line_text}"'
                new_prompt_line=KconfigLine(new_prompt_line_text, line_item.line_number)
                result.append(new_prompt_line)
                self.stats.file_changed_inprompt_bc_choice += 1
                continue            
            if line_item.line_type == 'depends_on':
                first_depends_on_for_mc.append(line_item)
            
            # everything else: prompt, default, depends on, help -> copy/transform as usual (because it's a first definition)
            transformed = transform_func(line_item, None, None)
            if transformed is None:
                continue

            if isinstance(transformed, list):
                result.extend(transformed)
            else:
                result.append(transformed)  
        
        # PROCESS: ADD ATTR OF OTHER DEFINITIONS ----------------------------------------------------------------------------------------------
        """ 
        # TODO: function die umgehende if und depends on von menus verbindet, ggb. die lines aus dem File wo sich die 2. definition befindet, result add (self.get_dep_from_other_def)
        # ADD depends on and default lines with extended if-condition  
        # TODO: CHANGE: dont take from parser -> instead read lines and get there the extenden
        # also +2 it's just quick fix
        # TODO: add teh extenden default/ depends from other definitions 
        # WRONG: from parser overall, user default_dependencies_extracted_list, node_dep_extracted_list) -> 'choice_def': choice_all_dep_list
        """
        choice_def = choice_info.get('choice_def')
        choice_configs = choice_info.get('choice_configs', [])
        choice_prompts = choice_info.get('prompt_lines', [])
        help_lines = choice_info.get('help_lines', [])

        if log_debug:
            print(f"    DEBUGG: choice_def {choice_def}")
            print(f"    choice_configs length: {len(choice_configs)}")
            print(f"    choice_configs {choice_configs}")
            print(f"    choice_prompts {choice_prompts}")
            print(f"    help_lines {help_lines}")

            for idx, cfg in enumerate(choice_configs):
                print(f"    [{idx}] type={cfg.get('type')}, symbol={cfg.get('symbol')}, symbols={cfg.get('symbols')}, choice_line={cfg.get('choice_line')}")
        
        menuconfigs_to_add_after = []  # Collect menuconfigs to add after endchoice
        len_menuconfig_block_first_def = 0

        # dont add choice_prompts and help_lines here bc doppel, add them later   
        if not choice_def:
            print(f"    No choice_def found")
        else:
            # Unpack the single entry
            _, all_default_deps, all_node_deps = choice_def[0]
            
            if log_debug:
                print(f"    all_default_deps: {all_default_deps}")
                print(f"    all_node_deps: {all_node_deps}")
            
            # Group configs by choice_line to identify which definition they belong to
            configs_by_definition = {}
            for cfg in choice_configs:
                cfg_choice_line = cfg.get('choice_line')
                if cfg_choice_line not in configs_by_definition:
                    configs_by_definition[cfg_choice_line] = []
                configs_by_definition[cfg_choice_line].append(cfg)
            
            # Sort by choice_line to get definitions in order
            sorted_def_lines = sorted(configs_by_definition.keys())
            print(f"    Found {len(sorted_def_lines)} choice definitions at lines: {sorted_def_lines}")
            
            def_index_by_line = {
                line: idx for idx, line in enumerate(sorted_def_lines)
            }

            depends_by_choice_line = {}  # Map: choice_line -> depends_from_def Liste
            
            # Process each definition (skip the first one, index 0)
            # so that we get all depends on/defaults and elements
            for def_idx in range(1, len(sorted_def_lines)):
                depends_from_def = []
                choice_line_num = sorted_def_lines[def_idx]
                configs_in_this_def = configs_by_definition[choice_line_num]
                
                # Get dependencies for this definition
                default_deps = all_default_deps[def_idx] if def_idx < len(all_default_deps) else []
                node_deps = all_node_deps[def_idx] if def_idx < len(all_node_deps) else []
                
                print(f"\n  Processing definition {def_idx} at line {choice_line_num}")
                if log_debug:
                    print(f"    default_deps: {default_deps}")
                    print(f"    node_deps: {node_deps}")
                    #print(f"  configs: {[c['symbol'] for c in configs_in_this_def]}")
                    print(f"    entries in this def:")
                    for c in configs_in_this_def:
                        if c.get('type') == 'if_block':
                            print(f"        if_block with configs: {c.get('configs')} and menuconfigs: {[mc['symbol'] for mc in c.get('menuconfigs', [])]}")
                        else:
                            print(f"        {c.get('type')}: {c.get('symbol')}")
                    
                # Take the first entry's lines as representative for this definition
                # (since all configs in same definition have same choice-level attributes)
                collect_additional = [] # needed additional dep for prompts of other definitions
                if configs_in_this_def:
                    representative_cfg = configs_in_this_def[0]
                    collect_additional_from_depends_on = []
                    collect_additional_from_default = []
                    
                    # -------- depends on ----------
                    for dep_line in representative_cfg.get('depends_lines', []):
                        raw = dep_line.raw_text.strip()
                        base_cond = raw[len('depends on'):].strip()

                        additional = [
                            d for d in node_deps
                            if d not in base_cond and d != 'y'
                        ]
                        print(f"    additional_from_depends_on: {additional} + {base_cond}")
                        """
                        Because if you don't take base_cond -> prompt cond is wrong 
                        additional_from_depends_on: ['OPT_ZZZ']
                        Added: depends on OPT_AAA && OPT_ZZZ
                        additional_from_default: ['OPT_AAA', 'OPT_ZZZ']
                        Added default: default CH_C if OPT_BBB && OPT_AAA && OPT_ZZZ
                        choice_prompts: [KconfigLine(prompt, line=22, indent=2), KconfigLine(prompt, line=48, indent=2)]
                        Added new_prompt: prompt "P1" if OPT_ZZZ
                        !! SHOULD BE prompt "P1" if OPT_AAA && OPT_ZZZ
                        """
                        collect_additional_from_depends_on.append(base_cond)    # append bc only one 
                        collect_additional_from_depends_on.extend(additional)
                        if additional:
                            new_line = (
                                f"{' ' * (choice_line.indent + 2)}"
                                f"depends on {base_cond} && {' && '.join(additional)}"
                            )
                        else:
                            new_line = (
                                f"{' ' * (choice_line.indent + 2)}"
                                f"depends on {base_cond}"
                            )
                        # WRONG: result.append(KconfigLine(new_line, dep_line.line_number))
                        # we propagate them to the (menu)configs of the definiton but dont' add the line to the output 
                        # because that would mean the depends on would be propagated to elments of all defintions
                        # and because we skip this -> counter + (WRONG WE COUNT AT THE END IN transform_lines)
                        depends_from_def.append(KconfigLine(new_line, dep_line.line_number))

                        if log_debug: print(f"      Found: {new_line.strip()}")
                    
                    print(f"        Found depends on: {len(depends_from_def)}")
                    
                    #self.stats.file_skipped_bc_named_choice += len(depends_from_def)
                    # depends on for the line 
                    depends_by_choice_line[choice_line_num] = depends_from_def
                    
                    added_def_counter = 0           # for each definition start from 0
                    # -------- default ----------
                    for def_line in representative_cfg.get('default_lines', []):    
                        raw = def_line.raw_text.strip()
                        rest = raw[len('default'):].strip()

                        if ' if ' in rest:
                            sym, existing_if = rest.split(' if ', 1)
                            existing_parts = [p.strip() for p in existing_if.split('&&')]
                        else:
                            sym = rest
                            existing_parts = []

                        additional = [
                            d for d in default_deps
                            if d not in existing_parts and d != 'y'
                        ]
                        print(f"    additional_from_default: {additional}")
                        collect_additional_from_default.extend(additional)

                        cond = existing_parts + additional

                        if cond:
                            new_line = (
                                f"{' ' * (choice_line.indent + 2)}"
                                f"default {sym} if {' && '.join(cond)}"
                            )
                        else:
                            new_line = (
                                f"{' ' * (choice_line.indent + 2)}"
                                f"default {sym}"
                            )

                        result.append(KconfigLine(new_line, def_line.line_number))
                        added_def_counter += 1
                        if log_debug: print(f"      Added default: {new_line.strip()}")

                    print(f"        Added default: {added_def_counter}")
                    self.stats.file_added_bc_named_choice += added_def_counter

                    # we would like to take conditions form depends on but if the choice doesn't have
                    # depends on, meaning no place to read all aditional cond from if/menu 
                    # that parser gives us, then we read the additional that default got 
                    if collect_additional_from_depends_on:
                        collect_additional = collect_additional_from_depends_on
                    else:
                        collect_additional = collect_additional_from_default

                if choice_prompts:
                    
                    #print(f"    choice_prompts other att: {choice_prompts}")
                    line = choice_prompts[def_idx-1]                    
                    line_text = line.content.get('prompt_text')
                    add = None
                    if collect_additional: 
                        #add = collect_additional[0]
                        add = ' && '.join(collect_additional)

                        #print(f"hhhhhshsh {add}")
                        indent_str = ' ' * (choice_line.indent + 2)
                        if line.line_type == 'inline_prompt_choice': 
                            inline_typ = line.content.get('inline_typ')
                            new_prompt_line_text = f'{indent_str}prompt "{line_text}" if {add}'
                        else: 
                            new_prompt_line_text = f'{indent_str}prompt "{line_text}" if {add}'
                        new_prompt_line=KconfigLine(new_prompt_line_text, line.line_number)
                        result.append(new_prompt_line)
                        self.stats.file_added_bc_named_choice += 1
                        print(f"    Added new_prompt: {new_prompt_line_text.strip()}")
                    else:
                        result.append(line)
                        print(f"    Added old_prompt: {line.raw_text}")
                        self.stats.file_added_bc_named_choice += 1
                        #print(f"heeee {line} + {} + {add}")
            
            """ 
            # move this up for each def, so that we can add conditions from if/menu
            if choice_prompts:
                for pl in choice_prompts:
                    result.append(pl)
                    self.stats.file_added_bc_named_choice += 1
                    print(f"Added prompt {pl}")
            """
            if help_lines:
                for hl in help_lines:
                    result.append(hl)    
                    self.stats.file_added_bc_named_choice += 1
                    print(f"    Added help {hl}")

        if log_debug:
            print(f"\n  Final result has {len(result)} lines before adding configs")
            print(f"    Added Lines bc named choice {self.stats.file_added_bc_named_choice}")

        # ADD all configs in choice block
        # 1. TRACK configs already present in this choice block
        existing_configs = set()
        menuconfigs_to_add_after = []  # Collect menuconfigs to add after endchoice
        added_items = 0
        added_lines = 0

        # SPECIAL CASE: If there's only ONE definition, process sequentially
        if len(sorted_def_lines) == 1:
            print(f"    Single definition detected - processing sequentially")
            
            idx = first_ch_config_idx
            while idx is not None and idx < block_end_index:
                line_item = lines[idx]
                
                # Stop at endchoice
                if line_item.line_type == 'endchoice':
                    break

                # Handle menuconfig - collect for after endchoice
                if line_item.line_type == 'menuconfig':
                    sym_name = line_item.content.get('symbol')
                    if sym_name:
                        existing_configs.add(sym_name)
                    
                    menuconfig_block = []
                    # Collect the entire menuconfig block
                    while idx < block_end_index:
                        current = lines[idx]
                        
                        # Stop if next config/menuconfig/if/endchoice starts
                        if (current.line_type in ('config', 'menuconfig', 'if', 'endchoice', 'comment') 
                            and current is not line_item):
                            break
                        
                        current = self._transform_typ_choice_help(current, already_counted=True)
                        
                        menuconfig_block.append(current)
                        idx += 1
                    
                    # Store for adding after endchoice
                    menuconfigs_to_add_after.append({
                        'symbol': sym_name,
                        'block': menuconfig_block,
                        'depends_from_def': first_depends_on_for_mc
                    })
                    
                    print(f"      Collected menuconfig {sym_name} ({len(menuconfig_block)} lines)")
                    len_menuconfig_block_first_def += len(menuconfig_block)
                    continue

                # Handle if blocks - add directly to result
                if line_item.line_type == 'if':
                    if_block_lines = []
                    if_start_idx = idx
                    if_depth = 1
                    
                    # Collect entire if block including nested ifs
                    if_block_lines.append(lines[idx])  # Add the 'if' line
                    idx += 1
                    
                    while idx < block_end_index and if_depth > 0:
                        current = lines[idx]
                        if_block_lines.append(current)
                        
                        if current.line_type == 'if':
                            if_depth += 1
                        elif current.line_type == 'endif':
                            if_depth -= 1
                        
                        idx += 1
                    
                    # Now process the collected if_block_lines
                    if_line_idx = 0
                    while if_line_idx < len(if_block_lines):
                        if_line = if_block_lines[if_line_idx]
                        
                        # Handle menuconfig inside if block
                        if if_line.line_type == 'menuconfig':
                            sym_name = if_line.content.get('symbol')
                            if sym_name:
                                existing_configs.add(sym_name)
                            
                            menuconfig_block = [if_line]
                            if_line_idx += 1
                            
                            # Collect menuconfig properties until next symbol or block boundary
                            while if_line_idx < len(if_block_lines):
                                next_line = if_block_lines[if_line_idx]
                                
                                # Stop if next config/menuconfig/if/endif/endchoice starts
                                if (next_line.indent <= if_line.indent and
                                    next_line.line_type in ('config', 'menuconfig', 'if', 'endif', 'endchoice', 'comment')):
                                    break

                                next_line = self._transform_typ_choice_help(next_line, already_counted=True)

                                menuconfig_block.append(next_line)
                                if_line_idx += 1
                            
                            # Store for adding after endchoice
                            menuconfigs_to_add_after.append({
                                'symbol': sym_name,
                                'block': menuconfig_block,
                                'depends_from_def': first_depends_on_for_mc  
                            })
                            
                            print(f"      Collected menuconfig {sym_name} inside if-block ({len(menuconfig_block)} lines)")
                            len_menuconfig_block_first_def += len(menuconfig_block)
                            
                            continue
                        
                        # For all other lines (if, endif, config, etc.), transform and add
                        transformed = transform_func(if_line, None, None)
                        if transformed is not None:
                            if isinstance(transformed, list):
                                result.extend(transformed)
                            else:
                                result.append(transformed)
                        
                        if_line_idx += 1
                    
                    print(f"      Added if-block ({len(if_block_lines)} lines)")
                    continue

                # Handle regular config - add directly to result
                if line_item.line_type == 'config':
                    sym_name = line_item.content.get('symbol')
                    if sym_name:
                        existing_configs.add(sym_name)

                    # Process the whole config block
                    while idx < block_end_index:
                        current = lines[idx]

                        # Stop if next config/menuconfig/if/endchoice starts
                        if (current.line_type in ('config', 'if', 'menuconfig', 'endchoice', 'comment') 
                            and current is not line_item):
                            break
                        
                        current = self._transform_typ_choice_help(current)

                        transformed = transform_func(current, None, None)
                        if transformed is not None:
                            if isinstance(transformed, list):
                                result.extend(transformed)
                            else:
                                result.append(transformed)
                        idx += 1
                    continue
                
                idx += 1
            
            print(f"    Single definition: processed all entries sequentially")
        
        else:
            # MULTIPLE DEFINTIONS 
            idx = first_ch_config_idx
            while idx is not None and idx < block_end_index:
                line_item = lines[idx]
                if log_debug: print(f"  Track existing configs: {line_item}")
                # Stop at endchoice
                if line_item.line_type == 'endchoice':
                    break

                # Start of a config block
                # skip menuconfig
                if line_item.line_type in ('config'):
                    sym_name = line_item.content.get('symbol')
                    if sym_name:
                        existing_configs.add(sym_name)  # list of existing 

                    # Process the whole config block
                    while idx < block_end_index:
                        current = lines[idx]
                        #print(f"current: {current}")

                        # Stop if next config or endchoice starts
                        if (current.line_type in ('config', 'if','menuconfig', 'endchoice', 'comment') and current is not line_item):
                            break
                        
                        #print(f"before:{current.raw_text}")
                        current = self._transform_typ_choice_help(current)
                        #print(f"after: {current.raw_text}")

                        transformed = transform_func(current, None, None)
                        if transformed is not None:
                            if isinstance(transformed, list):
                                result.extend(transformed)
                            else:
                                result.append(transformed)
                        idx += 1
                    continue
                
                # Handle menuconfig - collect for after endchoice
                if line_item.line_type == 'menuconfig':
                    sym_name = line_item.content.get('symbol')
                    if sym_name:
                        existing_configs.add(sym_name)
                    
                    menuconfig_block = []
                    # Collect the entire menuconfig block
                    while idx < block_end_index:
                        current = lines[idx]
                        
                        # Stop if next config/menuconfig/if/endchoice starts
                        if (current.line_type in ('config', 'menuconfig', 'if', 'endchoice', 'comment') 
                            and current is not line_item):
                            break
                        
                        current = self._transform_typ_choice_help(current)
                        menuconfig_block.append(current)
                        idx += 1
                    
                    # Store for adding after endchoice
                    menuconfigs_to_add_after.append({
                        'symbol': sym_name,
                        'block': menuconfig_block,
                        'depends_from_def': first_depends_on_for_mc  
                    })
                    
                    print(f"      Collected menuconfig {sym_name} ({len(menuconfig_block)} lines)")
                    len_menuconfig_block_first_def += len(menuconfig_block)
                    continue
                
                idx += 1

            #print(f"result after first definition: {len(result)} lines")
            
            # 2. ADD entries (configs/ifs/ but menuconfig shoild be skipped) from other definitions


            for entry in choice_configs:
                entry_type = entry.get('type', 'config')
                entry_choice_line = entry.get('choice_line')
                
                if entry_type == 'if_block':
                    # Add entire if-block (contains configs, maybe menuconfigs)
                    configs_in_if = entry.get('configs', [])
                    print(f"    configs_in_if {configs_in_if}")
                    menuconfigs_in_if = entry.get('menuconfigs', [])
                    print(f"    menuconfigs_in_if {menuconfigs_in_if}")

                    # Add the if-block to the choice
                    for line in entry.get('block', []):
                        result.append(line)
                        added_lines += 1
                    
                    # Collect menuconfigs to add after endchoice
                    for mc_info in menuconfigs_in_if:
                        mc_symbol = mc_info.get('symbol')

                        if mc_symbol in existing_configs:
                            continue

                        mc_info_copy = dict(mc_info)
                        mc_info_copy['depends_from_def'] = depends_by_choice_line.get(entry_choice_line, [])
                        menuconfigs_to_add_after.append(mc_info_copy)
                        existing_configs.add(mc_symbol)
                    
                    # Mark configs as existing - because it would be added as standalone 
                    for cfg in configs_in_if:
                        existing_configs.add(cfg)
                    added_items += 1
                    print(f"      Added if-block with configs {configs_in_if} from {entry.get('file')}")
                
                # mc outside if 
                elif entry_type == 'menuconfig':
                    # Menuconfig - collect to add after endchoice
                    config_symbol = entry.get('symbol')

                    if config_symbol in existing_configs:
                        continue

                    def_idx_for_entry = def_index_by_line.get(entry_choice_line, 0)
                    
                    menuconfigs_to_add_after.append({
                        'symbol': config_symbol,
                        'block': entry.get('block', []),
                        'if_condition': entry.get('if_condition'),
                        'depends_lines': entry.get('depends_lines', []),
                        'depends_from_def': depends_by_choice_line.get(entry_choice_line, []),
                        'node_deps': all_node_deps[def_idx_for_entry] if def_idx_for_entry < len(all_node_deps) else []
                    })
                    
                    existing_configs.add(config_symbol)
                    added_items += 1
                    print(f"      Collected menuconfig {config_symbol} from {entry.get('file')} (will add after endchoice)")
                
                elif entry_type == 'config':
                    config_symbol = entry.get('symbol')
                    
                    # Skip configs already present
                    if config_symbol in existing_configs:
                        continue
                    
                    for config_line in entry.get('block', []):
                        result.append(config_line)
                        added_lines += 1
                    
                    existing_configs.add(config_symbol)
                    added_items += 1
                    print(f"      Added config {config_symbol} from {entry.get('file')}")

            print(f"    Added {added_items} entries from other choice definitions")
            print(f"    Added {added_lines} lines from other choice definitions")

        # ADD endchoice
        result.append(end_line)
        
        # ADD menuconfigs after endchoice
        menuconfig_lines_added = 0
        print(f"\n  Adding {len(menuconfigs_to_add_after)} menuconfigs after endchoice")
        for mc_info in menuconfigs_to_add_after:
            mc_symbol = mc_info['symbol']
            mc_block = mc_info['block']
            if_cond = mc_info.get('if_condition')
            depends_lines = mc_info.get('depends_lines', [])
            node_deps = mc_info.get('node_deps', [])
            depends_from_def = mc_info.get('depends_from_def', [])
            
            print(f"    Adding menuconfig {mc_symbol}, depends_from_def={depends_from_def}")
            
            mc_lines_counter = 0
            # Add menuconfig line
            result.append(mc_block[0])  # First line is menuconfig declaration
            mc_lines_counter += 1
            
            # Modify prompt line to add if condition if needed
            for line in mc_block[1:]:
                result.append(line)
                mc_lines_counter += 1
            for dep_line in depends_from_def:
                raw = dep_line.raw_text.strip()
                new_line = f"{' ' * (line.indent)}{raw}"
                #print(f"        new line: {new_line}")
                #print(line.indent)
                result.append(KconfigLine(new_line, dep_line.line_number))
                mc_lines_counter += 1
            
            menuconfig_lines_added += mc_lines_counter
        
        print(f"    Added {menuconfig_lines_added} menuconfig lines (after endchoice) from other choice definitions")
        print(f"    But in the first definition there where {len_menuconfig_block_first_def} menuconfig lines")
        new_mc_lines = menuconfig_lines_added - len_menuconfig_block_first_def
        print(f"    Diff: {new_mc_lines}")
        self.stats.file_added_bc_named_choice += (new_mc_lines + added_lines)
        print(f"    Added Total Lines bc named choice {self.stats.file_added_bc_named_choice}")
        """ 
        for line in result:
            print(f"resultttt {line}")
        """
        return block_end_index

    def _transform_typ_choice_help(self, current, already_counted: Optional[bool]=None):
        
        if (current.line_type == 'inline_prompt_choice' and current.content.get('inline_typ') == 'tristate'):
            #print("Kjskasj")
            current_transformed = self._transform_bool_to_tristate_choice_typ(current, current.indent, current.content.get('prompt_text'), already_counted)
            return current_transformed
        
        if current.line_type == 'type_tristate':
            #print("Kjskasj2")
            current_transformed = self._transform_bool_to_tristate_choice_typ(current, already_counted)
            return current_transformed
        
        return current


    def _transform_bool_to_tristate_choice_typ(self, line_item, indent: Optional[int] = 0,prompt_text: Optional[str] = "", already_counted: Optional[bool]=None):
        from core.kconfig_writer import KconfigLine
        import re
        
        # actually it wouldn't be right for choice_conifg to not have prompt
        if indent:
            indent_str = ' ' * (indent)  
        else:
            indent_str = ' ' * (line_item.indent)   

        if prompt_text:
          new_line_text = f'{indent_str}bool "{prompt_text}"'
        else:
          #match = re.match(r'tristate\s+["\']([^"\']+)["\']', line_item.stripped)
          #match = re.match(r'\s*(bool|tristate)\s+"([^"]*)"', line_stripped)
          #re.match(r'^\s*(tristate)\s*$', s)
          #line_text = match.group(1)
          new_line_text = f'{indent_str}bool'
        
        if already_counted: 
            print(f" already counted the typ change {new_line_text}")
        else: 
            self.stats.file_changed_typ_tristate_to_bool += 1
            #print(f" meein {new_line_text}")

        return KconfigLine(new_line_text, line_item.line_number)

    def _transform_cd(self, lines: List, current_index: int, transformed_entries: List, result: List, transform_func) -> int:
       
        line = lines[current_index]
        current_symbol = line.content.get('symbol') if hasattr(line, 'content') else None
        result.append(line)  # first line = config/menuconfig <symbol name>
        block_end_index = current_index + 1

        # find index for block end 
        while block_end_index < len(lines):
            next_line = lines[block_end_index]
            
            if next_line.indent == 0:
                break
            
            if next_line.line_type in ['config', 'menuconfig']:
                break
                
            block_end_index += 1
        
        # call transform_single_line for lines in block itself 
        for idx in range(current_index + 1, block_end_index):
            line = lines[idx]
            
            transformed = transform_func(line, current_symbol, None)
            
            if transformed is None:
                continue
                
            if isinstance(transformed, list):
                result.extend(transformed)
            else:
                result.append(transformed)
        
        result.extend(transformed_entries) 
        self.stats.file_configdefault_nr += len(transformed_entries)  
        return block_end_index

    def _transform_single_line(self, line, current_symbol: Optional[str], current_file: Path, resolve_log: None):
        """ 
        Returns:
            - KconfigLine: 1:1
            - List[KconfigLine]: 1:n
        """
        if line.line_type in self.DEF_KEYWORDS:
            self.stats.file_def_keywords_count += 1                                      # for each def_* -> count 1 one added line   
            return self._transform_def_keyword(line)
        elif line.line_type in self.SOURCE_KEYWORDS:
            self.stats.file_source_keywords_all_nr += 1                                  # for each self.SOURCE_KEYWORDS -> count 1, so that we have SUM of all 
            return self._transform_source_line(line, current_file, resolve_log)    # if resolve_log == True, than there is log for resolving and also iglob check is active 
        elif line.line_type == "option modules":
            self.stats.option_modules_counter += 1
            return self._transform_opt_modules(line, current_file)
        elif line.line_type == "option env":
            self.stats.file_opt_env += 1
            return self._transform_opt_env(line)
        elif line.line_type == "help_old":
            self.stats.old_help += 1
            return self._transform_stats.old_help(line)
        elif line.line_type == "typ_bool_old":
            self.stats.old_boolean += 1
            return self._transform_stats.old_boolean(line)
        else:
            if line.line_type == "allnoconfig_y":
                self.stats.file_opt_allnoconfig += 1
            if line.line_type == "defconfig_list":
                self.stats.file_opt_defconfig += 1
            if line.line_type == "warning":
                self.stats.file_warning_attr += 1
            if line.line_type == "set":
                self.stats.file_set_option += 1
            if line.line_type == "set_default":
                self.stats.file_set_default_option += 1
            return line    

    def _transform_old_help(self, line):
        from core.kconfig_writer import KconfigLine  
            
        indent_str = ' ' * line.indent

        new_text = f"{indent_str}help"
            
        new_line = KconfigLine(
            new_text,
            line.line_number  
        )
            
        return new_line
    
    def _transform_old_boolean(self, line):
       from core.kconfig_writer import KconfigLine  
            
       indent_str = ' ' * line.indent

       new_text = f"{indent_str}bool"
            
       new_line = KconfigLine(
           new_text,
           line.line_number  
       )
            
       return new_line
    
    def _transform_def_keyword(self, line) -> List:
        """
        For def_* keywords == def_bool, def_int, def_hex, def_string 
        config                            config 
            def_<typ> [if <exp>]   -->      <type> 
                                            default [if <exp>]
        """
        from core.kconfig_writer import KconfigLine  # avoid circular import
            
        indent_str = ' ' * line.indent
        keyword = line.content.get('_keyword')
        value = line.content.get('default_value')
        condition = line.content.get('condition')
            
        typ_line = KconfigLine(
            f"{indent_str}{keyword}",
            line.line_number
        )
            
        if condition:
            default_text = f"{indent_str}default {value} if {condition}"
        else:
            default_text = f"{indent_str}default {value}"
            
        default_line = KconfigLine(
            default_text,
            line.line_number  
        )
            
        return [typ_line, default_line]

    def _replace_env_var(self, match):
        import os
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    def _transform_source_line(self, line, current_file, resolve_log) -> List:
        from core.kconfig_writer import KconfigLine
        import re, os

        # GET needed information
        match = re.match(r'(source|osource|rsource|orsource)\s+["\']([^"\']+)["\']', line.stripped) # Future work: I think there is no need to check for both types: ' and ". I think only " is allowed 
        if not match:
            print(f"error at source line: {line}")      
        indent_str = ' ' * line.indent
        source_keyword = match.group(1)
        pattern = match.group(2)
        has_glob = any(c in pattern for c in ['*', '?', '[', ']', '!'])

        # COUNT each keyword in file
        if source_keyword == "osource": self.stats.file_osource_nr += 1
        elif source_keyword == "rsource": self.stats.file_rsource_nr += 1  
        elif source_keyword == "orsource": self.stats.file_orsource_nr += 1      

        # COUNT source with and without glob
        if has_glob and source_keyword == "source":
            self.stats.file_source_w_glob += 1
        if not has_glob and source_keyword == "source":
            self.stats.file_source_nr += 1 

        # NO GLOB -> copy line as it is to the output! BUT skip this for (o)r/(o)source because these have to be transformed to source before returning the line
        if not has_glob and not source_keyword == 'rsource' \
            and not source_keyword == 'orsource' and not source_keyword == 'osource':
            print(f"    source without glob: 1")    # this is just for LOGGING, no need of using stats.file_source_out_diff, because it's always 1 line that we look at and return
            return line

        # GLOB
        print(f"    GLOB LOG ----------------------------------------------------------------------------")
        print(f"    Resolve {source_keyword}: {pattern} at line {line.line_number}")
        
        #print("tests")

        # RESOLVE 
        matched_files = []          # we only need matched_files, that we get through node iteration 
        filenames = []              # this is just to show that both ways (matched and iglob) work 
        iglob_with_rel_path = []    # so that we can compare lists - matched_files and filenames (but filenames are transformed to SRCTREE relative path)
        if self.context is not None:
            kconf = self.context.parser_result['kconf']
            srctree = Path(kconf.srctree or "")

            if current_file is None:
                # FOR RTTHREAD: If current_file None -> use current dir 
                current_file_abs_path = Path.cwd()
                print(f"    WARNING: current_file is None, using cwd: {current_file_abs_path}")
            else:
                current_file_abs_path = Path(current_file).resolve()
            current_line_nr = line.line_number
            
            # ITERATE over all nodes in menutree 
            # main idea: for each node look were it's included from (-> From: {src_file} at {src_linenr})
            # MATCHED = when current_file (==src_file) is at exacly current_line_nr (==src_linenr) (example in the comment)
            """
            when there is: source "uo3/K*" at current_file = uo2/Kconfig, line 9
            than look for all nodes that have ('uo2/Kconfig', 9) as last element in node.include_path
            AND add their node.filename to the matched_files 
            
            older explanation: 
            # when current file == src_file (meaning file with source_keyword), 
            # --- to compare we use absolute paths from these (current_abs and src_abs)
            # AND line at current file == include location (got this from src_linenr)
            # then add node.filename to the list (== string after source_keywords)
            """
            node_item_name = None
            for node in kconf.node_iter(): 
                
                if not node.filename: continue
                if not node.include_path: continue

                src_file, src_linenr = node.include_path[-1] # file and line where this node was sourced from

                # create absolute path from source file
                src_file_abs_path = (srctree / src_file).resolve() \
                    if not os.path.isabs(src_file) else Path(src_file).resolve()

                if src_file_abs_path.samefile(current_file_abs_path) and current_line_nr == src_linenr and node.filename not in matched_files:
                    matched_files.append(node.filename)

                    if resolve_log:
                        print(f"        ---- RESOLVE LOG ------------------------------------------------------")
                        print(f"        node's file: {node.filename}")
                        print(f"        node's include paths: {node.include_path}") 
                        #print(f"        node: --- \n    {node}\n        ---")
                        print(f"        -> relevant is where node was sourced from: {src_file} at line {src_linenr}") 
                        print(f"        resolved: ")
                    continue
            
            # use iglob (exacly as kconfiglib) just to show/check that both ways work 
            if resolve_log:
                if source_keyword == "rsource" or source_keyword == "orsource":
                    pattern = join(dirname(current_file), pattern)
                    #print(f"{pattern}")
                    
                #print(f"JOIN {join(srctree, pattern)}")

                filenames = sorted(iglob(join(srctree, pattern)))
                #print(f"{filenames}")
                # iglob returnes abs path -> convert to SRCTREE-relative path
                for file in filenames:
                    iglob_with_rel_path.append(str(Path(file).relative_to(os.environ["srctree"])))
            
        if not matched_files:
            # don't just comment the line, instead skip -> no output line, when there is no match 
            print(f"      no files found for the: {pattern}")   

            if resolve_log:      
                print(f"        ---- CHECK RESOLVE LOG with iglob------------------------------------------------------")
                if not filenames:
                    print(f"    iglob didn't find anything")
                else:
                    for file in filenames:
                        print(f"        iglob found: {file}")
                    print(f"            transformed iglob list (relative paths): {iglob_with_rel_path}")
                    if matched_files == iglob_with_rel_path:
                        print(f"        CHECK OK: transformed iglob list == list of matched_files through iteration")
                    else: 
                        raise RuntimeError("check source matching")

            self.stats.file_o_source_keywords_no_match += 1
            """
            if source_keyword == "orsource" or source_keyword == "osource":
                new_line_text = f'#{indent_str}source "{pattern}"' # comment, but transform ((o)r/o)source and path before? 
                new_line = KconfigLine(new_line_text, line.line_number)
                return new_line
            """
            return None
        
        # bild source for each found file, after that calculate the output diff.-> if 1 source keyword matches 5 --> Diff: 4 new lines in output
        result_lines = []
        for matched_file in matched_files:
            # matched_files - don't need to be sorted, already sorted through previous node iteration 
            if source_keyword == 'rsource' or source_keyword == 'orsource' or source_keyword == 'osource':
                #base_dir = Path(current_file).parent
                #transform_to_abs = Path(matched_file).resolve()   WRONG 
                #print(f'HERE {base_dir} + {matched_file}')^       WRONG
                #print(f'HERE2 {transform_to_abs}')                WRONG
                new_line_text = f'{indent_str}source "{matched_file}"'
                new_line = KconfigLine(new_line_text, line.line_number)
                result_lines.append(new_line)
                print(f"      -> {matched_file}")
                continue
            else:
                # for source keyword just print  
                new_line_text = f'{indent_str}source "{matched_file}"'
                new_line = KconfigLine(new_line_text, line.line_number)
                result_lines.append(new_line)
                print(f"      -> {matched_file}")
        
        # for glob log:
        self.stats.one_source_keywords_matched_glob += len(result_lines)   
        print(f"    Files matching: {self.stats.one_source_keywords_matched_glob} (using {source_keyword})")
        
        # for file log, save diff. when source matches more files (1:n)
        self.stats.new_bc_glob = self.stats.one_source_keywords_matched_glob - 1
        self.stats.file_source_out_diff += self.stats.new_bc_glob  # sum all diff for 1 file, reset after FILE logging
        
        self.stats.one_source_keywords_matched_glob = 0 # set back for the next line with keyword
        return result_lines

    def _transform_opt_modules(self, line, current_file):
        # option modules --> modules
        from core.kconfig_writer import KconfigLine 
        indent_str = ' ' * line.indent
        new_line_text = f'{indent_str}modules'
        new_line = KconfigLine(new_line_text, line.line_number)

        self.stats.option_modules_info.append({
            'line': line.line_number, 
            'file': current_file
        })
        return new_line

    def _transform_opt_env(self, line):
        # option env="<value>" --> default "$(<value>)"
        from core.kconfig_writer import KconfigLine  # avoid circular import
        indent_str = ' ' * line.indent
        env_var = line.content.get('env')
        #env_value = os.environ.get(env_var) WRONG

        default_text = f"{indent_str}default \"$({env_var})\""
            
        default_line = KconfigLine(
            default_text,
            line.line_number  
        )
            
        return default_line
    
    def _get_all_choice_configs(self, choice_name: str, reader, project_dir: Path, log_cd_nc_details: bool, choice_info=None):
        """
        Get all config entries for a named choice from all its definitions.
        
        Collects:
        - Choice-level default and depends lines
        - Choice-level prompt und help
        - Config entries (standalone or in if-blocks)
        - Menuconfig entries (standalone or in if-blocks) with their if-conditions
        """
        print(f"\n=== _get_all_choice_configs for {choice_name} ===")
        from core.kconfig_writer import KconfigLine
        
        if choice_name not in self.context.choice_definitions:
            print(f"  {choice_name} not in choice_definitions!")
            return []

        choice_definitions = self.context.choice_definitions[choice_name]
        print(f"  Found {len(choice_definitions)} definitions:")
        for idx, cd in enumerate(choice_definitions):
            print(f"    [{idx}] file={cd.get('file')}, line={cd.get('line')}")
        
        # Extrahiere node_deps aus choice_info
        all_node_deps = []
        all_default_deps = []
        if choice_info and 'choice_def' in choice_info:
            choice_def_list = choice_info['choice_def']
            if choice_def_list:
                # Unpack: (choice_name, default_deps_list, node_deps_list)
                _, all_default_deps, all_node_deps = choice_def_list[0]
                print(f"  Extracted node_deps: {all_node_deps}")
                print(f"  Extracted default_deps: {all_default_deps}")

        all_entries = []
        all_choice_prompt_lines = []
        all_choice_help_lines = []

        # Process each choice definition
        for def_idx, choice_def_dict in enumerate(choice_definitions):
            choice_file = choice_def_dict.get('file')
            choice_line = choice_def_dict.get('line')

            print(f"\n  Processing definition [{def_idx}]: {choice_file}:{choice_line}")

            if not choice_file or not choice_line:
                print(f"    Missing file or line!")
                continue

            input_file = project_dir / choice_file
            print(f"    Looking for file: {input_file}")
            
            if not input_file.exists():
                print(f"    WARNING: file not found!")
                continue
            
            print(f"    File exists, reading...")
            lines = reader.read_file(input_file)
            print(f"    Read {len(lines)} lines")

            # Get node_deps for this specific definition
            node_deps = []
            if def_idx < len(all_node_deps):
                node_deps = all_node_deps[def_idx]
            
            print(f"    node_deps for definition [{def_idx}]: {node_deps}")

            # Find the choice line
            for i, line in enumerate(lines):
                if (
                    line.line_type in ('choice', 'named_choice') and
                    line.line_number == choice_line
                ):
                    print(f"    Found choice at line index {i}, line_number={line.line_number}")
                    
                    # Collect choice-level default and depends lines
                    choice_default_lines = []
                    choice_depends_lines = []
                    choice_prompt_lines = []
                    choice_help_lines = []
                    
                    j = i + 1
                    first_config_idx = None
                    
                    # Scan until first config/if to get choice-level attributes
                    while j < len(lines):
                        next_line = lines[j]
                        
                        # Found first config or if - stop collecting choice attributes
                        if next_line.line_type in ('config', 'menuconfig', 'if'):
                            first_config_idx = j
                            break
                        
                        # Found endchoice without any config - break
                        if next_line.line_type == 'endchoice':
                            break
                        
                        # Collect choice-level default and depends
                        if next_line.line_type == 'default':
                            choice_default_lines.append(next_line)
                        elif next_line.line_type == 'depends_on':
                            choice_depends_lines.append(next_line)
                        
                        # because if we don't skip the first definition, than we'll have redundant attr
                        # because the attributs of the first definition are transformed in transform_named_choice
                        if def_idx != 0:
                            #print("collect from other def")
                            #print(f"nextttt {next_line.line_type}")
                            
                            if next_line.line_type == 'prompt':
                                choice_prompt_lines.append(next_line)
                                all_choice_prompt_lines.append(next_line)
                            
                            elif next_line.line_type == 'inline_prompt_choice':
                                inline_typ = next_line.content.get('inline_typ', '')
                                prompt_text = next_line.content.get('prompt_text', '')
                                indent_str = ' ' * next_line.indent

                                new_prompt_line = f'{indent_str}prompt "{prompt_text}"'
                                modified_line = KconfigLine(new_prompt_line, next_line.line_number)
                                #print(f"mod: {modified_line.raw_text}")
                                all_choice_prompt_lines.append(modified_line)
                                self.stats.file_changed_inprompt_bc_choice += 1
                                #print(all_choice_prompt_lines)
                                
                            elif next_line.line_type == 'help':
                                # store the 'help' keyword line
                                choice_help_lines.append(next_line)
                                all_choice_help_lines.append(next_line)

                                help_indent = next_line.indent
                                j += 1

                                # collect all following help text lines
                                while j < len(lines):
                                    help_line = lines[j]

                                    # help text must be more indented than 'help'
                                    if help_line.indent <= help_indent:
                                        break

                                    # safety: stop if structure starts unexpectedly
                                    if help_line.line_type in (
                                        'default', 'depends_on', 'prompt',
                                        'config', 'menuconfig', 'if', 'endchoice'
                                    ):
                                        break

                                    choice_help_lines.append(help_line)
                                    all_choice_help_lines.append(help_line)

                                    j += 1

                                continue  # important: j already advanced

                        j += 1
                    
                    print(f"  DEBUG: Found choice {choice_name} at {choice_file}:{choice_line}")
                    if log_cd_nc_details:
                        print(f"  DEBUG: choice_default_lines: {choice_default_lines}")
                        print(f"  DEBUG: choice_depends_lines: {choice_depends_lines}")
                        print(f"  DEBUG: choice_prompt_lines: {choice_prompt_lines}")
                        print(f"  DEBUG: choice_help_lines: {choice_help_lines}")

                    additional_deps = []

                    # 1. base_cond
                    for dep_line in choice_depends_lines:
                        raw = dep_line.raw_text.strip()
                        base_cond = raw[len('depends on'):].strip()
                        additional_deps.append(base_cond)
                                
                    # 2. Additional (nur für def_idx > 0)
                    if def_idx > 0 and node_deps:
                        base_conds = additional_deps.copy()
                        for base_cond in base_conds:
                            additional = [
                                d for d in node_deps
                                if d not in base_cond and d != 'y'
                            ]
                            additional_deps.extend(additional)
                                    
                        if not base_conds:
                            additional_deps.extend([d for d in node_deps if d != 'y'])
                                
                    additional_deps = list(dict.fromkeys(additional_deps))
                    
                    # Now collect all configs AND if-blocks in this choice block
                    if first_config_idx is not None:
                        k = first_config_idx
                        while k < len(lines):
                            current_line = lines[k]
                            
                            if current_line.line_type == 'endchoice':
                                break
                            
                            # Handle IF blocks --------------------------------------------------------------------------------------
                            if current_line.line_type == 'if':
                                # Get if condition from the line
                                if_condition_raw = current_line.raw_text.strip()
                                if_condition = if_condition_raw[2:].strip() if if_condition_raw.startswith('if') else ''
                                
                                if_block = [current_line]
                                if_configs = []
                                if_menuconfigs = []
                                
                                # Collect everything until endif
                                m = k + 1
                                if_depth = 1
                                while m < len(lines) and if_depth > 0:
                                    next_line = lines[m]
                                    
                                    if next_line.line_type == 'if':
                                        if_depth += 1
                                    elif next_line.line_type == 'endif':
                                        if_depth -= 1
                                        if if_depth == 0:
                                            if_block.append(next_line)
                                            m += 1
                                            break
                                           
                                    if next_line.line_type == 'comment':
                                        if_block.append(next_line)
                                        m += 1
                                        continue
                                    
                                    # Track config symbols inside the if
                                    if next_line.line_type == 'config':
                                        sym_name = next_line.content.get('symbol')
                                        if sym_name: if_configs.append(sym_name)
                                        # HERE HANDLE THE ADDITIONAL DEPENDENCIES FOR CONFIGS OF OTHER DEFINITIONS INSIDE IF!!!!
                                        
                                        if_block.append(next_line) #config line itself

                                        config_m = m + 1
                                        # add dependecies as you collect the block
                                        while config_m < len(lines):
                                            config_line = lines[config_m]
                                            
                                            if (config_line.line_type in ('config', 'menuconfig', 'if', 'endif', 'comment', 'endchoice')):
                                                break
                                            
                                            # MODIFY LINES 
                                            if config_line.line_type in ('prompt', 'inline_prompt_choice', 'depends_on') and def_idx > 0:
                                                if additional_deps:
                                                    prompt_text = config_line.content.get('prompt_text', '')
                                                    inline_typ = config_line.content.get('inline_typ', '')
                                                    indent_str = ' ' * config_line.indent
                                                    combined_cond = ' && '.join(additional_deps)
                                                    
                                                    if config_line.line_type == 'depends_on':
                                                        raw = config_line.raw_text.strip()
                                                        base_cond = raw[len('depends on'):].strip()
                                                        new_prompt_line = f'{indent_str}depends on {base_cond} && {combined_cond}'
                                                    elif config_line.line_type == 'inline_prompt_choice': 
                                                        new_prompt_line = f'{indent_str}bool "{prompt_text}" if {combined_cond}'
                                                        if inline_typ == 'tristate': 
                                                            self.stats.file_changed_typ_tristate_to_bool += 1
                                                            #print(f"meeinn {new_prompt_line}")

                                                    elif config_line.line_type == 'prompt': 
                                                        new_prompt_line = f'{indent_str}prompt "{prompt_text}" if {combined_cond}'

                                                    modified_line = KconfigLine(new_prompt_line, next_line.line_number)
                                                    if_block.append(modified_line)
                                                else:
                                                    if_block.append(next_line)
                                            else:
                                                if_block.append(next_line)

                                            config_m += 1
                                                                                
                                        m = config_m
                                        continue

                                    # Track menuconfig symbols with their blocks, at the end we want these after choice-endchoice block 
                                    if next_line.line_type == 'menuconfig':
                                        sym_name = next_line.content.get('symbol')
                                        if sym_name:
                                            # Collect menuconfig block
                                            mc_block = [next_line]
                                            mc_m = m + 1
                                            while mc_m < len(lines):
                                                mc_line = lines[mc_m]
                                                if (
                                                    mc_line.indent <= next_line.indent and
                                                    mc_line.line_type in ('config', 'menuconfig', 'endchoice', 'if', 'endif', 'comment')
                                                ):
                                                    break
                                                #print(f"mc before: {mc_line.raw_text}")
                                                mc_line = self._transform_typ_choice_help(mc_line)
                                                #print(f"mc after: {mc_line.raw_text}")

                                                mc_block.append(mc_line)
                                                m = mc_m
                                                mc_m += 1
                                            
                                            if_menuconfigs.append({
                                                'symbol': sym_name,
                                                'block': mc_block,
                                                'if_condition': if_condition
                                            })
                                    
                                    m += 1
                                    
                                    if if_depth == 0:
                                        break
                                
                                # Add the entire if-block as a single entry
                                all_entries.append({
                                    'type': 'if_block',
                                    'configs': if_configs,
                                    'menuconfigs': if_menuconfigs,
                                    'file': choice_file,
                                    'line': current_line.line_number,
                                    'choice_line': choice_line,
                                    'block': if_block,
                                    'default_lines': choice_default_lines.copy(),
                                    'depends_lines': choice_depends_lines.copy(),
                                })
                                
                                if log_cd_nc_details:
                                    print(f"  DEBUG: Adding if-block with configs {if_configs} and menuconfigs {[mc['symbol'] for mc in if_menuconfigs]}")
                                
                                k = m
                            
                            # Handle standalone configs (not inside if)
                            elif current_line.line_type in ('config'):
                                sym_name = current_line.content.get('symbol')
                                config_block = [current_line]

                                # Collect the config block
                                m = k + 1
                                while m < len(lines):
                                    next_line = lines[m]
                                    
                                    if (
                                        next_line.indent <= current_line.indent and
                                        next_line.line_type in (
                                            'config', 'menuconfig', 'endchoice', 'if', 'endif', 'comment'
                                        )
                                    ):
                                        break
                                    
                                    #print(f"eehehjwe {next_line.line_type} + {next_line.raw_text}")
                                    if next_line.line_type == 'prompt' or next_line.line_type == 'inline_prompt_choice' and def_idx > 0:
                                        
                                        """ 
                                        # Von depends_on Zeilen
                                        for dep_line in choice_depends_lines:
                                            raw = dep_line.raw_text.strip()
                                            base_cond = raw[len('depends on'):].strip()
                                            additional_deps.append(base_cond)
                                            base_conds = additional_deps.copy()
                                            for base_cond in base_conds:
                                                additional = [
                                                    d for d in node_deps
                                                    if d not in base_cond and d != 'y'
                                                ]
                                                additional_deps.extend(additional)
                                        """                                        
                                        
                                        prompt_text = next_line.content.get('prompt_text', '')
                                        inline_typ = next_line.content.get('inline_typ', '')
                                        # ELEMENTS OF CHOICE CANT HAVE DEFAULT
                                        #default_value = next_line.content.get('value', '')
                                        #default_cond = next_line.content.get('condition', '')
                                        indent_str = ' ' * next_line.indent
                                        if additional_deps:
                                            combined_cond = ' && '.join(additional_deps)
                                            if next_line.line_type == 'inline_prompt_choice': 
                                                new_prompt_line = f'{indent_str}bool "{prompt_text}" if {combined_cond}'

                                                if inline_typ == 'tristate': 
                                                    self.stats.file_changed_typ_tristate_to_bool += 1 # bc we are looking at prompts at config level 
                                                    #print(f"meeinn {new_prompt_line}")
                                                
                                            if next_line.line_type == 'prompt': new_prompt_line = f'{indent_str}prompt "{prompt_text}" if {combined_cond}'
                                            #if next_line.line_type == 'default' and default_cond: new_prompt_line = f'{indent_str}default {default_value} if {default_cond} && {combined_cond}'
                                            #if next_line.line_type == 'default' and not default_cond: new_prompt_line = f'{indent_str}default {default_value} if {combined_cond}'

                                            modified_line = KconfigLine(new_prompt_line, next_line.line_number)
                                            config_block.append(modified_line)
                                        else:
                                            if next_line.line_type == 'prompt': 
                                                new_prompt_line = f'{indent_str}prompt "{prompt_text}"'
                                            if next_line.line_type == 'inline_prompt_choice': 
                                                new_prompt_line = f'{indent_str}bool "{prompt_text}"'    # config tristate -> bool "xxxx" BUT also bool -> bool 
                                                if inline_typ == 'tristate': 
                                                    self.stats.file_changed_typ_tristate_to_bool += 1
                                                    #print(f"meeinn {new_prompt_line}")

                                            modified_line = KconfigLine(new_prompt_line, next_line.line_number)
                                            config_block.append(modified_line)
                                    else:
                                        config_block.append(next_line)
                                    
                                    m += 1
                                
                                if log_cd_nc_details: print(f"  DEBUG: Adding config {sym_name}")
                                
                                all_entries.append({
                                    'type': 'config',
                                    'symbol': sym_name,
                                    'file': choice_file,
                                    'line': current_line.line_number,
                                    'choice_line': choice_line,
                                    'block': config_block,
                                    'default_lines': choice_default_lines.copy(),
                                    'depends_lines': choice_depends_lines.copy(),
                                    'if_condition': None  # Not inside if
                                })
                                
                                k = m
                            
                            elif current_line.line_type in ('menuconfig'):
                                sym_name = current_line.content.get('symbol')
                                is_menuconfig = (current_line.line_type == 'menuconfig')
                                config_block = [current_line]


                                # Collect the menuconfig block
                                m = k + 1
                                while m < len(lines):
                                    next_line = lines[m]
                                    
                                    if (
                                        next_line.indent <= current_line.indent and
                                        next_line.line_type in (
                                            'config', 'menuconfig', 'endchoice', 'if', 'endif', 'comment'
                                        )
                                    ):
                                        break
                                    
                                    next_line = self._transform_typ_choice_help(next_line)
                                    config_block.append(next_line)
                                    m += 1
                                
                                if log_cd_nc_details: print(f"  DEBUG: Adding {'menuconfig' if is_menuconfig else 'config'} {sym_name}")
                                
                                all_entries.append({
                                    'type': 'menuconfig' if is_menuconfig else 'config',
                                    'symbol': sym_name,
                                    'file': choice_file,
                                    'line': current_line.line_number,
                                    'choice_line': choice_line,
                                    'block': config_block,
                                    'default_lines': choice_default_lines.copy(),
                                    'depends_lines': choice_depends_lines.copy(),
                                    'if_condition': None  # Not inside if
                                })
                                
                                k = m
                            else:
                                k += 1
                    else:
                        print(f"  DEBUG: No configs found in this choice definition")
                    
                    break  # Break from line search loop
            
            print(f"  Finished processing definition [{def_idx}]")

        print(f"  DEBUG: Total entries collected: {len(all_entries)}")
        print(f"  DEBUG: Total prompts collected: {len(all_choice_prompt_lines)}")
        print(f"  DEBUG: Total helps collected: {len(all_choice_help_lines)} + {all_choice_help_lines}")

        return {
            'entries': all_entries,
            'choice_prompt_lines': all_choice_prompt_lines,
            'choice_help_lines': all_choice_help_lines
        }

    def _log_file_and_reset_count(self, new_lines_skw : int, current_file : Path, len_input : int, len_result : int):
        print(f"    FILE LOG --------------------------------------------------------------")
        #print(f"    File:                      {str(current_file)}")
        print(f"    Reader input                {len_input} lines")
        print(f"    -----------------------------------------------------------------------")
        print(f"    All source without glob:    {self.stats.file_source_nr}")
        print(f"    All source using glob:      {self.stats.file_source_w_glob}")
        print(f"    All osource_keywords:       {self.stats.file_osource_nr}")
        print(f"    All rsource_keywords:       {self.stats.file_rsource_nr}")
        print(f"    All orsource_keywords:      {self.stats.file_orsource_nr}")  
        print(f"    SUM (r/or/o)source lines:   {self.stats.file_source_keywords_all_nr}")
        print(f"    All \"option env\" attr:      {self.stats.file_opt_env}")
        print(f"    -----------------------------------------------------------------------")
        print(f"    Transformer Output:         {len_result} lines")
        print(f"    -----------------------------------------------------------------------")
        print(f"        Added new bc of def_*:           {self.stats.file_def_keywords_count}")
        print(f"        Added new bc of glob:            {new_lines_skw}")
        print(f"        Added new bc of config_default:  {self.stats.file_configdefault_nr}")
        print(f"        Added new bc of named choice:    {self.stats.file_added_bc_named_choice}") 
    #print(f"        Removed consecutive empty lines:  {self.stats.file_removed_consecutive_empty_lines}") 
        print(f"        Removed bc of config_default:    {self.stats.file_skipped_bc_configdefault}") 
        print(f"        Removed bc of named choice:      {self.stats.file_skipped_bc_named_choice}") 
        print(f"        Removed no match for o(r)source: {self.stats.file_o_source_keywords_no_match}")  
        print(f"        Removed optional choice attr:    {self.stats.file_skip_optional_choice_attr}")
        print(f"        Removed bool     choice attr:    {self.stats.file_skip_choice_typ_def_bool}")
        print(f"        Removed tristate choice attr:    {self.stats.file_skip_choice_typ_def_tristate}") 
        
        # STORE FOR EXCEL
        file_stats_excel = {
            'test file' : str(current_file),
            'input'     : len_input,
            'output'    : len_result,
            'source_keyword_wo_glob' : self.stats.file_source_nr,
            'source_keyword_w_glob' : self.stats.file_source_w_glob,
            'osource_keyword' : self.stats.file_osource_nr,
            'rource_keyword' : self.stats.file_rsource_nr,
            'orsource_keyword' : self.stats.file_orsource_nr,
            'sum_all_source' : self.stats.file_source_keywords_all_nr,
            'option_env' : self.stats.file_opt_env,

            'new_lines_bc_of_def_': self.stats.file_def_keywords_count,

            'new_lines_bc_of_glob': new_lines_skw,
            'new_lines_bc_cd': self.stats.file_configdefault_nr,
            'new_lines_bc_named_choice': self.stats.file_added_bc_named_choice,

            'removed_bc_orsource': self.stats.file_o_source_keywords_no_match,
            'removed_lines_bc_cd': self.stats.file_skipped_bc_configdefault,
            'removed_lines_bc_named_choice': self.stats.file_skipped_bc_named_choice,

            'removed_optional_choice_attr': self.stats.file_skip_optional_choice_attr,
            'removed_bool_choice_attr': self.stats.file_skip_choice_typ_def_bool,
            'removed_tristate_choice_attr': self.stats.file_skip_choice_typ_def_tristate
        }

        self.stats.file_source_nr = 0
        self.stats.file_source_w_glob = 0
        self.stats.file_osource_nr = 0
        self.stats.file_rsource_nr = 0
        self.stats.file_orsource_nr = 0
        self.stats.file_source_keywords_all_nr = 0
        self.stats.file_def_keywords_count = 0
        self.stats.file_all_added_lines_skw = 0
        self.stats.file_configdefault_nr = 0
        self.stats.file_removed_consecutive_empty_lines = 0
        self.stats.file_skipped_bc_configdefault = 0
        self.stats.new_bc_glob = 0
        self.stats.file_source_out_diff = 0
        self.stats.file_o_source_keywords_no_match = 0
        self.stats.file_opt_env = 0
        self.stats.file_skip_optional_choice_attr = 0
        self.stats.file_warning_attr = 0
        self.stats.file_set_option = 0
        self.stats.file_set_default_option = 0
        self.stats.file_skip_choice_typ_def_bool = 0
        self.stats.file_skip_choice_typ_def_tristate = 0
        self.stats.file_skipped_bc_named_choice = 0
        self.stats.file_added_bc_named_choice = 0

        return file_stats_excel
        
    def _log_parser_context(self, given_context):
        
        print(f"\n For each symbol found in parser_result['unique_defined_syms']")
        print(f"    -> call sym.name/.origin/.name_and_loc")
        print(f"    -> call for each sym.nodes (.filename/.linenr/node/.defaults/is_configdefault")
        print(f"    -> call all sym.defaults")
        print(f"    -> call all sym.orig_defaults")
        print(f"\n------------ symbol_infos --------------------------------------------------")
        #print(given_context.symbol_infos)
        for symbol_name, infos in given_context.symbol_infos.items():
            for symbol_info in infos:
                print(f"{symbol_name}: [{symbol_info}]")
        print(f"\n------------ symbol_definitions --------------------------------------------------")
        #print(given_context.symbol_definitions)
        for symbol_name, definitions in given_context.symbol_definitions.items():
            for definition in definitions:
                print(f"{symbol_name}: [{definition}]")
        print(f"\n------------ symbol_defaults -----------------------------------------------")
        #print(given_context.symbol_defaults)
        for symbol_name, defaults in given_context.symbol_defaults.items():
            for default in defaults:
                print(f"{symbol_name}: [{default}]")
        #print(f"\n------------ sym.orig_defaults ---------------------------------------------")
        #print(f"these omit any dependencies propagated from 'depends on' and surrounding 'if's & strip location of default line")
        #print(given_context.symbol_orig_defaults)
        print(f"\n------------ choice_infos -----------------------------------------------")
        for choice_name, infos in given_context.choice_infos.items():
            print(f"{choice_name}")
            for info in infos:
                for sym in info.get('choice.syms', []) or []:
                    print(f"    [{repr(sym)}]")
        
        print(f"\n------------ choice_definitions -----------------------------------------------")
        for choice_name, definitions in given_context.choice_definitions.items():
            for definition in definitions:
                print(f"{choice_name}: [{repr(definition)}]")
       
        print(f"\n   Symbol definitions and corresponding locations in ExParserContext: ")
        for sym_name, definitions in given_context.symbol_definitions.items():
            if len(definitions) >= 1:
                print(f"   '{sym_name}' is defined x{len(definitions)}")
                for defn in definitions:
                    is_default = defn.get('is_configdefault', False)
                    default_tag = " (as configdefault)" if is_default else ""
                    file = defn.get('file') or "<unknown file>"
                    line = defn.get('line') or "<unknown line>"
                    print(f"     - {file}:{line}{default_tag}")
        
    def _if_block_contains_only_configdefault(self, lines, if_start_indx) -> bool:
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

    def _skip_if_block(self, lines, if_start_index) -> int:
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

    def _remove_consecutive_empty_lines(self, lines):
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

    def _filter_cd_from_context(self, reader, project_dir, log_cd_nc_details):

        cd_definition_info = {}
        print("\n3. Filter ExtParserContext")
        print("extract all configdefault options and for each get transformed lines and last config")
        for cd in self.context.configdefault_options:
            
            if cd not in cd_definition_info:
                cd_definition_info[cd] = []     # replace defaultdict

            info = self._extract_symbol_info(self.context, cd)
            last_config = self._get_last_config(info['sym_def'])
            cd_default_lines = self._get_cd_entries(info['sym_def'])
            tcd_list = self._get_transformed_config_defaults(cd_default_lines, reader, project_dir)
            cd_all_sym = {
               'last_config': last_config,
               'cd_default_lines': cd_default_lines,
               'transformed_entries_list': tcd_list
            } 
            cd_definition_info[cd].append(cd_all_sym)

            if log_cd_nc_details:
                print(f"\ninfos about whole configdefault dictionary")

                print(f"configdefault: {cd}")
                print(f"'last_config': {cd_definition_info[cd][0].get('last_config')}")
                print(f"'cd_default_lines': {cd_definition_info[cd][0].get('cd_default_lines')}")
                print(f"'transformed_cd_default_lines': {cd_definition_info[cd][0].get('transformed_entries_list')}")
               

                print(f"\nfilter: symbol definitions & each sym.node.defaults extracted ---------------------------------------------------------------")
                for sn, file, line, cf_flag, extr_nd in info['sym_def']:
                    print(f"{sn}, {file}, {line}, {cf_flag}, {extr_nd}")
                print("filter: default definitions of symbol (loc & complete list for if cond) ------------------------------------------------------")
                for sn, def_loc, def_dep in info['def_dep']:
                    print(f"{sn}, {def_loc}, ({', '.join(def_dep)})")
                print(f"\n - last conf")
                print(last_config)
                print(f"\n - configdefault entries")
                print(cd_default_lines)   
                print(f"\n - transformed cd entries")
                print(tcd_list)             

        return cd_definition_info
    
    def _filter_nc_from_context(self, reader, project_dir, log, log_cd_nc_details):

        choice_definition_info = {}
        
        print("extract infos for named choices - their definition & entries")
        for choice_name in self.context.choice_definitions.keys():
            if choice_name not in choice_definition_info:
                choice_definition_info[choice_name] = {}
            
            choice_info = self._extract_named_choice_info(choice_name, log, log_cd_nc_details)
       
            # Get all config entries for this choice
            choice_data = self._get_all_choice_configs(choice_name, reader, project_dir, log_cd_nc_details, choice_info=choice_info)
            choice_info['choice_configs'] = choice_data['entries']
            choice_info['prompt_lines'] = choice_data['choice_prompt_lines']
            choice_info['help_lines'] = choice_data['choice_help_lines']
            
            choice_definition_info[choice_name] = choice_info
            
            if log_cd_nc_details:
                print(f"\n  named choice: {choice_name}")
                print(f"    'choice_def': {choice_info.get('choice_def')}")
                print(f"    'choice_configs': {len(choice_data)} config entries")
                print(f"    'prompt_lines': {choice_info.get('prompt_lines')}")
                print(f"    'help_lines': {choice_info.get('help_lines')}")

        return choice_definition_info
        
    def transform_all_files(self, reader, writer, project_dir: Path, output_dir: Path, \
                            log: bool, log_lines: bool, log_and_check_resolve_glob: bool, \
                                log_cd_nc_details: bool, log_excel_after_each_file: bool, \
                                    log_excel_output: Optional[str] = None, \
                                        outside_file_relative_to: Optional[str] = None):
        """
        1. get all source files parser found (these are all realtive to srctree)
        2. Filter ExtParserContext -> get needed infos for transformation of configdefault and named choice options 
        3. build paths for input & output files
        """
        excel_stats = []
        transformed_count = 0

        if self.context is None:
            raise RuntimeError("Context missing!")
        
        # GET source_files & filtered info for configdefault & named choice 
        source_files = self._get_all_source_files()             # all paths are relative to srctree 
        cd_definition_info = self._filter_cd_from_context(reader, project_dir, log_cd_nc_details)
        choice_definition_info = self._filter_nc_from_context(reader, project_dir, log, log_cd_nc_details)

        print(f"\nfor each given file at source_files start building path output structur and call reader and writer")     
        print(f"\n4. Transform all files - needs reader & writer")
        for file_path in source_files:
            input_file = (project_dir / file_path).resolve()

            # this solution bc of ../ in paths 
            try:
                #print(f"\nDEBUG: input_file={input_file}")
                #print(f"DEBUG: project_dir={project_dir}")
                relative_normalized = input_file.relative_to(project_dir)
                #print(f"DEBUG: relative_path={relative_normalized}")
                #print(f"DEBUG: output_file would be={output_dir / relative_normalized}")
            except ValueError:
                if outside_file_relative_to:
                    relative_normalized = input_file.relative_to(Path(outside_file_relative_to))
                    #print(relative_normalized)
                else:
                    print(f"    Skip file outside project: {input_file}")

            output_file = output_dir / relative_normalized
            #print(f"DEBUG: output_file would be={output_file}")
                
            #print(f"\ninput file: {input_file}")
            #print(f"relative_normalized: {relative_normalized}")
            #print(f"output file: {output_file}")
            if not input_file.exists():
                print(f"  Skip not found: {input_file}")
                continue
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            lines = reader.read_file(input_file)

            if log_lines:
                for line in lines:
                    #if line.line_type in LINE_TYP_LOG:
                        print(f"    {line}")
                        if line.line_type != 'empty' and line.line_type != 'other':
                            print(f"        -> Content: {line.content}")

            print("call _transform_lines(lines from reader, input, configdefault dict info)")
            # also collect not only transformed lines but some statistics 
            transformed, source_out_diff, len_reader_input, len_transformed_lines \
                  = self._transform_lines(lines, input_file, cd_definition_info, choice_definition_info, log_and_check_resolve_glob)
             
            # TODO: add new_lines to excel stats 
            # DON'T NEED THIS FOR THE STATISTICS - it just makes a lot compilcated 
            #new_lines = self._remove_consecutive_empty_lines(transformed)
            #removed_consecutive_lines_nr = self.stats.file_removed_consecutive_empty_lines

            stats = self._log_file_and_reset_count(source_out_diff, input_file, len_reader_input, len_transformed_lines)

            excel_stats.append(stats)
            if log_excel_after_each_file:
                write_to_excel(excel_stats, log_excel_output)
            
            try:
                writer.write(transformed, output_file)
                transformed_count += 1
            except Exception as e:
                print(f"     Error write: {e}")
        
        print(f"----------------------------------------------------------------------")
        print(f"finished transforming: {transformed_count} files transformed")
        print(f"----------------------------------------------------------------------")
        print("Overall parser info: ")
        print(f"    -> ExParserContext - unique options: {self.context.symbol_nr}")
        print(f"    -> ExParserContext - configdefaults: {self.context.configdefault_options_nr} ({', '.join(self.context.configdefault_options)})")
        print(f"    -> ExParserContext - unique choices: {self.context.choice_nr}")
        print(f"    -> ExParserContext - named choices:  {self.context.named_choices_nr}")
        print(f"----------------------------------------------------------------------")
        if self.stats.option_modules_info:
            for info in self.stats.option_modules_info:
                print(f"    {self.stats.option_modules_counter} option modules-attr found at line {info['line']} in {info['file']}")
        else:
            print(f"    option modules: 0")          
        print(f"----------------------------------------------------------------------")
        print("count options/attr that are not transformed: ")
        print(f"    allnoconfig_y:  {self.stats.file_opt_allnoconfig}")        
        print(f"    defconfig_list: {self.stats.file_opt_defconfig}")
        print(f"    warning:        {self.stats.file_warning_attr}")
        print(f"    set:            {self.stats.file_set_option}")
        print(f"    set default:    {self.stats.file_set_default_option}")
        print(f"----------------------------------------------------------------------")
        print("count changes that don't affect the output size: ")
        print(f"        Changed inline prompt choice:    {self.stats.file_changed_inprompt_bc_choice}") 
        print(f"        Changed typ of choice element:   {self.stats.file_changed_typ_tristate_to_bool}") 
        print(f"----------------------------------------------------------------------")
        #print("additionaly count --help-- for PX4")
        print(f"Attr --help--: {self.stats.old_help}")
        print(f"Attr boolean: {self.stats.old_boolean}")

        self.stats.file_opt_defconfig = 0
        self.stats.file_opt_allnoconfig = 0
        self.stats.option_modules_counter = 0
        self.stats.option_modules_info.clear()
        self.stats.file_warning_attr = 0
        self.stats.file_set_option = 0
        self.stats.file_set_default_option = 0
        self.stats.file_changed_inprompt_bc_choice = 0        # for choice -> bool "pick something" --> prompt "pick something"
        self.stats.file_changed_typ_tristate_to_bool = 0      # tristate elements of choice should be restricted to bool 
        self.stats.old_help = 0
        self.stats.old_boolean = 0

        return excel_stats
