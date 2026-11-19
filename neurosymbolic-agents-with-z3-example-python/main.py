from z3 import Int, Solver, Distinct, And, sat

jobs = ["ingest", "train", "evaluate", "deploy"]
t = {j: Int(j) for j in jobs}             # start hour of each job

def base():
    """One-hour slots from 09:00 to 17:00, one job per slot."""
    return [And(t[j] >= 9, t[j] <= 17) for j in jobs] + [Distinct(*t.values())]

def schedule(spec):
    s = Solver()
    s.add(base())
    for name, c in spec.items():           # one named constraint per sentence
        s.assert_and_track(c, name)
    if s.check() == sat:
        m = s.model()
        return {j: m[t[j]].as_long() for j in jobs}
    return sorted(str(c) for c in s.unsat_core())

llm_spec = {   # the LLM's translation
    "ingest_first":     And(t["ingest"] < t["train"], t["ingest"] < t["evaluate"]),
    "eval_after_train": t["train"] < t["evaluate"],
    "eval_before_noon": t["evaluate"] < 12,
    "nothing_at_noon":  And([t[j] != 12 for j in jobs]),
    "deploy_afternoon": t["deploy"] >= 13,
    "deploy_gap":       t["evaluate"] >= t["deploy"] + 2,   # reversed
}
print(schedule(llm_spec))


llm_spec["deploy_gap"] = t["deploy"] >= t["evaluate"] + 2   # after feedback
print(schedule(llm_spec))

# Bad translation - solver

others = [c for name, c in llm_spec.items() if name != "deploy_afternoon"]
reading_a = t["deploy"] >= 13    # "afternoon" begins at 13:00
reading_b = t["deploy"] >= 14    # "afternoon" begins at 14:00

def find(*extra):
    s = Solver()
    s.add(base() + others + list(extra))
    if s.check() == sat:
        m = s.model()
        return {j: m[t[j]].as_long() for j in jobs}

print(find(reading_a != reading_b))   # a schedule on which the readings disagree
print(find(reading_a, reading_b))     # a schedule both readings accept