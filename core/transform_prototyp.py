from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass

@dataclass
class ExtParserContext:
    symbol_infos: Dict[str, List[dict]]
    symbol_definitions: Dict[str, List[dict]]  # symbol_name -> [location1, location2, ...]
    symbol_nr: int
    symbol_defaults: Dict[str, List[dict]]
    symbol_orig_defaults: Dict[str, List[dict]]
    configdefault_symbols: Set[str]
    configdefault_symbols_nr: int
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
    DEF_KEYWORDS = ('def_bool', 'def_string', 'def_int', 'def_hex')
    FILE_DEF_KEYWORDS_COUNT = 0
    PROJECT_DEF_KEYWORDS_COUNT = 0
    SOURCE_KEYWORDS = ('source', 'osource', 'rsource', 'orsource')
    #RSOURCE_KEYWORDS = ('rsource')
    FILE_SOURCE_NR = 0
    FILE_OSOURCE_NR = 0
    FILE_RSOURCE_NR = 0
    FILE_ORSOURCE_NR = 0
    FILE_SOURCE_KEYWORDS_ALL_NR = 0
    FILE_ALL_ADDED_LINES_SKW = 0
    ONE_SOURCE_KEYWORDS_MATCHED_GLOB = 0
    FILE_ALL_SOURCE_KEYWORDS_RESULT_OF_GLOB = 0
    

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
         
        context = ExtParserContext(
            symbol_infos = symbol_infos,
            symbol_definitions = symbol_definitions,
            symbol_nr = len(symbol_definitions),
            configdefault_symbols = configdefault_symbols,
            configdefault_symbols_nr = len(configdefault_symbols),
            symbol_defaults = symbol_defaults,
            symbol_orig_defaults = symbol_orig_defaults,
            parser_result=parser_result,
            srctree=Path(konf.srctree)
        )
        
        self.context = context
        if log: self._log_parser_context(self.context)
        return context

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
            for location_info in symbol_definitions[symbol_name]:
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
        
        for loc, deps_ext in cd_entries:
            file_path, line_number = loc
            full_path = project_dir / Path(file_path)
            print(loc)
            print(full_path)
            
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

    def _transform_lines(self, lines: List, current_file: Path, cd_definition_info) -> List:
            """
            lines -> from reader 
            """
            print(f"start transforming lines")
            print(f"    Reader Input: {len(lines)} lines")
            if self.context is None:
                raise RuntimeError("call build_context_from_parser() first")
            
            result = []             # list for whole output  
            i = 0                   # counter
            current_symbol = None   
                
            while i < len(lines):
                cd_processed = False
                line = lines[i]
                print(f"\n while counter i: {i} given line: {line}")
                
                if line.line_type in ['config', 'menuconfig']:
                    print("line is config/ menuconfig")
                    current_symbol = line.content.get('symbol')
                    print(f"line's symbol: {current_symbol}")
                    
                    if current_symbol and current_symbol in cd_definition_info:
                        cd_info_list = cd_definition_info[current_symbol]
                        print(f"\ncd_info_list: {cd_info_list}")

                        # Durchlaufe alle Einträge für dieses Symbol (normalerweise nur einer)
                        for cd_entry in cd_info_list:
                            last_config = cd_entry.get('last_config')
                            print(f"\nlast_config: {last_config}")
                            transformed_entries = cd_entry.get('transformed_entries_list', [])
                            print(f"transformed_entries: {transformed_entries}")

                            if last_config:
                                last_conf_symbol = last_config[0]
                                last_conf_file = last_config[1]
                                last_conf_line = last_config[2]
                                print(f"last_conf_symbol: {last_conf_symbol}")
                                print(f"last_conf_file: {last_conf_file}")
                                print(f"last_conf_line: {last_conf_line}") 

                                last_conf_full_path = self.context.srctree / last_conf_file
                                print(f"last_conf_full_path: {last_conf_full_path}")

                                if (current_symbol == last_conf_symbol and 
                                    line.line_number == last_conf_line and 
                                    current_file == last_conf_full_path):
                                    
                                    print(f"    Found matching config for {current_symbol} at line {line.line_number}")
                                    print(f"    Adding {len(transformed_entries)} configdefault entries")
                                    
                                    i = self.transform_cd(lines, i, transformed_entries, result, 
                                                lambda l, s, f: self._transform_single_line(l, s, f))
                                    print(f"i = self.transform_cd {i}")
                                    cd_processed = True
                                    break 
                
                if cd_processed:
                    continue

                print(f"\nget transformed wenn line is not config/menuconfig:")
                transformed = self._transform_single_line(line, current_symbol, current_file)
                
                print(f"transformed: {transformed}")
                
                if transformed is None:
                    print(f"transformed is non i++")
                    i += 1
                    continue
                
                if isinstance(transformed, list):
                    result.extend(transformed) # 1:n (def_bool → bool + default)
                else:
                    result.append(transformed) # 1:1         
                i += 1  # go to the next line
                print(f"result: {result}")
            
            # count how many lines were added to output file
            # = SUM of all lines matched through glob - SUM of all (r/or/o)source_keywords 
            self.FILE_ALL_ADDED_LINES_SKW = self.FILE_ALL_SOURCE_KEYWORDS_RESULT_OF_GLOB - self.FILE_SOURCE_KEYWORDS_ALL_NR   
            transformed_lines = len(result)
            self._log_file_and_reset_count(self.FILE_ALL_ADDED_LINES_SKW, transformed_lines)
            return result
    
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
        
        # call transfor_single_line for lines in block itself 
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
        return block_end_index

    def _transform_single_line(self, line, current_symbol: Optional[str], current_file: Path):
        """ 
        Returns:
            - KconfigLine: 1:1
            - List[KconfigLine]: 1:n
        """
        if line.line_type in self.DEF_KEYWORDS:
            self.FILE_DEF_KEYWORDS_COUNT += 1           # for each def_* -> count 1 one added line   
            return self._transform_def_keyword(line)
        elif line.line_type in self.SOURCE_KEYWORDS:
            self.FILE_SOURCE_KEYWORDS_ALL_NR += 1       # for each self.SOURCE_KEYWORDS -> count 1
            return self._transform_source_line(line, current_file)
        else:
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

    def _transform_source_line(self, line, current_file) -> List:
        from kconfig_writer import KconfigLine
        import re, os

        match = re.match(r'(source|osource|rsource|orsource)\s+["\']([^"\']+)["\']', line.stripped)
        if not match:
            print(f"error at source line: {line}")
        
        indent_str = ' ' * line.indent
        source_keyword = match.group(1)
        pattern = match.group(2)
        has_glob = any(c in pattern for c in ['*', '?', '[', ']'])

        # count each keyword in file
        if source_keyword == "source": self.FILE_SOURCE_NR += 1
        elif source_keyword == "osource": self.FILE_OSOURCE_NR += 1
        elif source_keyword == "rsource": self.FILE_RSOURCE_NR += 1       
        else: self.FILE_ORSOURCE_NR += 1  
        # no glob -> copy line to the output as it is 
        if not has_glob and not source_keyword == 'rsource' \
            and not source_keyword == 'orsource' and not source_keyword == 'osource':
            return line

        print(f"    GLOB LOG --------------------------------------------------------------")
        if source_keyword == "rsource" or "orsource" or "osource": print(f"    Resolve {source_keyword}: {pattern}")
        else: print(f"    Resolve glob: {pattern}")
        
        matched_files = []
        if self.context is not None:
            kconf = self.context.parser_result['kconf']
            srctree = Path(kconf.srctree or "")
            current_abs = Path(current_file).resolve()
            
            # iterate over all nodes in tree - From: {src_file} at {src_linenr}
            for node in kconf.node_iter(): 
                
                if not node.filename: continue
                if not node.include_path: continue
                #print(f"    {node.filename}\n and {node.include_path}\n and {node}") # DON'T DELETE FOR DEBUGGING
                
                # file and line where this node was sourced from
                src_file, src_linenr = node.include_path[-1]
                #print(f"    -> From: {src_file} at {src_linenr}") # DON'T DELETE FOR DEBUGGING

                # absolute path from source file
                src_abs = (srctree / src_file).resolve() \
                    if not os.path.isabs(src_file) else Path(src_file).resolve()

                # current file == src_file which has source_keyword 
                # AND line at current file == include location in src_linenr 
                # add node.filename to the list (== string after source_keywords)
                if src_abs.samefile(current_abs) and line.line_number == src_linenr:
                    matched_files.append(node.filename)
                    continue
               
        if not matched_files:
            print(f"      no files found for the: {pattern}")
            self.FILE_ALL_SOURCE_KEYWORDS_RESULT_OF_GLOB +=1    #TODO: maybe another counter and rename this = output source lines
            if source_keyword == "orsource" or source_keyword == "osource":
                new_line_text = f'#{indent_str}{source_keyword} "{pattern}"'
                new_line = KconfigLine(new_line_text, line.line_number)
                return new_line
            return line
        
        # bild source for each found file #TODO: check sorted
        result_lines = []
        for matched_file in sorted(set(matched_files)):

            if source_keyword == 'rsource' or source_keyword == 'orsource' or source_keyword == 'osource':
                base_dir = Path(current_file).parent
                #transform_to_abs = Path(matched_file).resolve()   WRONG 
                transform_to_abs = (base_dir / matched_file).resolve()
                new_line_text = f'{indent_str}{source_keyword} "{transform_to_abs}"'
                new_line = KconfigLine(new_line_text, line.line_number)
                result_lines.append(new_line)
                print(f"      -> {transform_to_abs}")
                continue

            new_line_text = f'{indent_str}{source_keyword} "{matched_file}"'
            new_line = KconfigLine(new_line_text, line.line_number)
            result_lines.append(new_line)
            print(f"      -> {matched_file}")

        # for resolve glob log - one keyword matched 
        self.ONE_SOURCE_KEYWORDS_MATCHED_GLOB += len(result_lines)      
        print(f"    Files matching glob: {self.ONE_SOURCE_KEYWORDS_MATCHED_GLOB} (using {source_keyword})")
        self.ONE_SOURCE_KEYWORDS_MATCHED_GLOB = 0 # set back for the next line with keyword

        # for file log
        self.FILE_ALL_SOURCE_KEYWORDS_RESULT_OF_GLOB += len(result_lines)
        
        return result_lines
    
    def _transform_configdefaults(self, line, current_sym) -> List:
            kconf = self.context.parser_result['kconf']
            
            """for sym, definition in self.context.symbol_definitions.items():
                if (sym == current_sym):
                    print(f"   '{sym}' is defined x{len(definition)}")
            
            for node in kconf.node_iter(): 
                
                if not node.filename: continue
                if not node.include_path: continue
                #if not node.is_configdefault: continue
                print(f"    {node.filename} and {node.include_path} and \n {node.item}")
                #print(f"    {node.is_configdefault}\n and {node}") # DON'T DELETE FOR DEBUGGING
                src_file, src_linenr = node.include_path[-1]
                print(f"    -> From: {src_file} at {src_linenr}") # DON'T DELETE FOR DEBUGGING
                print("--------------------------------------------------")"""
            return line  

    def transform_all_files(self, reader, writer, project_dir: Path, output_dir: Path, log: bool):
        """
        1. get all source files parser found (these are all realtive to srctree)
        2. build paths for input & output files

        """
        if self.context is None:
            raise RuntimeError("Context missing!")
        
        # all paths are relative to srctree 
        source_files = self._get_all_source_files()
        transformed_count = 0
        LINE_TYP_LOG = ("configdefault", "default")
        cd_definition_info = {}

        print(f"/n")
        print("extract configdefault symbols and for each get transformed lines and last config")
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

        print("here")
        print(cd_definition_info)
          #info = self.extract_symbol_info(self.context, 'FOO')

        for file_path in source_files:
            input_file = project_dir / file_path
            output_file = output_dir / file_path
            
            if not input_file.exists():
                print(f"  Skip not found: {input_file}")
                continue
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            lines = reader.read_file(input_file)

            if log:
                for line in lines:
                    #if line.line_type in LINE_TYP_LOG:
                        print(f"    {line}")
                        if line.line_type != 'empty' and line.line_type != 'other':
                            print(f"        -> Content: {line.content}")

            transformed = self._transform_lines(lines, input_file, cd_definition_info)
            try:
                writer.write(transformed, output_file)
                transformed_count += 1
            except Exception as e:
                print(f"     Error write: {e}")
        
        print(f"----------------------------------------------------------------------")
        print(f"finished transforming: {transformed_count} files transformed")

    def _log_file_and_reset_count(self, new_lines_skw : int, len_result : int):
        print(f"    FILE LOG --------------------------------------------------------------")
        print(f"    All source_keywords:        {self.FILE_SOURCE_NR}")
        print(f"    All osource_keywords:       {self.FILE_OSOURCE_NR}")
        print(f"    All rsource_keywords:       {self.FILE_RSOURCE_NR}")
        print(f"    All orsource_keywords:      {self.FILE_ORSOURCE_NR}")  
        print(f"    SUM (r/or/o)source lines:   {self.FILE_SOURCE_KEYWORDS_ALL_NR}")
        print(f"    SUM output source lines:    {self.FILE_ALL_SOURCE_KEYWORDS_RESULT_OF_GLOB}")                                  
        print(f"    Transformer Output:         {len_result} lines")
        print(f"        Added new bc of def_*:      {self.FILE_DEF_KEYWORDS_COUNT}")
        print(f"        Added new lines of source: -1 (= means one line was just overwritten)" if new_lines_skw < 0 \
              else f"        Added new lines of source:  {new_lines_skw}")
           
        self.FILE_SOURCE_NR = 0
        self.FILE_OSOURCE_NR = 0
        self.FILE_RSOURCE_NR = 0
        self.FILE_ORSOURCE_NR = 0
        self.FILE_SOURCE_KEYWORDS_ALL_NR = 0
        self.FILE_DEF_KEYWORDS_COUNT = 0
        self.FILE_ALL_ADDED_LINES_SKW = 0
        self.FILE_ALL_SOURCE_KEYWORDS_RESULT_OF_GLOB = 0

    def _log_parser_context(self, given_context):
        
        print(f"\n For each symbol found in parser_result['unique_defined_syms']")
        print(f"    -> call sym.name/.origin/.name_and_loc")
        print(f"    -> call for each sym.nodes (.filename/.linenr/node/.defaults/is_configdefault")
        print(f"    -> call all sym.defaults")
        print(f"    -> call all sym.orig_defaults")
        print(f"\n------------ symbol_infos --------------------------------------------------")
        print(given_context.symbol_infos)
        print(f"\n------------ symbol_definitions --------------------------------------------------")
        print(given_context.symbol_definitions)
        print(f"\n------------ symbol_defaults -----------------------------------------------")
        print(given_context.symbol_defaults)
        print(f"\n------------ sym.orig_defaults ---------------------------------------------")
        print(f"these omit any dependencies propagated from 'depends on' and surrounding 'if's & strip location of default line")
        #TODO: delete not needed
        print(given_context.symbol_orig_defaults)

        print(f"\n")
        print(f"    -> ExParserContext - symbols: {given_context.symbol_nr} ({', '.join(given_context.symbol_definitions.keys())})")
        print(f"    -> ExParserContext - configdefaults: {given_context.configdefault_symbols_nr} ({', '.join(given_context.configdefault_symbols)})")
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
