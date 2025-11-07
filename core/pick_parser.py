import sys 
import os
from pathlib import Path

# core  
base_dir = Path(__file__).parent

class PickParser(object):

    __slots__= (
        "spec_version"
    )

    def __init__(
            self,
            spec_version,
    ):
        self.spec_version = spec_version
        if spec_version == "ZRTOS":
            zephyr_rtos_root = base_dir.parent / "external" / "ZephyrRTOS"
            zephyr_rtos_kconfiglib_path = zephyr_rtos_root / "scripts" / "kconfig"
            sys.path.insert(0, str(zephyr_rtos_kconfiglib_path))
            assert(zephyr_rtos_kconfiglib_path / "kconfiglib.py").exists(), f"kconfiglib.py not found in {zephyr_rtos_kconfiglib_path}"
            import kconfiglib 
        elif spec_version == "Z"
            import kconfiglib
        elif spec_version == "ESPIDF"
            from  esp_kconfiglib import Kconfig as kconfiglib
        self()

    