"""Daily buy-candidates pipeline orchestrator.

universe -> data -> score -> news -> narrate -> archive -> render -> email.
"""

from __future__ import annotations


def run() -> None:
    raise NotImplementedError("Wire up the pipeline once individual modules are ready.")


if __name__ == "__main__":
    run()
