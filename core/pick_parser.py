import sys 
import os
from pathlib import Path

# /core  
base_dir = Path(__file__).parent
# /external 
external_dir = base_dir.parent / "external"

class PickParser:

    __slots__= (
        "spec_version",
        "_kconfig_folder",
        "kconfiglib"
    )

    def __str__(self):
        return (
            f"spec_version: {self.spec_version}\n"
            f"kconfig_folder: {self._kconfig_folder}\n"
            f"kconfiglib: {self.kconfiglib}"
        )

    def __init__(self, spec_version: str):
        """
        Init ParserPicker based on given specification version (specification = main Kconfig file)
        valid specification versions are ("ZKCL", "ZRTOS", "ESPIDF")
        ZKCL    = Kconfiglib specification                  for zephyr-rtos/Kconfiglib
        ZRTOS   = project specific Kconfiglib specification for zephyr-rtos/zephyr 
        ESPIDF  = project specific Kconfiglib specification for espressif/esp-idf-kconfig
        """

        self.spec_version = spec_version.upper() # make sure is upper case 
        self._kconfig_folder = None
        self.kconfiglib = None
        self._load_kconfiglib()
            
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
            zephyr_rtos_root = external_dir / "ZephyrRTOS"
            zephyr_rtos_kconfiglib_folder = zephyr_rtos_root / "scripts" / "kconfig"
            zephyr_rtos_kconfiglib_file = zephyr_rtos_kconfiglib_folder / "kconfiglib.py"

            assert(zephyr_rtos_kconfiglib_file).exists(), f"kconfiglib.py not found in {zephyr_rtos_kconfiglib_folder}"
            self._kconfig_folder = zephyr_rtos_kconfiglib_folder

            if str(zephyr_rtos_kconfiglib_folder) not in sys.path:
                sys.path.insert(0, str(zephyr_rtos_kconfiglib_folder))

            try:
                import kconfiglib as kconfiglib_zrtos
                self.kconfiglib = kconfiglib_zrtos
            except ImportError as e:
                raise ImportError(f"couldn't import from ")

            """ elif self.spec_version == "Z":
                import kconfiglib
            elif self.spec_version == "ESPIDF":
                from  esp_kconfiglib import Kconfig as kconfiglib"""

if __name__ == "__main__":
    print("test")
    picker_zrtos = PickParser("ZRTOS")
    print(picker_zrtos)
    