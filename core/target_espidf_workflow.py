from pathlib import Path
from pick_parser import PickParser
from espidf_parser import ESPIDFParser
from kconfig_writer import KconfigReader, KconfigWriter
from transform_prototyp import KconfigTransformer
from time_writer import TransformTimer
import sys
import os 

def main():    
    log_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_esp_idf/ESP_IDF_log/transform2.log"
    excel_file = "/home/ljd/wsMA_prototyp/transform_projects/transform_esp_idf/ESP_IDF_log/results2.xlsx"
    project_dir = "/home/ljd/espcode/v5.5.2/esp-idf"
    output_dir = "/home/ljd/wsMA_prototyp/transform_projects/transform_esp_idf/ESP_IDF_demo_output"
    main_file = "Kconfig"

    os.environ["IDF_ENV_FPGA"] = "false"
    os.environ["srctree"] = project_dir
    os.environ["IDF_TARGET"] = "esp32"
    os.environ["COMPONENT_KCONFIGS_SOURCE_FILE"] = "/home/ljd/wsMA_prototyp/ESP_IDF_demo/build/kconfigs.in"
    os.environ["COMPONENT_KCONFIGS_PROJBUILD_SOURCE_FILE"] = "/home/ljd/wsMA_prototyp/ESP_IDF_demo/build/kconfigs_projbuild.in"

    timer = TransformTimer()
    sys.stdout = open(log_file, "w")
    sys.stderr = sys.stdout 

    print("=" * 100)
    print("TRANSFORMATION PROTOTYP LOG")
    print("=" * 100)
    print(f"{log_file}")
    print(f"Root: {project_dir}")
    print(f"Main file: {main_file}")
    print(f"Output dir: {output_dir}")
    print("=" * 100)
    
    
    print("PROJBUILD exists:",
      os.path.exists(os.environ["COMPONENT_KCONFIGS_PROJBUILD_SOURCE_FILE"]))

    picker = PickParser("ESPIDF")
    parser = ESPIDFParser(picker.kconfiglib_version)
    timer.lap("Parser initialization")
    print(parser)

    try:
        parser_result = parser.parse_files(project_dir, main_file)
        timer.lap("Got parser results")
        print(f"Defined symbols: {len(parser_result['defined_syms'])}")
        print(f"Unique symbols: {len(parser_result['unique_defined_syms'])}")
        print(f"Files: {len(parser_result['kconf'].kconfig_filenames)}")
    except Exception as e:
        print(f"Parser error {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    transformer = KconfigTransformer(source_spec="ESPIDF")
    print("\n2. Bild ExtParserContext FROM PARSER RESULTS")
    print(f" Transformer used: {transformer.source_spec}")

    context = transformer._build_context_from_parser(
        parser_result,
        log=False
    )
    
    timer.lap("Built context from parser results")
    print("=" * 100)
    print(f"Build context finished")

    reader = KconfigReader("ESPIDF")
    writer = KconfigWriter("ESPIDF")

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
        log_excel_output=excel_file
    )   

    timer.lap("File transformation and excel log")

    timer.stop()

    return 0

if __name__ == '__main__':
    sys.exit(main())