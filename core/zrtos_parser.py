import os
from pathlib import Path

class ZRTOSParser:
    """
    help-class -> Parser for Zephyr RTOS specifications 
    init: save kconfiglib_module that the PickParser chose -> input for subclass 
    in the subclass: call the Kconfig from the kconfiglib_module + override functions 
    """
    def __init__(self, kconfiglib_module):
        self.kconfiglib = kconfiglib_module

    def parse_files(self, project_dir: str, kconfig_file: str):
        project_dir_path = Path(project_dir)
        assert(project_dir_path).exists(), f"{project_dir_path} not found"
        os.environ["srctree"] = str(project_dir_path)

        kconfig_file_path = project_dir_path / kconfig_file
        assert(kconfig_file_path).exists(), f"{kconfig_file} not found in {project_dir_path}"
        
        Kconfig = self.kconfiglib.Kconfig   # parent Kconfig class from kconfiglib_module

        class KconfigParser(Kconfig):
            def __init__(self, filename):
                self._parse_only = True     # flag used for override 
                super().__init__(filename)  # call init from parent Kconfig

            def _finalize_node(self, node, visible):
                """
                only when class has attribute _parse_only and it's = True -> set _parsing_complete = True
                else: call _finalize_node() like in parent Kconfig class
                """
                if hasattr(self, '_parse_only') and self._parse_only:
                    print("skip _finalize_node")
                    self._parsing_complete = True
                    return
                return super()._finalize_node(node, visible)
            
            def _finalize_sym(self, sym):
                if hasattr(self, '_parse_only') and self._parse_only:
                    print("skip _finalize_sym: takes care of configdefault")
                    return
                return super()._finalize_sym(sym)
            
            # some of these depend on everything being finalized 
            # TODO: check workaround 
            def _check_sym_sanity(self):
                if hasattr(self, '_parse_only') and self._parse_only:
                    print("skip _check_sym_synity")
                    return
                return super()._check_sym_sanity()
            
            def _check_choice_sanity(self):
                if hasattr(self, '_parse_only') and self._parse_only:
                    print("skip _check_choice_sanity")
                    return
                return super()._check_choice_sanity()
            
            def _check_undef_syms(self):
                if hasattr(self, '_parse_only') and self._parse_only:
                    print("skip _check_undef_syms")
                    return
                return super()._check_undef_syms()
            
            def _check_undef_syms(self):
                if hasattr(self, '_parse_only') and self._parse_only:
                    print("skip _check_undef_syms")
                    return
                return super()._check_undef_syms()

            def _build_dep(self):
                if hasattr(self, '_parse_only') and self._parse_only:
                    print("skip _build_dep")
                    return
                return super()._build_dep()
            
            def _add_choice_deps(self):
                if hasattr(self, '_parse_only') and self._parse_only:
                    print("skip _add_choice_deps")
                    return
                return super()._add_choice_deps()    

        kconf = KconfigParser(kconfig_file)

        return {
            'kconf': kconf,
            'top_node': kconf.top_node,
            'syms': kconf.syms,
            'const_sysm': kconf.const_syms,
            'defined_sysm': kconf.defined_syms,
            'missing_syms': kconf.missing_syms,
            'named_choices': kconf.named_choices,
            'choices': kconf.choices,
            'menus': kconf.menus,
            'comments': kconf.comments,
            'unique_defined_syms': kconf.unique_defined_syms,
            'unique_choices': kconf.unique_choices
        }
    
