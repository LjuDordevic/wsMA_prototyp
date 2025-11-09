from pathlib import Path
from pick_parser import PickParser
from zrtos_parser import ZRTOSParser
from kconfig_writer import KconfigReader, KconfigWriter
from transform_prototyp import KconfigTransformer
import pprint

project_dir = "/home/ljd/wsMA_prototyp/exp"
output_dir = "/home/ljd/wsMA_prototyp/exp_copy"
main_file = "KconfigZephyrRTOS"

picker = PickParser("ZRTOS")
print(picker)
print("-" * 50)

#picker._test_kconfiglib(project_dir, main_file)
#result = picker._parse_only(project_dir, main_file)

print("1.  Parser Output: ")
parser = ZRTOSParser(picker.kconfiglib_version)
parser_result = parser.parse_files(project_dir, main_file)
pprint.pprint(parser_result)
print("-" * 50)
print(f"   Parser found: {len(parser_result['defined_syms'])} defined syms")
print(f"   Parser found: {len(parser_result['unique_defined_syms'])} unique defined syms")
print(f"   Parser found: {len(parser_result['kconf'].kconfig_filenames)} files")
print("-" * 50)

transformer = KconfigTransformer("ZRTOS")
print("\n2. Bild TransformationContext FROM PARSER RESULTS")
print(f" Transformer used for: {transformer.source_spec}")
context = transformer.build_context_from_parser(
    parser_result
)
print(f" TransformationContext - configs: {len(context.symbol_definitions)}({', '.join(context.symbol_definitions.keys())})")
print(f" TransformationContext - configdefaults: {len(context.configdefault_symbols)}({', '.join(context.configdefault_symbols)})")
print("look at TransformationContext")

for sym_name, definitions in context.symbol_definitions.items():
    if len(definitions) >= 1:
        print(f"   '{sym_name}' is defined x{len(definitions)}")
        for defn in definitions:
            is_default = defn.get('is_configdefault', False)
            default_tag = " (as configdefault)" if is_default else ""
            file = defn.get('file') or "<unknown file>"
            line = defn.get('line') or "<unknown line>"
            print(f"     - {file}:{line}{default_tag}")