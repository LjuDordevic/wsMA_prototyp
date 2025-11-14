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

transformer = KconfigTransformer(source_spec="ZRTOS")
print("\n2. Bild ExParserContext FROM PARSER RESULTS")
print(f" Transformer used for: {transformer.source_spec}")
context = transformer.build_context_from_parser(
    parser_result
)
print(f"\n")
print(f" ExParserContext - symbols: {len(context.symbol_definitions)} ({', '.join(context.symbol_definitions.keys())})")
print(f" ExParserContext - configdefaults: {len(context.configdefault_symbols)} ({', '.join(context.configdefault_symbols)})")
print(f"\n look at ExParserContext: ")

for sym_name, definitions in context.symbol_definitions.items():
    if len(definitions) >= 1:
        print(f"   '{sym_name}' is defined x{len(definitions)}")
        for defn in definitions:
            is_default = defn.get('is_configdefault', False)
            default_tag = " (as configdefault)" if is_default else ""
            file = defn.get('file') or "<unknown file>"
            line = defn.get('line') or "<unknown line>"
            print(f"     - {file}:{line}{default_tag}")
""" 
default_line_nr = []
for sym_name, default_info in context.symbol_defaults.items():
    if sym_name == "FOO":
        for result in default_info:
            result_tupel = result[2]
            default_line_nr.append(result_tupel)
print("here")
print(default_line_nr)
"""
#print("filter ------------------------------------------------------")
#results = transformer.extract_symbol_info(context, 'FOO')
#for symbol_name, location, deps in results:
#    print(f"{symbol_name}, {location}, ({', '.join(deps)})")
print("filter ------------------------------------------------------")
info = transformer.extract_symbol_info(context, 'FOO')
for sn, file, line in info['sym_def']:
    print(f"{sn}, {file}, {line}")
print("\n")
for sn, def_loc, def_dep in info['def_dep']:
    print(f"{sn}, {def_loc}, ({', '.join(def_dep)})")
print("filter ------------------------------------------------------")

reader = KconfigReader("ZRTOS")
writer = KconfigWriter("ZRTOS")
input_file = Path(project_dir) / main_file
output_file = Path(output_dir) / main_file

print(f"\n3. Transform - needs reader & writer")
""" 
lines = reader.read_file(input_file)
for line in lines:
            print(f"  {line}")
            if line.line_type != 'empty' and line.line_type != 'other':
                print(f"    → Content: {line.content}")

print(f"\n4.  give these reader lines to transformer")
transformed_lines = transformer._transform_lines(lines, input_file)

print(f"\n5.  call writer - write transformed lines in {output_file}")
writer.write(transformed_lines, output_file)
"""
#transformer.get_all_source_files()
 
print(f"\n6. Transform all files")

transformer.transform_all_files(
    reader=reader,
    writer=writer,
    project_dir=Path(project_dir),
    output_dir=Path(output_dir),
    log=True
)
