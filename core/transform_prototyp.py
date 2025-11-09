from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

@dataclass
class TransformationContext:
    symbol_definitions: Dict[str, List[dict]]  # symbol_name -> [location1, location2, ...]
    configdefault_symbols: Set[str]
    parser_result: dict
    srctree: Path

class KconfigTransformer:
    """
    build context based on parser_result
    transform lines
    """
    def __init__(self, source_spec: str):
        self.source_spec = source_spec.upper()  # maybe for some later checks 
        self.context: Optional[TransformationContext] = None
   
    def build_context_from_parser(self, parser_result: dict) -> TransformationContext: 
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
                    
        context = TransformationContext(
            symbol_definitions=symbol_definitions,
            configdefault_symbols=configdefault_symbols,
            parser_result=parser_result,
            srctree=konf.srctree
        )
        
        self.context = context
        return context

    def transform_lines(self, lines: List, current_file: Path) -> List:
            """
            lines -> from reader 
            """
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
            
            return result
        
    def _transform_single_line(self, line, current_symbol: Optional[str], current_file: Path):
        """ 
        Returns:
            - KconfigLine: 1:1
            - List[KconfigLine]: 1:n
        """
        # def_bool --> bool + default
        if line.line_type == 'def_bool':
            return self._transform_def_bool(line)
        else:
            return line    

    def _transform_def_bool(self, line) -> List:
        
        from kconfig_writer import KconfigLine  # avoid circular import
            
        indent_str = ' ' * line.indent
        value = line.content.get('value', 'y')
        condition = line.content.get('condition')
            
        bool_line = KconfigLine(
            f"{indent_str}bool",
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
            
        return [bool_line, default_line]
