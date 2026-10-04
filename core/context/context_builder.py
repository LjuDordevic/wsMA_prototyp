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

    def get_all_choice_configs(self, choice_name: str, reader, project_dir: Path, log_cd_nc_details: bool, choice_info=None):
        """
        Get all config entries for a named choice from all its definitions.
        
        Collects:
        - Choice-level default and depends lines
        - Choice-level prompt und help
        - Config entries (standalone or in if-blocks)
        - Menuconfig entries (standalone or in if-blocks) with their if-conditions
        """
        print(f"\n=== _get_all_choice_configs for {choice_name} ===")
        from core.kconfig_writer import KconfigLine
        
        if choice_name not in self.context.choice_definitions:
            print(f"  {choice_name} not in choice_definitions!")
            return []

        choice_definitions = self.context.choice_definitions[choice_name]
        print(f"  Found {len(choice_definitions)} definitions:")
        for idx, cd in enumerate(choice_definitions):
            print(f"    [{idx}] file={cd.get('file')}, line={cd.get('line')}")
        
        # Extrahiere node_deps aus choice_info
        all_node_deps = []
        all_default_deps = []
        if choice_info and 'choice_def' in choice_info:
            choice_def_list = choice_info['choice_def']
            if choice_def_list:
                # Unpack: (choice_name, default_deps_list, node_deps_list)
                _, all_default_deps, all_node_deps = choice_def_list[0]
                print(f"  Extracted node_deps: {all_node_deps}")
                print(f"  Extracted default_deps: {all_default_deps}")

        all_entries = []
        all_choice_prompt_lines = []
        all_choice_help_lines = []

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

            # Get node_deps for this specific definition
            node_deps = []
            if def_idx < len(all_node_deps):
                node_deps = all_node_deps[def_idx]
            
            print(f"    node_deps for definition [{def_idx}]: {node_deps}")

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
                    choice_prompt_lines = []
                    choice_help_lines = []
                    
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
                        
                        # because if we don't skip the first definition, than we'll have redundant attr
                        # because the attributs of the first definition are transformed in transform_named_choice
                        if def_idx != 0:
                            #print("collect from other def")
                            #print(f"nextttt {next_line.line_type}")
                            
                            if next_line.line_type == 'prompt':
                                choice_prompt_lines.append(next_line)
                                all_choice_prompt_lines.append(next_line)
                            
                            elif next_line.line_type == 'inline_prompt_choice':
                                inline_typ = next_line.content.get('inline_typ', '')
                                prompt_text = next_line.content.get('prompt_text', '')
                                indent_str = ' ' * next_line.indent

                                new_prompt_line = f'{indent_str}prompt "{prompt_text}"'
                                modified_line = KconfigLine(new_prompt_line, next_line.line_number)
                                #print(f"mod: {modified_line.raw_text}")
                                all_choice_prompt_lines.append(modified_line)
                                self.stats.file_changed_inprompt_bc_choice += 1
                                #print(all_choice_prompt_lines)
                                
                            elif next_line.line_type == 'help':
                                # store the 'help' keyword line
                                choice_help_lines.append(next_line)
                                all_choice_help_lines.append(next_line)

                                help_indent = next_line.indent
                                j += 1

                                # collect all following help text lines
                                while j < len(lines):
                                    help_line = lines[j]

                                    # help text must be more indented than 'help'
                                    if help_line.indent <= help_indent:
                                        break

                                    # safety: stop if structure starts unexpectedly
                                    if help_line.line_type in (
                                        'default', 'depends_on', 'prompt',
                                        'config', 'menuconfig', 'if', 'endchoice'
                                    ):
                                        break

                                    choice_help_lines.append(help_line)
                                    all_choice_help_lines.append(help_line)

                                    j += 1

                                continue  # important: j already advanced

                        j += 1
                    
                    print(f"  DEBUG: Found choice {choice_name} at {choice_file}:{choice_line}")
                    if log_cd_nc_details:
                        print(f"  DEBUG: choice_default_lines: {choice_default_lines}")
                        print(f"  DEBUG: choice_depends_lines: {choice_depends_lines}")
                        print(f"  DEBUG: choice_prompt_lines: {choice_prompt_lines}")
                        print(f"  DEBUG: choice_help_lines: {choice_help_lines}")

                    additional_deps = []

                    # 1. base_cond
                    for dep_line in choice_depends_lines:
                        raw = dep_line.raw_text.strip()
                        base_cond = raw[len('depends on'):].strip()
                        additional_deps.append(base_cond)
                                
                    # 2. Additional (nur für def_idx > 0)
                    if def_idx > 0 and node_deps:
                        base_conds = additional_deps.copy()
                        for base_cond in base_conds:
                            additional = [
                                d for d in node_deps
                                if d not in base_cond and d != 'y'
                            ]
                            additional_deps.extend(additional)
                                    
                        if not base_conds:
                            additional_deps.extend([d for d in node_deps if d != 'y'])
                                
                    additional_deps = list(dict.fromkeys(additional_deps))
                    
                    # Now collect all configs AND if-blocks in this choice block
                    if first_config_idx is not None:
                        k = first_config_idx
                        while k < len(lines):
                            current_line = lines[k]
                            
                            if current_line.line_type == 'endchoice':
                                break
                            
                            # Handle IF blocks --------------------------------------------------------------------------------------
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
                                        if if_depth == 0:
                                            if_block.append(next_line)
                                            m += 1
                                            break
                                           
                                    if next_line.line_type == 'comment':
                                        if_block.append(next_line)
                                        m += 1
                                        continue
                                    
                                    # Track config symbols inside the if
                                    if next_line.line_type == 'config':
                                        sym_name = next_line.content.get('symbol')
                                        if sym_name: if_configs.append(sym_name)
                                        # HERE HANDLE THE ADDITIONAL DEPENDENCIES FOR CONFIGS OF OTHER DEFINITIONS INSIDE IF!!!!
                                        
                                        if_block.append(next_line) #config line itself

                                        config_m = m + 1
                                        # add dependecies as you collect the block
                                        while config_m < len(lines):
                                            config_line = lines[config_m]
                                            
                                            if (config_line.line_type in ('config', 'menuconfig', 'if', 'endif', 'comment', 'endchoice')):
                                                break
                                            
                                            # MODIFY LINES 
                                            if config_line.line_type in ('prompt', 'inline_prompt_choice', 'depends_on') and def_idx > 0:
                                                if additional_deps:
                                                    prompt_text = config_line.content.get('prompt_text', '')
                                                    inline_typ = config_line.content.get('inline_typ', '')
                                                    indent_str = ' ' * config_line.indent
                                                    combined_cond = ' && '.join(additional_deps)
                                                    
                                                    if config_line.line_type == 'depends_on':
                                                        raw = config_line.raw_text.strip()
                                                        base_cond = raw[len('depends on'):].strip()
                                                        new_prompt_line = f'{indent_str}depends on {base_cond} && {combined_cond}'
                                                    elif config_line.line_type == 'inline_prompt_choice': 
                                                        new_prompt_line = f'{indent_str}bool "{prompt_text}" if {combined_cond}'
                                                        if inline_typ == 'tristate': 
                                                            self.stats.file_changed_typ_tristate_to_bool += 1
                                                            #print(f"meeinn {new_prompt_line}")

                                                    elif config_line.line_type == 'prompt': 
                                                        new_prompt_line = f'{indent_str}prompt "{prompt_text}" if {combined_cond}'

                                                    modified_line = KconfigLine(new_prompt_line, next_line.line_number)
                                                    if_block.append(modified_line)
                                                else:
                                                    if_block.append(next_line)
                                            else:
                                                if_block.append(next_line)

                                            config_m += 1
                                                                                
                                        m = config_m
                                        continue

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
                                                #print(f"mc before: {mc_line.raw_text}")
                                                mc_line = self._transform_typ_choice_help(mc_line)
                                                #print(f"mc after: {mc_line.raw_text}")

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
                                
                                if log_cd_nc_details:
                                    print(f"  DEBUG: Adding if-block with configs {if_configs} and menuconfigs {[mc['symbol'] for mc in if_menuconfigs]}")
                                
                                k = m
                            
                            # Handle standalone configs (not inside if)
                            elif current_line.line_type in ('config'):
                                sym_name = current_line.content.get('symbol')
                                config_block = [current_line]

                                # Collect the config block
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
                                    
                                    #print(f"eehehjwe {next_line.line_type} + {next_line.raw_text}")
                                    if next_line.line_type == 'prompt' or next_line.line_type == 'inline_prompt_choice' and def_idx > 0:
                                        
                                        """ 
                                        # Von depends_on Zeilen
                                        for dep_line in choice_depends_lines:
                                            raw = dep_line.raw_text.strip()
                                            base_cond = raw[len('depends on'):].strip()
                                            additional_deps.append(base_cond)
                                            base_conds = additional_deps.copy()
                                            for base_cond in base_conds:
                                                additional = [
                                                    d for d in node_deps
                                                    if d not in base_cond and d != 'y'
                                                ]
                                                additional_deps.extend(additional)
                                        """                                        
                                        
                                        prompt_text = next_line.content.get('prompt_text', '')
                                        inline_typ = next_line.content.get('inline_typ', '')
                                        # ELEMENTS OF CHOICE CANT HAVE DEFAULT
                                        #default_value = next_line.content.get('value', '')
                                        #default_cond = next_line.content.get('condition', '')
                                        indent_str = ' ' * next_line.indent
                                        if additional_deps:
                                            combined_cond = ' && '.join(additional_deps)
                                            if next_line.line_type == 'inline_prompt_choice': 
                                                new_prompt_line = f'{indent_str}bool "{prompt_text}" if {combined_cond}'

                                                if inline_typ == 'tristate': 
                                                    self.stats.file_changed_typ_tristate_to_bool += 1 # bc we are looking at prompts at config level 
                                                    #print(f"meeinn {new_prompt_line}")
                                                
                                            if next_line.line_type == 'prompt': new_prompt_line = f'{indent_str}prompt "{prompt_text}" if {combined_cond}'
                                            #if next_line.line_type == 'default' and default_cond: new_prompt_line = f'{indent_str}default {default_value} if {default_cond} && {combined_cond}'
                                            #if next_line.line_type == 'default' and not default_cond: new_prompt_line = f'{indent_str}default {default_value} if {combined_cond}'

                                            modified_line = KconfigLine(new_prompt_line, next_line.line_number)
                                            config_block.append(modified_line)
                                        else:
                                            if next_line.line_type == 'prompt': 
                                                new_prompt_line = f'{indent_str}prompt "{prompt_text}"'
                                            if next_line.line_type == 'inline_prompt_choice': 
                                                new_prompt_line = f'{indent_str}bool "{prompt_text}"'    # config tristate -> bool "xxxx" BUT also bool -> bool 
                                                if inline_typ == 'tristate': 
                                                    self.stats.file_changed_typ_tristate_to_bool += 1
                                                    #print(f"meeinn {new_prompt_line}")

                                            modified_line = KconfigLine(new_prompt_line, next_line.line_number)
                                            config_block.append(modified_line)
                                    else:
                                        config_block.append(next_line)
                                    
                                    m += 1
                                
                                if log_cd_nc_details: print(f"  DEBUG: Adding config {sym_name}")
                                
                                all_entries.append({
                                    'type': 'config',
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
                            
                            elif current_line.line_type in ('menuconfig'):
                                sym_name = current_line.content.get('symbol')
                                is_menuconfig = (current_line.line_type == 'menuconfig')
                                config_block = [current_line]


                                # Collect the menuconfig block
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
                                    
                                    next_line = self._transform_typ_choice_help(next_line)
                                    config_block.append(next_line)
                                    m += 1
                                
                                if log_cd_nc_details: print(f"  DEBUG: Adding {'menuconfig' if is_menuconfig else 'config'} {sym_name}")
                                
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
        print(f"  DEBUG: Total prompts collected: {len(all_choice_prompt_lines)}")
        print(f"  DEBUG: Total helps collected: {len(all_choice_help_lines)} + {all_choice_help_lines}")

        return {
            'entries': all_entries,
            'choice_prompt_lines': all_choice_prompt_lines,
            'choice_help_lines': all_choice_help_lines
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