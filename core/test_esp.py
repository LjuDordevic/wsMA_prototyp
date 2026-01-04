from pathlib import Path
from pick_parser import PickParser
from espidf_parser import ESPIDFParser
import sys
import os 

def main():    
    log_file = "/home/ljd/wsMA_prototyp/testESPIDF/transform.log"
    project_dir = "/home/ljd/espcode/v5.5.2/esp-idf"
    main_file = "Kconfig"

    os.environ["IDF_ENV_FPGA"] = "false"
    os.environ["srctree"] = project_dir
    os.environ["IDF_TARGET"] = "esp32"
    os.environ["COMPONENT_KCONFIGS_SOURCE_FILE"] = "/home/ljd/wsMA_prototyp/ESP_IDF_demo/build/kconfigs.in"
    os.environ["COMPONENT_KCONFIGS_PROJBUILD_SOURCE_FILE"] = "/home/ljd/wsMA_prototyp/ESP_IDF_demo/build/kconfigs_projbuild.in"

    sys.stdout = open(log_file, "w")
    sys.stderr = sys.stdout 

    print("=" * 100)
    print("TRANSFORMATION PROTOTYP LOG")
    print("=" * 100)
    print(f"Root: {project_dir}")
    print(f"Main file: {main_file}")
    #print(f"Output dir: {output_dir}")
    print("=" * 100)
    
    picker = PickParser("ESPIDF")
    parser = ESPIDFParser(picker.kconfiglib_version)
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

    return 0

if __name__ == '__main__':
    sys.exit(main())