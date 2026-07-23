"""Vercel serverless entry point.

Vercel's @vercel/python runtime imports the ASGI ``app`` from this file. The
package lives under ``src/`` (src layout), so add it to the path before import.

Note: Vercel is stateless — in-memory data (created campaigns, sessions, the
Google refresh token) does not persist across cold starts. Seeded example
campaigns always appear. Use Render (render.yaml) or a DB for durable state.
"""

from __future__ import annotations

import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gtm_paid_ai_distribution.main import app  # noqa: E402

__all__ = ["app"]
