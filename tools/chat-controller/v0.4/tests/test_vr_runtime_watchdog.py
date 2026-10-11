"""Functional tests for the external VR scheduler heartbeat watchdog."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

WATCHDOG = Path(__file__).resolve().parents[1] / 'vr-runtime-watchdog.sh'


class RuntimeWatchdogTest(unittest.TestCase):
    @staticmethod
    def stop_process(proc):
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=3)

    def run_watchdog(self, heartbeat_age=0):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        marker = base / 'controller-started'
        marker.touch()
        status = base / 'runtime_status.json'
        status.write_text('{"queue_loop_heartbeat_at":"test"}')
        if heartbeat_age:
            t = time.time() - heartbeat_age
            os.utime(status, (t, t))
        worker = subprocess.Popen(['sleep', '60'])
        self.addCleanup(lambda: self.stop_process(worker))
        env = {**os.environ,
            'VR_RUNTIME_WATCHDOG_FILE': str(status),
            'VR_RUNTIME_WATCHDOG_MARKER': str(marker),
            'VR_RUNTIME_WATCHDOG_LOG': str(base / 'watchdog.log'),
            'VR_RUNTIME_WATCHDOG_CHECK_SECONDS': '1',
            'VR_RUNTIME_WATCHDOG_STALE_SECONDS': '3',
            'VR_RUNTIME_WATCHDOG_STARTUP_GRACE_SECONDS': '1'}
        guard = subprocess.Popen(['bash', str(WATCHDOG), str(worker.pid)], env=env)
        self.addCleanup(lambda: self.stop_process(guard))
        return worker, guard, status, base

    def test_stale_heartbeat_stops_hung_controller(self):
        worker, guard, _, base = self.run_watchdog(heartbeat_age=20)
        worker.wait(timeout=5)
        guard.wait(timeout=5)
        self.assertEqual(worker.returncode, -signal.SIGTERM)
        self.assertIn('no runtime heartbeat', (base / 'watchdog.log').read_text())

    def test_fresh_heartbeat_keeps_healthy_controller(self):
        worker, guard, status, _ = self.run_watchdog()
        time.sleep(1.4)
        status.touch()
        time.sleep(1.1)
        self.assertIsNone(worker.poll())
        self.assertIsNone(guard.poll())


if __name__ == '__main__':
    unittest.main()
