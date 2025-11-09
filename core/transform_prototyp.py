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
   
    def build_context_from_parser(self, parser_result: dict, srctree: Path) -> TransformationContext: 
        symbol_definitions = {}
        configdefault_symbols = set()
        
        for sym in parser_result['defined_syms']:
            if sym.name not in symbol_definitions:
                symbol_definitions[sym.name] = []
            
            for node in sym.nodes:
                location_info = {
                    'file': node.filename if hasattr(node, 'filename') else None,
                    'line': node.linenr if hasattr(node, 'linenr') else None,
                    'node': node,
                    'is_configdefault': hasattr(node, 'is_configdefault') and node.is_configdefault
                }
                symbol_definitions[sym.name].append(location_info)
            
        context = TransformationContext(
            symbol_definitions=symbol_definitions,
            configdefault_symbols=configdefault_symbols,
            parser_result=parser_result,
            srctree=srctree
        )
        
        self.context = context
        return context

