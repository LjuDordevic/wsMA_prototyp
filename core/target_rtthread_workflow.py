from pathlib import Path
from pick_parser import PickParser
from zrtos_parser import ZRTOSParser
from kconfig_writer import KconfigReader, KconfigWriter
from transform_prototyp import KconfigTransformer
import excel_writer
from time_writer import TransformTimer
import sys
import pprint
import os

def main():    
    log_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_rt_thread/RT_Thread_log/transform.log"
    excel_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_rt_thread/RT_Thread_log/results.xlsx"
    project_dir = "/home/ljd/rtthread/rt-thread/bsp/qemu-vexpress-a9"
    output_dir = "/home/ljd/wsMA_prototyp/transform_projects/transform_rt_thread/RT_Thread_output"
    main_file = "Kconfig"

    #os.environ["RTT_DIR"] = "/home/ljd/rtthread/rt-thread"
    #os.environ["BSP_DIR"] = "/home/ljd/rtthread/rt-thread/bsp/qemu-vexpress-a9"
    #os.environ["PKGS_DIR"] = "/home/ljd/rtthread/rt-thread/bsp/qemu-vexpress-a9/packages"
    

    #project_dir = "/home/ljd/wsMA_prototyp/ZRTOS_demo/zephyr"
    #output_dir = "/home/ljd/wsMA_prototyp/transform_projects/transform_zrtos/ZRTOS_copy1"

    original_cwd = os.getcwd()
    os.chdir(project_dir)

    os.environ["RTT_DIR"] = "../.."
    os.environ["BSP_DIR"] = "."
    os.environ["PKGS_DIR"] = "packages"

    timer = TransformTimer()
    sys.stdout = open(log_file, "w")
    sys.stderr = sys.stdout 

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
        # Jetzt nur noch den Dateinamen übergeben, da wir bereits im richtigen Verzeichnis sind
        parser_result = parser.parse_files(".", main_file)
        timer.lap("Got parser results")
        print(f"Defined symbols: {len(parser_result['defined_syms'])}")
        print(f"Unique symbols: {len(parser_result['unique_defined_syms'])}")
        print(f"Files: {len(parser_result['kconf'].kconfig_filenames)}")
    except Exception as e:
        print(f"Parser error {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        os.chdir(original_cwd)

    transformer = KconfigTransformer(source_spec="ZRTOS")
    print("\n2. Bild ExtParserContext FROM PARSER RESULTS")
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
        project_dir=Path("."),
        output_dir=Path(output_dir),
        log=True,
        log_lines=False,
        log_and_check_resolve_glob=False,
        log_cd_nc_details=False,
        log_excel_after_each_file=True,
        log_excel_output=excel_file
    )   

    timer.lap("File transformation and excel log")

    timer.stop()

    #excel_writer.write_excel(excel_data, "/home/ljd/wsMA_prototyp/results.xlsx")

    return 0
    

if __name__ == '__main__':
    sys.exit(main())