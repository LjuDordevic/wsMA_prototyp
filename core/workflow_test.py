from pathlib import Path
from pick_parser import PickParser
from zrtos_parser import ZRTOSParser
from kconfig_writer import KconfigReader, KconfigWriter
from transform_prototyp import KconfigTransformer
import pprint

project_dir = "/home/ljd/wsMA_prototyp/exp" #"/home/ljd/wsMA_prototyp/exp_conf_def/"       
output_dir = "/home/ljd/wsMA_prototyp/exp_copy" #"/home/ljd/wsMA_prototyp/exp_conf_def_copy/"   
main_file =  "KconfigZephyrRTOS" #"Kconfig"                                      

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
print("\n2. Bild ExtParserContext FROM PARSER RESULTS")
print(f" Transformer used: {transformer.source_spec}")

context = transformer.build_context_from_parser(
    parser_result,
    log=True
)

""" 
print("filter: symbol definitions & each sym.node.defaults extracted ---------------------------------------------------------------")
info = transformer.extract_symbol_info(context, 'FOO')
for sn, file, line, cf_flag, extr_nd in info['sym_def']:
    print(f"{sn}, {file}, {line}, {cf_flag}, {extr_nd}")
print("\n")
print("filter: default definitions of symbol (loc & complete list for if cond) ------------------------------------------------------")
for sn, def_loc, def_dep in info['def_dep']:
    print(f"{sn}, {def_loc}, ({', '.join(def_dep)})")

print(f"\n - last conf")
last_conf = transformer._get_last_config(info['sym_def'])
print(last_conf)

print(f"\n - configdefault entries")
cd_default_entries = transformer._get_cd_entries(info['sym_def'])
print(cd_default_entries)
print(f"\n - transform cd entries")
tcd = transformer._get_transformed_config_defaults(cd_default_entries, reader, project_dir)
print(tcd)
"""
reader = KconfigReader("ZRTOS")
writer = KconfigWriter("ZRTOS")
input_file = Path(project_dir) / main_file
output_file = Path(output_dir) / main_file


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

transformer.transform_all_files(
    reader=reader,
    writer=writer,
    project_dir=Path(project_dir),
    output_dir=Path(output_dir),
    log=True,
    log_lines=False
)
