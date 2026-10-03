from pathlib import Path
from core.pick_parser import PickParser
from core.parser.zrtos_parser import ZRTOSParser
from core.kconfig_writer import KconfigReader, KconfigWriter
from core.transform_prototyp import KconfigTransformer
from core.utils.time_writer import TransformTimer
from core.utils.logger import Logger
from core.utils.cli_helper import ExitCode, WorkflowRunnerHelper                    
import os
import sys

def main():
    setup_helper = WorkflowRunnerHelper()
    logger = Logger()

    # 1. Parse & validate CLI or environment parameters
    project_dir, output_dir, main_file, log_file, spec_version = setup_helper.parse_and_validate()

    # 2. Configure environment & activate logging redirection
    os.environ["srctree"] = project_dir
    setup_helper.redirect_stdout_to_log(log_file)

    try:
            reader = KconfigReader(spec_version)
            writer = KconfigWriter(spec_version)
            timer = TransformTimer()
            
            # PickParser as Factory 
            parser = PickParser(spec_version).get_parser()
            timer.lap("Parser initialization")  
            logger.start(project_dir, main_file, output_dir, parser, spec_version)

            # File Parsing
            print("1. Parser output: ")
            parser_result = parser.parse_files(project_dir, main_file)
            timer.lap("Got parser results")
            logger.print_parser_result(parser_result)

            # Transformation Context Build 
            transformer = KconfigTransformer(spec_version, parser_result)
            timer.lap("Built context from parser results")

            # Transform Files (aka Specifications) 
            excel_log_path = str(Path(output_dir) / "results.xlsx")
            generate_excel_report = False

            transformer.transform_all_files(
                reader=reader,
                writer=writer,
                project_dir=Path(project_dir),
                output_dir=Path(output_dir),
                log=True,
                log_lines=False,
                log_and_check_resolve_glob=False,
                log_cd_nc_details=True,
                log_excel_after_each_file=generate_excel_report,
                log_excel_output=excel_log_path,
            )

            timer.lap("File transformation and excel log")
            timer.stop()

            # Success-JSON-Response & Prozess end
            setup_helper.send_json_response(
                success=True,
                status_code=ExitCode.SUCCESS,
                message="Kconfig transformation completed successfully.",
                data={
                    "project_dir": project_dir,
                    "output_dir": output_dir,
                    "spec_version": spec_version,
                    "log_file": log_file,
                    **({"excel_report": excel_log_path} if generate_excel_report else {})
                },
            )

    except Exception as e:
        # catch unexpected errors and send JSON-Response
        setup_helper.send_json_response(
            success=False,
            status_code=ExitCode.TRANSFORM_ERROR,
            message="An error occurred during Kconfig transformation.",
            error_details={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )


if __name__ == "__main__":
    main()
