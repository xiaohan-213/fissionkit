"""Timing benchmark backing the performance figures quoted in the paper.

Timings vary with hardware; the shapes and seeds are fixed so the workload is
exactly reproducible.
"""
import time

import numpy as np

from fissionkit import count_split_de, thin

rng = np.random.default_rng(0)


def clock(label, fn):
    t0 = time.perf_counter(); fn(); t1 = time.perf_counter()
    print(f"{label:<48s} {t1 - t0:6.2f} s")


X_pois = rng.poisson(6.0, size=(2000, 5000))
X_gaus = rng.normal(0, 1, size=(2000, 5000))
X_nb = rng.negative_binomial(10, 10 / 15, size=(500, 150))

clock("poisson thin, 2000 x 5000 (1e7 entries)", lambda: thin(X_pois, "poisson", K=2, random_state=1))
clock("gaussian thin, 2000 x 5000", lambda: thin(X_gaus, "gaussian", K=2, sigma2=1.0, random_state=1))
clock("count_split_de, 500 x 150 (NB, size estimated)", lambda: count_split_de(X_nb, family="negative_binomial", random_state=1))
try:
    with open("/proc/cpuinfo") as f:
        for line in f:
            if line.startswith("model name"):
                print("hardware:", line.split(":", 1)[1].strip()); break
except OSError:
    pass
