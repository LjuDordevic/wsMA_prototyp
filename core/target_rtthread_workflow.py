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
    log_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_rt_thread/RT_Thread_log/transform6.log"
    excel_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_rt_thread/RT_Thread_log/results6.xlsx"
    project_dir = "/home/ljd/rtthread/rt-thread/bsp/qemu-vexpress-a9"
    output_dir = "/home/ljd/wsMA_prototyp/transform_projects/transform_rt_thread/RT_Thread_output"
    main_file = "Kconfig"

    # Because the main Kconfig in /bsp/qemu-vexpress-a9 refers to other Kconfig that are in ../ or ../..
    # we give this as outside_file_relative_to to transform_all_files() 
    # without this the output structur of transformation is not right 
    rt_thread_root = "/home/ljd/rtthread/rt-thread"
    
    # Ins Projektverzeichnis wechseln
    original_cwd = os.getcwd()
    os.chdir(project_dir)
    
    # Relative Pfade setzen (relativ zum project_dir)
    os.environ["RTT_DIR"] = "../.."
    os.environ["BSP_DIR"] = "."
    os.environ["PKGS_DIR"] = "packages"

    # Log-Datei öffnen
    log_handle = open(log_file, "w")
    sys.stdout = log_handle
    sys.stderr = log_handle

    timer = TransformTimer()

    print("=" * 100)
    print("TRANSFORMATION PROTOTYP LOG")
    print("=" * 100)
    print(f"Log file: {log_file}")
    
    print("=" * 100)
    print(f"Project dir: {project_dir}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Main file: {main_file}")
    print(f"Output dir: {output_dir}")
    print("Environment variables:")
    print(f"  RTT_DIR={os.environ.get('RTT_DIR')}")
    print(f"  BSP_DIR={os.environ.get('BSP_DIR')}")
    print(f"  PKGS_DIR={os.environ.get('PKGS_DIR')}")
    print("=" * 100)
    
    picker = PickParser("ZRTOS")
    parser = ZRTOSParser(picker.kconfiglib_version)
    timer.lap("Parser initialization")
    print(parser)

    try:
        # Parser ausführen (wir sind bereits im richtigen Verzeichnis)
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

        # Absolute Pfade verwenden für beide Parameter
        excel_data = transformer.transform_all_files(
            reader=reader,
            writer=writer,
            project_dir=Path(project_dir).resolve(),  # Absoluter Pfad
            output_dir=Path(output_dir).resolve(),     # Absoluter Pfad
            log=True,
            log_lines=False,
            log_and_check_resolve_glob=False,
            log_cd_nc_details=False,
            log_excel_after_each_file=True,
            log_excel_output=excel_file, 
            outside_file_relative_to = rt_thread_root
        )   

        timer.lap("File transformation and excel log")
        timer.stop()

        # Optional: Excel-Daten schreiben
        # excel_writer.write_excel(excel_data, "/home/ljd/wsMA_prototyp/results.xlsx")

        return_code = 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return_code = 1

    finally:
        # Aufräumen: Log-Datei schließen und zurück ins ursprüngliche Verzeichnis
        log_handle.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        os.chdir(original_cwd)

    return return_code

if __name__ == '__main__':
    sys.exit(main())