# E-Scooter Data Audit

[![CI and delivery](https://github.com/izanamax/escooter-data-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/izanamax/escooter-data-audit/actions/workflows/ci.yml)

A small scientific Python tool for checking COCO detection annotations before
training e-scooter detectors. Developed for Assignment 3: Software Development
and Integration, Maxim Mussin, CSE-2507M, Astana IT University.

The tool checks metadata and dataset partitions. It does not train models,
evaluate detection accuracy, decode photographs or certify label correctness.

## Quick start

Python 3.11 or newer. The module and tests use only the standard library.

```sh
git clone https://github.com/izanamax/escooter-data-audit.git
cd escooter-data-audit
python -m escooter_audit --split train=examples/train.json --split val=examples/val.json --split test=examples/test.json --require-sequences --output outputs/audit.json
python -m unittest discover -s tests -v
```

Use `py -3.11` instead of `python` on Windows if needed. A valid sample produces
`PASS: 0 errors, 0 warnings`. All examples are synthetic metadata authored for
this project; their named image files are illustrative and are not required.

To check your own existing COCO exports, replace the three example paths.
Use a common relative filename namespace across splits. Export source recording
identifiers as the optional `images[].source_sequence` field. Add
`--require-sequences` when recording-level independence is required.

## Checks and outputs

* Required `images`, `annotations` and `categories` arrays and unique integer IDs.
* Positive image dimensions, safe relative filenames and valid category names.
* Valid image/category references and finite `[x, y, width, height]` boxes.
* Positive box sizes and boxes inside the declared image dimensions.
* Duplicate filenames, category-map differences and split overlap by filename.
* Recording-level overlap when `source_sequence` is present.
* Counts of images, annotations, categories, sequences and unannotated images.
* Input SHA-256 digests, tool version, structured errors and warnings.

IDs are local to each JSON file: image ID 1 in train and image ID 1 in test do
not imply overlap. Filenames normalize slash direction and redundant `.` parts;
comparison remains case-sensitive. Negative images with no objects are allowed.
Missing sequence metadata warns by default and fails in strict mode.

| Exit code | Meaning |
|---|---|
| 0 | Audit has no errors; warnings may remain |
| 1 | Audit completed and found validation errors |
| 2 | Invalid CLI arguments, unreadable/malformed input, or output error |

Reports do not contain a timestamp, so identical named inputs and options give
identical output. Inputs are read-only, and the CLI rejects an output path that
would overwrite an input. Reports include supplied record identifiers and must
be reviewed before sharing if those identifiers are sensitive.

## Deliberately invalid example

```sh
python -m escooter_audit --split train=examples/invalid.json --require-sequences
```

Expected: exit 1, with `bbox_geometry` and `image_reference` findings. This
negative case is also verified by the test suite; it is not a training result.

## Build and install

Create an isolated virtual environment before installing build tools:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-build.txt
python -m build --no-isolation
python -m pip install dist/escooter_data_audit-1.0.0-py3-none-any.whl
escooter-audit --split train=examples/train.json --require-sequences
```

The wheel and source archive are built with pinned tooling. There are no runtime
dependencies. Pins improve repeatability but do not guarantee identical binary
archives across all operating systems and build times.

## Git, issues and CI/CD

Work is recorded in focused commits. Issues describe acceptance conditions;
changes can use short-lived branches and pull requests. A single-author project
does not imply independent peer review or configured branch protection.

On pushes, pull requests and manual dispatch, [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
runs tests and a strict sample audit on Ubuntu/Python 3.11, Ubuntu/Python 3.12 and
Windows/Python 3.11. The delivery job waits for all tests, builds a wheel and
source archive, installs the wheel into a clean environment, and audits the
example from outside the source directory. It uploads the distributions and
sample report as a versioned Actions artifact retained for 30 days.

This is basic continuous delivery of a tested downloadable package; installing
it is a user decision. There is no production service or automatic deployment.
Download artifacts from a successful [Actions run](https://github.com/izanamax/escooter-data-audit/actions).
GitHub may require sign-in to download Actions artifacts. The public source
remains accessible and can be built locally after an artifact expires.

## Research context and limitations

The parent dissertation compares Faster R-CNN, YOLO and a hybrid, then integrates
tracking. This module supports the data-quality and reproducibility requirements
from Assignments 1 and 2. Run it before an expensive training job, preserve its
report alongside the split manifest, and resolve findings before comparing models.

The audit implements a documented detection-only subset, not the entire COCO
specification: segmentation, keypoints, `area` and `iscrowd` are not validated.
It cannot detect near-duplicate pixels, wrong labels, missing image files,
incorrect declared dimensions or unrecorded common source videos. Passing is
evidence of these checks only. Missing source information requires a provenance
audit, not an invented sequence ID or a claim that leakage is impossible.

Local research photographs, model weights, raw annotations and machine settings
are not needed for the public example. This independent package can be used from
the existing detector project without adding PyTorch to CI.

## Layout

```text
escooter_audit/       validation library and command-line interface
tests/               behavioral and subprocess tests
examples/            synthetic valid splits and an invalid case
.github/workflows/   test matrix and package delivery
docs/                design and evidence notes
pyproject.toml       package metadata and console command
requirements-build.txt  pinned build tools
LICENSE              MIT license for this module
```

See [design notes](docs/DESIGN.md) and [verification evidence](docs/VERIFICATION.md).
The [Assignment 3 report (PDF, 10 pages)](docs/Mussin_Assignment_3_2026.pdf)
connects the theory, implementation and observed results.
MIT applies to this new module and its synthetic examples, not to outside
datasets or the separate dissertation detector code.
