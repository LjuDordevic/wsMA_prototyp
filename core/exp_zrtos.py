from pick_parser import PickParser
from zrtos_parser import ZRTOSParser
from transform_prototyp import KconfigTransformer
import os

project_dir = ""
main_file = "Kconfig.zephyr"
os.environ["KCONFIG_BINARY_DIR"] = ""

picker = PickParser("ZRTOS")
print("-" * 50)

print("1.  Parser Output: ")
parser = ZRTOSParser(picker.kconfiglib_version)
parser_result = parser.parse_files(project_dir, main_file)

transformer = KconfigTransformer(source_spec="ZRTOS")
transformer._get_all_source_files()