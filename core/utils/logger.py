import pprint
class Logger:

    def start(self, project_dir: str, main_file: str, output_dir: str, parser, spec_version: str):
        print("=" * 100)
        print("TRANSFORMATION PROTOTYP LOG")
        print("=" * 100)
        print(f"    Root: {project_dir}")
        print(f"    Main file: {main_file}")
        print(f"    Output dir: {output_dir}")
        print(f"    Specification Version: {spec_version}")
        print(f"    Parser obj: {parser}")
        print("=" * 100)

    def print_parser_result(self, parser_result: dict):
        pprint.pprint(parser_result)
        print("-" * 50)
        print(f"   Parser found: {len(parser_result['defined_syms'])} defined syms")
        print(f"   Parser found: {len(parser_result['unique_defined_syms'])} unique defined syms")
        print(f"   Parser found: {len(parser_result['kconf'].kconfig_filenames)} files")
        print("-" * 50)