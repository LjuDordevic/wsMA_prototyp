from pathlib import Path
from pick_parser import PickParser
from zrtos_parser import ZRTOSParser
from kconfig_writer import KconfigReader, KconfigWriter
from transform_prototyp import KconfigTransformer
import sys
import pprint
import os

def main():
    log_file = "/home/ljd/wsMA_prototyp/transform.log"
    sys.stoutput = open(log_file, "w")
    sys.stderr = sys.stdout 

    project_dir = "/home/ljd/wsMA_prototyp/ZRTOS_demo/zephyr"
    main_file = "Kconfig"
    output_dir = "/home/ljd/wsMA_prototyp/ZRTOS_copy"

    print("VARS: ")
    vars = ['ZEPHYR_BASE', 'WORKING_DIRECTORY', 'PROJECT_BINARY_DIR', 
            'BOARD', 'srctree', 'KCONFIG_BINARY_DIR', 'ZEPHYR_ACPICA_KCONFIG']
    
    print(f"  project dir: {project_dir}\n  main file: {main_file}\n  output_dir: {output_dir}")
    
    for key in vars:
        value = os.environ.get(key, '<NOT SET>')
        print(f"  {key}='{value}'")

    picker = PickParser("ZRTOS")
    print(picker)
    parser = ZRTOSParser(picker.kconfiglib_version)

    try:
        parser_result = parser.parse_files(project_dir, main_file)
        print(f"Defined symbols: {len(parser_result['defined_syms'])}")
        print(f"Unique symbols: {len(parser_result['unique_defined_syms'])}")
        print(f"Files: {len(parser_result['kconf'].kconfig_filenames)}")
    except Exception as e:
        print(f"Parser error {e}")

    sys.stdout.close()

    return 0

if __name__ == '__main__':
    sys.exit(main())