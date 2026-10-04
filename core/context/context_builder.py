from pathlib import Path
from typing import List
from core.context.context import ExtParserContext
from core.utils.logger import Logger

class ContextBuilder:

    def build(self, parser_result: dict, log: bool) -> ExtParserContext:

        konf = parser_result["kconf"]
        symbol_infos = {}
        symbol_definitions = {}
        symbol_defaults = {}
        symbol_orig_defaults = {}
        configdefault_options = set()
        choice_infos = {}
        choice_definitions = {}
        choice_dep = {}
        unique_syms_nr = len(parser_result["unique_defined_syms"])
        unique_choice_nr = len(parser_result["unique_choices"])
        unique_named_choices_nr = len(parser_result["named_choices"])

        for sym in parser_result["unique_defined_syms"]:
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
            if sym.name not in symbol_infos:
                symbol_infos[sym.name] = []
                symbol_definitions[sym.name] = []
                symbol_defaults[sym.name] = []
                symbol_orig_defaults[sym.name] = []

            symbol_infos[sym.name].append(
                {
                    "sym.name": sym.name,
                    "sym.name_and_loc": sym.name_and_loc
                    #'sym.origin' : sym.origin,
                }
            )

            for sd in sym.defaults:
                symbol_defaults[sym.name].append(
                    {
                        "sym.default": sd
                    }
                )

            for sod in sym.orig_defaults:
                symbol_orig_defaults[sym.name].append(
                    {
                        "orig_defaults": sod
                    }
                )

            for node in sym.nodes:

                is_configdefault = getattr(
                    node,
                    "is_configdefault",
                    False
                )

                symbol_definitions[sym.name].append(
                    {
                        "file": getattr(node, "filename", None),
                        "line": getattr(node, "linenr", None),
                        "node": node,
                        "node.defaults": node.defaults,
                        "is_configdefault": is_configdefault
                    }
                )

                if is_configdefault:
                    configdefault_options.add(sym.name)

        for choice in parser_result["unique_choices"]:

            if choice.name not in choice_infos:

                choice_infos[choice.name] = []
                choice_definitions[choice.name] = []
                choice_dep[choice.name] = []

            choice_infos[choice.name].append(
                {
                    "choice.name": choice.name,
                    "choice.syms": choice.syms,
                    #'choice.type' : choice.type,
                    #'choice.name_and_loc' : choice.name_and_loc,
                    #'choice.direct_dep': choice.direct_dep,
                    #'choice.orig_defaults': choice.orig_defaults
                }
            )

            for node in choice.nodes:

                choice_definitions[choice.name].append(
                    {
                        "file": getattr(node, "filename", None),
                        "line": getattr(node, "linenr", None),
                        "node.prompt": node.prompt,
                        "node.defaults": node.defaults,
                        "node.dep": node.dep
                        #'node.item.dd': node.item.direct_dep,
                        #'node.item.name': node.item.name
                    }
                )

                choice_dep[choice.name].append(
                    {
                        "node.defaults": node.defaults,
                        "node.dep": node.dep,
                    }
                )

        context = ExtParserContext(
            symbol_infos = symbol_infos,
            symbol_definitions = symbol_definitions,
            symbol_nr = unique_syms_nr, #len(symbol_definitions),
            configdefault_options = configdefault_options,
            configdefault_options_nr = len(configdefault_options),
            symbol_defaults = symbol_defaults,
            symbol_orig_defaults = symbol_orig_defaults,
            choice_infos = choice_infos,
            choice_definitions = choice_definitions,
            choice_nr = unique_choice_nr, #len(choice_definitions),
            named_choices_nr = unique_named_choices_nr,
            choice_dep = choice_dep,
            parser_result=parser_result,
            srctree=Path(konf.srctree), 
        )

        if log: 
            logger = Logger()
            logger.log_parser_context(self.context)
        return context

    def get_all_source_files(self, context: ExtParserContext) -> List[Path]:
        """
        get all paths that parser found. These are relative to srctree 
        """
        if context is None:
            raise RuntimeError(" build context from parser first")
                
        kconf = context.parser_result['kconf']
        files = []
            
        for filename in kconf.kconfig_filenames:
            file_path = Path(filename)
            files.append(file_path)
        print("    get_all_source_files: ")
        for file in files:
            print(f"    parser found: {file}")
    
        return files   

    def extract_named_choice_info(self, context: ExtParserContext, choice_name: str, log: bool, log_cd_nc_details: bool):
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
                    if_cond_ext = self.helper.extract_dependencies(d_cond)
                    d_value_ext = self.helper.extract_value(d_value)
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
            dependencies = self.helper.extract_dependencies(default_dependencies)
                
            default_dependencies_list.append((symbol_name, default_location, dependencies))
            
        return {
            'sym_def' : symbol_definitions_list,
            #'last_config': last_config_for_sym,
            #'configdefaults': configdefault_entries,
            'def_dep' : default_dependencies_list
        }