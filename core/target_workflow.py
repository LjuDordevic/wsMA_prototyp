from pathlib import Path
from pick_parser import PickParser
from zrtos_parser import ZRTOSParser
from kconfig_writer import KconfigReader, KconfigWriter
from transform_prototyp import KconfigTransformer
import excel_writer
import sys
import pprint
import os

def main():
    log_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_zrtos/ZRTOS_copy1/transform.log"
    sys.stdout = open(log_file, "w")
    sys.stderr = sys.stdout 

    project_dir = "/home/ljd/wsMA_prototyp/ZRTOS_demo/zephyr"
    main_file = "Kconfig"
    output_dir = "/home/ljd/wsMA_prototyp/transform_projects/transform_zrtos/ZRTOS_copy1"

    print("=" * 100)
    print("TRNASFORMATION PROTOTYP LOG")
    print("=" * 100)

    print("VARS: ")
    vars = ['ZEPHYR_BASE', 'WORKING_DIRECTORY', 'PROJECT_BINARY_DIR', 
            'BOARD', 'srctree', 'KCONFIG_BINARY_DIR', 'ZEPHYR_ACPICA_KCONFIG']
    
    print(f"  project dir: {project_dir}\n  main file: {main_file}\n  output_dir: {output_dir}")
    
    for key in vars:
        value = os.environ.get(key, '<NOT SET>')
        print(f"  {key}='{value}'")

    print("=" * 100)
    print(f"Root: {project_dir}")
    print(f"Main file: {main_file}")
    print(f"Output dir: {output_dir}")
    print("=" * 100)
    
    picker = PickParser("ZRTOS")
    parser = ZRTOSParser(picker.kconfiglib_version)
    print(parser)

    try:
        parser_result = parser.parse_files(project_dir, main_file)
        print(f"Defined symbols: {len(parser_result['defined_syms'])}")
        print(f"Unique symbols: {len(parser_result['unique_defined_syms'])}")
        print(f"Files: {len(parser_result['kconf'].kconfig_filenames)}")
    except Exception as e:
        print(f"Parser error {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    transformer = KconfigTransformer(source_spec="ZRTOS")
    print("\n2. Bild ExtParserContext FROM PARSER RESULTS")
    print(f" Transformer used: {transformer.source_spec}")

    context = transformer._build_context_from_parser(
        parser_result,
        log=False
    )

    print("=" * 100)
    print(f"Build context finished")

    reader = KconfigReader("ZRTOS")
    writer = KconfigWriter("ZRTOS")

    excel_data = transformer.transform_all_files(
        reader=reader,
        writer=writer,
        project_dir=Path(project_dir),
        output_dir=Path(output_dir),
        log=True,
        log_lines=False,
        log_and_check_resolve_glob=False,
        log_cd_nc_details=False,
        log_excel_after_each_file=True,
        log_excel_output="/home/ljd/wsMA_prototyp/results.xlsx"
    )    

    #excel_writer.write_excel(excel_data, "/home/ljd/wsMA_prototyp/results.xlsx")

    return 0

if __name__ == '__main__':
    sys.exit(main())