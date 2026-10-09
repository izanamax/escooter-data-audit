import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from escooter_audit import audit_splits


def dataset(filename="train/a.jpg", sequence="recording-a"):
    return {"images": [{"id": 1, "file_name": filename, "width": 100, "height": 80,
                        "source_sequence": sequence}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [10, 20, 30, 40]}],
            "categories": [{"id": 1, "name": "e-scooter"}]}


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.data = dataset()

    def codes(self, data=None):
        report = audit_splits({"train": self.data if data is None else data})
        return {finding["code"] for finding in report["findings"]}

    def test_valid_dataset_and_summary(self):
        report = audit_splits({"train": self.data})
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["splits"]["train"]["annotations_per_category"], {"1": 1})
        self.assertEqual(report["warning_count"], 0)

    def test_box_exactly_on_boundary_is_valid(self):
        self.data["annotations"][0]["bbox"] = [0, 0, 100, 80]
        self.assertFalse(self.codes())

    def test_negative_zero_and_outside_boxes(self):
        for box, code in [([-1, 0, 4, 5], "bbox_geometry"), ([0, 0, 0, 5], "bbox_geometry"),
                          ([0, 0, 4, -5], "bbox_geometry"), ([99, 0, 2, 5], "bbox_bounds"),
                          ([0, 79, 2, 2], "bbox_bounds")]:
            with self.subTest(box=box):
                self.data["annotations"][0]["bbox"] = box
                self.assertIn(code, self.codes())

    def test_malformed_box_is_reported(self):
        for box in (None, {}, "1,2,3,4", [1, 2, 3], [True, 0, 3, 4],
                    [0, 0, float("nan"), 1], [0, 0, float("inf"), 1]):
            with self.subTest(box=box):
                self.data["annotations"][0]["bbox"] = box
                self.assertIn("bbox_format", self.codes())

    def test_unrepresentable_numeric_box_does_not_crash(self):
        self.data["annotations"][0]["bbox"] = [0, 0, 10**400, 1]
        self.assertIn("bbox_format", self.codes())

    def test_broken_image_reference(self):
        self.data["annotations"][0]["image_id"] = 99
        self.assertIn("image_reference", self.codes())

    def test_broken_category_reference(self):
        self.data["annotations"][0]["category_id"] = 99
        self.assertIn("category_reference", self.codes())

    def test_unhashable_references_do_not_crash(self):
        self.data["annotations"][0].update(image_id=[], category_id={})
        self.assertTrue({"image_reference", "category_reference"} <= self.codes())

    def test_duplicate_ids_in_each_collection(self):
        for key in ("images", "annotations", "categories"):
            with self.subTest(key=key):
                data = dataset()
                data[key].append(copy.deepcopy(data[key][0]))
                self.assertIn("duplicate_id", self.codes(data))

    def test_invalid_ids_in_each_collection(self):
        for key in ("images", "annotations", "categories"):
            for value in (True, -1, "1", [], None):
                with self.subTest(key=key, value=value):
                    data = dataset()
                    data[key][0]["id"] = value
                    self.assertIn("invalid_id", self.codes(data))

    def test_invalid_dimensions(self):
        for value in (0, -1, True, 1.5, "100", None):
            with self.subTest(value=value):
                self.data["images"][0]["width"] = value
                self.assertIn("image_size", self.codes())

    def test_unsafe_filenames(self):
        for name in ("../secret.jpg", "/tmp/x.jpg", "C:\\x.jpg", "", ".", None):
            with self.subTest(name=name):
                self.data["images"][0]["file_name"] = name
                self.assertIn("file_name", self.codes())

    def test_duplicate_normalized_filename(self):
        image = copy.deepcopy(self.data["images"][0])
        image.update(id=2, file_name="train\\a.jpg")
        self.data["images"].append(image)
        self.assertIn("duplicate_file", self.codes())

    def test_negative_images_are_allowed(self):
        self.data["annotations"] = []
        report = audit_splits({"train": self.data})
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["splits"]["train"]["images_without_annotations"], 1)

    def test_empty_split_fails(self):
        self.data["images"] = []
        self.assertIn("empty_split", self.codes())

    def test_missing_sequence_warns_by_default(self):
        del self.data["images"][0]["source_sequence"]
        report = audit_splits({"train": self.data})
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["warning_count"], 1)
        self.assertFalse(report["sequence_check_complete"])

    def test_missing_sequence_fails_in_strict_mode(self):
        self.data["images"][0]["source_sequence"] = " "
        report = audit_splits({"train": self.data}, require_sequences=True)
        self.assertEqual(report["status"], "fail")

    def test_local_ids_can_repeat_across_splits(self):
        report = audit_splits({"train": self.data, "test": dataset("test/b.jpg", "recording-b")})
        self.assertEqual(report["status"], "pass")

    def test_repeated_file_across_splits_fails(self):
        report = audit_splits({"train": self.data, "test": dataset("train\\a.jpg", "recording-b")})
        self.assertIn("file_overlap", {item["code"] for item in report["findings"]})

    def test_sequence_overlap_with_different_frames_fails(self):
        report = audit_splits({"train": self.data, "test": dataset("test/b.jpg", "recording-a")})
        self.assertIn("sequence_overlap", {item["code"] for item in report["findings"]})

    def test_changed_category_mapping_fails(self):
        other = dataset("test/b.jpg", "recording-b")
        other["categories"][0]["name"] = "bicycle"
        report = audit_splits({"train": self.data, "test": other})
        self.assertIn("category_map_mismatch", {item["code"] for item in report["findings"]})

    def test_missing_category_name(self):
        self.data["categories"][0]["name"] = ""
        self.assertIn("category_name", self.codes())

    def test_invalid_top_level_and_collections(self):
        for data in ([], None, {}, {"images": "bad", "annotations": {}, "categories": None}):
            with self.subTest(data=data):
                report = audit_splits({"train": data})
                self.assertEqual(report["status"], "fail")
                self.assertIn("schema", {item["code"] for item in report["findings"]})
                self.assertFalse(report["sequence_check_complete"])

    def test_invalid_record_types(self):
        for key in ("images", "annotations", "categories"):
            with self.subTest(key=key):
                data = dataset()
                data[key].append([])
                self.assertIn("record_type", self.codes(data))

    def test_inputs_are_unchanged(self):
        before = copy.deepcopy(self.data)
        audit_splits({"train": self.data})
        self.assertEqual(before, self.data)

    def test_report_is_deterministic(self):
        self.assertEqual(audit_splits({"train": self.data}), audit_splits({"train": self.data}))

    def test_no_splits_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_splits({})


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "data.json"
        self.path.write_text(json.dumps(dataset()), encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "escooter_audit", *args],
                              capture_output=True, text=True)

    def test_success_json_and_input_hash(self):
        result = self.run_cli("--split", f"train={self.path}")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(len(report["inputs"]["train"]["sha256"]), 64)
        self.assertEqual(report["tool_version"], "1.0.0")

    def test_failure_report_has_exit_one(self):
        data = dataset()
        data["annotations"][0]["bbox"] = [0, 0, -1, 4]
        self.path.write_text(json.dumps(data), encoding="utf-8")
        output = Path(self.temp.name) / "nested" / "report.json"
        result = self.run_cli("--split", f"train={self.path}", "--output", str(output))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(output.read_text())["status"], "fail")

    def test_missing_file_has_exit_two(self):
        result = self.run_cli("--split", f"train={self.path}.missing")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_bad_json_has_exit_two(self):
        self.path.write_text("{broken", encoding="utf-8")
        result = self.run_cli("--split", f"train={self.path}")
        self.assertEqual(result.returncode, 2)

    def test_nonstandard_nan_has_exit_two(self):
        self.path.write_text('{"images": NaN}', encoding="utf-8")
        result = self.run_cli("--split", f"train={self.path}")
        self.assertEqual(result.returncode, 2)

    def test_duplicate_split_names_have_exit_two(self):
        result = self.run_cli("--split", f"train={self.path}", "--split", f"train={self.path}")
        self.assertEqual(result.returncode, 2)

    def test_invalid_split_specification(self):
        result = self.run_cli("--split", str(self.path))
        self.assertEqual(result.returncode, 2)

    def test_output_cannot_overwrite_input(self):
        before = self.path.read_bytes()
        result = self.run_cli("--split", f"train={self.path}", "--output", str(self.path))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_cli_strict_sequence_mode(self):
        data = dataset()
        del data["images"][0]["source_sequence"]
        self.path.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_cli("--split", f"train={self.path}", "--require-sequences")
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
