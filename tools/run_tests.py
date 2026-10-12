"""Run the full unittest suite with compact per-test timing diagnostics."""
from __future__ import annotations

import argparse
import gc
import threading
import traceback
import sys
import time
import unittest
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ProgressSuite(unittest.TestSuite):
    def _handleClassSetUp(self, test, result):
        cls = test.__class__
        if cls is getattr(result, "_previousTestClass", None):
            return super()._handleClassSetUp(test, result)
        name = f"{cls.__module__}.{cls.__qualname__}"
        started = time.perf_counter()
        print(f"[SETUP] {name}", flush=True)
        super()._handleClassSetUp(test, result)
        elapsed = time.perf_counter() - started
        if isinstance(result, ProgressResult):
            result.setup_timings.append(TestTiming(name, elapsed, "SETUP"))
        print(f"[READY] {name} ({elapsed:.2f}s)", flush=True)


@dataclass
class TestTiming:
    name: str
    elapsed: float
    status: str


class ProgressResult(unittest.TextTestResult):
    def __init__(self, *args, slow_threshold: float = 5.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings: list[TestTiming] = []
        self.setup_timings: list[TestTiming] = []
        self._started: dict[str, float] = {}
        self.slow_threshold = slow_threshold

    def startTest(self, test):
        super().startTest(test)
        name = test.id()
        self._started[name] = time.perf_counter()
        print(f"[START] {name}", flush=True)

    def _finish(self, test, status: str):
        name = test.id()
        elapsed = time.perf_counter() - self._started.pop(name, time.perf_counter())
        self.timings.append(TestTiming(name, elapsed, status))
        marker = " SLOW" if elapsed >= self.slow_threshold else ""
        print(f"[{status}] {name} ({elapsed:.2f}s){marker}", flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._finish(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._finish(test, "FAIL")

    def addError(self, test, err):
        super().addError(test, err)
        self._finish(test, "ERROR")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._finish(test, "SKIP")

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._finish(test, "XFAIL")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._finish(test, "XPASS")


class ProgressRunner(unittest.TextTestRunner):
    resultclass = ProgressResult

    def __init__(self, *args, slow_threshold: float = 5.0, **kwargs):
        self.slow_threshold = slow_threshold
        super().__init__(*args, **kwargs)

    def _makeResult(self):
        return self.resultclass(self.stream, self.descriptions,
                                self.verbosity, slow_threshold=self.slow_threshold)

    def run(self, test):
        started = time.perf_counter()
        result = super().run(test)
        elapsed = time.perf_counter() - started
        print("\n=== TEST SUMMARY ===", flush=True)
        print(f"ran={result.testsRun} failures={len(result.failures)} "
              f"errors={len(result.errors)} skipped={len(result.skipped)} "
              f"wall={elapsed:.2f}s", flush=True)
        slow = sorted(result.timings, key=lambda item: item.elapsed, reverse=True)[:15]
        print("slowest:", flush=True)
        for item in slow:
            print(f"  {item.elapsed:7.2f}s {item.status:5s} {item.name}", flush=True)
        print("slowest class setups:", flush=True)
        for item in sorted(result.setup_timings, key=lambda item: item.elapsed,
                           reverse=True)[:10]:
            print(f"  {item.elapsed:7.2f}s {item.name}", flush=True)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--slow-threshold", type=float, default=5.0)
    parser.add_argument("--stack-after", type=float, default=60.0,
                        help="Print the main-thread stack while a stage is slow; 0 disables.")
    args = parser.parse_args()
    loader = unittest.TestLoader()
    loader.suiteClass = ProgressSuite
    suite = loader.discover(str(ROOT / "tests"), pattern=args.pattern)
    done = threading.Event()
    main_thread = threading.get_ident()

    def watchdog():
        while not done.wait(args.stack_after):
            print("[WAIT] main-thread stack:", flush=True)
            traceback.print_stack(sys._current_frames()[main_thread], file=sys.stdout)

    if args.stack_after > 0:
        threading.Thread(target=watchdog, daemon=True).start()
    try:
        result = ProgressRunner(
            verbosity=0, stream=sys.stdout, slow_threshold=args.slow_threshold).run(suite)
        print("[CLEANUP] releasing suite fixtures", flush=True)
        fixture = sys.modules.get("test_support")
        if fixture is not None:
            fixture.clear_shared_fixtures()
        # unittest retains test classes in imported modules after their last case.
        for module in list(sys.modules.values()):
            if module is None or not getattr(module, "__name__", "").startswith("test_"):
                continue
            for value in list(vars(module).values()):
                if isinstance(value, type) and issubclass(value, unittest.TestCase):
                    for name in ("stack", "index", "retriever", "ctx", "app", "client"):
                        if name in vars(value):
                            delattr(value, name)
        started = time.perf_counter()
        collected = gc.collect()
        print(f"[CLEANUP DONE] objects={collected} wall={time.perf_counter()-started:.2f}s",
              flush=True)
        return 0 if result.wasSuccessful() else 1
    finally:
        done.set()


if __name__ == "__main__":
    raise SystemExit(main())
