import sys 
import os
from pathlib import Path

# /core  
base_dir = Path(__file__).parent
# /external 
external_dir = base_dir.parent / "external"

class PickParser(object):

    __slots__= (
        "spec_version"
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
            zephyr_rtos_root = base_dir.parent / "external" / "ZephyrRTOS"
            zephyr_rtos_kconfiglib_path = zephyr_rtos_root / "scripts" / "kconfig"
            sys.path.insert(0, str(zephyr_rtos_kconfiglib_path))
            assert(zephyr_rtos_kconfiglib_path / "kconfiglib.py").exists(), f"kconfiglib.py not found in {zephyr_rtos_kconfiglib_path}"
            import kconfiglib 
        elif self.spec_version == "Z":
            import kconfiglib
        elif self.spec_version == "ESPIDF":
            from  esp_kconfiglib import Kconfig as kconfiglib

if __name__ == "__main__":
    try:
        picker_zrtos = PickParser("ZRTOS")
    except(ImportError) as e:
        print(f"Initial error: {e}")