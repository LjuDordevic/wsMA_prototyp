from pathlib import Path
from typing import List
from core.context.context import ExtParserContext

class TransformHelperUtils:

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

    def extract_named_choice_info(self, context, choice_name: str, log: bool, log_cd_nc_details: bool):
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
        