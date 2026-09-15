import time


def now() -> float:
    return time.perf_counter()


def elapsed(start_time: float) -> float:
    return time.perf_counter() - start_time
