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