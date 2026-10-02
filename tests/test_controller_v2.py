"""Deployment runner entry point for the lane/asset controller regression suite."""
import runpy
from pathlib import Path

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] /
                      'tools/chat-controller/v0.4/tests/test_event_model_v2.py'),
                  run_name='__main__')
