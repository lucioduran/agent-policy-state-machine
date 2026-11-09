# Contributing

Use small focused commits, English content, and no em dash characters. Run the
README testing commands. Keep source comments sparse; explain policy decisions
in docs/design.md. Avoid third-party runtime dependencies and external effects.

Policy changes need matching runtime tests and a reviewed formal-model update.
The intentionally faulty configuration must keep producing an authorization
counterexample. Do not change expected observations merely to hide a mismatch.

Run expensive work serially through the host's shared benchmark lock when present.
On the original host, the wrapper path is documented in the README. Use one TLC
worker and bounded memory. Keep raw failures. Record actual timestamps, source
hashes, versions, finite bounds, hardware and measurement limitations.

Before publication, verify the public repository, passing CI on the exact release
commit, installed-wheel smoke test and release-tag target. All synthetic fixtures
and generated evidence in this repository use the MIT license.
