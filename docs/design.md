# Policy contract

One Policy owns one immutable, synthetic effect: increment an internal ledger by
one. Compensation decrements it once. The caller creates an opaque approval
object and retains it outside untrusted input. Object identity authenticates an
approval for this policy instance. The CLI owns that object and is a demonstration,
not an authentication service. Never expose the capability to an untrusted agent.

Each dispatch is serialized with a lock. Validation and journal updates occur in
the same critical section as the synthetic effect. Accepted IDs are remembered;
rejected IDs are not consumed. Reusing an accepted ID for another kind returns
conflict. Duplicate authorization still requires the capability. Terminal states
accept no new transitions, though an authenticated duplicate returns duplicate.
No external callbacks, files, network requests, or arbitrary tool invocations
are supported. User code with Python introspection privileges is trusted.

The formal model uses a relation of source/event/target triples, independently
of the runtime's imperative branches. It bounds the world to one operation, one
unit effect, one approval capability equivalence class, nine event symbols, and
one stable ID per event symbol. Forge represents an invalid approval. It explores
the complete reachable graph in this finite abstraction, including retries,
rejections, duplicates and cycles, with no depth cutoff. Fresh IDs, conflicting
IDs, real threading, malformed inputs and cross-instance approval are outside the
abstraction and receive ordinary runtime regression tests.

TLC checks type bounds, authorization before any effect, effect accounting,
complete rollback, and terminal core stability. It checks safety in this finite
model, not unbounded correctness or liveness. No fairness assumptions are made;
execution can stay unfinished forever. Fingerprinting has a reported collision
probability. There is no durable journal, restart recovery, revocation, multiple
operations, or distributed exactly-once guarantee.

The conformance checker parses TLC's actual DOT graph without implementing a
second transition policy. It finds a shortest path to every model node, replays
that path through a fresh runtime, then exercises every outgoing graph edge.
It compares outcomes, phases, authorization, effect counts and accepted IDs.
This covers every edge from a representative history, not every possible runtime
history, and does not prove refinement. Parser and graph completeness checks are
required before comparison. Runtime-produced edge observations are saved as JSONL.

The intentionally faulty configuration adds planned -> execute without approval.
TLC must reject it for Authorization. Its counterexample is translated into a
runtime regression that verifies no effect occurs on plan, execute.
