# Design and technology decisions

The module addresses two concrete failure modes: malformed bounding boxes and
training/evaluation partitions that share image names or declared recordings.
The baseline is the dissertation's e-scooter dataset workflow. The tool is an
independent, small data-preparation component rather than a new detector.

## Requirements and acceptance

| ID | Requirement | Acceptance evidence |
|---|---|---|
| R1 | Validate detection metadata | Malformed-record and geometry tests |
| R2 | Check split independence | Repeated-file and repeated-sequence negative tests |
| R3 | Preserve input data | Input immutability and overwrite protection tests |
| R4 | Export traceable results | JSON schema version, tool version and input hashes |
| R5 | Automate repeatable verification | CI matrix, installed-wheel smoke test and artifact |

The public library accepts a mapping of split names to decoded COCO objects.
Validation returns findings rather than stopping after the first broken record.
The CLI owns filesystem access, strict JSON decoding, hashing and exit codes.
Keeping I/O outside the core makes in-memory fixtures straightforward.

## Technology trade-offs

Python matches the surrounding computer-vision project and provides JSON,
argument parsing, hashing and unit tests without runtime packages. A pandas
pipeline would be convenient for large tabular summaries but is unnecessary for
these nested annotation checks. PyTorch is relevant to detector training, not
this module. A web framework would add interfaces and deployment work without
improving the acceptance checks.

The standard-library unittest runner covers structured cases and CLI subprocess
behavior. Pytest is a reasonable extension for richer plugins; it is unnecessary
for this small suite. Setuptools and build produce standard installable Python
distributions. Their versions are pinned in requirements-build.txt.

Git supplies distributed history; GitHub supplies hosting, issues and Actions.
Subversion is a centralized alternative, with repository commits depending on
the server. GitHub is a hosting platform, not an alternative VCS to Git.
GitHub Actions keeps the build definition beside the code and avoids maintaining
a separate Jenkins server for one student's module.

## Integration and scientific limits

Run the audit before detector training and retain the JSON with the experiment's
data manifest. A changed annotation hash means the input bytes changed; it does
not show whether the scientific quality improved. Data partition decisions still
need source-recording knowledge and manual review.

Synthetic fixtures prove software behavior on controlled cases. They do not
establish the prevalence of defects in real traffic datasets. Sequence checking
is incomplete without source_sequence. A future image-content hash check and
an image-existence/dimension check are distinct extensions, tracked in Issues.

## Sources

* [Pro Git: version control](https://git-scm.com/book/en/v2/Getting-Started-About-Version-Control)
* [Python unittest](https://docs.python.org/3/library/unittest.html)
* [COCO reference implementation](https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/coco.py)
* [GitHub: building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)
* [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
