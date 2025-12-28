from pathlib import Path
from pick_parser import PickParser
from zrtos_parser import ZRTOSParser
from kconfig_writer import KconfigReader, KconfigWriter
from transform_prototyp import KconfigTransformer
import pprint
import os
import sys

#project_dir = "/home/ljd/wsMA_prototyp/exp" 
#output_dir = "/home/ljd/wsMA_prototyp/exp_copy"   
#main_file =  "KconfigZephyrRTOS"                                   
#project_dir = "/home/ljd/wsMA_prototyp/test_dir_old/exp_conf_def/"       
#output_dir = "/home/ljd/wsMA_prototyp/test_dir_old/exp_conf_def_copy/"   
#main_file =  "Kconfig"  
#project_dir = "/home/ljd/wsMA_prototyp/expr_zrtos/zephyr/"  # old 
#project_dir = "/home/ljd/wsMA_prototyp/ZRTOS_demo/zephyr"   # documented  
#output_dir = "/home/ljd/wsMA_prototyp/ZRTOS_copy/"   
#project_dir = "/home/ljd/wsMA_prototyp/test_dir_old/exp_A"       
#output_dir = "/home/ljd/wsMA_prototyp/test_dir_old/exp_B"   
#picker._test_kconfiglib(project_dir, main_file)
#result = picker._parse_only(project_dir, main_file)
#transformer.extract_named_choice_info("NAMED_CH")

def main():

    #log_file = "/home/ljd/wsMA_prototyp/test_dir_/test_glob/test_glob.log"
    #log_file="/home/ljd/wsMA_prototyp/test_dir_/transform_source_output/transform_log_resolve_steps.log"
    #project_dir = "/home/ljd/wsMA_prototyp/test_dir_/transform_source"       
    #output_dir = "/home/ljd/wsMA_prototyp/test_dir_/test_glob"  

    #log_file = "/home/ljd/wsMA_prototyp/test_dir_/transform_source_output/transform.log"
    #project_dir = "/home/ljd/wsMA_prototyp/test_dir_/transform_source"       
    #output_dir = "/home/ljd/wsMA_prototyp/test_dir_/transform_source_output"  

    #log_file = "/home/ljd/wsMA_prototyp/test_dir_/transform_def_output/transform.log"
    #project_dir = "/home/ljd/wsMA_prototyp/test_dir_/transform_def"       
    #output_dir = "/home/ljd/wsMA_prototyp/test_dir_/transform_def_output"  

    #log_file="/home/ljd/wsMA_prototyp/test_dir_/transform_option_output/transform.log"
    #project_dir = "/home/ljd/wsMA_prototyp/test_dir_/transform_option"       
    #output_dir = "/home/ljd/wsMA_prototyp/test_dir_/transform_option_output"  
    #os.environ["ENV_A"] = "i7-1260P"

    #log_file="/home/ljd/wsMA_prototyp/test_dir_/transform_choice_output/transform.log"
    #project_dir="/home/ljd/wsMA_prototyp/test_dir_/transform_choice"
    #output_dir="/home/ljd/wsMA_prototyp/test_dir_/transform_choice_output"

    log_file="/home/ljd/wsMA_prototyp/test_dir_/transform_configdefault_output/transform.log"
    project_dir="/home/ljd/wsMA_prototyp/test_dir_/transform_configdefault"
    output_dir="/home/ljd/wsMA_prototyp/test_dir_/transform_configdefault_output"
    
    main_file = "Kconfig"  
    os.environ["srctree"] = project_dir
    
    sys.stdout = open(log_file, "w")
    sys.stderr = sys.stdout 
    print("=" * 100)
    print("TRNASFORMATION PROTOTYP LOG")
    print("=" * 100)
    print(f"    Root: {project_dir}")
    print(f"    Main file: {main_file}")
    print(f"    Output dir: {output_dir}")
    print("=" * 100)

    picker = PickParser("ZRTOS")
    print(picker)

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
    
    #info = transformer.extract_named_choice_info('NAMED_CH')
    """ print("choice definition ------------------------------------------------------")
    for cn, file, line, node in info['choice_def']:
        print(f"{cn}, {file}, {line}, {node}")
    print("\n")"""

    reader = KconfigReader("ZRTOS")
    writer = KconfigWriter("ZRTOS")
    #input_file = Path(project_dir) / main_file
    #output_file = Path(output_dir) / main_file

    transformer.transform_all_files(
        reader=reader,
        writer=writer,
        project_dir=Path(project_dir),
        output_dir=Path(output_dir),
        log=True,
        log_lines=False,
        log_and_check_resolve_glob=False,
        log_excel_after_each_file=False,
        log_excel_output="/home/ljd/wsMA_prototyp/results.xlsx"
    )    

    return 0

if __name__ == '__main__':
    sys.exit(main())

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
