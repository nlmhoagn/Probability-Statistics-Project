import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(dir=REPO)
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        for folder, name in (
            ("data", "raw_experiment_data.csv"),
            ("logs", "experiment_config.json"),
        ):
            (self.root / folder).mkdir()
            shutil.copyfile(REPO / folder / name, self.root / folder / name)
        for script in REPO.glob("*.py"):
            shutil.copyfile(script, self.root / script.name)
        self.raw = self.root / "data" / "raw_experiment_data.csv"

    def run_step(self, step):
        script = next(self.root.glob(f"{step:02}_*.py"))
        return subprocess.run(
            [sys.executable, "-B", "-S", str(script)],
            cwd=self.root, capture_output=True, text=True, timeout=15,
        )

    def test_reproduce_saved_measurements(self):
        raw_digest = hashlib.sha256(self.raw.read_bytes()).digest()
        for step in range(2, 6):
            result = self.run_step(step)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hashlib.sha256(self.raw.read_bytes()).digest(), raw_digest)

        results = self.root / "results"
        residuals = read_csv(results / "residuals_data.csv")
        self.assertEqual(len(residuals), 340)
        self.assertEqual(sum(bool(r["axis1_fitted_log10_time_ms"]) for r in residuals), 200)
        self.assertEqual(sum(int(r["os_jitter_flag"]) for r in residuals), 16)

        comparisons = read_csv(results / "table_axis2_pairwise.csv")
        self.assertEqual(len(comparisons), 6)
        comparison = next(row for row in comparisons if row["reference_charset"] == "alphanumeric")
        self.assertAlmostEqual(float(comparison["holm_adjusted_p_value"]), 0.1286755245, places=8)
        anova = json.loads((results / "statistical_summary.json").read_text())["axis2_charset_anova"]
        self.assertAlmostEqual(anova["f_stat"], 737.9388901, places=6)
        tradeoff = read_csv(results / "table_tradeoff_length_vs_complexity.csv")
        self.assertEqual(sum(bool(r["measured_mean_time_sec"]) for r in tradeoff), 2)
        self.assertEqual(sum(bool(r["projected_mean_time_sec"]) for r in tradeoff), 3)

    def test_reject_corrupt_input(self):
        for field, value, error in (
            ("obs_id", "2", "Duplicate observation ID"),
            ("attempts", "19", "Attempt count does not match target rank"),
            ("time_ms", "inf", "differ from the experiment log"),
        ):
            with self.subTest(field=field):
                rows = read_csv(REPO / "data" / self.raw.name)
                rows[0][field] = value
                with self.raw.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                result = self.run_step(2)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(error, result.stderr)
                self.assertFalse((self.root / "data" / "processed_experiment_data.csv").exists())


if __name__ == "__main__":
    unittest.main()
