------------------------------ MODULE Policy ------------------------------
EXTENDS Naturals, FiniteSets
CONSTANT Bug
VARIABLES phase, authorized, applied, reverted, seen, event, result
vars == <<phase, authorized, applied, reverted, seen, event, result>>
core == <<phase, authorized, applied, reverted, seen>>
Events == {"plan", "authorize", "forge", "execute", "succeed", "fail",
           "compensate", "compensation_fail", "cancel"}
Phases == {"new", "planned", "authorized", "executing", "done",
           "compensating", "compensation_failed", "rolled_back", "cancelled"}
Terminal == {"done", "rolled_back", "cancelled"}

Init == /\ phase = "new" /\ authorized = FALSE
        /\ applied = 0 /\ reverted = 0 /\ seen = {}
        /\ event = "init" /\ result = "init"

(* A relation table, independent of the runtime's imperative branches. *)
Routes == {<<"new", "plan", "planned">>,
           <<"planned", "authorize", "authorized">>,
           <<"authorized", "execute", "executing">>,
           <<"executing", "succeed", "done">>,
           <<"executing", "fail", "compensating">>,
           <<"compensating", "compensate", "rolled_back">>,
           <<"compensation_failed", "compensate", "rolled_back">>,
           <<"compensating", "compensation_fail", "compensation_failed">>,
           <<"new", "cancel", "cancelled">>,
           <<"planned", "cancel", "cancelled">>,
           <<"authorized", "cancel", "cancelled">>}
EffectiveRoutes == Routes \cup
    (IF Bug THEN {<<"planned", "execute", "executing">>} ELSE {})
Targets(e) == {p \in Phases : <<phase, e, p>> \in EffectiveRoutes}

Step(e) ==
    /\ event' = e
    /\ IF e \in seen THEN
          /\ result' = "duplicate" /\ UNCHANGED core
       ELSE IF Targets(e) # {} THEN
          /\ phase' \in Targets(e)
          /\ authorized' = (authorized \/ e = "authorize")
          /\ applied' = applied + (IF e = "execute" THEN 1 ELSE 0)
          /\ reverted' = reverted + (IF e = "compensate" THEN 1 ELSE 0)
          /\ seen' = seen \cup {e}
          /\ result' = "accepted"
       ELSE /\ result' = "rejected" /\ UNCHANGED core
Next == \E e \in Events : Step(e)
Spec == Init /\ [][Next]_vars
TypeOK == /\ phase \in Phases /\ authorized \in BOOLEAN
          /\ applied \in 0..1 /\ reverted \in 0..1
          /\ seen \subseteq Events /\ event \in Events \cup {"init"}
          /\ result \in {"init", "accepted", "duplicate", "rejected"}
Authorization == applied > 0 => authorized
EffectAccounting == reverted <= applied
Rollback == phase = "rolled_back" => applied = reverted
TerminalStability == [][(phase \in Terminal) => (core' = core)]_vars
=============================================================================
