import argparse
import json
import os
import sys
from enum import IntEnum
from pathlib import Path
from dotenv import load_dotenv

class ExitCode(IntEnum):
    """Standardized exit codes for process status signaling."""

    SUCCESS = 0
    INVALID_ARGS = 2
    FILE_NOT_FOUND = 3
    TRANSFORM_ERROR = 5
    UNEXPECTED_ERROR = 99

class WorkflowRunnerHelper:
    """Helper class for CLI parsing, logging redirection, and JSON response handling."""

    VALID_SPEC_VERSIONS = {"ZKCL", "ZRTOS", "ESPIDF"}

    def __init__(self, description: str = "Kconfig Workflow Transformation"):
        load_dotenv()
        self.parser = argparse.ArgumentParser(description=description)
        self._setup_args()
        self.log_file_handle = None

    def _setup_args(self):
        """Define CLI arguments with fallbacks to environment variables."""
        self.parser.add_argument(
            "--project-dir",
            default=os.getenv("PROJECT_DIR"),
            help="Path to the project directory",
        )
        self.parser.add_argument(
            "--output-dir",
            default=os.getenv("OUTPUT_DIR"),
            help="Path to the output directory",
        )
        self.parser.add_argument(
            "--log-file",
            default=os.getenv("LOG_FILE"),
            help="Path to the log file (optional)",
        )
        self.parser.add_argument(
            "--main-file",
            default="Kconfig",
            help="Main entry file name (default: Kconfig)",
        )
        self.parser.add_argument(
            "--spec-version",
            default=os.getenv("SPEC_VERSION", "ZRTOS"),
            help="Specification version (options: sZKCL, ZRTOS, ESPIDF; default: ZRTOS)(specification = Kconfig file)",
        )

    def parse_and_validate(self) -> tuple[str, str, str, str, str]:
        """Parse CLI arguments, validate paths, and return normalized parameters."""
        try:
            args = self.parser.parse_args()
        except SystemExit:
            self.send_json_response(
                success=False,
                status_code=ExitCode.INVALID_ARGS,
                message="Invalid CLI arguments provided.",
            )

        if not args.project_dir or not args.output_dir or not args.spec_version:
            self.send_json_response(
                success=False,
                status_code=ExitCode.INVALID_ARGS,
                message="Missing required parameters: --project-dir and --output-dir and --spec-version are required.",
            )

        project_dir = args.project_dir
        output_dir = args.output_dir
        main_file = args.main_file
        spec_version = args.spec_version.upper()
        log_file = args.log_file or str(Path(output_dir) / "transform.log")

        if spec_version not in self.VALID_SPEC_VERSIONS:
            self.send_json_response(
                success=False,
                status_code=ExitCode.INVALID_ARGS,
                message=f"Invalid --spec-version: '{args.spec_version}'. Allowed values are: {', '.join(sorted(self.VALID_SPEC_VERSIONS))}.",
            )

        if not os.path.exists(project_dir):
            self.send_json_response(
                success=False,
                status_code=ExitCode.FILE_NOT_FOUND,
                message="Project directory does not exist.",
                error_details={"project_dir": project_dir},
            )

        # Ensure target directory exists
        os.makedirs(output_dir, exist_ok=True)
        return project_dir, output_dir, main_file, log_file, spec_version

    def redirect_stdout_to_log(self, log_file: str):
        """Redirect standard print/log outputs to the log file while keeping STDOUT clean for JSON."""
        self.log_file_handle = open(log_file, "w")
        sys.stdout = self.log_file_handle
        sys.stderr = self.log_file_handle

    def close_log(self):
        """Safely close the log file handle if active."""
        if self.log_file_handle and not self.log_file_handle.closed:
            self.log_file_handle.close()

    def send_json_response(
        self,
        success: bool,
        status_code: int,
        message: str,
        data: dict = None,
        error_details: dict = None,
    ):
        """Output the structured result as JSON to STDOUT and terminate the process with the matching exit code."""
        self.close_log()

        response = {
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": data or {},
            "error": error_details or {},
        }
        # Print directly to original stdout (bypassing file redirection)
        print(json.dumps(response, indent=2), file=sys.__stdout__)
        sys.exit(status_code)