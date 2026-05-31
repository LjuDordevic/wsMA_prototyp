from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Any


@dataclass
class ExtParserContext:
    symbol_infos: Dict[str, List[dict]]
    symbol_definitions: Dict[str, List[dict]]
    symbol_nr: int
    symbol_defaults: Dict[str, List[dict]]
    symbol_orig_defaults: Dict[str, List[dict]]
    configdefault_options: Set[str]
    configdefault_options_nr: int
    choice_infos: Dict[str, List[dict]]
    choice_definitions: Dict[str, List[dict]]
    choice_nr: int
    named_choices_nr: int
    choice_dep: Dict[str, List[dict]]
    parser_result: dict
    srctree: Path