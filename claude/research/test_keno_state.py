import os
import shlex
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "keno_break.c"
MAGIC = "KENO_BREAK_MT19937"
FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211
MASK64 = (1 << 64) - 1


class MT19937:
    def __init__(self, seed):
        self.mt = [seed & 0xFFFFFFFF]
        for i in range(1, 624):
            previous = self.mt[-1]
            self.mt.append((1812433253 * (previous ^ (previous >> 30)) + i) & 0xFFFFFFFF)
        self.mti = 624

    def twist(self):
        for k in range(227):
            y = (self.mt[k] & 0x80000000) | (self.mt[k + 1] & 0x7FFFFFFF)
            self.mt[k] = (self.mt[k + 397] ^ (y >> 1) ^ (0x9908B0DF if y & 1 else 0)) & 0xFFFFFFFF
        for k in range(227, 623):
            y = (self.mt[k] & 0x80000000) | (self.mt[k + 1] & 0x7FFFFFFF)
            self.mt[k] = (self.mt[k - 227] ^ (y >> 1) ^ (0x9908B0DF if y & 1 else 0)) & 0xFFFFFFFF
        y = (self.mt[623] & 0x80000000) | (self.mt[0] & 0x7FFFFFFF)
        self.mt[623] = (self.mt[396] ^ (y >> 1) ^ (0x9908B0DF if y & 1 else 0)) & 0xFFFFFFFF
        self.mti = 0

    def next(self):
        if self.mti >= 624:
            self.twist()
        value = self.mt[self.mti]
        self.mti += 1
        value ^= value >> 11
        value ^= (value << 7) & 0x9D2C5680
        value ^= (value << 15) & 0xEFC60000
        value ^= value >> 18
        return value & 0xFFFFFFFF


def forward_mulhi_draw(generator, stride):
    pool = list(range(1, 81))
    ordered = []
    for i in range(20):
        width = 80 - i
        index = i + ((generator.next() * width) >> 32)
        pool[i], pool[index] = pool[index], pool[i]
        ordered.append(pool[i])
    for _ in range(20, stride):
        generator.next()
    return ordered


def synthetic_draws(seed, skip, stride, count):
    generator = MT19937(seed)
    for _ in range(skip):
        generator.next()
    return [forward_mulhi_draw(generator, stride) for _ in range(count)]


def ordered_predictions(stdout):
    return [
        [int(value) for value in line.split(" ordered:", 1)[1].split()]
        for line in stdout.splitlines()
        if line.startswith("prediction ") and " ordered:" in line
    ]


def fnv_byte(value, byte):
    return ((value ^ byte) * FNV_PRIME) & MASK64


def fnv_integer(value, integer, byte_count):
    for shift in range(0, byte_count * 8, 8):
        value = fnv_byte(value, (integer >> shift) & 0xFF)
    return value


def checkpoint_checksum(fields, words):
    value = FNV_OFFSET
    for byte in MAGIC.encode("ascii"):
        value = fnv_byte(value, byte)
    for integer in (
        1,
        fields["sampler"],
        fields["mapping"],
        fields["stride"],
        fields["draws_consumed"],
        fields["holdout"],
    ):
        value = fnv_integer(value, integer, 4)
    value = fnv_integer(value, fields["input_fnv1a64"], 8)
    value = fnv_integer(value, fields["mti"], 4)
    for word in words:
        value = fnv_integer(value, word, 4)
    return value


class KenoStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name)
        cls.binary = cls.directory / "keno_break"
        cls.state = cls.directory / "state-v1.txt"
        compiler = os.environ.get("CC", "cc")
        subprocess.run(
            [*shlex.split(compiler), "-O3", "-std=c11", "-Wall", "-Wextra", "-Werror", "-o", str(cls.binary), str(SOURCE)],
            text=True,
            capture_output=True,
            check=True,
        )
        cls.draws = synthetic_draws(0xC0FFEE42, 41, 21, 480)
        cls.recovery = subprocess.run(
            [
                str(cls.binary),
                "demo",
                "400",
                "0xC0FFEE42",
                "41",
                "0",
                "0",
                "21",
                "--state-out",
                str(cls.state),
                "--predict",
                "30",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        if cls.recovery.returncode != 0:
            raise RuntimeError(cls.recovery.stdout + cls.recovery.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_predict(self, path=None, count=30):
        return subprocess.run(
            [str(self.binary), "predict", str(path or self.state), str(count)],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

    def checkpoint_parts(self):
        lines = self.state.read_text(encoding="ascii").splitlines()
        words_line = lines.index("words 624")
        checksum_line = next(i for i, line in enumerate(lines) if line.startswith("checksum_fnv1a64 "))
        fields = {}
        for line in lines[1:words_line]:
            key, raw = line.split()
            fields[key] = int(raw, 16) if key == "input_fnv1a64" else int(raw)
        words = [int(token, 16) for line in lines[words_line + 1 : checksum_line] for token in line.split()]
        return lines, fields, words_line, checksum_line, words

    def write_checkpoint_fixture(self, path, fields, words):
        lines = [
            f"{MAGIC} 1",
            f"sampler {fields['sampler']}",
            f"mapping {fields['mapping']}",
            f"stride {fields['stride']}",
            f"draws_consumed {fields['draws_consumed']}",
            f"holdout {fields['holdout']}",
            f"input_fnv1a64 {fields['input_fnv1a64']:016x}",
            f"mti {fields['mti']}",
            "words 624",
        ]
        lines.extend(" ".join(f"{word:08x}" for word in words[i : i + 8]) for i in range(0, 624, 8))
        lines.extend([f"checksum_fnv1a64 {checkpoint_checksum(fields, words):016x}", "end"])
        path.write_text("\n".join(lines) + "\n", encoding="ascii")

    def test_checkpoint_is_versioned_complete_and_private(self):
        lines, fields, _, _, words = self.checkpoint_parts()
        self.assertEqual(lines[0], f"{MAGIC} 1")
        self.assertEqual(fields["sampler"], 0)
        self.assertEqual(fields["mapping"], 0)
        self.assertEqual(fields["stride"], 21)
        self.assertEqual(fields["draws_consumed"], 450)
        self.assertEqual(fields["holdout"], 50)
        self.assertEqual(fields["mti"], 90)
        self.assertEqual(len(words), 624)
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)
        self.assertEqual(list(self.directory.glob("state-v1.txt.tmp.*")), [])

    def test_reload_matches_direct_predictions_and_independent_oracle(self):
        before = self.state.read_bytes()
        loaded = self.run_predict()
        self.assertEqual(loaded.returncode, 0, loaded.stderr)
        self.assertEqual(ordered_predictions(loaded.stdout), ordered_predictions(self.recovery.stdout))
        self.assertEqual(ordered_predictions(loaded.stdout), self.draws[450:480])
        self.assertEqual(self.state.read_bytes(), before)

    def test_corrupted_and_noncanonical_words_are_rejected(self):
        lines, _, words_line, _, _ = self.checkpoint_parts()
        original_lines = list(lines)
        tokens = original_lines[words_line + 1].split()
        tokens[0] = "00000000" if tokens[0] != "00000000" else "00000001"
        lines[words_line + 1] = " ".join(tokens)
        corrupted = self.directory / "corrupted.txt"
        corrupted.write_text("\n".join(lines) + "\n", encoding="ascii")
        result = self.run_predict(corrupted, 1)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid or corrupted", result.stderr)

        lines = list(original_lines)
        tokens = lines[words_line + 1].split()
        tokens[0] = "0" + tokens[0]
        lines[words_line + 1] = " ".join(tokens)
        noncanonical = self.directory / "noncanonical.txt"
        noncanonical.write_text("\n".join(lines) + "\n", encoding="ascii")
        self.assertEqual(self.run_predict(noncanonical, 1).returncode, 1)

    def test_unknown_version_and_embedded_nul_are_rejected(self):
        original = self.state.read_bytes()
        wrong_version = self.directory / "version2.txt"
        wrong_version.write_bytes(original.replace(f"{MAGIC} 1".encode(), f"{MAGIC} 2".encode(), 1))
        self.assertEqual(self.run_predict(wrong_version, 1).returncode, 1)

        overflowing_version = self.directory / "overflowing-version.txt"
        overflowing_version.write_bytes(original.replace(f"{MAGIC} 1".encode(), f"{MAGIC} 4294967297".encode(), 1))
        self.assertEqual(self.run_predict(overflowing_version, 1).returncode, 1)

        embedded_nul = self.directory / "nul.txt"
        embedded_nul.write_bytes(original.replace(MAGIC.encode(), MAGIC.encode() + b"\0suffix", 1))
        self.assertEqual(self.run_predict(embedded_nul, 1).returncode, 1)

    def test_all_zero_state_is_rejected_even_with_matching_checksum(self):
        lines, fields, words_line, checksum_line, words = self.checkpoint_parts()
        zero_words = [0] * len(words)
        replacement = [" ".join(["00000000"] * 8) for _ in range(78)]
        lines[words_line + 1 : checksum_line] = replacement
        new_checksum_line = words_line + 1 + len(replacement)
        lines[new_checksum_line] = f"checksum_fnv1a64 {checkpoint_checksum(fields, zero_words):016x}"
        zero_state = self.directory / "zero.txt"
        zero_state.write_text("\n".join(lines) + "\n", encoding="ascii")
        self.assertEqual(self.run_predict(zero_state, 1).returncode, 1)

    def test_prediction_respects_checkpoint_index_at_twist_boundaries(self):
        _, original_fields, _, _, words = self.checkpoint_parts()
        for mti in (624, 623, 1):
            with self.subTest(mti=mti):
                fields = dict(original_fields, mti=mti, stride=25)
                fixture = self.directory / f"phase-{mti}.txt"
                self.write_checkpoint_fixture(fixture, fields, words)
                generator = MT19937.__new__(MT19937)
                generator.mt = list(words)
                generator.mti = mti
                expected = [forward_mulhi_draw(generator, 25) for _ in range(2)]
                result = self.run_predict(fixture, 2)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(ordered_predictions(result.stdout), expected)

    def test_no_checkpoint_or_prediction_without_holdout(self):
        capture = self.directory / "only-training.txt"
        capture.write_text("\n".join(" ".join(map(str, draw)) for draw in self.draws[:350]) + "\n", encoding="ascii")
        refused_state = self.directory / "must-not-exist.txt"
        result = subprocess.run(
            [
                str(self.binary),
                "file",
                str(capture),
                "0",
                "0",
                "21",
                "--state-out",
                str(refused_state),
                "--predict",
                "1",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("holdout 0/0", result.stdout)
        self.assertIn("refused", result.stderr)
        self.assertFalse(refused_state.exists())
        self.assertFalse(Path(str(refused_state) + ".tmp").exists())

    def test_exactly_450_file_draws_reserve_fifty_for_validation(self):
        capture = self.directory / "exactly-450.txt"
        capture.write_text(
            "\n".join(" ".join(map(str, draw)) for draw in self.draws[:450]) + "\n",
            encoding="ascii",
        )
        checkpoint = self.directory / "exactly-450-state.txt"
        result = subprocess.run(
            [
                str(self.binary),
                "file",
                str(capture),
                "0",
                "0",
                "21",
                "--state-out",
                str(checkpoint),
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("holdout 50/50", result.stdout)
        fields = {
            line.split()[0]: line.split()[1]
            for line in checkpoint.read_text(encoding="ascii").splitlines()
            if len(line.split()) == 2
        }
        self.assertEqual(fields["draws_consumed"], "450")
        self.assertEqual(fields["holdout"], "50")

    def test_checkpoint_output_cannot_alias_the_capture(self):
        capture = self.directory / "capture-must-survive.txt"
        alias = self.directory / "capture-hardlink.txt"
        original = b"input bytes must not be replaced\n"
        capture.write_bytes(original)
        os.link(capture, alias)
        result = subprocess.run(
            [str(self.binary), "file", str(capture), "0", "0", "20", "--state-out", str(alias)],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("must differ", result.stderr)
        self.assertEqual(capture.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
