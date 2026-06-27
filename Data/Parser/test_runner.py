"""
Parser Test Runner

Iterative test harness for developing the PlantUML parser against the dataset.
Supports stop-on-failure mode for debugging and full-run mode for validation.

Usage:
    # Run from command line
    python -m Data.Parser.test_runner

    # Or use programmatically
    from Data.Parser import PlantUMLParser, ParserTestRunner

    parser = PlantUMLParser(strict=True)
    runner = ParserTestRunner(parser)
    report = runner.run_all(stop_on_failure=True)
    report.print_summary()
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Iterator, Tuple, List

from .parser import PlantUMLParser
from .models import ParsedModel
from .test_report import TestResult, TestReport


# Resolve dataset path relative to project root
PARSER_DIR = Path(__file__).parent
DUMMY_METRIC_DIR = PARSER_DIR.parent
TESTING_METRICS_DIR = DUMMY_METRIC_DIR.parent
PROJECT_ROOT = TESTING_METRICS_DIR.parent
DEFAULT_DATASET_PATH = PROJECT_ROOT / "Dataset" / "combined-data.json"


class ParserTestRunner:
    """
    Test runner that iterates through all PlantUML strings in the dataset.

    The runner loads the dataset, extracts all PlantUML strings (both reference
    and generated), and runs the parser on each. Results are collected into
    a TestReport for analysis.

    Attributes:
        parser: The PlantUML parser instance to test.
        dataset_path: Path to the combined-data.json file.
    """

    # Settings/prompting strategies
    SETTINGS = ['0shot', '1shot_BTMS', '1shot_H2S', '2shots', 'CoT']

    def __init__(
        self,
        parser: Optional[PlantUMLParser] = None,
        dataset_path: Optional[str] = None
    ):
        """
        Initialize the test runner.

        Args:
            parser: PlantUML parser to test. Defaults to strict parser.
            dataset_path: Path to dataset JSON. Defaults to standard location.
        """
        self.parser = parser or PlantUMLParser(strict=True)
        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
        self._dataset: Optional[dict] = None

    def _load_dataset(self) -> dict:
        """Load and cache the dataset."""
        if self._dataset is None:
            if not self.dataset_path.exists():
                raise FileNotFoundError(f"Dataset not found at: {self.dataset_path}")

            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                self._dataset = json.load(f)

        return self._dataset

    def iter_plantuml_strings(self) -> Iterator[Tuple[str, str, str, bool]]:
        """
        Iterate through all PlantUML strings in the dataset.

        Yields tuples of:
            (model_key, setting, plantuml_string, is_reference)

        For reference models, setting is 'reference'.
        """
        dataset = self._load_dataset()
        models = dataset.get('models', {})

        for model_key, model_data in models.items():
            # Yield reference model
            reference_uml = model_data.get('reference_plantuml', '')
            if reference_uml:
                yield (model_key, 'reference', reference_uml, True)

            # Yield generated models for each setting
            generated = model_data.get('generated_plantuml', {})
            for setting in self.SETTINGS:
                gen_uml = generated.get(setting, '')
                if gen_uml:
                    yield (model_key, setting, gen_uml, False)

    def run_single(
        self,
        model_key: str,
        setting: str,
        plantuml_string: str,
        is_reference: bool
    ) -> TestResult:
        """
        Run the parser on a single PlantUML string.

        Args:
            model_key: Model identifier (e.g., "LabTracker")
            setting: Setting identifier (e.g., "0shot" or "reference")
            plantuml_string: The PlantUML string to parse
            is_reference: True if this is a reference model

        Returns:
            TestResult with success/failure status and details.
        """
        comparison_id = f"{model_key}_{setting}"

        try:
            model = self.parser.parse(plantuml_string)

            return TestResult(
                model_key=model_key,
                setting=setting,
                comparison_id=comparison_id,
                success=True,
                is_reference=is_reference,
                num_classes=len(model.classes),
                num_enums=len(model.enums),
                num_relationships=len(model.relationships),
                num_implicit_classes=len(model.implicit_classes),
            )

        except ValueError as e:
            # Parse the error message to extract line info
            error_msg = str(e)
            line_number = None
            failed_line = None
            context_lines = []

            # Try to extract line number from error message
            line_match = re.search(r'line (\d+)', error_msg)
            if line_match:
                line_number = int(line_match.group(1))

            # Try to extract the failed line content
            quote_match = re.search(r"'([^']*)'", error_msg)
            if quote_match:
                failed_line = quote_match.group(1)

            # Extract context lines if present
            if 'Context:' in error_msg:
                context_part = error_msg.split('Context:')[1]
                context_lines = [
                    line.strip()
                    for line in context_part.strip().split('\n')
                    if line.strip()
                ]

            return TestResult(
                model_key=model_key,
                setting=setting,
                comparison_id=comparison_id,
                success=False,
                is_reference=is_reference,
                error_type='ValueError',
                error_message=error_msg.split('\n')[0],  # First line only
                failed_line=failed_line,
                line_number=line_number,
                context_lines=context_lines,
            )

        except Exception as e:
            return TestResult(
                model_key=model_key,
                setting=setting,
                comparison_id=comparison_id,
                success=False,
                is_reference=is_reference,
                error_type=type(e).__name__,
                error_message=str(e),
            )

    def run_all(self, stop_on_failure: bool = True, verbose: bool = False) -> TestReport:
        """
        Run the parser against all PlantUML strings in the dataset.

        Args:
            stop_on_failure: If True, stop at the first failure for debugging.
            verbose: If True, print progress for each test.

        Returns:
            TestReport with results for all (or some if stopped) tests.
        """
        report = TestReport()

        for model_key, setting, uml_string, is_reference in self.iter_plantuml_strings():
            result = self.run_single(model_key, setting, uml_string, is_reference)
            report.add_result(result)

            if verbose:
                status = "PASS" if result.success else "FAIL"
                print(f"[{status}] {result.comparison_id}")

            if not result.success and stop_on_failure:
                report.stopped_early = True
                break

        return report

    def run_references_only(self, stop_on_failure: bool = True) -> TestReport:
        """
        Run the parser only on reference models (faster for initial testing).

        Args:
            stop_on_failure: If True, stop at the first failure.

        Returns:
            TestReport for reference models only.
        """
        report = TestReport()

        for model_key, setting, uml_string, is_reference in self.iter_plantuml_strings():
            if not is_reference:
                continue

            result = self.run_single(model_key, setting, uml_string, is_reference)
            report.add_result(result)

            if not result.success and stop_on_failure:
                report.stopped_early = True
                break

        return report

    def run_specific(self, model_key: str, setting: str = 'reference') -> TestResult:
        """
        Run the parser on a specific model/setting combination.

        Useful for debugging a particular failure.

        Args:
            model_key: Model identifier (e.g., "LabTracker")
            setting: Setting identifier (e.g., "0shot", "reference")

        Returns:
            TestResult for the specified combination.

        Raises:
            ValueError: If the model/setting combination is not found.
        """
        dataset = self._load_dataset()
        models = dataset.get('models', {})

        if model_key not in models:
            raise ValueError(f"Model '{model_key}' not found in dataset")

        model_data = models[model_key]

        if setting == 'reference':
            uml_string = model_data.get('reference_plantuml', '')
            is_reference = True
        else:
            uml_string = model_data.get('generated_plantuml', {}).get(setting, '')
            is_reference = False

        if not uml_string:
            raise ValueError(f"No PlantUML string found for {model_key}/{setting}")

        return self.run_single(model_key, setting, uml_string, is_reference)

    def get_model_keys(self) -> List[str]:
        """Get list of all model keys in the dataset."""
        dataset = self._load_dataset()
        return list(dataset.get('models', {}).keys())

    def count_total_strings(self) -> int:
        """Count total number of PlantUML strings to process."""
        count = 0
        for _ in self.iter_plantuml_strings():
            count += 1
        return count


def main():
    """Command-line entry point for the test runner."""
    import argparse

    arg_parser = argparse.ArgumentParser(
        description='Run PlantUML parser against dataset'
    )
    arg_parser.add_argument(
        '--no-stop',
        action='store_true',
        help='Continue on failure instead of stopping'
    )
    arg_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print progress for each test'
    )
    arg_parser.add_argument(
        '--references-only',
        action='store_true',
        help='Only test reference models (faster)'
    )
    arg_parser.add_argument(
        '--model',
        type=str,
        help='Test a specific model only'
    )
    arg_parser.add_argument(
        '--setting',
        type=str,
        default='reference',
        help='Test a specific setting (with --model)'
    )
    arg_parser.add_argument(
        '--save-report',
        type=str,
        help='Save report to JSON file'
    )

    args = arg_parser.parse_args()

    # Create parser and runner
    parser = PlantUMLParser(strict=True)
    runner = ParserTestRunner(parser)

    # Run tests based on arguments
    if args.model:
        # Test specific model
        print(f"\nTesting: {args.model}/{args.setting}")
        result = runner.run_specific(args.model, args.setting)
        print(result.detailed_report())
        sys.exit(0 if result.success else 1)

    elif args.references_only:
        # Test reference models only
        print("\nTesting reference models only...")
        report = runner.run_references_only(stop_on_failure=not args.no_stop)

    else:
        # Test all models
        total = runner.count_total_strings()
        print(f"\nTesting {total} PlantUML strings...")
        report = runner.run_all(
            stop_on_failure=not args.no_stop,
            verbose=args.verbose
        )

    # Print summary
    report.print_summary()

    # Save report if requested
    if args.save_report:
        report.save_json(args.save_report)

    # Exit with appropriate code
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == '__main__':
    main()
