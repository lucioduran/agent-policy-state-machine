# CI environment history

The first public run at commit 3ce9a14fae52946d2090d172f0466d118a858aac failed
before project checks, because ubuntu-latest resolved to Ubuntu 26.04 and
setup-python had no Python 3.14.0 binary for that runner image.

Raw run and job logs: https://github.com/lucioduran/agent-policy-state-machine/actions/runs/42692324461

The workflow now pins Ubuntu 24.04 and Python 3.14.0. Local formal measurements
remain on macOS with CPython 3.14.7 and Java 17.0.17. CI runs the small regression
suite and offline saved-evidence replay, not the local model-checking measurement.
