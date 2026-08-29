"""Audit trail helpers.

Explainability is the point of the engine: every model object exposes a
``to_explanation()`` returning a numbered, human-readable trace from inputs and
parameters to the value shown. The helpers here provide the shared vocabulary
for those traces so they read consistently across stages.
"""
