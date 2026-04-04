#!/usr/bin/env python

"""Tests that all example backends in example/backend/
produce the corresponding output in example/output/<backend>/."""

import importlib.util
import tempfile
import unittest
import sys
from pathlib import Path

from stone.compiler import Compiler
from stone.frontend.frontend import specs_to_ir

_REPO_DIR = Path(__file__).resolve().parent.parent
_EXAMPLE_DIR = _REPO_DIR / 'example'
_SPEC_DIR = _EXAMPLE_DIR / 'api'
_BACKEND_DIR = _EXAMPLE_DIR / 'backend'
_OUTPUT_DIR = _EXAMPLE_DIR / 'output'


def _load_specs():
    """Read all .stone files from the example spec directory."""
    specs = []
    for path in sorted(_SPEC_DIR.glob('*.stone')):
        with open(path, encoding='utf-8') as f:
            specs.append((str(path), f.read()))
    return specs


_SPECS = _load_specs()
_API = specs_to_ir(_SPECS)


def _load_backend_module(backend_name: str):
    """Dynamically import a .stoneg.py backend module with safe sys.path handling."""
    stoneg_path = _BACKEND_DIR / f'{backend_name}.stoneg.py'

    if not stoneg_path.is_file():
        raise FileNotFoundError(f"Backend file not found: {stoneg_path}")

    backend_dir = str(stoneg_path.parent)

    added = False
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
        added = True

    try:
        module_name = f'backend_{backend_name}'
        spec = importlib.util.spec_from_file_location(module_name, stoneg_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if added and backend_dir in sys.path:
            sys.path.remove(backend_dir)


def _run_backend(backend_name: str, output_dir: str):
    """Run the named backend into output_dir using the shared API."""
    backend_module = _load_backend_module(backend_name)
    compiler = Compiler(_API, backend_module, [], output_dir)
    compiler.build()


def _assert_output_matches_fixtures(test_case, backend_name: str, output_dir: str):
    """Compare every file in output_dir against the expected fixtures."""
    expected_dir = _OUTPUT_DIR / backend_name
    output_path = Path(output_dir)

    if not expected_dir.is_dir():
        test_case.fail(f"Expected output directory missing: {expected_dir}")

    expected_files = sorted(p.name for p in expected_dir.iterdir() if p.is_file())
    actual_files = sorted(p.name for p in output_path.iterdir() if p.is_file())

    test_case.assertEqual(
        actual_files, expected_files,
        f'Output files for {backend_name} do not match expected set'
    )

    for filename in expected_files:
        expected = (expected_dir / filename).read_text(encoding='utf-8')
        actual = (output_path / filename).read_text(encoding='utf-8')
        test_case.assertEqual(
            actual, expected,
            f'{backend_name}/{filename} output does not match fixture'
        )


class TestExampleBackends(unittest.TestCase):

    def _run_and_compare(self, backend_name: str):
        """Run backend and compare output against example output."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            _run_backend(backend_name, tmp_dir)
            _assert_output_matches_fixtures(self, backend_name, tmp_dir)

    def test_ex1(self):
        """ex1 backend output should match example files."""
        self._run_and_compare('ex1')

    def test_ex2(self):
        """ex2 backend output should match example files."""
        self._run_and_compare('ex2')

    def test_ex3(self):
        """ex3 backend output should match example files."""
        self._run_and_compare('ex3')

    def test_unstone(self):
        """unstone backend output should match example files."""
        self._run_and_compare('unstone')


if __name__ == '__main__':
    unittest.main()