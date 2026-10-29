import pandas
import rapidfuzz

import patient_record_deduplication


def test_project_package_imports():
    assert patient_record_deduplication.__doc__ is not None


def test_required_libraries_are_available():
    assert pandas.__name__ == "pandas"
    assert rapidfuzz.__name__ == "rapidfuzz"
