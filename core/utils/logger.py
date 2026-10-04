from datetime import datetime
import pprint
from pathlib import Path
from core.utils.transformation_stats import TransformationStats

class Logger:

    def start(self, project_dir: str, main_file: str, output_dir: str, parser, spec_version: str):
        print("=" * 100)
        print("TRANSFORMATION PROTOTYP LOG")
        print("=" * 100)
        print(f"    Root (srctree): {project_dir}")
        print(f"    Main file:      {main_file}")
        print(f"    Output dir:     {output_dir}")
        print(f"    Specification:  {spec_version}")
        print(f"    Parser obj:     {parser}")
        print(f"    Timestamp:      {datetime.now().strftime("%d.%m.%Y %H:%M")}")
        print("=" * 100)

    def print_parser_result(self, parser_result: dict):
        pprint.pprint(parser_result)
        print("-" * 50)
        print(f"   Parser found: {len(parser_result['defined_syms'])} defined syms")
        print(f"   Parser found: {len(parser_result['unique_defined_syms'])} unique defined syms")
        print(f"   Parser found: {len(parser_result['kconf'].kconfig_filenames)} files")
        print("-" * 50)

    def _log_file_stats(self, stats: TransformationStats, new_lines_skw : int, current_file : Path, len_input : int, len_result : int):
        print(f"    FILE LOG --------------------------------------------------------------")
        #print(f"    File:                      {str(current_file)}")
        print(f"    Reader input                {len_input} lines")
        print(f"    -----------------------------------------------------------------------")
        print(f"    All source without glob:    {stats.file_source_nr}")
        print(f"    All source using glob:      {stats.file_source_w_glob}")
        print(f"    All osource_keywords:       {stats.file_osource_nr}")
        print(f"    All rsource_keywords:       {stats.file_rsource_nr}")
        print(f"    All orsource_keywords:      {stats.file_orsource_nr}")  
        print(f"    SUM (r/or/o)source lines:   {stats.file_source_keywords_all_nr}")
        print(f"    All \"option env\" attr:      {stats.file_opt_env}")
        print(f"    -----------------------------------------------------------------------")
        print(f"    Transformer Output:         {len_result} lines")
        print(f"    -----------------------------------------------------------------------")
        print(f"        Added new bc of def_*:           {stats.file_def_keywords_count}")
        print(f"        Added new bc of glob:            {new_lines_skw}")
        print(f"        Added new bc of config_default:  {stats.file_configdefault_nr}")
        print(f"        Added new bc of named choice:    {stats.file_added_bc_named_choice}") 
    #print(f"        Removed consecutive empty lines:  {self.stats.file_removed_consecutive_empty_lines}") 
        print(f"        Removed bc of config_default:    {stats.file_skipped_bc_configdefault}") 
        print(f"        Removed bc of named choice:      {stats.file_skipped_bc_named_choice}") 
        print(f"        Removed no match for o(r)source: {stats.file_o_source_keywords_no_match}")  
        print(f"        Removed optional choice attr:    {stats.file_skip_optional_choice_attr}")
        print(f"        Removed bool     choice attr:    {stats.file_skip_choice_typ_def_bool}")
        print(f"        Removed tristate choice attr:    {stats.file_skip_choice_typ_def_tristate}") 

        file_stats_excel = {
            'test file' : str(current_file),
            'input'     : len_input,
            'output'    : len_result,
            'source_keyword_wo_glob' : stats.file_source_nr,
            'source_keyword_w_glob' : stats.file_source_w_glob,
            'osource_keyword' : stats.file_osource_nr,
            'rource_keyword' : stats.file_rsource_nr,
            'orsource_keyword' : stats.file_orsource_nr,
            'sum_all_source' : stats.file_source_keywords_all_nr,
            'option_env' : stats.file_opt_env,

            'new_lines_bc_of_def_': stats.file_def_keywords_count,

            'new_lines_bc_of_glob': new_lines_skw,
            'new_lines_bc_cd': stats.file_configdefault_nr,
            'new_lines_bc_named_choice': stats.file_added_bc_named_choice,

            'removed_bc_orsource': stats.file_o_source_keywords_no_match,
            'removed_lines_bc_cd': stats.file_skipped_bc_configdefault,
            'removed_lines_bc_named_choice': stats.file_skipped_bc_named_choice,

            'removed_optional_choice_attr': stats.file_skip_optional_choice_attr,
            'removed_bool_choice_attr': stats.file_skip_choice_typ_def_bool,
            'removed_tristate_choice_attr': stats.file_skip_choice_typ_def_tristate
        }

        return file_stats_excel

    def log_parser_context(self, given_context):
        
        print(f"\n For each symbol found in parser_result['unique_defined_syms']")
        print(f"    -> call sym.name/.origin/.name_and_loc")
        print(f"    -> call for each sym.nodes (.filename/.linenr/node/.defaults/is_configdefault")
        print(f"    -> call all sym.defaults")
        print(f"    -> call all sym.orig_defaults")
        print(f"\n------------ symbol_infos --------------------------------------------------")
        #print(given_context.symbol_infos)
        for symbol_name, infos in given_context.symbol_infos.items():
            for symbol_info in infos:
                print(f"{symbol_name}: [{symbol_info}]")
        print(f"\n------------ symbol_definitions --------------------------------------------------")
        #print(given_context.symbol_definitions)
        for symbol_name, definitions in given_context.symbol_definitions.items():
            for definition in definitions:
                print(f"{symbol_name}: [{definition}]")
        print(f"\n------------ symbol_defaults -----------------------------------------------")
        #print(given_context.symbol_defaults)
        for symbol_name, defaults in given_context.symbol_defaults.items():
            for default in defaults:
                print(f"{symbol_name}: [{default}]")
        #print(f"\n------------ sym.orig_defaults ---------------------------------------------")
        #print(f"these omit any dependencies propagated from 'depends on' and surrounding 'if's & strip location of default line")
        #print(given_context.symbol_orig_defaults)
        print(f"\n------------ choice_infos -----------------------------------------------")
        for choice_name, infos in given_context.choice_infos.items():
            print(f"{choice_name}")
            for info in infos:
                for sym in info.get('choice.syms', []) or []:
                    print(f"    [{repr(sym)}]")
        
        print(f"\n------------ choice_definitions -----------------------------------------------")
        for choice_name, definitions in given_context.choice_definitions.items():
            for definition in definitions:
                print(f"{choice_name}: [{repr(definition)}]")
       
        print(f"\n   Symbol definitions and corresponding locations in ExParserContext: ")
        for sym_name, definitions in given_context.symbol_definitions.items():
            if len(definitions) >= 1:
                print(f"   '{sym_name}' is defined x{len(definitions)}")
                for defn in definitions:
                    is_default = defn.get('is_configdefault', False)
                    default_tag = " (as configdefault)" if is_default else ""
                    file = defn.get('file') or "<unknown file>"
                    line = defn.get('line') or "<unknown line>"
                    print(f"     - {file}:{line}{default_tag}")
