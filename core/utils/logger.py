import pprint
class Logger:

    def start(project_dir: str, main_file: str, output_dir: str, parser):
        print("=" * 100)
        print("TRANSFORMATION PROTOTYP LOG")
        print("=" * 100)
        print(f"    Root: {project_dir}")
        print(f"    Main file: {main_file}")
        print(f"    Output dir: {output_dir}")
        print(parser)
        print("=" * 100)

    def print_parser_result(parser_result: dict):
        pprint.pprint(parser_result)
        print("-" * 50)
        print(f"   Parser found: {len(parser_result['defined_syms'])} defined syms")
        print(f"   Parser found: {len(parser_result['unique_defined_syms'])} unique defined syms")
        print(f"   Parser found: {len(parser_result['kconf'].kconfig_filenames)} files")
        print("-" * 50)