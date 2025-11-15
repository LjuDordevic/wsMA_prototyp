from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

@dataclass
class ExtParserContext:
    symbol_infos: Dict[str, List[dict]]
    symbol_definitions: Dict[str, List[dict]]  # symbol_name -> [location1, location2, ...]
    symbol_defaults: Dict[str, List[dict]]
    symbol_orig_defaults: Dict[str, List[dict]]
    configdefault_symbols: Set[str]
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
   
    def build_context_from_parser(self, parser_result: dict) -> ExtParserContext: 
        konf = parser_result['kconf']
        symbol_infos = {}
        symbol_definitions = {}
        symbol_defaults = {}
        symbol_orig_defaults = {}
        configdefault_symbols = set()
        
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

        print(f"\n For each symbol found in parser_result['unique_defined_syms']")
        print(f"    -> filter sym.name/.origin/.name_and_loc")
        print(f"    -> filter all sym.defaults")
        print(f"    -> filter all sym.orig_defaults")
        print(f"\n------------ symbol_infos --------------------------------------------------")
        print(symbol_infos)
        print(f"\n------------ symbol_defaults -----------------------------------------------")
        print(symbol_defaults)
        print(f"\n------------ sym.orig_defaults ---------------------------------------------")
        print(f"these omit any dependencies propagated from 'depends on' and surrounding 'if's & strip location of default line")
        #TODO: delete not needed
        print(symbol_orig_defaults)
         
        context = ExtParserContext(
            symbol_infos = symbol_infos,
            symbol_definitions = symbol_definitions,
            configdefault_symbols = configdefault_symbols,
            symbol_defaults = symbol_defaults,
            symbol_orig_defaults = symbol_orig_defaults,
            parser_result=parser_result,
            srctree=Path(konf.srctree)
        )
        
        self.context = context
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

        default_dependencies_list = []

        for entry in symbol_defaults[symbol_name]:
            default_tuple = entry['sym.default']
            default_location = default_tuple[2]
                
            default_dependencies = default_tuple[1]
            dependencies = self._extract_dependencies(default_dependencies)
                
            default_dependencies_list.append((symbol_name, default_location, dependencies))
            
        return {
            'sym_def' : symbol_definitions_list,
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

    def _transform_lines(self, lines: List, current_file: Path) -> List:
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
            
            while i < len(lines):   # as long as we got lines from the reader
                line = lines[i]     # take one line at index i
                
                if line.line_type in ['config', 'menuconfig']:
                    current_symbol = line.content.get('symbol') # save sym name 
                
                transformed = self._transform_single_line(line, current_symbol, current_file)

                # line without transformation needed, go to the next line from the reader list    
                if transformed is None:
                    i += 1
                    continue
                # is output list? -> extend, else: add one line
                if isinstance(transformed, list):
                    result.extend(transformed) # 1:n (def_bool → bool + default)
                else:
                    result.append(transformed) # 1:1         
                i += 1  # go to the next 
            
            # count how many lines were added to output file
            # = SUM of all lines matched through glob - SUM of all (r/or/o)source_keywords 
            self.FILE_ALL_ADDED_LINES_SKW = self.FILE_ALL_SOURCE_KEYWORDS_RESULT_OF_GLOB - self.FILE_SOURCE_KEYWORDS_ALL_NR   
            # call log
            transformed_lines = len(result)
            self._file_log_and_reset(self.FILE_ALL_ADDED_LINES_SKW, transformed_lines)
            return result
        
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
        elif line.line_type == 'configdefault':
            return self._transform_configdefaults(line, current_symbol)
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

    def _file_log_and_reset(self, new_lines_skw : int, len_result : int):
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

            transformed = self._transform_lines(lines, input_file)
            try:
                writer.write(transformed, output_file)
                transformed_count += 1
            except Exception as e:
                print(f"     Error write: {e}")
        
        print(f"----------------------------------------------------------------------")
        print(f"finished transforming: {transformed_count} files transformed")
