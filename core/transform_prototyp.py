from pathlib import Path
from posixpath import join, dirname
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass
import excel_writer
from glob import iglob

@dataclass
class ExtParserContext:
    symbol_infos: Dict[str, List[dict]]
    symbol_definitions: Dict[str, List[dict]]  # symbol_name -> [location1, location2, ...]
    symbol_nr: int
    symbol_defaults: Dict[str, List[dict]]
    symbol_orig_defaults: Dict[str, List[dict]]
    configdefault_symbols: Set[str]
    configdefault_symbols_nr: int
    choice_infos: Dict[str, List[dict]]
    choice_definitions : Dict[str, List[dict]] # choice_name -> [location1, location2, ...]
    choice_nr: int
    choice_dep: Dict[str, List[dict]]
    parser_result: dict
    srctree: Path

class KconfigTransformer:
    """
    build context based on parser_result
    transform lines

    FOR SOURCE_KEYWORDS_TRANSFORMED 
    input:  source "exp_u1/*" (1 line)
    output: source "exp_u1/Kconfig"  (1 line overwrite)
            source "exp_u1/Kconfig2" (1 line added)
    """
    DEF_KEYWORDS = ('def_string', 'def_int', 'def_hex')
    FILE_DEF_KEYWORDS_COUNT = 0
    PROJECT_DEF_KEYWORDS_COUNT = 0
    SOURCE_KEYWORDS = ('source', 'osource', 'rsource', 'orsource')
    FILE_SOURCE_NR = 0
    FILE_OSOURCE_NR = 0
    FILE_RSOURCE_NR = 0
    FILE_ORSOURCE_NR = 0
    FILE_SOURCE_OUT_DIFF = 0
    FILE_OSOURCE_OUT = 0
    FILE_RSOURCE_OUT = 0
    FILE_ORSOURCE_OUT = 0
    NEW_BC_GLOB = 0
    FILE_SOURCE_KEYWORDS_ALL_NR = 0
    FILE_ALL_ADDED_LINES_SKW = 0
    ONE_SOURCE_KEYWORDS_MATCHED_GLOB = 0
    FILE_CONFIGDEFAULT_NR = 0
    FILE_O_SOURCE_KEYWORDS_NO_MATCH = 0
    OPTION_MODULES_COUNTER = 0
    OPTION_MODULES_INFO = []
    FILE_OPT_ENV = 0
    FILE_OPT_ALLNONCONG = 0
    FILE_OPT_DEFCONFIG = 0
    PROCESSED_CHOICES = set()

    def __init__(self, source_spec: str):
        self.source_spec = source_spec.upper()  # maybe for some later checks 
        self.context: Optional[ExtParserContext] = None
   
    def build_context_from_parser(self, parser_result: dict, log: bool) -> ExtParserContext: 
        konf = parser_result['kconf']
        symbol_infos = {}
        symbol_definitions = {}
        symbol_defaults = {}
        symbol_orig_defaults = {}
        configdefault_symbols = set()
        choice_infos = {}
        choice_definitions = {}
        choice_dep = {}

        print(" call different attributes on symbols found in parser_result['unique_defined_syms']")
        
        for sym in parser_result['unique_defined_syms']:
            if sym.name not in (symbol_infos or symbol_definitions or symbol_defaults or symbol_orig_defaults):
                #print(sym.name)
                symbol_infos[sym.name] = []
                symbol_definitions[sym.name] = []
                symbol_defaults[sym.name] = []
                symbol_orig_defaults[sym.name] = []
            
            """ 
            if sym.name == "DEFSTRING" or sym.name=="FOO":
                print(f"sym.name: {sym.name}")
                print(f"sym.origin: {sym.origin}")
                print(f"sym.name_and_loc: {sym.name_and_loc}")
                print(f"\n sym.defaults---------------------")
                for d in sym.defaults:
                    print(f"{d}")
                print(f"\n sym.orig_defaults---------------------")
                for od in sym.orig_defaults:
                    print(f"{od}")
                print(f"\n sym.nodes---------------------")
                for n in sym.nodes:
                    print(f"{n}\n")
                    print(f"{n.dep}\n")
                print(f"\n sym.nodes---------------------")
            """
            symbol_info ={
                'sym.name' : sym.name,
                'sym.origin' : sym.origin,
                'sym.name_and_loc' : sym.name_and_loc
            }  
            symbol_infos[sym.name].append(symbol_info)
            
            for sd in sym.defaults:              
                #print(f"{sd}\n")
                defaults_info = {
                    'sym.default': sd
                }
                symbol_defaults[sym.name].append(defaults_info)
             
            for sod in sym.orig_defaults:
                #print(f"{sod}")  
                orig_defaults_info = {
                    'orig_defaults': sod
                }    
                symbol_orig_defaults[sym.name].append(orig_defaults_info)
            
            for node in sym.nodes:
                is_configdefault = getattr(node, 'is_configdefault', False)
                #print(node.is_configdefault)               
                
                """ 
                if node.defaults and len(node.defaults)>=1:   
                    print("DEBUG")
                    print(len(node.defaults))
                    print(node.defaults)        
                    node_default_dep = self._extract_dependencies(node.defaults[1])
                    node_default_loc = node.defaults[2]
                    print(node_default_dep)
                    print(node_default_loc)
                else:
                    node_default_dep = None
                    node_default_loc = None
                """
                location_info = {
                    'file': node.filename if hasattr(node, 'filename') else None,
                    'line': node.linenr if hasattr(node, 'linenr') else None,
                    'node': node,
                    'node.defaults': node.defaults,
                    #'node.default.dep':  node_default_dep,
                    #'node.default.loc': node_default_loc,
                    'is_configdefault': is_configdefault
                }
                symbol_definitions[sym.name].append(location_info)
            
                if is_configdefault: configdefault_symbols.add(sym.name)
         
        for choice in parser_result['unique_choices']:
            if choice.name not in (choice_infos or choice_definitions or choice_dep):
                choice_infos[choice.name] = []
                choice_definitions[choice.name] = []
                choice_dep[choice.name] = []

            choice_info ={
                'choice.name' : choice.name,
                #'choice.type' : choice.type,
                #'choice.name_and_loc' : choice.name_and_loc,
                'choice.syms': choice.syms,
                #'choice.direct_dep': choice.direct_dep,
                #'choice.orig_defaults': choice.orig_defaults
            }  
            choice_infos[choice.name].append(choice_info)
            #print(f"chinfo: {choice.name_and_loc}: {choice_info}")

            for node in choice.nodes:

                location_info = {
                    'file': node.filename if hasattr(node, 'filename') else None,
                    'line': node.linenr if hasattr(node, 'linenr') else None,
                    'node.prompt': node.prompt,
                    'node.defaults': node.defaults,
                    #'node.item.dd': node.item.direct_dep,
                    'node.dep': node.dep,
                    #'node.item.name': node.item.name
    
                }

                dep_info = {
                    'node.defaults': node.defaults,
                    'node.dep': node.dep,
                }

                choice_definitions[choice.name].append(location_info)
                choice_dep[choice.name].append(dep_info)

        context = ExtParserContext(
            symbol_infos = symbol_infos,
            symbol_definitions = symbol_definitions,
            symbol_nr = len(symbol_definitions),
            configdefault_symbols = configdefault_symbols,
            configdefault_symbols_nr = len(configdefault_symbols),
            symbol_defaults = symbol_defaults,
            symbol_orig_defaults = symbol_orig_defaults,
            choice_infos = choice_infos,
            choice_definitions = choice_definitions,
            choice_nr = len(choice_definitions),
            choice_dep = choice_dep,
            parser_result=parser_result,
            srctree=Path(konf.srctree)
        )
        
        self.context = context
        if log: self._log_parser_context(self.context)
        return context

    def extract_named_choice_info(self, choice_name: str):
        context = self.context
        choice_infos = context.choice_infos
        choice_definitions = context.choice_definitions
        choice_deps = context.choice_dep

        print("------H-----------")
        print(f"context.choice_infos:       {choice_infos}")
        print(f"context.choice_definitions: {choice_definitions}")
        print(f"context.choice_deps:        {choice_deps}\n")

        if choice_name not in choice_infos:
            return {
            'choice_def': []
            }
        
        default_dependencies_extracted_list = []
        node_dep_extracted_list = []

        print(f"choice_deps[{choice_name}]:")
        for entry in choice_deps[choice_name]:
            default_tuple = entry['node.defaults']
            print(f"node.defaults:   {default_tuple}")
            for default in default_tuple:
                default_dependencies = default[1]
                dependencies = self._extract_dependencies(default_dependencies)
                default_dependencies_extracted_list.append(dependencies)
             
            dep_tuple = entry['node.dep']
            print(f"node.dep:        {repr(dep_tuple)}")
            extr_dep_dependencies = self._extract_dependencies(dep_tuple)
            node_dep_extracted_list.append(extr_dep_dependencies)

        print(f"def dependencies extr: {default_dependencies_extracted_list}")
        print(f"dep dependencies extr: {node_dep_extracted_list}")
        
        choice_all_dep_list = []
        choice_all_dep_list.append((choice_name, default_dependencies_extracted_list, node_dep_extracted_list))
    
        print()
        return {
            'choice_def': choice_all_dep_list
        }
        
    def extract_symbol_info(self, context: ExtParserContext, symbol_name: str):
       
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
        from kconfig_writer import KconfigLine
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
            
            # build if <...>
            cond_full = self._create_extended_condition(line_entry.content.get('condition'), deps_ext)
            
            # build line
            indent_str = " " * line_entry.indent
            line_value = line_entry.content.get('value')

            if cond_full:
                transformed_content = f"{indent_str}default {line_value} if {cond_full}"
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
        #for file in files:
        #    print(f"    parser found: {file}")

        return files    

    def _transform_lines(self, lines: List, current_file: Path, cd_definition_info, choice_definition_info):
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
                #print(f"\n while counter i: {i} given line: {line}")
                
                if line.line_type == 'if':
                    if_contains_only_configdefault = self._if_block_contains_only_configdefault(lines, i)
            
                    if if_contains_only_configdefault:
                        print(f"    Skipping if-endif block (only configdefaults) starting at line {line.line_number}")
                        i = self._skip_if_block(lines, i)
                        continue

                if line.line_type == 'configdefault':
                    print(f"    Skipping configdefault block starting at line {line.line_number}")
                    i += 1
                    while i < len(lines) and lines[i].indent > line.indent:
                        print(f"      Skipping line {lines[i].line_number}: {lines[i].line_type}")
                        i += 1
                    # i = 1. line after the block 
                    continue

                if line.line_type == 'named_choice':
                    choice_name = line.content.get('name')
                    print("kdkls")
                    
                    if not choice_name or choice_name not in choice_definition_info:
                        print("kdkls2")
                        pass  
  
                    else:
                        print("kdkls3")
                        choice_info = choice_definition_info[choice_name]
                        # FIRST DEF?
                        #if choice_info['choice_def']:
                        
                        print(f"    processed_choices vor if: {self.PROCESSED_CHOICES}")

                        if choice_name in self.PROCESSED_CHOICES:
                            print("kdkls4")

                            print(f"    Skipping non-first definition of choice {choice_name} at line {line.line_number}")
                            # Skip until endchoice
                            i += 1
                            while i < len(lines) and lines[i].line_type != 'endchoice':
                                i += 1
                            i += 1  # consume endchoice
                            continue
                        
                        print("kdkls5")
                        first_def = self.context.choice_definitions[choice_name][0]
                        first_def_file = self.context.srctree / first_def['file']
                        first_def_line = first_def['line']
                            
                        if (current_file == first_def_file and 
                            line.line_number == first_def_line):
                            print("kdkls6")

                                
                            print(f"    Found first definition of choice {choice_name} at line {line.line_number}")
                            print(f"    Processing choice transformation")

                            self.PROCESSED_CHOICES.add(choice_name)
                            print(f"    processed_choices now: {self.PROCESSED_CHOICES}")

                            i = self.transform_choice(lines, i, choice_info, result, 
                                                lambda l, s, f: self._transform_single_line(l, s, f))
                            #choice_processed = True
                            continue

                
                #if choice_processed:
                #    continue

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
                                    
                                    i = self.transform_cd(lines, i, transformed_entries, result, 
                                                lambda l, s, f: self._transform_single_line(l, s, f))
                                    #print(f"i = self.transform_cd {i}")
                                    cd_processed = True
                                    break 
                
                if cd_processed:
                    continue

                #print(f"\nget transformed wenn line is not config/menuconfig:")
                transformed = self._transform_single_line(line, current_symbol, current_file)
                
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
            stats = self._log_file_and_reset_count(self.FILE_SOURCE_OUT_DIFF, current_file, len_reader_input, len_transformed_lines)
            return result, stats
    
    def transform_choice(self, lines: List, current_index: int, choice_info: dict, result: List, transform_func) -> int:
        from kconfig_writer import KconfigLine
        
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
        # TODO: Kconfiglib can have menuconfig as choice elements (see wsMA_prototyp/test_dir_/transform_choice_analysis/transform_choice_analysis.log)
        print(f"process lines until first choice config/if was found") 
        print(f"current_indx: {current_index + 1} - block endidx {block_end_index}")
        
        # FIND line where first config/if starts
        first_ch_config_idx = None
        for idx in range(current_index + 1, block_end_index):
            if lines[idx].line_type in ['config', 'if']:
                first_ch_config_idx = idx
                break
        
        # PROCESS attr of choice 
        choice_attr_end = first_ch_config_idx if first_ch_config_idx is not None else block_end_index
        print(f"current_indx: {current_index + 1} - choice_attr_end: {choice_attr_end}")
        
        for idx in range(current_index + 1, choice_attr_end):
            line_item = lines[idx]

            # SKIP: type attr (bool/tristate) & optional attr
            if line_item.line_type in ('type_bool', 'type_tristate', 'optional'):
                continue
            
            # everything else: prompt, default, depends on, help -> copy/transform as usual (because it's a first definition)
            transformed = transform_func(line_item, None, None)
            if transformed is None:
                continue

            if isinstance(transformed, list):
                result.extend(transformed)
            else:
                result.append(transformed)  
        
        print(f"PROCESS attr {result}")

        # PROCESS: ADD ATTR OF OTHER DEFINITIONS ----------------------------------------------------------------------------------------------
        # TODO: function die umgehende if und depends on von menus verbindet, ggb. die lines aus dem File wo sich die 2. definition befindet, result.append(self.get_dep_from_other_def)
        # ADD depends on and default lines with extended if-condition  
        # TODO: CHANGE: dont take from parser -> instead read lines and get there the extenden
        # also +2 it's just quick fix
        # TODO: add teh extenden default/ depends from other definitions 
        # WRONG: from parser overall, user default_dependencies_extracted_list, node_dep_extracted_list) -> 'choice_def': choice_all_dep_list
        choice_def = choice_info.get('choice_def')
        choice_configs = choice_info.get('choice_configs', [])
        print(f"choice_def {choice_def}")
        print(f"choice_configs length: {len(choice_configs)}")
        print(f"choice_configs {choice_configs}")
        for idx, cfg in enumerate(choice_configs):
            print(f"  [{idx}] type={cfg.get('type')}, symbol={cfg.get('symbol')}, symbols={cfg.get('symbols')}, choice_line={cfg.get('choice_line')}")

        menuconfigs_to_add_after = []  # Collect menuconfigs to add after endchoice

        if not choice_def:
            print("No choice_def found")
        else:
            # Unpack the single entry
            _, all_default_deps, all_node_deps = choice_def[0]
            
            print(f"all_default_deps: {all_default_deps}")
            print(f"all_node_deps: {all_node_deps}")
            
            # Group configs by choice_line to identify which definition they belong to
            configs_by_definition = {}
            for cfg in choice_configs:
                cfg_choice_line = cfg.get('choice_line')
                if cfg_choice_line not in configs_by_definition:
                    configs_by_definition[cfg_choice_line] = []
                configs_by_definition[cfg_choice_line].append(cfg)
            
            # Sort by choice_line to get definitions in order
            sorted_def_lines = sorted(configs_by_definition.keys())
            print(f"Found {len(sorted_def_lines)} choice definitions at lines: {sorted_def_lines}")
            # Process each definition (skip the first one, index 0)
            for def_idx in range(1, len(sorted_def_lines)):
                depends_from_def = []
                choice_line_num = sorted_def_lines[def_idx]
                configs_in_this_def = configs_by_definition[choice_line_num]
                
                
                # Get dependencies for this definition
                default_deps = all_default_deps[def_idx] if def_idx < len(all_default_deps) else []
                node_deps = all_node_deps[def_idx] if def_idx < len(all_node_deps) else []
                
                print(f"\nProcessing definition {def_idx} at line {choice_line_num}")
                print(f"  default_deps: {default_deps}")
                print(f"  node_deps: {node_deps}")
                #print(f"  configs: {[c['symbol'] for c in configs_in_this_def]}")
                print(f"  entries in this def:")
                for c in configs_in_this_def:
                    if c.get('type') == 'if_block':
                        print(f"    if_block with configs: {c.get('configs')} and menuconfigs: {[mc['symbol'] for mc in c.get('menuconfigs', [])]}")
                    else:
                        print(f"    {c.get('type')}: {c.get('symbol')}")
                
                # Take the first entry's lines as representative for this definition
                # (since all configs in same definition have same choice-level attributes)
                if configs_in_this_def:
                    representative_cfg = configs_in_this_def[0]
                    
                    # -------- depends on ----------
                    for dep_line in representative_cfg.get('depends_lines', []):
                        raw = dep_line.raw_text.strip()
                        base_cond = raw[len('depends on'):].strip()

                        additional = [
                            d for d in node_deps
                            if d not in base_cond and d != 'y'
                        ]

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
                        result.append(KconfigLine(new_line, dep_line.line_number))
                        depends_from_def.append(KconfigLine(new_line, dep_line.line_number))
                        print(f"depdsksakl {depends_from_def}")
                        print(f"  Added depends: {new_line.strip()}")

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
                        print(f"  Added default: {new_line.strip()}")

        print(f"\nFinal result has {len(result)} lines before adding configs")
        
        # ADD all configs in choice block
        # 1. TRACK configs already present in this choice block
        existing_configs = set()

        idx = first_ch_config_idx
        while idx is not None and idx < block_end_index:
            line_item = lines[idx]
            print(f"Track existing configs: {line_item}")
            # Stop at endchoice
            if line_item.line_type == 'endchoice':
                break

            # Start of a config/menuconfig block
            if line_item.line_type in ('config', 'menuconfig'):
                sym_name = line_item.content.get('symbol')
                if sym_name:
                    existing_configs.add(sym_name)  # list of existing 

                # Process the whole config block
                while idx < block_end_index:
                    current = lines[idx]
                    print(f"current: {current}")

                    # Stop if next config or endchoice starts
                    if (current.line_type in ('config', 'menuconfig', 'endchoice') and current is not line_item):
                        break

                    transformed = transform_func(current, None, None)
                    if transformed is not None:
                        if isinstance(transformed, list):
                            result.extend(transformed)
                        else:
                            result.append(transformed)
                    idx += 1
                continue
            idx += 1

        print(f"result after first definition: {len(result)} lines")
        
        # 2. ADD entries (configs/ifs/ but menuconfig shoild be skipped) from other definitions
        added_items = 0
        for entry in choice_configs:
            entry_type = entry.get('type', 'config')
            
            if entry_type == 'if_block':
                # Add entire if-block (contains configs, maybe menuconfigs)
                configs_in_if = entry.get('configs', [])
                menuconfigs_in_if = entry.get('menuconfigs', [])
                
                # Add the if-block to the choice
                for line in entry.get('block', []):
                    result.append(line)
                
                # Collect menuconfigs to add after endchoice
                for mc_info in menuconfigs_in_if:
                    mc_symbol = mc_info.get('symbol')

                    if mc_symbol in existing_configs:
                        continue

                    mc_info_copy = dict(mc_info)
                    mc_info_copy['depends_from_def'] = depends_from_def
                    menuconfigs_to_add_after.append(mc_info_copy)
                    #menuconfigs_to_add_after.append(mc_info)
                    existing_configs.add(mc_symbol)
                
                # Mark configs as existing
                for cfg in configs_in_if:
                    existing_configs.add(cfg)
                added_items += 1
                print(f"      Added if-block with configs {configs_in_if} from {entry.get('file')}")
            
            elif entry_type == 'menuconfig':
                # Menuconfig - collect to add after endchoice
                config_symbol = entry.get('symbol')

                if config_symbol in existing_configs:
                    continue
                
                menuconfigs_to_add_after.append({
                    'symbol': config_symbol,
                    'block': entry.get('block', []),
                    'if_condition': entry.get('if_condition'),
                    'depends_lines': entry.get('depends_lines', []),
                    'depends_from_def': depends_from_def,
                    'node_deps': all_node_deps[def_idx] if def_idx < len(all_node_deps) else []
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
                
                existing_configs.add(config_symbol)
                added_items += 1
                print(f"      Added config {config_symbol} from {entry.get('file')}")

        print(f"    Added {added_items} entries from other choice definitions")

        # ADD endchoice
        result.append(end_line)
        
        # ADD menuconfigs after endchoice
        print(f"\n  Adding {len(menuconfigs_to_add_after)} menuconfigs after endchoice")
        for mc_info in menuconfigs_to_add_after:
            mc_symbol = mc_info['symbol']
            mc_block = mc_info['block']
            if_cond = mc_info.get('if_condition')
            depends_lines = mc_info.get('depends_lines', [])
            node_deps = mc_info.get('node_deps', [])
            depends_from_def = mc_info.get('depends_from_def', [])
            
            print(f"    Adding menuconfig {mc_symbol}, depends_from_def={depends_from_def}")
            
            # Add menuconfig line
            result.append(mc_block[0])  # First line is menuconfig declaration
            
            # Modify prompt line to add if condition if needed
            for line in mc_block[1:]:
                result.append(line)
            for dep_line in depends_from_def:
                raw = dep_line.raw_text.strip()
                new_line = f"{' ' * (line.indent)}{raw}"
                print(f"hello {new_line}")
                print(line.indent)
                result.append(KconfigLine(new_line, dep_line.line_number))
        
        return block_end_index

    def transform_cd(self, lines: List, current_index: int, transformed_entries: List, result: List, transform_func) -> int:
       
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
        self.FILE_CONFIGDEFAULT_NR += len(transformed_entries)  
        return block_end_index

    def _transform_single_line(self, line, current_symbol: Optional[str], current_file: Path):
        """ 
        Returns:
            - KconfigLine: 1:1
            - List[KconfigLine]: 1:n
        """
        if line.line_type in self.DEF_KEYWORDS:
            self.FILE_DEF_KEYWORDS_COUNT += 1                                            # for each def_* -> count 1 one added line   
            return self._transform_def_keyword(line)
        elif line.line_type in self.SOURCE_KEYWORDS:
            # count all source keywords 
            self.FILE_SOURCE_KEYWORDS_ALL_NR += 1                                        # for each self.SOURCE_KEYWORDS -> count 1, so that we have SUM of all 
            return self._transform_source_line(line, current_file, resolve_log=True)    # if last parameter == True, than there is log for resolving and also iglob check is active 
        elif line.line_type == "option modules":
            return self._transform_opt_modules(line, current_file)
        elif line.line_type == "option env":
            self.FILE_OPT_ENV += 1
            return self._transform_opt_env(line)
        else:
            if line.line_type == "allnoconfig_y":
                self.FILE_OPT_ALLNONCONG += 1
            if line.line_type == "defconfig_list":
                self.FILE_OPT_DEFCONFIG += 1
            return line    

    def _transform_def_keyword(self, line) -> List:
        """
        For def_* keywords == def_bool, def_int, def_hex, def_string 
        config                            config 
            def_<typ> [if <exp>]   -->      <type> 
                                            default [if <exp>]
        """
        from kconfig_writer import KconfigLine  # avoid circular import
            
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

    def _transform_source_line(self, line, current_file, resolve_log: Optional[bool]) -> List:
        from kconfig_writer import KconfigLine
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
        if source_keyword == "source": self.FILE_SOURCE_NR += 1
        elif source_keyword == "osource": self.FILE_OSOURCE_NR += 1
        elif source_keyword == "rsource": self.FILE_RSOURCE_NR += 1  
        elif source_keyword == "orsource": self.FILE_ORSOURCE_NR += 1       

        # NO GLOB -> copy line as it is to the output! BUT skip this for (o)r/(o)source because these have to be transformed to source before returning the line
        if not has_glob and not source_keyword == 'rsource' \
            and not source_keyword == 'orsource' and not source_keyword == 'osource':
            print(f"    source without glob: 1")    # this is just for LOGGING, no need of using FILE_SOURCE_OUT_DIFF, because it's always 1 line that we look at and return
            return line
        
        # GLOB
        print(f"    GLOB LOG ----------------------------------------------------------------------------")
        print(f"    Resolve {source_keyword}: {pattern} at line {line.line_number}")
        
        # RESOLVE 
        matched_files = []          # we only need matched_files, that we get through node iteration 
        filenames = []              # this is just to show that both ways (matched and iglob) work 
        iglob_with_rel_path = []    # so that we can compare lists - matched_files and filenames (but filenames are transformed to SRCTREE relative path)
        if self.context is not None:
            kconf = self.context.parser_result['kconf']
            srctree = Path(kconf.srctree or "")
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

                if src_file_abs_path.samefile(current_file_abs_path) and current_line_nr == src_linenr:
                    matched_files.append(node.filename)


                    #if node.item.name:
                    #    node_item_name = node.item.name

                    if resolve_log:
                        print(f"        ---- RESOLVE LOG ------------------------------------------------------")
                     #   print(f"        {source_keyword} includes node for: {node_item_name}")
                        print(f"        node's file: {node.filename}")
                        print(f"        node's include paths: {node.include_path}") 
                        print(f"        -> relevant is where node was sourced from: {src_file} at line {src_linenr}") 
                        print(f"        resolved: ")
                    continue
            
            if resolve_log:
                # use iglob (exacly as kconfiglib) just to show that both ways work 
                if source_keyword == "rsource" or source_keyword == "orsource":
                    pattern = join(dirname(current_file), pattern)
                filenames = sorted(iglob(join(srctree, pattern)))
                # iglob returnes abs path -> convert to SRCTREE-relative path
                for file in filenames:
                    iglob_with_rel_path.append(str(Path(file).relative_to(os.environ["srctree"])))
            
        if not matched_files:
            # don't just comment the line, instead skip -> no output line, when there is no match 
            print(f"      no files found for the: {pattern}")   

            if not filenames:
                print(f"    iglob didn't find anything")

            self.FILE_O_SOURCE_KEYWORDS_NO_MATCH += 1
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
                new_line_text = f'{indent_str}{source_keyword} "{matched_file}"'
                new_line = KconfigLine(new_line_text, line.line_number)
                result_lines.append(new_line)
                print(f"      -> {matched_file}")
        
        # for glob log:
        self.ONE_SOURCE_KEYWORDS_MATCHED_GLOB += len(result_lines)   
        print(f"    Files matching: {self.ONE_SOURCE_KEYWORDS_MATCHED_GLOB} (using {source_keyword})")

        if resolve_log:
            for file in filenames:
                print(f"    iglob found: {file}")
            print(f"    transformed iglob list (relative paths): {iglob_with_rel_path}")
            if matched_files == iglob_with_rel_path:
                print(f"    CHECK OK: transformed iglob list == list of matched_files through iteration")
            else: 
                raise RuntimeError("check source matching")
        
        # for file log, save diff. when source matches more files (1:n)
        self.NEW_BC_GLOB = self.ONE_SOURCE_KEYWORDS_MATCHED_GLOB - 1
        self.FILE_SOURCE_OUT_DIFF += self.NEW_BC_GLOB  # sum all diff for 1 file, reset after FILE logging
        
        self.ONE_SOURCE_KEYWORDS_MATCHED_GLOB = 0 # set back for the next line with keyword
        return result_lines

    def _transform_opt_modules(self, line, current_file):
        # option modules --> modules
        from kconfig_writer import KconfigLine 
        indent_str = ' ' * line.indent
        new_line_text = f'{indent_str}modules'
        new_line = KconfigLine(new_line_text, line.line_number)
        self.OPTION_MODULES_COUNTER += 1 

        self.OPTION_MODULES_INFO.append({
            'counter': self.OPTION_MODULES_COUNTER, 
            'line': line.line_number, 
            'file': current_file
        })
        return new_line

    def _transform_opt_env(self, line):
        # option env="<value>" --> default "$(<value>)"
        from kconfig_writer import KconfigLine  # avoid circular import
        indent_str = ' ' * line.indent
        env_var = line.content.get('env')
        #env_value = os.environ.get(env_var) WRONG

        default_text = f"{indent_str}default \"$({env_var})\""
            
        default_line = KconfigLine(
            default_text,
            line.line_number  
        )
            
        return default_line

    def transform_all_files(self, reader, writer, project_dir: Path, output_dir: Path, \
                            log: bool, log_lines: bool, log_excel_after_each_file: bool, log_excel_output: Optional[str]):
        """
        1. get all source files parser found (these are all realtive to srctree)
        2. build paths for input & output files
        """
        excel_stats = []
        if self.context is None:
            raise RuntimeError("Context missing!")
        
        source_files = self._get_all_source_files() # all paths are relative to srctree 
        transformed_count = 0
        cd_definition_info = {}
        choice_definition_info = {}

        print("\n3. Filter ExtParserContext")
        print("extract all configdefault symbols and for each get transformed lines and last config")
        for cd in self.context.configdefault_symbols:
            
            if cd not in cd_definition_info:
                cd_definition_info[cd] = []     # replace defaultdict

            info = self.extract_symbol_info(self.context, cd)
            last_config = self._get_last_config(info['sym_def'])
            cd_default_lines = self._get_cd_entries(info['sym_def'])
            tcd_list = self._get_transformed_config_defaults(cd_default_lines, reader, project_dir)
            cd_all_sym = {
               'last_config': last_config,
               'cd_default_lines': cd_default_lines,
               'transformed_entries_list': tcd_list
            } 
            cd_definition_info[cd].append(cd_all_sym)

            if log:
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

        for choice_name in self.context.choice_definitions.keys():
            if choice_name not in choice_definition_info:
                choice_definition_info[choice_name] = {}
            
            choice_info = self.extract_named_choice_info(choice_name)
       
            # Get all config entries for this choice
            choice_configs = self._get_all_choice_configs(choice_name, reader, project_dir)
            choice_info['choice_configs'] = choice_configs
            
            choice_definition_info[choice_name] = choice_info
            
            if log:
                print(f"\n  named choice: {choice_name}")
                print(f"    'choice_def': {choice_info.get('choice_def')}")
                print(f"    'choice_configs': {len(choice_configs)} config entries")

        print(f"\nfor each given file at source_files start building path output structur and call reader and writer")     
        print(f"\n4. Transform all files - needs reader & writer")
        for file_path in source_files:
            input_file = project_dir / file_path
            output_file = output_dir / file_path
            
            print(f"test file: {input_file}")
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
            transformed, stats = self._transform_lines(lines, input_file, cd_definition_info, choice_definition_info)
            
            excel_stats.append(stats)

            if log_excel_after_each_file:
                excel_writer.write_to_excel(excel_stats, log_excel_output)
            
            new_lines = self._remove_consecutive_empty_lines(transformed)
            try:
                writer.write(new_lines, output_file)
                transformed_count += 1
            except Exception as e:
                print(f"     Error write: {e}")
        
        print(f"----------------------------------------------------------------------")
        print(f"finished transforming: {transformed_count} files transformed")
        print(f"----------------------------------------------------------------------")
        if self.OPTION_MODULES_INFO:
            print("info about option-attr: ")
            for info in self.OPTION_MODULES_INFO:
                print(f"    {info['counter']} option modules-attr found at line {info['line']} in {info['file']}")
            print(f"    allnoconfig_y:  {self.FILE_OPT_ALLNONCONG}")
            print(f"    defconfig_list: {self.FILE_OPT_DEFCONFIG}")
        
        self.FILE_OPT_DEFCONFIG = 0
        self.FILE_OPT_ALLNONCONG = 0
        self.OPTION_MODULES_COUNTER = 0
        self.OPTION_MODULES_INFO.clear()
        return excel_stats

    # TODO: check again 
    def _get_all_choice_configs(self, choice_name: str, reader, project_dir: Path):
        """
        Get all config entries for a named choice from all its definitions.
        
        Collects:
        - Choice-level default and depends lines
        - Config entries (standalone or in if-blocks)
        - Menuconfig entries (standalone or in if-blocks) with their if-conditions
        """
        print(f"\n=== _get_all_choice_configs for {choice_name} ===")
        
        if choice_name not in self.context.choice_definitions:
            print(f"  {choice_name} not in choice_definitions!")
            return []

        choice_definitions = self.context.choice_definitions[choice_name]
        print(f"  Found {len(choice_definitions)} definitions:")
        for idx, cd in enumerate(choice_definitions):
            print(f"    [{idx}] file={cd.get('file')}, line={cd.get('line')}")
        
        all_entries = []

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
                        
                        j += 1
                    
                    print(f"  DEBUG: Found choice {choice_name} at {choice_file}:{choice_line}")
                    print(f"  DEBUG: choice_default_lines: {choice_default_lines}")
                    print(f"  DEBUG: choice_depends_lines: {choice_depends_lines}")
                    
                    # Now collect all configs AND if-blocks in this choice block
                    if first_config_idx is not None:
                        k = first_config_idx
                        while k < len(lines):
                            current_line = lines[k]
                            
                            if current_line.line_type == 'endchoice':
                                break
                            
                            # Handle IF blocks
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
                                           
                                    # skip if menuconfig for the copy 
                                    if next_line.line_type != 'menuconfig':
                                        if_block.append(next_line)
                                    
                                    # Track config symbols inside the if
                                    if next_line.line_type == 'config':
                                        sym_name = next_line.content.get('symbol')
                                        if sym_name:
                                            if_configs.append(sym_name)
                                    
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
                                
                                print(f"  DEBUG: Adding if-block with configs {if_configs} and menuconfigs {[mc['symbol'] for mc in if_menuconfigs]}")
                                k = m
                            
                            # Handle standalone configs/menuconfigs (not inside if)
                            elif current_line.line_type in ('config', 'menuconfig'):
                                sym_name = current_line.content.get('symbol')
                                is_menuconfig = (current_line.line_type == 'menuconfig')
                                config_block = [current_line]
                                
                                # Collect the config/menuconfig block
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
                                    
                                    config_block.append(next_line)
                                    m += 1
                                
                                print(f"  DEBUG: Adding {'menuconfig' if is_menuconfig else 'config'} {sym_name}")
                                
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
        return all_entries

    def _log_file_and_reset_count(self, new_lines_skw : int, current_file : Path, len_input : int, len_result : int):
        print(f"    FILE LOG --------------------------------------------------------------")
        #print(f"    File:                      {str(current_file)}")
        print(f"    Reader input                {len_input} lines")
        print(f"    -----------------------------------------------------------------------")
        print(f"    All source_keywords:        {self.FILE_SOURCE_NR}")
        print(f"    All osource_keywords:       {self.FILE_OSOURCE_NR}")
        print(f"    All rsource_keywords:       {self.FILE_RSOURCE_NR}")
        print(f"    All orsource_keywords:      {self.FILE_ORSOURCE_NR}")  
        print(f"    SUM (r/or/o)source lines:   {self.FILE_SOURCE_KEYWORDS_ALL_NR}")
        print(f"    All \"option env\" attr:      {self.FILE_OPT_ENV}")
        print(f"    -----------------------------------------------------------------------")
        print(f"    Transformer Output:         {len_result} lines")
        print(f"    -----------------------------------------------------------------------")
        print(f"        Added new bc of def_*:           {self.FILE_DEF_KEYWORDS_COUNT}")
        print(f"        Added new lines of source: -1 (= means one line was just overwritten)" if new_lines_skw < 0 \
              else f"        Added new lines of source:       {new_lines_skw}")
        print(f"        Added new bc of config_default:  {self.FILE_CONFIGDEFAULT_NR}")
        print(f"        Removed   bc of config_default:  {self.FILE_CONFIGDEFAULT_NR}") 
        print(f"        Removed no match for o(r)source: {self.FILE_O_SOURCE_KEYWORDS_NO_MATCH}")   

        # STORE FOR EXCEL
        file_stats_excel = {
            'test file' : str(current_file),
            'input'     : len_input,
            'output'    : len_result,
            'source_keyword' : self.FILE_SOURCE_NR,
            'osource_keyword' : self.FILE_OSOURCE_NR,
            'rource_keyword' : self.FILE_RSOURCE_NR,
            'orource_keyword' : self.FILE_ORSOURCE_NR,
            'new lines bc source': new_lines_skw,
            'new lines bc cd': self.FILE_CONFIGDEFAULT_NR,
            'removed bc o(r)source': self.FILE_O_SOURCE_KEYWORDS_NO_MATCH
        }

        self.FILE_SOURCE_NR = 0
        self.FILE_OSOURCE_NR = 0
        self.FILE_RSOURCE_NR = 0
        self.FILE_ORSOURCE_NR = 0
        self.FILE_SOURCE_KEYWORDS_ALL_NR = 0
        self.FILE_DEF_KEYWORDS_COUNT = 0
        self.FILE_ALL_ADDED_LINES_SKW = 0
        self.FILE_CONFIGDEFAULT_NR = 0
        self.NEW_BC_GLOB = 0
        self.FILE_SOURCE_OUT_DIFF = 0
        self.FILE_O_SOURCE_KEYWORDS_NO_MATCH = 0
        self.FILE_OPT_ENV = 0

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

        print(f"\n")
        print(f"    -> ExParserContext - symbols: {given_context.symbol_nr} ")#({', '.join(given_context.symbol_definitions.keys())})")
        print(f"    -> ExParserContext - configdefaults: {given_context.configdefault_symbols_nr}({', '.join(given_context.configdefault_symbols)})")
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

        for line in lines:
            if line.line_type == 'empty':        # looking at empty line, so 
                if previous_line_empty:
                    removed_nr += 1
                    continue                     # skip this empty line, go check the next one           
                previous_line_empty = True       # if previous line wasn't empty, than set a flag on this one 
            else:
                previous_line_empty = False      # the line we are looking at it's not empty, so set the flag

            cleaned.append(line)
        return cleaned
