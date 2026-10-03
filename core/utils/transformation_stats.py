from dataclasses import dataclass, field
from typing import List

@dataclass
class TransformationStats:
    file_def_keywords_count: int = 0
    project_def_keywords_count: int = 0

    file_source_nr: int = 0
    file_source_w_glob: int = 0
    file_osource_nr: int = 0
    file_rsource_nr: int = 0
    file_orsource_nr: int = 0

    file_source_out_diff: int = 0

    new_bc_glob: int = 0
    file_source_keywords_all_nr: int = 0
    file_all_added_lines_skw: int = 0
    one_source_keywords_matched_glob: int = 0

    file_configdefault_nr: int = 0
    file_removed_consecutive_empty_lines: int = 0
    file_skipped_bc_configdefault: int = 0

    file_o_source_keywords_no_match: int = 0

    option_modules_counter: int = 0
    option_modules_info: List[str] = field(default_factory=list)

    file_opt_env: int = 0
    file_opt_allnoconfig: int = 0
    file_opt_defconfig: int = 0

    file_skip_optional_choice_attr: int = 0
    file_warning_attr: int = 0

    file_set_option: int = 0
    file_set_default_option: int = 0

    file_skip_choice_typ_def_bool: int = 0
    file_skip_choice_typ_def_tristate: int = 0

    file_skipped_bc_named_choice: int = 0
    file_added_bc_named_choice: int = 0

    file_changed_inprompt_bc_choice: int = 0
    file_changed_typ_tristate_to_bool: int = 0

    old_help: int = 0
    old_boolean: int = 0

    def reset_file_stats(self) -> None:
        self.file_source_nr = 0
        self.file_source_w_glob = 0
        self.file_osource_nr = 0
        self.file_rsource_nr = 0
        self.file_orsource_nr = 0
        self.file_source_keywords_all_nr = 0
        self.file_def_keywords_count = 0
        self.file_all_added_lines_skw = 0
        self.file_configdefault_nr = 0
        self.file_removed_consecutive_empty_lines = 0
        self.file_skipped_bc_configdefault = 0
        self.new_bc_glob = 0
        self.file_source_out_diff = 0
        self.file_o_source_keywords_no_match = 0
        self.file_opt_env = 0
        self.file_skip_optional_choice_attr = 0
        self.file_skip_choice_typ_def_bool = 0
        self.file_skip_choice_typ_def_tristate = 0
        self.file_skipped_bc_named_choice = 0
        self.file_added_bc_named_choice = 0

    def reset_global_stats(self) -> None:
        self.file_opt_defconfig = 0
        self.file_opt_allnoconfig = 0
        self.option_modules_counter = 0
        self.option_modules_info.clear()
        self.file_warning_attr = 0
        self.file_set_option = 0
        self.file_set_default_option = 0
        self.file_changed_inprompt_bc_choice = 0
        self.file_changed_typ_tristate_to_bool = 0
        self.old_help = 0
        self.old_boolean = 0

    
