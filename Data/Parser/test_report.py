"""
Test Report Module

Provides data classes and utilities for tracking and reporting parser test results.
Designed for the iterative development workflow where failures need detailed context.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime


@dataclass
class TestResult:
    """
    Result of parsing a single PlantUML string.

    Contains both success/failure status and detailed error information
    for debugging when parsing fails.
    """
    # Identification
    model_key: str          # e.g., "LabTracker"
    setting: str            # e.g., "0shot", "reference"
    comparison_id: str      # e.g., "LabTracker_0shot"

    # Status
    success: bool
    is_reference: bool      # True if this is a reference model

    # Error information (populated on failure)
    error_type: Optional[str] = None      # Exception type name
    error_message: Optional[str] = None   # Exception message
    failed_line: Optional[str] = None     # The line that caused the error
    line_number: Optional[int] = None     # Line number in source
    context_lines: List[str] = field(default_factory=list)  # Surrounding lines

    # Success information (populated on success)
    num_classes: int = 0
    num_enums: int = 0
    num_relationships: int = 0
    num_implicit_classes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def short_description(self) -> str:
        """Return a brief description of the result."""
        if self.success:
            return (
                f"[PASS] {self.comparison_id}: "
                f"{self.num_classes} classes, {self.num_enums} enums, "
                f"{self.num_relationships} relationships"
            )
        else:
            return f"[FAIL] {self.comparison_id}: {self.error_type}: {self.error_message}"

    def detailed_report(self) -> str:
        """Return a detailed report of the result."""
        lines = [
            f"{'=' * 60}",
            f"Test Result: {self.comparison_id}",
            f"{'=' * 60}",
            f"Model: {self.model_key}",
            f"Setting: {self.setting}",
            f"Is Reference: {self.is_reference}",
            f"Status: {'PASS' if self.success else 'FAIL'}",
        ]

        if self.success:
            lines.extend([
                f"",
                f"Parsed Elements:",
                f"  - Classes: {self.num_classes}",
                f"  - Enums: {self.num_enums}",
                f"  - Relationships: {self.num_relationships}",
                f"  - Implicit Classes: {self.num_implicit_classes}",
            ])
        else:
            lines.extend([
                f"",
                f"Error Type: {self.error_type}",
                f"Error Message: {self.error_message}",
            ])
            if self.line_number:
                lines.append(f"Line Number: {self.line_number}")
            if self.failed_line:
                lines.append(f"Failed Line: '{self.failed_line}'")
            if self.context_lines:
                lines.append(f"")
                lines.append(f"Context:")
                for ctx_line in self.context_lines:
                    lines.append(f"  {ctx_line}")

        lines.append(f"{'=' * 60}")
        return '\n'.join(lines)


@dataclass
class TestReport:
    """
    Complete report of running the parser against multiple PlantUML strings.

    Provides summary statistics and detailed failure analysis.
    """
    # Summary counts
    total: int = 0
    passed: int = 0
    failed: int = 0

    # Detailed results
    results: List[TestResult] = field(default_factory=list)

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    parser_version: str = "1.0.0"
    stopped_early: bool = False  # True if stopped on first failure

    @property
    def first_failure(self) -> Optional[TestResult]:
        """Get the first failed result, if any."""
        for result in self.results:
            if not result.success:
                return result
        return None

    @property
    def all_failures(self) -> List[TestResult]:
        """Get all failed results."""
        return [r for r in self.results if not r.success]

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    def add_result(self, result: TestResult) -> None:
        """Add a test result to the report."""
        self.results.append(result)
        self.total += 1
        if result.success:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self) -> None:
        """Print summary to console."""
        print(f"\n{'=' * 60}")
        print(f"Parser Test Report")
        print(f"{'=' * 60}")
        print(f"Timestamp: {self.timestamp}")
        print(f"Total Tests: {self.total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {self.success_rate:.1f}%")

        if self.stopped_early:
            print(f"\n[!] Testing stopped early on first failure")

        if self.failed > 0:
            print(f"\n--- First Failure ---")
            first = self.first_failure
            if first:
                print(first.detailed_report())

        print(f"{'=' * 60}\n")

    def print_all_failures(self) -> None:
        """Print detailed reports for all failures."""
        failures = self.all_failures
        if not failures:
            print("No failures to report.")
            return

        print(f"\n{'=' * 60}")
        print(f"All Failures ({len(failures)} total)")
        print(f"{'=' * 60}\n")

        for failure in failures:
            print(failure.detailed_report())
            print()

    def get_failure_patterns(self) -> Dict[str, int]:
        """
        Analyze failure patterns to identify common issues.

        Returns a dictionary mapping error types to counts.
        """
        patterns: Dict[str, int] = {}

        for result in self.results:
            if not result.success and result.error_type:
                key = result.error_type
                patterns[key] = patterns.get(key, 0) + 1

        return dict(sorted(patterns.items(), key=lambda x: -x[1]))

    def get_failures_by_model(self) -> Dict[str, List[TestResult]]:
        """Group failures by model key."""
        by_model: Dict[str, List[TestResult]] = {}

        for result in self.results:
            if not result.success:
                if result.model_key not in by_model:
                    by_model[result.model_key] = []
                by_model[result.model_key].append(result)

        return by_model

    def get_failures_by_setting(self) -> Dict[str, List[TestResult]]:
        """Group failures by setting."""
        by_setting: Dict[str, List[TestResult]] = {}

        for result in self.results:
            if not result.success:
                if result.setting not in by_setting:
                    by_setting[result.setting] = []
                by_setting[result.setting].append(result)

        return by_setting

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'parser_version': self.parser_version,
            'summary': {
                'total': self.total,
                'passed': self.passed,
                'failed': self.failed,
                'success_rate': self.success_rate,
                'stopped_early': self.stopped_early,
            },
            'results': [r.to_dict() for r in self.results],
            'failure_patterns': self.get_failure_patterns(),
        }

    def save_json(self, path: str) -> None:
        """Save detailed report as JSON file."""
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"Report saved to: {filepath}")

    @classmethod
    def load_json(cls, path: str) -> 'TestReport':
        """Load a report from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        report = cls()
        report.timestamp = data.get('timestamp', '')
        report.parser_version = data.get('parser_version', '')
        report.stopped_early = data.get('summary', {}).get('stopped_early', False)

        for result_data in data.get('results', []):
            result = TestResult(
                model_key=result_data['model_key'],
                setting=result_data['setting'],
                comparison_id=result_data['comparison_id'],
                success=result_data['success'],
                is_reference=result_data['is_reference'],
                error_type=result_data.get('error_type'),
                error_message=result_data.get('error_message'),
                failed_line=result_data.get('failed_line'),
                line_number=result_data.get('line_number'),
                context_lines=result_data.get('context_lines', []),
                num_classes=result_data.get('num_classes', 0),
                num_enums=result_data.get('num_enums', 0),
                num_relationships=result_data.get('num_relationships', 0),
                num_implicit_classes=result_data.get('num_implicit_classes', 0),
            )
            report.add_result(result)

        return report
