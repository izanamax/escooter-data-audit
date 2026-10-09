# Verification evidence

Local verification on Windows / Python 3.11:

* 36 unittest cases passed, including CLI subprocess checks and malformed input.
* Three synthetic splits passed strict sequence checking: 7 images, 7 boxes,
  3 distinct source sequences, zero errors and zero warnings.
* The deliberately invalid fixture produced exit 1 and exactly 2 errors:
  bbox_geometry and image_reference.

Remote verification:

* [Run 37936258798](https://github.com/izanamax/escooter-data-audit/actions/runs/37936258798)
  completed successfully for commit `151be74299834326b04f46f0ec5db21f18c4d274`.
* All three test jobs passed: Ubuntu/Python 3.11, Ubuntu/Python 3.12 and
  Windows/Python 3.11. Each ran the same 36 tests and the strict example audit.
* The dependent delivery job built a wheel and source archive, installed the
  wheel into a fresh environment, and successfully ran the console command
  outside the source checkout.
* A 26,011-byte artifact was uploaded, containing the distributions and example
  report. Its name includes the verified commit; retention is 30 days.

Integration with the local research exports found 111 images and 237 annotations
across train (76/189), validation (15/18) and test (20/30). There were no errors
under the metadata checks and three missing-sequence warnings. All 111 image
records lack source_sequence. This leaves recording-level independence
unverified; it does not establish that overlap occurred. Raw exports and detailed
local findings are not part of this public repository.

Synthetic test evidence is not model-accuracy evidence. The report identifies
the inspected exports rather than treating the original pilot README's image
count as an observed result.
