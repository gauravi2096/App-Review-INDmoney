# Product Pulse pipeline: P1–P5 in Python for Streamlit deployment.
#
# Avoid importing `pipeline.runner` at package import time. This prevents
# `runpy` from hitting a sys.modules import-order warning when executing
# `python -m pipeline.runner`.

__all__ = ["run_weekly_pipeline"]


def run_weekly_pipeline(*args, **kwargs):
    from .runner import run_weekly_pipeline as _impl

    return _impl(*args, **kwargs)
