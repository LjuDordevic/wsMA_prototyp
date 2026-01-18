import sys 
import os
from pathlib import Path
import pprint
from zrtos_parser import ZRTOSParser

# /core  
base_dir = Path(__file__).parent
# /external 
external_dir = base_dir.parent / "external"

class PickParser:

    __slots__= (
        "spec_version",
        "_kconfig_folder",
        "kconfiglib_version"
    )

    def __str__(self):
        return (
            f"START using parser: \n"
            f"  spec_version: {self.spec_version}\n"
            f"  kconfig_folder: {self._kconfig_folder}\n"
            f"  kconfiglib_version: {self.kconfiglib_version}"
        )

    def __init__(self, spec_version: str):
        """
        Init ParserPicker based on given specification version (specification = Kconfig file)
        valid specification versions are ("ZKCL", "ZRTOS", "ESPIDF")
        ZKCL    = Kconfiglib specification                  for zephyr-rtos/Kconfiglib
        ZRTOS   = project specific Kconfiglib specification for zephyr-rtos/zephyr 
        ESPIDF  = project specific Kconfiglib specification for espressif/esp-idf-kconfig
        """
        self.spec_version = spec_version.upper() # make sure is upper case 
        self._kconfig_folder = None
        self.kconfiglib_version = None
        self._load_kconfiglib()
    
    def _load_zrtos(self):
        zephyr_rtos_root = external_dir / "ZephyrRTOS"
        zephyr_rtos_kconfiglib_folder = zephyr_rtos_root / "scripts" / "kconfig"
        zephyr_rtos_kconfiglib_file = zephyr_rtos_kconfiglib_folder / "kconfiglib.py"

        assert(zephyr_rtos_kconfiglib_file).exists(), f"kconfiglib.py not found in {zephyr_rtos_kconfiglib_folder}"
        self._kconfig_folder = zephyr_rtos_kconfiglib_folder

        # clear cache
        if 'kconfiglib' in sys.modules:
            del sys.modules['kconfiglib']
            
        kcl_folder_str = str(zephyr_rtos_kconfiglib_folder)
        if kcl_folder_str not in sys.path:
                sys.path.insert(0, kcl_folder_str)

        try:
            import kconfiglib as kconfiglib_zrtos
            self.kconfiglib_version = kconfiglib_zrtos
        except ImportError as e:
            raise ImportError(f"couldn't import from {kcl_folder_str}: {e}")

    def _load_zkcl(self):
    
        zephyr_kcl_root = external_dir / "ZephyrKconfiglib"
        zephyr_kcl_file = zephyr_kcl_root / "kconfiglib.py"

        assert(zephyr_kcl_file).exists(), f"kconfiglib.py not found in {zephyr_kcl_root}"
        self._kconfig_folder = zephyr_kcl_root # no extra folder

        # clear cache
        if 'kconfiglib' in sys.modules:
            del sys.modules['kconfiglib']

        kcl_folder_str = str(zephyr_kcl_root)
        # remove all "old paths" from sys.paths that have 'kconfiglib'
        # leave the current one = /external/ZephyrKconfiglib 
        # and the ones that don't even have 'kconfiglib'           
        sys.path = [p for p in sys.path if p == kcl_folder_str or 'kconfiglib' not in p.lower()]

        if kcl_folder_str not in sys.path:
            sys.path.insert(0, kcl_folder_str)           

        try:
            import kconfiglib as z_kconfiglib
            self.kconfiglib_version = z_kconfiglib
        except ImportError as e:
            raise ImportError(f"couldn't import from {kcl_folder_str}: {e}")    

    def _load_espidf(self):

        espidf_kcl_root = external_dir / "ESPIDFKconfig"
        espidf_kcl_folder = espidf_kcl_root / "esp_kconfiglib"

        assert espidf_kcl_folder.exists(), (
            f"esp_kconfiglib module not found in {espidf_kcl_root}"
        )

        self._kconfig_folder = espidf_kcl_folder

        # clear module cache
        if 'esp_kconfiglib' in sys.modules:
            del sys.modules['esp_kconfiglib']

        kcl_folder_str = str(espidf_kcl_root)
        if kcl_folder_str not in sys.path:
            sys.path.insert(0, kcl_folder_str)

        try:
            from esp_kconfiglib import Kconfig
            self.kconfiglib_version = Kconfig
        except ImportError as e:
            raise ImportError(
                f"couldn't import from {kcl_folder_str}: {e}"
            )


    def _load_kconfiglib(self):
        """
        get right version of kconfiglib
        assure that folder with submodules exist 
        """
        if not external_dir.exists():
            raise FileNotFoundError(
                f"external folder with needed submodules not found: {external_dir}"
            )
        
        if self.spec_version == "ZRTOS":
            self._load_zrtos()

        elif self.spec_version == "ZKCL":
            self._load_zkcl()

        elif self.spec_version == "ESPIDF":
            self._load_espidf()

""" 
#------------ ZUM TESTEN TODO: soll weg ------------------- 
    def _test_kconfiglib(self, project_dir: str, kconfig_file: str):
        project_dir_path = Path(project_dir)
        os.environ["srctree"] = str(project_dir_path)
        esp_kconfig_file = project_dir_path / kconfig_file

        if self.spec_version == "ESPIDF":
            print("esp file path: " + str(esp_kconfig_file))
            kconf = self.kconfiglib_version(str(esp_kconfig_file))
        else:
            kconf = self.kconfiglib_version.Kconfig(str(kconfig_file))
        print('Symbols: ', len(kconf.defined_syms))

    def _parse_only(self, project_dir: str, kconfig_file: str):
        if self.spec_version != "ZRTOS":
            raise ValueError("FOR ZRTOS")
        parser = ZRTOSParser(self.kconfiglib_version)
        return parser.parse_files(project_dir, kconfig_file)
#----------------------------------------------------------
if __name__ == "__main__":
  
    picker_zrtos = PickParser("ZRTOS")
    print(picker_zrtos)
    picker_zrtos._test_kconfiglib("/home/ljd/wsMA_prototyp/exp", "KconfigZephyrRTOS")
    print("-" * 50)
    #result = picker_zrtos._parse_only("/home/ljd/wsMA_prototyp/exp", "KconfigZephyrRTOS")
    #pprint.pprint(result)

    picker_zkcl = PickParser("ZKCL")
    print(picker_zkcl)
    picker_zkcl._test_kconfiglib("/home/ljd/wsMA_prototyp/exp", "Kconfig")
    print("-" * 50)
    
    picker_esp = PickParser("ESPIDF")
    print(picker_esp)
    picker_esp._test_kconfiglib("/home/ljd/wsMA_prototyp/exp", "KconfigEsp")
"""