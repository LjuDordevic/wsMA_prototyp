from pathlib import Path
from posixpath import join, dirname
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass
from core.utils.transform_helper import TransformHelperUtils
from core.utils.transformation_stats import TransformationStats
from core.utils.excel_writer import write_to_excel
from core.context.context import ExtParserContext
from core.context.context_builder import ContextBuilder
from glob import iglob
from core.utils.logger import Logger

class KconfigTransformer:
    DEF_KEYWORDS = ('def_string', 'def_int', 'def_hex')
    SOURCE_KEYWORDS = ('source', 'osource', 'rsource', 'orsource')

    def __init__(self, source_spec: str, parser_result: dict):
        self.logger = Logger()
        self.helper = TransformHelperUtils()
        self.stats = TransformationStats()
        self.processed_choices = set()
        self.source_spec = source_spec.upper()  
        print("\n2. Build ExtParserContext from PARSER RESULTS")
        print(f" Parser used: {self.source_spec}")   
        self.context_builder = ContextBuilder()
        self.context = self.context_builder.build(parser_result, log=False)
    
    def _transform_choice(self, lines: List, current_index: int, result: List, transform_func) -> int:
        from core.kconfig_writer import KconfigLine
        import re

        choice_line = lines[current_index]        
        result.append(choice_line)

        #find endblock 
        end_line = None
        block_end_index = current_index + 1
        while block_end_index < len(lines):
            next_line = lines[block_end_index]   
            if next_line.line_type == 'endchoice':
                # copy this line, so that we can add it at the end of result 
                indent_str = ' ' * (next_line.indent)   
                new_line_text = f'{indent_str}endchoice'
                end_line = KconfigLine(new_line_text, next_line.line_number, line_type='endchoice')
                block_end_index += 1
                break
            block_end_index += 1
        
        # FIND line where first config/if starts
        first_ch_config_idx = None
        for idx in range(current_index + 1, block_end_index):
            if lines[idx].line_type in ['config', 'if']:
                first_ch_config_idx = idx
                break
        
        # CHOICE ATTR
        choice_attr_end = first_ch_config_idx if first_ch_config_idx is not None else block_end_index - 1
        print(f"    current_indx: {current_index + 1} - choice_attr_end: {choice_attr_end}")
        
        idx = current_index + 1
        while idx < choice_attr_end:
            line_item = lines[idx]
            #print(f"dahjskaj {line_item.line_type}")

            # SKIP: type attr (bool/tristate) & optional attr
            if line_item.line_type == 'optional':
                self.stats.file_skip_optional_choice_attr += 1 
                idx += 1
                continue
            if line_item.line_type == 'type_tristate':
                self.stats.file_skip_choice_typ_def_tristate += 1
                idx += 1
                continue
            if line_item.line_type == 'type_bool':
                self.stats.file_skip_choice_typ_def_bool += 1
                idx += 1
                continue
            if line_item.line_type == 'inline_prompt_choice':
                #inline_typ = line_item.content.get('inline_typ', '')
                indent_str = ' ' * line_item.indent
                prompt_text = line_item.content.get('prompt_text', '')
                new_prompt_line = f'{indent_str}prompt "{prompt_text}"'
                modified_line = KconfigLine(new_prompt_line, line_item.line_number)
                result.append(modified_line)
                self.stats.file_changed_inprompt_bc_choice += 1
                idx += 1
                continue

            # everything else: copy/transform as usual (because it's a first definition)
            transformed = transform_func(line_item, None, None)
            if transformed is None:
                idx += 1
                continue

            if isinstance(transformed, list):
                result.extend(transformed)
            else:
                result.append(transformed)  
            
            idx += 1

        # CHOICE ELEMENTS
        while idx < block_end_index - 1 and lines[current_index].line_type != 'endchoice':
            
            line_item = lines[idx]

            # IF CONFIG INSIDE CHOICE is type tristate 
            if line_item.line_type in ('type_tristate', 'inline_prompt_choice'):
                line_item = self._transform_typ_choice_help(line_item)

            # everything else: copy/transform as usual (because it's a first definition)
            transformed = transform_func(line_item, None, None)
            if transformed is None:
                idx += 1
                continue

            if isinstance(transformed, list):
                result.extend(transformed)
            else:
                result.append(transformed)  
            
            idx += 1

        result.append(end_line)

        #print(f"PROCESS choice: {result}")
        return block_end_index

    def _transform_named_choice(self, log_debug: bool, lines: List, current_index: int, choice_info: dict, result: List, transform_func) -> int:
        from core.kconfig_writer import KconfigLine
        
        choice_line = lines[current_index]        
        # save first line without name
        indent_str = ' ' * choice_line.indent
        anonymous_choice = KconfigLine(f'{indent_str}choice', choice_line.line_number, line_type='choice')
        result.append(anonymous_choice)
        
        # EXTEND DEPENDENCIES for depends on & default line -----------------------------------------------------------------
        # WRONG: from parser 
        # Find endchoice index
        end_line = None
        block_end_index = current_index + 1
        while block_end_index < len(lines):
            next_line = lines[block_end_index]   
            if next_line.line_type == 'endchoice':
                # copy this line, so that we can add it at the end of result 
                indent_str = ' ' * (next_line.indent)   
                new_line_text = f'{indent_str}endchoice'
                end_line = KconfigLine(new_line_text, next_line.line_number, line_type='endchoice')
                block_end_index += 1
                break
            block_end_index += 1
        
        # PROCESS: ATTR OF THE FIRST DEFINITION ----------------------------------------------------------------------------------------------
        # Kconfiglib can have menuconfig as choice elements (see wsMA_prototyp/test_dir_/transform_choice_analysis/transform_choice_analysis.log)
        print(f"    process lines until first choice config/if was found") 
        print(f"    current_indx: {current_index + 1} - block endidx {block_end_index}")
        
        # FIND line where first config/if starts ! Kconfiglib allows menuconfig as elements of choice Option
        first_ch_config_idx = None
        for idx in range(current_index + 1, block_end_index):
            if lines[idx].line_type in ['config', 'if', 'menuconfig']:
                first_ch_config_idx = idx
                break
        
        # PROCESS attr of choice ---------------------------------------------------------------------------------------------------- 
        choice_attr_end = first_ch_config_idx if first_ch_config_idx is not None else block_end_index
        print(f"    current_indx: {current_index + 1} - choice_attr_end: {choice_attr_end}")
        # save depends on of first definition -> add them to menuconfigs of the first definition 
        first_depends_on_for_mc = []
        
        for idx in range(current_index + 1, choice_attr_end):
            line_item = lines[idx]

            # SKIP: type attr (bool/tristate) & optional attr
            if line_item.line_type == 'optional':
                self.stats.file_skip_optional_choice_attr += 1 
                continue
            if line_item.line_type == 'type_tristate':
                self.stats.file_skip_choice_typ_def_tristate += 1
                continue
            if line_item.line_type == 'type_bool':
                self.stats.file_skip_choice_typ_def_bool += 1
                continue
            if line_item.line_type == 'inline_prompt_choice': 
                #inline_typ = line_item.content.get('inline_typ') Linux doesn't allow bool "..."
                indent_str = ' ' * (choice_line.indent + 2)
                line_text = line_item.content.get('prompt_text')
                new_prompt_line_text = f'{indent_str}prompt "{line_text}"'
                new_prompt_line=KconfigLine(new_prompt_line_text, line_item.line_number)
                result.append(new_prompt_line)
                self.stats.file_changed_inprompt_bc_choice += 1
                continue            
            if line_item.line_type == 'depends_on':
                first_depends_on_for_mc.append(line_item)
            
            # everything else: prompt, default, depends on, help -> copy/transform as usual (because it's a first definition)
            transformed = transform_func(line_item, None, None)
            if transformed is None:
                continue

            if isinstance(transformed, list):
                result.extend(transformed)
            else:
                result.append(transformed)  
        
        # PROCESS: ADD ATTR OF OTHER DEFINITIONS ----------------------------------------------------------------------------------------------
        """ 
        # TODO: function die umgehende if und depends on von menus verbindet, ggb. die lines aus dem File wo sich die 2. definition befindet, result add (self.get_dep_from_other_def)
        # ADD depends on and default lines with extended if-condition  
        # TODO: CHANGE: dont take from parser -> instead read lines and get there the extenden
        # also +2 it's just quick fix
        # TODO: add teh extenden default/ depends from other definitions 
        # WRONG: from parser overall, user default_dependencies_extracted_list, node_dep_extracted_list) -> 'choice_def': choice_all_dep_list
        """
        choice_def = choice_info.get('choice_def')
        choice_configs = choice_info.get('choice_configs', [])
        choice_prompts = choice_info.get('prompt_lines', [])
        help_lines = choice_info.get('help_lines', [])

        if log_debug:
            print(f"    DEBUGG: choice_def {choice_def}")
            print(f"    choice_configs length: {len(choice_configs)}")
            print(f"    choice_configs {choice_configs}")
            print(f"    choice_prompts {choice_prompts}")
            print(f"    help_lines {help_lines}")

            for idx, cfg in enumerate(choice_configs):
                print(f"    [{idx}] type={cfg.get('type')}, symbol={cfg.get('symbol')}, symbols={cfg.get('symbols')}, choice_line={cfg.get('choice_line')}")
        
        menuconfigs_to_add_after = []  # Collect menuconfigs to add after endchoice
        len_menuconfig_block_first_def = 0

        # dont add choice_prompts and help_lines here bc doppel, add them later   
        if not choice_def:
            print(f"    No choice_def found")
        else:
            # Unpack the single entry
            _, all_default_deps, all_node_deps = choice_def[0]
            
            if log_debug:
                print(f"    all_default_deps: {all_default_deps}")
                print(f"    all_node_deps: {all_node_deps}")
            
            # Group configs by choice_line to identify which definition they belong to
            configs_by_definition = {}
            for cfg in choice_configs:
                cfg_choice_line = cfg.get('choice_line')
                if cfg_choice_line not in configs_by_definition:
                    configs_by_definition[cfg_choice_line] = []
                configs_by_definition[cfg_choice_line].append(cfg)
            
            # Sort by choice_line to get definitions in order
            sorted_def_lines = sorted(configs_by_definition.keys())
            print(f"    Found {len(sorted_def_lines)} choice definitions at lines: {sorted_def_lines}")
            
            def_index_by_line = {
                line: idx for idx, line in enumerate(sorted_def_lines)
            }

            depends_by_choice_line = {}  # Map: choice_line -> depends_from_def Liste
            
            # Process each definition (skip the first one, index 0)
            # so that we get all depends on/defaults and elements
            for def_idx in range(1, len(sorted_def_lines)):
                depends_from_def = []
                choice_line_num = sorted_def_lines[def_idx]
                configs_in_this_def = configs_by_definition[choice_line_num]
                
                # Get dependencies for this definition
                default_deps = all_default_deps[def_idx] if def_idx < len(all_default_deps) else []
                node_deps = all_node_deps[def_idx] if def_idx < len(all_node_deps) else []
                
                print(f"\n  Processing definition {def_idx} at line {choice_line_num}")
                if log_debug:
                    print(f"    default_deps: {default_deps}")
                    print(f"    node_deps: {node_deps}")
                    #print(f"  configs: {[c['symbol'] for c in configs_in_this_def]}")
                    print(f"    entries in this def:")
                    for c in configs_in_this_def:
                        if c.get('type') == 'if_block':
                            print(f"        if_block with configs: {c.get('configs')} and menuconfigs: {[mc['symbol'] for mc in c.get('menuconfigs', [])]}")
                        else:
                            print(f"        {c.get('type')}: {c.get('symbol')}")
                    
                # Take the first entry's lines as representative for this definition
                # (since all configs in same definition have same choice-level attributes)
                collect_additional = [] # needed additional dep for prompts of other definitions
                if configs_in_this_def:
                    representative_cfg = configs_in_this_def[0]
                    collect_additional_from_depends_on = []
                    collect_additional_from_default = []
                    
                    # -------- depends on ----------
                    for dep_line in representative_cfg.get('depends_lines', []):
                        raw = dep_line.raw_text.strip()
                        base_cond = raw[len('depends on'):].strip()

                        additional = [
                            d for d in node_deps
                            if d not in base_cond and d != 'y'
                        ]
                        print(f"    additional_from_depends_on: {additional} + {base_cond}")
                        """
                        Because if you don't take base_cond -> prompt cond is wrong 
                        additional_from_depends_on: ['OPT_ZZZ']
                        Added: depends on OPT_AAA && OPT_ZZZ
                        additional_from_default: ['OPT_AAA', 'OPT_ZZZ']
                        Added default: default CH_C if OPT_BBB && OPT_AAA && OPT_ZZZ
                        choice_prompts: [KconfigLine(prompt, line=22, indent=2), KconfigLine(prompt, line=48, indent=2)]
                        Added new_prompt: prompt "P1" if OPT_ZZZ
                        !! SHOULD BE prompt "P1" if OPT_AAA && OPT_ZZZ
                        """
                        collect_additional_from_depends_on.append(base_cond)    # append bc only one 
                        collect_additional_from_depends_on.extend(additional)
                        if additional:
                            new_line = (
                                f"{' ' * (choice_line.indent + 2)}"
                                f"depends on {base_cond} && {' && '.join(additional)}"
                            )
                        else:
                            new_line = (
                                f"{' ' * (choice_line.indent + 2)}"
                                f"depends on {base_cond}"
                            )
                        # WRONG: result.append(KconfigLine(new_line, dep_line.line_number))
                        # we propagate them to the (menu)configs of the definiton but dont' add the line to the output 
                        # because that would mean the depends on would be propagated to elments of all defintions
                        # and because we skip this -> counter + (WRONG WE COUNT AT THE END IN transform_lines)
                        depends_from_def.append(KconfigLine(new_line, dep_line.line_number))

                        if log_debug: print(f"      Found: {new_line.strip()}")
                    
                    print(f"        Found depends on: {len(depends_from_def)}")
                    
                    #self.stats.file_skipped_bc_named_choice += len(depends_from_def)
                    # depends on for the line 
                    depends_by_choice_line[choice_line_num] = depends_from_def
                    
                    added_def_counter = 0           # for each definition start from 0
                    # -------- default ----------
                    for def_line in representative_cfg.get('default_lines', []):    
                        raw = def_line.raw_text.strip()
                        rest = raw[len('default'):].strip()

                        if ' if ' in rest:
                            sym, existing_if = rest.split(' if ', 1)
                            existing_parts = [p.strip() for p in existing_if.split('&&')]
                        else:
                            sym = rest
                            existing_parts = []

                        additional = [
                            d for d in default_deps
                            if d not in existing_parts and d != 'y'
                        ]
                        print(f"    additional_from_default: {additional}")
                        collect_additional_from_default.extend(additional)

                        cond = existing_parts + additional

                        if cond:
                            new_line = (
                                f"{' ' * (choice_line.indent + 2)}"
                                f"default {sym} if {' && '.join(cond)}"
                            )
                        else:
                            new_line = (
                                f"{' ' * (choice_line.indent + 2)}"
                                f"default {sym}"
                            )

                        result.append(KconfigLine(new_line, def_line.line_number))
                        added_def_counter += 1
                        if log_debug: print(f"      Added default: {new_line.strip()}")

                    print(f"        Added default: {added_def_counter}")
                    self.stats.file_added_bc_named_choice += added_def_counter

                    # we would like to take conditions form depends on but if the choice doesn't have
                    # depends on, meaning no place to read all aditional cond from if/menu 
                    # that parser gives us, then we read the additional that default got 
                    if collect_additional_from_depends_on:
                        collect_additional = collect_additional_from_depends_on
                    else:
                        collect_additional = collect_additional_from_default

                if choice_prompts:
                    
                    #print(f"    choice_prompts other att: {choice_prompts}")
                    line = choice_prompts[def_idx-1]                    
                    line_text = line.content.get('prompt_text')
                    add = None
                    if collect_additional: 
                        #add = collect_additional[0]
                        add = ' && '.join(collect_additional)

                        #print(f"hhhhhshsh {add}")
                        indent_str = ' ' * (choice_line.indent + 2)
                        if line.line_type == 'inline_prompt_choice': 
                            inline_typ = line.content.get('inline_typ')
                            new_prompt_line_text = f'{indent_str}prompt "{line_text}" if {add}'
                        else: 
                            new_prompt_line_text = f'{indent_str}prompt "{line_text}" if {add}'
                        new_prompt_line=KconfigLine(new_prompt_line_text, line.line_number)
                        result.append(new_prompt_line)
                        self.stats.file_added_bc_named_choice += 1
                        print(f"    Added new_prompt: {new_prompt_line_text.strip()}")
                    else:
                        result.append(line)
                        print(f"    Added old_prompt: {line.raw_text}")
                        self.stats.file_added_bc_named_choice += 1
                        #print(f"heeee {line} + {} + {add}")
            
            """ 
            # move this up for each def, so that we can add conditions from if/menu
            if choice_prompts:
                for pl in choice_prompts:
                    result.append(pl)
                    self.stats.file_added_bc_named_choice += 1
                    print(f"Added prompt {pl}")
            """
            if help_lines:
                for hl in help_lines:
                    result.append(hl)    
                    self.stats.file_added_bc_named_choice += 1
                    print(f"    Added help {hl}")

        if log_debug:
            print(f"\n  Final result has {len(result)} lines before adding configs")
            print(f"    Added Lines bc named choice {self.stats.file_added_bc_named_choice}")

        # ADD all configs in choice block
        # 1. TRACK configs already present in this choice block
        existing_configs = set()
        menuconfigs_to_add_after = []  # Collect menuconfigs to add after endchoice
        added_items = 0
        added_lines = 0

        # SPECIAL CASE: If there's only ONE definition, process sequentially
        if len(sorted_def_lines) == 1:
            print(f"    Single definition detected - processing sequentially")
            
            idx = first_ch_config_idx
            while idx is not None and idx < block_end_index:
                line_item = lines[idx]
                
                # Stop at endchoice
                if line_item.line_type == 'endchoice':
                    break

                # Handle menuconfig - collect for after endchoice
                if line_item.line_type == 'menuconfig':
                    sym_name = line_item.content.get('symbol')
                    if sym_name:
                        existing_configs.add(sym_name)
                    
                    menuconfig_block = []
                    # Collect the entire menuconfig block
                    while idx < block_end_index:
                        current = lines[idx]
                        
                        # Stop if next config/menuconfig/if/endchoice starts
                        if (current.line_type in ('config', 'menuconfig', 'if', 'endchoice', 'comment') 
                            and current is not line_item):
                            break
                        
                        current = self._transform_typ_choice_help(current, already_counted=True)
                        
                        menuconfig_block.append(current)
                        idx += 1
                    
                    # Store for adding after endchoice
                    menuconfigs_to_add_after.append({
                        'symbol': sym_name,
                        'block': menuconfig_block,
                        'depends_from_def': first_depends_on_for_mc
                    })
                    
                    print(f"      Collected menuconfig {sym_name} ({len(menuconfig_block)} lines)")
                    len_menuconfig_block_first_def += len(menuconfig_block)
                    continue

                # Handle if blocks - add directly to result
                if line_item.line_type == 'if':
                    if_block_lines = []
                    if_start_idx = idx
                    if_depth = 1
                    
                    # Collect entire if block including nested ifs
                    if_block_lines.append(lines[idx])  # Add the 'if' line
                    idx += 1
                    
                    while idx < block_end_index and if_depth > 0:
                        current = lines[idx]
                        if_block_lines.append(current)
                        
                        if current.line_type == 'if':
                            if_depth += 1
                        elif current.line_type == 'endif':
                            if_depth -= 1
                        
                        idx += 1
                    
                    # Now process the collected if_block_lines
                    if_line_idx = 0
                    while if_line_idx < len(if_block_lines):
                        if_line = if_block_lines[if_line_idx]
                        
                        # Handle menuconfig inside if block
                        if if_line.line_type == 'menuconfig':
                            sym_name = if_line.content.get('symbol')
                            if sym_name:
                                existing_configs.add(sym_name)
                            
                            menuconfig_block = [if_line]
                            if_line_idx += 1
                            
                            # Collect menuconfig properties until next symbol or block boundary
                            while if_line_idx < len(if_block_lines):
                                next_line = if_block_lines[if_line_idx]
                                
                                # Stop if next config/menuconfig/if/endif/endchoice starts
                                if (next_line.indent <= if_line.indent and
                                    next_line.line_type in ('config', 'menuconfig', 'if', 'endif', 'endchoice', 'comment')):
                                    break

                                next_line = self._transform_typ_choice_help(next_line, already_counted=True)

                                menuconfig_block.append(next_line)
                                if_line_idx += 1
                            
                            # Store for adding after endchoice
                            menuconfigs_to_add_after.append({
                                'symbol': sym_name,
                                'block': menuconfig_block,
                                'depends_from_def': first_depends_on_for_mc  
                            })
                            
                            print(f"      Collected menuconfig {sym_name} inside if-block ({len(menuconfig_block)} lines)")
                            len_menuconfig_block_first_def += len(menuconfig_block)
                            
                            continue
                        
                        # For all other lines (if, endif, config, etc.), transform and add
                        transformed = transform_func(if_line, None, None)
                        if transformed is not None:
                            if isinstance(transformed, list):
                                result.extend(transformed)
                            else:
                                result.append(transformed)
                        
                        if_line_idx += 1
                    
                    print(f"      Added if-block ({len(if_block_lines)} lines)")
                    continue

                # Handle regular config - add directly to result
                if line_item.line_type == 'config':
                    sym_name = line_item.content.get('symbol')
                    if sym_name:
                        existing_configs.add(sym_name)

                    # Process the whole config block
                    while idx < block_end_index:
                        current = lines[idx]

                        # Stop if next config/menuconfig/if/endchoice starts
                        if (current.line_type in ('config', 'if', 'menuconfig', 'endchoice', 'comment') 
                            and current is not line_item):
                            break
                        
                        current = self._transform_typ_choice_help(current)

                        transformed = transform_func(current, None, None)
                        if transformed is not None:
                            if isinstance(transformed, list):
                                result.extend(transformed)
                            else:
                                result.append(transformed)
                        idx += 1
                    continue
                
                idx += 1
            
            print(f"    Single definition: processed all entries sequentially")
        
        else:
            # MULTIPLE DEFINTIONS 
            idx = first_ch_config_idx
            while idx is not None and idx < block_end_index:
                line_item = lines[idx]
                if log_debug: print(f"  Track existing configs: {line_item}")
                # Stop at endchoice
                if line_item.line_type == 'endchoice':
                    break

                # Start of a config block
                # skip menuconfig
                if line_item.line_type in ('config'):
                    sym_name = line_item.content.get('symbol')
                    if sym_name:
                        existing_configs.add(sym_name)  # list of existing 

                    # Process the whole config block
                    while idx < block_end_index:
                        current = lines[idx]
                        #print(f"current: {current}")

                        # Stop if next config or endchoice starts
                        if (current.line_type in ('config', 'if','menuconfig', 'endchoice', 'comment') and current is not line_item):
                            break
                        
                        #print(f"before:{current.raw_text}")
                        current = self._transform_typ_choice_help(current)
                        #print(f"after: {current.raw_text}")

                        transformed = transform_func(current, None, None)
                        if transformed is not None:
                            if isinstance(transformed, list):
                                result.extend(transformed)
                            else:
                                result.append(transformed)
                        idx += 1
                    continue
                
                # Handle menuconfig - collect for after endchoice
                if line_item.line_type == 'menuconfig':
                    sym_name = line_item.content.get('symbol')
                    if sym_name:
                        existing_configs.add(sym_name)
                    
                    menuconfig_block = []
                    # Collect the entire menuconfig block
                    while idx < block_end_index:
                        current = lines[idx]
                        
                        # Stop if next config/menuconfig/if/endchoice starts
                        if (current.line_type in ('config', 'menuconfig', 'if', 'endchoice', 'comment') 
                            and current is not line_item):
                            break
                        
                        current = self._transform_typ_choice_help(current)
                        menuconfig_block.append(current)
                        idx += 1
                    
                    # Store for adding after endchoice
                    menuconfigs_to_add_after.append({
                        'symbol': sym_name,
                        'block': menuconfig_block,
                        'depends_from_def': first_depends_on_for_mc  
                    })
                    
                    print(f"      Collected menuconfig {sym_name} ({len(menuconfig_block)} lines)")
                    len_menuconfig_block_first_def += len(menuconfig_block)
                    continue
                
                idx += 1

            #print(f"result after first definition: {len(result)} lines")
            
            # 2. ADD entries (configs/ifs/ but menuconfig shoild be skipped) from other definitions


            for entry in choice_configs:
                entry_type = entry.get('type', 'config')
                entry_choice_line = entry.get('choice_line')
                
                if entry_type == 'if_block':
                    # Add entire if-block (contains configs, maybe menuconfigs)
                    configs_in_if = entry.get('configs', [])
                    print(f"    configs_in_if {configs_in_if}")
                    menuconfigs_in_if = entry.get('menuconfigs', [])
                    print(f"    menuconfigs_in_if {menuconfigs_in_if}")

                    # Add the if-block to the choice
                    for line in entry.get('block', []):
                        result.append(line)
                        added_lines += 1
                    
                    # Collect menuconfigs to add after endchoice
                    for mc_info in menuconfigs_in_if:
                        mc_symbol = mc_info.get('symbol')

                        if mc_symbol in existing_configs:
                            continue

                        mc_info_copy = dict(mc_info)
                        mc_info_copy['depends_from_def'] = depends_by_choice_line.get(entry_choice_line, [])
                        menuconfigs_to_add_after.append(mc_info_copy)
                        existing_configs.add(mc_symbol)
                    
                    # Mark configs as existing - because it would be added as standalone 
                    for cfg in configs_in_if:
                        existing_configs.add(cfg)
                    added_items += 1
                    print(f"      Added if-block with configs {configs_in_if} from {entry.get('file')}")
                
                # mc outside if 
                elif entry_type == 'menuconfig':
                    # Menuconfig - collect to add after endchoice
                    config_symbol = entry.get('symbol')

                    if config_symbol in existing_configs:
                        continue

                    def_idx_for_entry = def_index_by_line.get(entry_choice_line, 0)
                    
                    menuconfigs_to_add_after.append({
                        'symbol': config_symbol,
                        'block': entry.get('block', []),
                        'if_condition': entry.get('if_condition'),
                        'depends_lines': entry.get('depends_lines', []),
                        'depends_from_def': depends_by_choice_line.get(entry_choice_line, []),
                        'node_deps': all_node_deps[def_idx_for_entry] if def_idx_for_entry < len(all_node_deps) else []
                    })
                    
                    existing_configs.add(config_symbol)
                    added_items += 1
                    print(f"      Collected menuconfig {config_symbol} from {entry.get('file')} (will add after endchoice)")
                
                elif entry_type == 'config':
                    config_symbol = entry.get('symbol')
                    
                    # Skip configs already present
                    if config_symbol in existing_configs:
                        continue
                    
                    for config_line in entry.get('block', []):
                        result.append(config_line)
                        added_lines += 1
                    
                    existing_configs.add(config_symbol)
                    added_items += 1
                    print(f"      Added config {config_symbol} from {entry.get('file')}")

            print(f"    Added {added_items} entries from other choice definitions")
            print(f"    Added {added_lines} lines from other choice definitions")

        # ADD endchoice
        result.append(end_line)
        
        # ADD menuconfigs after endchoice
        menuconfig_lines_added = 0
        print(f"\n  Adding {len(menuconfigs_to_add_after)} menuconfigs after endchoice")
        for mc_info in menuconfigs_to_add_after:
            mc_symbol = mc_info['symbol']
            mc_block = mc_info['block']
            if_cond = mc_info.get('if_condition')
            depends_lines = mc_info.get('depends_lines', [])
            node_deps = mc_info.get('node_deps', [])
            depends_from_def = mc_info.get('depends_from_def', [])
            
            print(f"    Adding menuconfig {mc_symbol}, depends_from_def={depends_from_def}")
            
            mc_lines_counter = 0
            # Add menuconfig line
            result.append(mc_block[0])  # First line is menuconfig declaration
            mc_lines_counter += 1
            
            # Modify prompt line to add if condition if needed
            for line in mc_block[1:]:
                result.append(line)
                mc_lines_counter += 1
            for dep_line in depends_from_def:
                raw = dep_line.raw_text.strip()
                new_line = f"{' ' * (line.indent)}{raw}"
                #print(f"        new line: {new_line}")
                #print(line.indent)
                result.append(KconfigLine(new_line, dep_line.line_number))
                mc_lines_counter += 1
            
            menuconfig_lines_added += mc_lines_counter
        
        print(f"    Added {menuconfig_lines_added} menuconfig lines (after endchoice) from other choice definitions")
        print(f"    But in the first definition there where {len_menuconfig_block_first_def} menuconfig lines")
        new_mc_lines = menuconfig_lines_added - len_menuconfig_block_first_def
        print(f"    Diff: {new_mc_lines}")
        self.stats.file_added_bc_named_choice += (new_mc_lines + added_lines)
        print(f"    Added Total Lines bc named choice {self.stats.file_added_bc_named_choice}")
        """ 
        for line in result:
            print(f"resultttt {line}")
        """
        return block_end_index

    def _transform_typ_choice_help(self, current, already_counted: Optional[bool]=None):
        
        if (current.line_type == 'inline_prompt_choice' and current.content.get('inline_typ') == 'tristate'):
            #print("Kjskasj")
            current_transformed = self._transform_bool_to_tristate_choice_typ(current, current.indent, current.content.get('prompt_text'), already_counted)
            return current_transformed
        
        if current.line_type == 'type_tristate':
            #print("Kjskasj2")
            current_transformed = self._transform_bool_to_tristate_choice_typ(current, already_counted)
            return current_transformed
        
        return current

    def _transform_bool_to_tristate_choice_typ(self, line_item, indent: Optional[int] = 0,prompt_text: Optional[str] = "", already_counted: Optional[bool]=None):
        from core.kconfig_writer import KconfigLine
        import re
        
        # actually it wouldn't be right for choice_conifg to not have prompt
        if indent:
            indent_str = ' ' * (indent)  
        else:
            indent_str = ' ' * (line_item.indent)   

        if prompt_text:
          new_line_text = f'{indent_str}bool "{prompt_text}"'
        else:
          #match = re.match(r'tristate\s+["\']([^"\']+)["\']', line_item.stripped)
          #match = re.match(r'\s*(bool|tristate)\s+"([^"]*)"', line_stripped)
          #re.match(r'^\s*(tristate)\s*$', s)
          #line_text = match.group(1)
          new_line_text = f'{indent_str}bool'
        
        if already_counted: 
            print(f" already counted the typ change {new_line_text}")
        else: 
            self.stats.file_changed_typ_tristate_to_bool += 1
            #print(f" meein {new_line_text}")

        return KconfigLine(new_line_text, line_item.line_number)

    def _transform_cd(self, lines: List, current_index: int, transformed_entries: List, result: List, transform_func) -> int:
       
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
        
        # call transform_single_line for lines in block itself 
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
        self.stats.file_configdefault_nr += len(transformed_entries)  
        return block_end_index

    def _transform_single_line(self, line, current_symbol: Optional[str], current_file: Path, resolve_log: None):
        """ 
        Returns:
            - KconfigLine: 1:1
            - List[KconfigLine]: 1:n
        """
        if line.line_type in self.DEF_KEYWORDS:
            self.stats.file_def_keywords_count += 1                                      # for each def_* -> count 1 one added line   
            return self._transform_def_keyword(line)
        elif line.line_type in self.SOURCE_KEYWORDS:
            self.stats.file_source_keywords_all_nr += 1                                  # for each self.SOURCE_KEYWORDS -> count 1, so that we have SUM of all 
            return self._transform_source_line(line, current_file, resolve_log)    # if resolve_log == True, than there is log for resolving and also iglob check is active 
        elif line.line_type == "option modules":
            self.stats.option_modules_counter += 1
            return self._transform_opt_modules(line, current_file)
        elif line.line_type == "option env":
            self.stats.file_opt_env += 1
            return self._transform_opt_env(line)
        elif line.line_type == "help_old":
            self.stats.old_help += 1
            return self._transform_stats.old_help(line)
        elif line.line_type == "typ_bool_old":
            self.stats.old_boolean += 1
            return self._transform_stats.old_boolean(line)
        else:
            if line.line_type == "allnoconfig_y":
                self.stats.file_opt_allnoconfig += 1
            if line.line_type == "defconfig_list":
                self.stats.file_opt_defconfig += 1
            if line.line_type == "warning":
                self.stats.file_warning_attr += 1
            if line.line_type == "set":
                self.stats.file_set_option += 1
            if line.line_type == "set_default":
                self.stats.file_set_default_option += 1
            return line    

    def _transform_old_help(self, line):
        from core.kconfig_writer import KconfigLine  
            
        indent_str = ' ' * line.indent

        new_text = f"{indent_str}help"
            
        new_line = KconfigLine(
            new_text,
            line.line_number  
        )
            
        return new_line
    
    def _transform_old_boolean(self, line):
       from core.kconfig_writer import KconfigLine  
            
       indent_str = ' ' * line.indent

       new_text = f"{indent_str}bool"
            
       new_line = KconfigLine(
           new_text,
           line.line_number  
       )
            
       return new_line
    
    def _transform_def_keyword(self, line) -> List:
        """
        For def_* keywords == def_bool, def_int, def_hex, def_string 
        config                            config 
            def_<typ> [if <exp>]   -->      <type> 
                                            default [if <exp>]
        """
        from core.kconfig_writer import KconfigLine  # avoid circular import
            
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

    def _transform_source_line(self, line, current_file, resolve_log) -> List:
        from core.kconfig_writer import KconfigLine
        import re, os

        # GET needed information
        match = re.match(r'(source|osource|rsource|orsource)\s+["\']([^"\']+)["\']', line.stripped) # Future work: I think there is no need to check for both types: ' and ". I think only " is allowed 
        if not match:
            print(f"error at source line: {line}")      
        indent_str = ' ' * line.indent
        source_keyword = match.group(1)
        pattern = match.group(2)
        has_glob = any(c in pattern for c in ['*', '?', '[', ']', '!'])

        # COUNT each keyword in file
        if source_keyword == "osource": self.stats.file_osource_nr += 1
        elif source_keyword == "rsource": self.stats.file_rsource_nr += 1  
        elif source_keyword == "orsource": self.stats.file_orsource_nr += 1      

        # COUNT source with and without glob
        if has_glob and source_keyword == "source":
            self.stats.file_source_w_glob += 1
        if not has_glob and source_keyword == "source":
            self.stats.file_source_nr += 1 

        # NO GLOB -> copy line as it is to the output! BUT skip this for (o)r/(o)source because these have to be transformed to source before returning the line
        if not has_glob and not source_keyword == 'rsource' \
            and not source_keyword == 'orsource' and not source_keyword == 'osource':
            print(f"    source without glob: 1")    # this is just for LOGGING, no need of using stats.file_source_out_diff, because it's always 1 line that we look at and return
            return line

        # GLOB
        print(f"    GLOB LOG ----------------------------------------------------------------------------")
        print(f"    Resolve {source_keyword}: {pattern} at line {line.line_number}")
        
        #print("tests")

        # RESOLVE 
        matched_files = []          # we only need matched_files, that we get through node iteration 
        filenames = []              # this is just to show that both ways (matched and iglob) work 
        iglob_with_rel_path = []    # so that we can compare lists - matched_files and filenames (but filenames are transformed to SRCTREE relative path)
        if self.context is not None:
            kconf = self.context.parser_result['kconf']
            srctree = Path(kconf.srctree or "")

            if current_file is None:
                # FOR RTTHREAD: If current_file None -> use current dir 
                current_file_abs_path = Path.cwd()
                print(f"    WARNING: current_file is None, using cwd: {current_file_abs_path}")
            else:
                current_file_abs_path = Path(current_file).resolve()
            current_line_nr = line.line_number
            
            # ITERATE over all nodes in menutree 
            # main idea: for each node look were it's included from (-> From: {src_file} at {src_linenr})
            # MATCHED = when current_file (==src_file) is at exacly current_line_nr (==src_linenr) (example in the comment)
            """
            when there is: source "uo3/K*" at current_file = uo2/Kconfig, line 9
            than look for all nodes that have ('uo2/Kconfig', 9) as last element in node.include_path
            AND add their node.filename to the matched_files 
            
            older explanation: 
            # when current file == src_file (meaning file with source_keyword), 
            # --- to compare we use absolute paths from these (current_abs and src_abs)
            # AND line at current file == include location (got this from src_linenr)
            # then add node.filename to the list (== string after source_keywords)
            """
            node_item_name = None
            for node in kconf.node_iter(): 
                
                if not node.filename: continue
                if not node.include_path: continue

                src_file, src_linenr = node.include_path[-1] # file and line where this node was sourced from

                # create absolute path from source file
                src_file_abs_path = (srctree / src_file).resolve() \
                    if not os.path.isabs(src_file) else Path(src_file).resolve()

                if src_file_abs_path.samefile(current_file_abs_path) and current_line_nr == src_linenr and node.filename not in matched_files:
                    matched_files.append(node.filename)

                    if resolve_log:
                        print(f"        ---- RESOLVE LOG ------------------------------------------------------")
                        print(f"        node's file: {node.filename}")
                        print(f"        node's include paths: {node.include_path}") 
                        #print(f"        node: --- \n    {node}\n        ---")
                        print(f"        -> relevant is where node was sourced from: {src_file} at line {src_linenr}") 
                        print(f"        resolved: ")
                    continue
            
            # use iglob (exacly as kconfiglib) just to show/check that both ways work 
            if resolve_log:
                if source_keyword == "rsource" or source_keyword == "orsource":
                    pattern = join(dirname(current_file), pattern)
                    #print(f"{pattern}")
                    
                #print(f"JOIN {join(srctree, pattern)}")

                filenames = sorted(iglob(join(srctree, pattern)))
                #print(f"{filenames}")
                # iglob returnes abs path -> convert to SRCTREE-relative path
                for file in filenames:
                    iglob_with_rel_path.append(str(Path(file).relative_to(os.environ["srctree"])))
            
        if not matched_files:
            # don't just comment the line, instead skip -> no output line, when there is no match 
            print(f"      no files found for the: {pattern}")   

            if resolve_log:      
                print(f"        ---- CHECK RESOLVE LOG with iglob------------------------------------------------------")
                if not filenames:
                    print(f"    iglob didn't find anything")
                else:
                    for file in filenames:
                        print(f"        iglob found: {file}")
                    print(f"            transformed iglob list (relative paths): {iglob_with_rel_path}")
                    if matched_files == iglob_with_rel_path:
                        print(f"        CHECK OK: transformed iglob list == list of matched_files through iteration")
                    else: 
                        raise RuntimeError("check source matching")

            self.stats.file_o_source_keywords_no_match += 1
            """
            if source_keyword == "orsource" or source_keyword == "osource":
                new_line_text = f'#{indent_str}source "{pattern}"' # comment, but transform ((o)r/o)source and path before? 
                new_line = KconfigLine(new_line_text, line.line_number)
                return new_line
            """
            return None
        
        # bild source for each found file, after that calculate the output diff.-> if 1 source keyword matches 5 --> Diff: 4 new lines in output
        result_lines = []
        for matched_file in matched_files:
            # matched_files - don't need to be sorted, already sorted through previous node iteration 
            if source_keyword == 'rsource' or source_keyword == 'orsource' or source_keyword == 'osource':
                #base_dir = Path(current_file).parent
                #transform_to_abs = Path(matched_file).resolve()   WRONG 
                #print(f'HERE {base_dir} + {matched_file}')^       WRONG
                #print(f'HERE2 {transform_to_abs}')                WRONG
                new_line_text = f'{indent_str}source "{matched_file}"'
                new_line = KconfigLine(new_line_text, line.line_number)
                result_lines.append(new_line)
                print(f"      -> {matched_file}")
                continue
            else:
                # for source keyword just print  
                new_line_text = f'{indent_str}source "{matched_file}"'
                new_line = KconfigLine(new_line_text, line.line_number)
                result_lines.append(new_line)
                print(f"      -> {matched_file}")
        
        # for glob log:
        self.stats.one_source_keywords_matched_glob += len(result_lines)   
        print(f"    Files matching: {self.stats.one_source_keywords_matched_glob} (using {source_keyword})")
        
        # for file log, save diff. when source matches more files (1:n)
        self.stats.new_bc_glob = self.stats.one_source_keywords_matched_glob - 1
        self.stats.file_source_out_diff += self.stats.new_bc_glob  # sum all diff for 1 file, reset after FILE logging
        
        self.stats.one_source_keywords_matched_glob = 0 # set back for the next line with keyword
        return result_lines

    def _transform_opt_modules(self, line, current_file):
        # option modules --> modules
        from core.kconfig_writer import KconfigLine 
        indent_str = ' ' * line.indent
        new_line_text = f'{indent_str}modules'
        new_line = KconfigLine(new_line_text, line.line_number)

        self.stats.option_modules_info.append({
            'line': line.line_number, 
            'file': current_file
        })
        return new_line

    def _transform_opt_env(self, line):
        # option env="<value>" --> default "$(<value>)"
        from core.kconfig_writer import KconfigLine  # avoid circular import
        indent_str = ' ' * line.indent
        env_var = line.content.get('env')
        #env_value = os.environ.get(env_var) WRONG

        default_text = f"{indent_str}default \"$({env_var})\""
            
        default_line = KconfigLine(
            default_text,
            line.line_number  
        )
            
        return default_line

    def _transform_lines(self, lines: List, current_file: Path, cd_definition_info, choice_definition_info, log_and_check_resolve_glob):
                """
                lines -> from reader 
                """
                len_reader_input = len(lines)
                print(f"start transforming {len(lines)} input lines")
                if self.context is None:
                    raise RuntimeError("call build_context_from_parser() first")
                
                result = []             # list for whole output  
                i = 0                   # counter
                current_symbol = None   
                while i < len(lines):
                    cd_processed = False
                    choice_processed = False
                    line = lines[i]
                    #print(f"hellooo {line}")     
                    #print(f"\n while counter i: {i} given line: {line}")
                    
                    if line.line_type == 'if':
                        if_contains_only_configdefault = self.helper.if_block_contains_only_configdefault(lines, i)
                
                        if if_contains_only_configdefault:
                            print(f"    Skipping if-endif block (only configdefaults) starting at line {line.line_number}")
                            old_i = i
                            i = self.helper.skip_if_block(lines, i)
                            self.stats.file_skipped_bc_configdefault += (i - old_i)
                            continue
    
                    if line.line_type == 'configdefault':
                        print(f"    Skipping configdefault block starting at line {line.line_number}")
                        self.stats.file_skipped_bc_configdefault += 1 # the configdefault line itself
                        i += 1
    
                        while i < len(lines) and lines[i].indent > line.indent:
                            print(f"      Skipping line {lines[i].line_number}: {lines[i].line_type}")
                            self.stats.file_skipped_bc_configdefault += 1
                            i += 1
                        # i = 1. line after the block 
                        continue
    
                    if line.line_type == 'named_choice':
                        choice_name = line.content.get('name')
                        
                        if not choice_name or choice_name not in choice_definition_info:
                            pass  
      
                        else:
                            choice_info = choice_definition_info[choice_name]
                            #print(f"choice_definition_info: {choice_definition_info}")
                            #print(f"choice_info {choice_info}")
                            
                            #print(f"    processed_choices before if: {self.PROCESSED_CHOICES}")
    
                            if choice_name in self.PROCESSED_CHOICES:
                                print(f"    Skipping non-first definition of choice {choice_name} at line {line.line_number}, {current_file}")
                                # Skip until endchoice
                                #print(f"    before_i {i}")
                                self.stats.file_skipped_bc_named_choice += 1 # the choice line itself
                                i += 1
                                while i < len(lines) and lines[i].line_type != 'endchoice':
                                    #print(f"        {lines[i]}")
                                    self.stats.file_skipped_bc_named_choice += 1
                                    i += 1
                                i += 1  # consume endchoice
                                self.stats.file_skipped_bc_named_choice += 1
                                #print(f"    after {i}")
                                #print("helloooend")     
                                continue
                            #print("helloooneu")
                            first_def = self.context.choice_definitions[choice_name][0]
                            first_def_file = self.context.srctree / first_def['file']
                            first_def_line = first_def['line']
                                
                            if (current_file == first_def_file and 
                                line.line_number == first_def_line):
                                    
                                print(f"    Found first definition of choice {choice_name} at line {line.line_number}")
                                print(f"    Processing choice transformation")
    
                                self.PROCESSED_CHOICES.add(choice_name)
                                print(f"    processed_choices now: {self.PROCESSED_CHOICES}")
    
                                # IF THE FIRST PARAMETER = True, then we log DEBUG info 
                                i = self._transform_named_choice(True, lines, i, choice_info, result, 
                                                    lambda l, s, f: self._transform_single_line(l, s, f, log_and_check_resolve_glob))
                                #choice_processed = True
                                continue
                    
                    if line.line_type == 'choice':
                        i = self._transform_choice(lines, i, result, 
                                                    lambda l, s, f: self._transform_single_line(l, s, f, log_and_check_resolve_glob))
                        continue
    
                    if line.line_type in ['config', 'menuconfig']:
                        #print("line is config/ menuconfig")
                        current_symbol = line.content.get('symbol')
                        #print(f"line's symbol: {current_symbol}")
                        
                        if current_symbol and current_symbol in cd_definition_info:
                            cd_info_list = cd_definition_info[current_symbol]
                            #print(f"\ncd_info_list: {cd_info_list}")
    
                            for cd_entry in cd_info_list:
                                last_config = cd_entry.get('last_config')
                                #print(f"\nlast_config: {last_config}")
                                transformed_entries = cd_entry.get('transformed_entries_list', [])
                                #print(f"transformed_entries: {transformed_entries}")
    
                                if last_config:
                                    last_conf_symbol = last_config[0]
                                    last_conf_file = last_config[1]
                                    last_conf_line = last_config[2]
                                    #print(f"last_conf_symbol: {last_conf_symbol}")
                                    #print(f"last_conf_file: {last_conf_file}")
                                    #print(f"last_conf_line: {last_conf_line}") 
    
                                    last_conf_full_path = self.context.srctree / last_conf_file
                                    #print(f"last_conf_full_path: {last_conf_full_path}")
    
                                    if (current_symbol == last_conf_symbol and 
                                        line.line_number == last_conf_line and 
                                        current_file == last_conf_full_path):
                                        
                                        print(f"    Found matching config for {current_symbol} at line {line.line_number}")
                                        print(f"    Adding {len(transformed_entries)} configdefault entries")
                                        
                                        i = self._transform_cd(lines, i, transformed_entries, result, 
                                                    lambda l, s, f: self._transform_single_line(l, s, f, log_and_check_resolve_glob))
                                        #print(f"i = self.transform_cd {i}")
                                        cd_processed = True
                                        break 
                    
                    if cd_processed:
                        continue
    
                    #print(f"\nget transformed wenn line is not config/menuconfig:")
                    transformed = self._transform_single_line(line, current_symbol, current_file, log_and_check_resolve_glob)
                    
                    #print(f"transformed: {transformed}")
                    
                    if transformed is None:
                        #print(f"transformed is non i++")
                        i += 1
                        continue
                    
                    if isinstance(transformed, list):
                        result.extend(transformed) # 1:n (def_bool → bool + default)
                    else:
                        result.append(transformed) # 1:1         
                    #print(f"after {i} is result: {result}")
                    i += 1  # go to the next line
                                
                len_transformed_lines = len(result)
                # EXCEL stats
                return result, self.stats.file_source_out_diff, len_reader_input, len_transformed_lines
        
    def transform_all_files(self, reader, writer, project_dir: Path, output_dir: Path, \
                            log: bool, log_lines: bool, log_and_check_resolve_glob: bool, \
                                log_cd_nc_details: bool, log_excel_after_each_file: bool, \
                                    log_excel_output: Optional[str] = None, \
                                        outside_file_relative_to: Optional[str] = None):
        """
        1. get all source files parser found (these are all realtive to srctree)
        2. Filter ExtParserContext -> get needed infos for transformation of configdefault and named choice options 
        3. build paths for input & output files
        """
        excel_stats = []
        transformed_count = 0

        if self.context is None:
            raise RuntimeError("Context missing!")
        
        # GET source_files & filtered info for configdefault & named choice 
        source_files = self.context_builder.get_all_source_files(self.context)             
        cd_definition_info = self.context_builder.filter_cd_from_context(self.context, reader, project_dir, log_cd_nc_details)
        choice_definition_info = self.context_builder.filter_nc_from_context(self.context, reader, project_dir, log, log_cd_nc_details)

        print(f"\nfor each given file at source_files start building path output structur and call reader and writer")     
        print(f"\n4. Transform all files - needs reader & writer")
        for file_path in source_files:
            input_file = (project_dir / file_path).resolve()

            # this solution bc of ../ in paths 
            try:
                #print(f"\nDEBUG: input_file={input_file}")
                #print(f"DEBUG: project_dir={project_dir}")
                relative_normalized = input_file.relative_to(project_dir)
                #print(f"DEBUG: relative_path={relative_normalized}")
                #print(f"DEBUG: output_file would be={output_dir / relative_normalized}")
            except ValueError:
                if outside_file_relative_to:
                    relative_normalized = input_file.relative_to(Path(outside_file_relative_to))
                    #print(relative_normalized)
                else:
                    print(f"    Skip file outside project: {input_file}")

            output_file = output_dir / relative_normalized
            #print(f"DEBUG: output_file would be={output_file}")
                
            #print(f"\ninput file: {input_file}")
            #print(f"relative_normalized: {relative_normalized}")
            #print(f"output file: {output_file}")
            if not input_file.exists():
                print(f"  Skip not found: {input_file}")
                continue
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            lines = reader.read_file(input_file)

            if log_lines:
                for line in lines:
                    #if line.line_type in LINE_TYP_LOG:
                        print(f"    {line}")
                        if line.line_type != 'empty' and line.line_type != 'other':
                            print(f"        -> Content: {line.content}")

            print("call _transform_lines(lines from reader, input, configdefault dict info)")
            # also collect not only transformed lines but some statistics 
            transformed, source_out_diff, len_reader_input, len_transformed_lines \
                  = self._transform_lines(lines, input_file, cd_definition_info, choice_definition_info, log_and_check_resolve_glob)
             
            # TODO: add new_lines to excel stats 
            statistics = self.logger.log_file_stats(self.stats, source_out_diff, input_file, len_reader_input, len_transformed_lines)
            excel_stats.append(statistics)
            self.stats.reset_file_stats()

            if log_excel_after_each_file:
                write_to_excel(excel_stats, log_excel_output)
            
            try:
                writer.write(transformed, output_file)
                transformed_count += 1
            except Exception as e:
                print(f"     Error write: {e}")
        
        print(f"----------------------------------------------------------------------")
        print(f"finished transforming: {transformed_count} files transformed")
        print(f"----------------------------------------------------------------------")
        print("Overall parser info: ")
        print(f"    -> ExParserContext - unique options: {self.context.symbol_nr}")
        print(f"    -> ExParserContext - configdefaults: {self.context.configdefault_options_nr} ({', '.join(self.context.configdefault_options)})")
        print(f"    -> ExParserContext - unique choices: {self.context.choice_nr}")
        print(f"    -> ExParserContext - named choices:  {self.context.named_choices_nr}")
        print(f"----------------------------------------------------------------------")
        if self.stats.option_modules_info:
            for info in self.stats.option_modules_info:
                print(f"    {self.stats.option_modules_counter} option modules-attr found at line {info['line']} in {info['file']}")
        else:
            print(f"    option modules: 0")          
        print(f"----------------------------------------------------------------------")
        print("count options/attr that are not transformed: ")
        print(f"    allnoconfig_y:  {self.stats.file_opt_allnoconfig}")        
        print(f"    defconfig_list: {self.stats.file_opt_defconfig}")
        print(f"    warning:        {self.stats.file_warning_attr}")
        print(f"    set:            {self.stats.file_set_option}")
        print(f"    set default:    {self.stats.file_set_default_option}")
        print(f"----------------------------------------------------------------------")
        print("count changes that don't affect the output size: ")
        print(f"        Changed inline prompt choice:    {self.stats.file_changed_inprompt_bc_choice}") 
        print(f"        Changed typ of choice element:   {self.stats.file_changed_typ_tristate_to_bool}") 
        print(f"----------------------------------------------------------------------")
        #print("additionaly count --help-- for PX4")
        print(f"Attr --help--: {self.stats.old_help}")
        print(f"Attr boolean: {self.stats.old_boolean}")

        self.stats.file_opt_defconfig = 0
        self.stats.file_opt_allnoconfig = 0
        self.stats.option_modules_counter = 0
        self.stats.option_modules_info.clear()
        self.stats.file_warning_attr = 0
        self.stats.file_set_option = 0
        self.stats.file_set_default_option = 0
        self.stats.file_changed_inprompt_bc_choice = 0        # for choice -> bool "pick something" --> prompt "pick something"
        self.stats.file_changed_typ_tristate_to_bool = 0      # tristate elements of choice should be restricted to bool 
        self.stats.old_help = 0
        self.stats.old_boolean = 0

        return excel_stats
