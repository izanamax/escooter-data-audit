# Verification evidence

Local verification on Windows / Python 3.11:

* 36 unittest cases passed, including CLI subprocess checks and malformed input.
* Three synthetic splits passed strict sequence checking: 7 images, 7 boxes,
  3 distinct source sequences, zero errors and zero warnings.
* The deliberately invalid fixture produced exit 1 and exactly 2 errors:
  bbox_geometry and image_reference.

The GitHub Actions run and delivered artifact will be recorded after the first
remote execution. Synthetic test evidence is not model-accuracy evidence.
