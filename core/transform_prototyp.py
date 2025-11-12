from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

@dataclass
class ExParserContext:
    symbol_definitions: Dict[str, List[dict]]  # symbol_name -> [location1, location2, ...]
    configdefault_symbols: Set[str]
    parser_result: dict
    srctree: Path

class KconfigTransformer:
    """
    build context based on parser_result
    transform lines
    """
    DEF_KEYWORDS = ('def_bool', 'def_string', 'def_int', 'def_hex')

    def __init__(self, source_spec: str):
        self.source_spec = source_spec.upper()  # maybe for some later checks 
        self.context: Optional[ExParserContext] = None
   
    def build_context_from_parser(self, parser_result: dict) -> ExParserContext: 
        konf = parser_result['kconf']
        symbol_definitions = {}
        configdefault_symbols = set()
        
        for sym in parser_result['unique_defined_syms']:
            if sym.name not in symbol_definitions:
                #print(sym.name)
                symbol_definitions[sym.name] = []
            
            for node in sym.nodes:
                is_configdefault = getattr(node, 'is_configdefault', False)
                #print(node.is_configdefault)
                
                location_info = {
                    'file': node.filename if hasattr(node, 'filename') else None,
                    'line': node.linenr if hasattr(node, 'linenr') else None,
                    'node': node,
                    'is_configdefault': is_configdefault
                }
                symbol_definitions[sym.name].append(location_info)
            
                if is_configdefault:
                    configdefault_symbols.add(sym.name)
                    
        context = ExParserContext(
            symbol_definitions=symbol_definitions,
            configdefault_symbols=configdefault_symbols,
            parser_result=parser_result,
            srctree=Path(konf.srctree)
        )
        
        self.context = context
        return context

    def transform_lines(self, lines: List, current_file: Path) -> List:
            """
            lines -> from reader 
            """
            print(f"    start transforming lines")
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
            
            print(f"    Transformer Output: {len(result)} lines")
            return result
        
    def _transform_single_line(self, line, current_symbol: Optional[str], current_file: Path):
        """ 
        Returns:
            - KconfigLine: 1:1
            - List[KconfigLine]: 1:n
        """
        if line.line_type in self.DEF_KEYWORDS:
            return self._transform_def_keyword(line)
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
   
    def get_all_source_files(self) -> List[Path]:
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

    def transform_all_files(self, reader, writer, project_dir: Path, output_dir: Path):
        if self.context is None:
            raise RuntimeError("Context missing!")
        
        # all paths are relative to srctree 
        source_files = self.get_all_source_files()
        transformed_count = 0
        
        for file_path in source_files:
            input_file = project_dir / file_path
            output_file = output_dir / file_path
            
            if not input_file.exists():
                print(f"  Skip not found: {input_file}")
                continue
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            lines = reader.read_file(input_file)
            transformed = self.transform_lines(lines, input_file)
            
            try:
                writer.write(transformed, output_file)
                transformed_count += 1
            except Exception as e:
                print(f"     Error write: {e}")
        
        print(f" {transformed_count} files transformed")