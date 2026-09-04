import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "keno_break.c"


class KenoBreakInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.temporary.name) / "keno_break"
        compiler = os.environ.get("CC", "cc")
        subprocess.run(
            [
                *shlex.split(compiler), "-O3", "-std=c11", "-Wall", "-Wextra",
                "-Werror", "-o", str(cls.binary), str(SOURCE),
            ],
            text=True,
            capture_output=True,
            check=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_file(self, rows, sampler="0", mapping="0", stride="20"):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.txt"
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            return subprocess.run(
                [str(self.binary), "file", str(path), sampler, mapping, stride],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_rejects_19_values_instead_of_skipping_line(self):
        result = self.run_file([" ".join(map(str, range(1, 20)))])
        self.assertEqual(result.returncode, 1)
        self.assertIn("exactly 20", result.stderr)

    def test_rejects_21_values_instead_of_truncating_line(self):
        result = self.run_file([" ".join(map(str, range(1, 22)))])
        self.assertEqual(result.returncode, 1)
        self.assertIn("exactly 20", result.stderr)

    def test_rejects_invalid_token(self):
        values = list(map(str, range(1, 21)))
        values[8] = "9x"
        result = self.run_file([" ".join(values)])
        self.assertEqual(result.returncode, 1)
        self.assertIn("trailing token", result.stderr)

    def test_floyd_rejects_value_above_current_domain(self):
        values = [80] + list(range(1, 20))
        result = self.run_file([" ".join(map(str, values))], sampler="2")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not consistent", result.stdout)

    def test_rejects_out_of_range_sampler_and_mapping(self):
        values = [20, 1, 80] + list(range(2, 19))
        sampler = self.run_file([" ".join(map(str, values))], sampler="3")
        mapping = self.run_file([" ".join(map(str, values))], mapping="3")
        self.assertEqual(sampler.returncode, 1)
        self.assertEqual(mapping.returncode, 1)


if __name__ == "__main__":
    unittest.main()
