// JalSaathi case policies (DECISIONS.md D-07, D-08).
// Evaluated by src/jalsaathi/policy.py, which also denies on any evaluation error (fail closed).
// Anything not permitted here is denied.

// Only a passing lab result can close a case. An engineer's "fixed" or a kit result never can.
@id("close-needs-lab-pass")
permit (principal, action == Action::"close_case", resource)
when { context.evidence == "lab_pass" };

// A field-kit "clean" result can only make a case provisionally safe.
@id("kit-only-provisional")
permit (principal, action == Action::"mark_provisional", resource)
when { context.evidence == "kit_clean" };

// Messages to villages and engineers are allowed...
@id("messages-allowed")
permit (principal, action == Action::"send_message", resource);

// ...except boil advice for chemical contaminants: boiling does not remove them, and it concentrates nitrate.
@id("no-boil-for-chemicals")
forbid (principal, action == Action::"send_message", resource)
when { context.contaminant_class == "chemical" && context.actions.contains("boil") };
