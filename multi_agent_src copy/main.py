from __future__ import annotations

try:
    from .orchestrator import MultiAgentOrchestrator
except ImportError:
    from orchestrator import MultiAgentOrchestrator


def main() -> None:
    orchestrator = MultiAgentOrchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()
