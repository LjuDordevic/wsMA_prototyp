import os
from pathlib import Path

class ZephyrKconfiglibParser:
    """
    help-class -> Parser for Zephyr Kconfiglib specifications, "ZKCL" in pick_parser.py
    init: save kconfiglib_module that the PickParser chose -> input for subclass 
    in the subclass: call the parser from parent Kconfig class 
    we don't override finalize functions, because we want final result
    """
    def __init__(self, kconfiglib_module):
        self.kconfiglib = kconfiglib_module

    def parse_files(self, project_dir: str, kconfig_file: str):
        project_dir_path = Path(project_dir)
        assert(project_dir_path).exists(), f"{project_dir_path} not found"
        kconfig_file_path = project_dir_path / kconfig_file
        assert(kconfig_file_path).exists(), f"{kconfig_file} not found in {project_dir_path}"
        
        Kconfig = self.kconfiglib.Kconfig   # parent Kconfig class from Zephyr Kconfiglib

        class KconfigParser(Kconfig):
            def __init__(self, filename):
                super().__init__(filename)  # call init from parent Kconfig

        kconf = KconfigParser(kconfig_file)
        # dictionary key: value 
        return {
            'kconf': kconf,
            'top_node': kconf.top_node,
            'syms': kconf.syms,
            'const_syms': kconf.const_syms,
            'defined_syms': kconf.defined_syms,
            'missing_syms': kconf.missing_syms,
            'named_choices': kconf.named_choices,
            'choices': kconf.choices,
            'menus': kconf.menus,
            'comments': kconf.comments,
            'unique_defined_syms': kconf.unique_defined_syms,
            'unique_choices': kconf.unique_choices
        }
    
