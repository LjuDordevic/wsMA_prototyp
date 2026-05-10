from pathlib import Path
from pick_parser import PickParser
from core.parser.zrtos_parser import ZRTOSParser
from kconfig_writer import KconfigReader, KconfigWriter
from transform_prototyp import KconfigTransformer
from core.utils.time_writer import TransformTimer
import sys
import pprint
import os

def main():    
    log_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_px4/PX4_log/transform8.log"
    excel_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_px4/PX4_log/results8.xlsx"
    project_dir = "/home/ljd/px4/PX4-Autopilot"
    output_dir = "/home/ljd/wsMA_prototyp/transform_projects/transform_px4/PX4_output"
    main_file = "Kconfig"

    original_cwd = os.getcwd()
    os.chdir(project_dir)

    timer = TransformTimer()
    log_handle = open(log_file, "w")
    sys.stdout = log_handle
    sys.stderr = log_handle

    print("=" * 100)
    print("TRANSFORMATION PROTOTYP LOG")
    print("=" * 100)
    print(f"{log_file}")
    print("=" * 100)
    print(f"Root: {project_dir}")
    print(f"Main file: {main_file}")
    print(f"Output dir: {output_dir}")
    print("=" * 100)
    
    picker = PickParser("ZRTOS")
    parser = ZRTOSParser(picker.kconfiglib_version)
    timer.lap("Parser initialization")
    print(parser)


    try:
        parser_result = parser.parse_files(".", main_file)
        timer.lap("Got parser results")
        print(f"Defined symbols: {len(parser_result['defined_syms'])}")
        print(f"Unique symbols: {len(parser_result['unique_defined_syms'])}")
        print(f"Files: {len(parser_result['kconf'].kconfig_filenames)}")

        transformer = KconfigTransformer(source_spec="ZRTOS")
        print("\n2. Build ExtParserContext FROM PARSER RESULTS")
        print(f" Transformer used: {transformer.source_spec}")

        context = transformer._build_context_from_parser(
            parser_result,
            log=False
        )
        
        timer.lap("Built context from parser results")
        print("=" * 100)
        print(f"Build context finished")

        reader = KconfigReader("ZRTOS")
        writer = KconfigWriter("ZRTOS")

        excel_data = transformer.transform_all_files(
            reader=reader,
            writer=writer,
            project_dir=Path(project_dir).resolve(),  
            output_dir=Path(output_dir).resolve(),     
            log=True,
            log_lines=False,
            log_and_check_resolve_glob=False,
            log_cd_nc_details=True,
            log_excel_after_each_file=True,
            log_excel_output=excel_file
        )   

        timer.lap("File transformation and excel log")
        timer.stop()

        return_code = 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return_code = 1

    finally:
        log_handle.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        os.chdir(original_cwd)

    return return_code

if __name__ == '__main__':
    sys.exit(main())   