"""run-facts.py PROJECT_DIR [...]: the FACTS sheet for RUBRIC.md (reviewers read code only, they do not build).

Per project: the harness's independent gradle verdicts (_gradle-<leaf>.log, _gradle-<leaf>.p2.log next to the project),
every test case from build/test-results (passed / failed / skipped), `docker compose config`, the agent's own Pi session
per phase (gradle runs and failures, compactions, its final message: section P), and grep hints for the rubric items that
are easy to miss (PII_KEY defaults, copies of contract files, Flyway migrations, DDL outside migrations, jars in the repo,
absolute or temp paths and dynamic versions in build files).
Hints are pointers, not verdicts: the reviewer still checks the line. Stdlib only.
"""
import datetime, glob, json, os, re, subprocess, sys
import xml.etree.ElementTree as ET

SKIP_DIRS = {"build", ".gradle", "bin", "node_modules", ".git", ".idea", "out", "target"}
TEXT_EXT = (".java", ".kt", ".kts", ".gradle", ".properties", ".yml", ".yaml", ".xml", ".sql", ".proto", ".wsdl",
            ".xsd", ".md", ".env", ".txt", ".sh")


def source_files(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            yield os.path.join(d, f)


def rel(root, p):
    return os.path.relpath(p, root).replace("\\", "/")


def gradle_verdicts(root):
    leaf, parent = os.path.basename(root.rstrip("\\/")), os.path.dirname(root.rstrip("\\/"))
    out = []
    for tag in ("", ".p2"):
        p = os.path.join(parent, f"_gradle-{leaf}{tag}.log")
        if os.path.exists(p):
            txt = open(p, errors="replace").read()
            m = re.search(r"BUILD (SUCCESSFUL|FAILED)[^\r\n]*", txt)
            out.append(f"phase {'2' if tag else '1'}: {m.group(0) if m else 'no BUILD line'} ({os.path.basename(p)})")
    return out or ["no harness gradle log found next to the project"]


def test_cases(root):
    rows = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in {"node_modules", ".git", ".gradle"}]
        if "test-results" not in d.replace("\\", "/"):
            continue
        for f in files:
            if f.startswith("TEST-") and f.endswith(".xml"):
                for tc in ET.parse(os.path.join(d, f)).getroot().iter("testcase"):
                    st = "FAILED" if tc.find("failure") is not None or tc.find("error") is not None else \
                         "skipped" if tc.find("skipped") is not None else "passed"
                    rows.append((rel(root, d).split("/build/")[0], tc.get("classname", ""), tc.get("name", ""), st))
    return rows


def hints(root):
    h = {"PII_KEY lines": [], "contract files": [], "flyway migrations": [], "DDL outside migrations": [],
         "jars in repo": [], "build plugins": [], "absolute/temp paths in build files": [], "dynamic versions": []}
    for p in source_files(root):
        r = rel(root, p)
        if re.match(r"SPEC(-\d+)?\.md$", r):   # the task text itself, not the agent's work
            continue
        if p.endswith(".jar") and not r.endswith("gradle/wrapper/gradle-wrapper.jar"):
            h["jars in repo"].append(r)
        if p.endswith((".proto", ".wsdl", ".xsd")):
            h["contract files"].append(r)
        if re.search(r"db/migration/(.+/)?V\d+__", r):   # Flyway also reads sub-folders (db/migration/orders/V1__...)
            h["flyway migrations"].append(r)
        if not p.endswith(TEXT_EXT) and not os.path.basename(p).lower().startswith(("dockerfile", "docker-compose")):
            continue
        try:
            lines = open(p, errors="replace").read().splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if "PII_KEY" in line:
                h["PII_KEY lines"].append(f"{r}:{i}: {line.strip()[:140]}")
            if re.search(r"\bCREATE TABLE\b", line, re.I) and "db/migration/" not in r:
                h["DDL outside migrations"].append(f"{r}:{i}")
            if p.endswith((".gradle", ".kts")) and re.search(r"wsimport|xjc|protobuf|flyway|testcontainers", line, re.I):
                h["build plugins"].append(f"{r}:{i}: {line.strip()[:120]}")
            if p.endswith((".gradle", ".kts", ".toml", ".properties")) and re.search(
                    r"[A-Za-z]:[\\/]|/tmp/|%TEMP%|\$TEMP|java\.io\.tmpdir|user\.home|\bcurl\b|\bwget\b", line):
                h["absolute/temp paths in build files"].append(f"{r}:{i}: {line.strip()[:120]}")
            if p.endswith((".gradle", ".kts", ".toml")) and re.search(r"latest\.(release|integration)|:\+[\"']|\d\.\+", line):
                h["dynamic versions"].append(f"{r}:{i}: {line.strip()[:120]}")
    return h


def compose_config(root):
    if not any(os.path.exists(os.path.join(root, f)) for f in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")):
        return "no compose file"
    env = dict(os.environ, PII_KEY="ZmFjdHMtY2hlY2stZHVtbXkta2V5LTMyLWJ5dGVzISE=")   # a required ${PII_KEY:?} must not fail it
    try:
        r = subprocess.run(["docker", "compose", "config", "-q"], cwd=root, env=env, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"not run ({e.__class__.__name__})"
    return "valid" if r.returncode == 0 else "INVALID: " + ((r.stderr or r.stdout).strip().splitlines() or ["?"])[-1][:200]


def _text(m):
    c = m.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return str(c or "")


def session_phases(root):
    """The newest Pi session of the project, split at the user message that starts phase 2 ("Phase 2. ...")."""
    key = "--" + root.replace(":", "-").replace("\\", "-").replace("/", "-") + "--"
    files = glob.glob(os.path.join(os.path.expanduser("~"), ".pi", "agent", "sessions", key, "*.jsonl"))
    return parse_session(max(files, key=os.path.getmtime)) if files else None


def _ts(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


STALL_S = 300   # a single model response waited for longer than this = a client/network stall, not model work


def parse_session(path):
    phases, cur, calls, prev_t = [], None, {}, None
    for line in open(path, encoding="utf-8"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        m = o.get("message") or {}
        text = _text(m)
        if m.get("role") == "user" and (cur is None or text.lstrip().startswith("Phase 2")):
            cur = {"start": o.get("timestamp", ""), "end": "", "tools": 0, "gradle": 0, "gradle_failed": 0,
                   "compactions": 0, "final": "", "tool_s": 0.0, "edited": False, "verified": False, "stalls": []}
            phases.append(cur)
        if cur is None:
            continue
        cur["end"] = o.get("timestamp", cur["end"])
        # 29.10: a 28 s server answer reached Pi 20 min later (GPU idle meanwhile) and counted as model time
        t_now = _ts(o.get("timestamp"))
        if m.get("role") == "assistant" and prev_t and t_now and (t_now - prev_t).total_seconds() > STALL_S:
            cur["stalls"].append(((t_now - prev_t).total_seconds(), o.get("timestamp", "")[11:16]))
        prev_t = t_now or prev_t
        if "compact" in (str(o.get("type", "")) + str(o.get("customType", ""))).lower():
            cur["compactions"] += 1
        for c in m.get("content") if isinstance(m.get("content"), list) else []:
            if isinstance(c, dict) and c.get("type") == "toolCall":
                cur["tools"] += 1
                calls[c.get("id")] = (json.dumps(c.get("arguments", {})), _ts(o.get("timestamp")))
                if c.get("name") in ("write", "edit"):   # edits made through bash heredocs are not seen
                    cur["edited"], cur["verified"] = True, False
        # a gradle RUN (gradle / ./gradlew / gradlew.bat as a command), not a file name like build.gradle.kts
        if m.get("role") == "toolResult" and re.search(r"(^|[\s;&|(\"'])(\./|\.\\\\)?(gradlew(\.bat)?|gradle)(\s|\"|$)",
                                                      calls.get(m.get("toolCallId"), ("", None))[0]):
            cur["gradle"] += 1
            cur["gradle_failed"] += bool(re.search(r"BUILD FAILED|FAILURE: Build failed", text))
            # P2: a full build/test run that passed after the last write/edit of this phase
            if re.search(r"\b(build|test|check)\b", calls.get(m.get("toolCallId"), ("", None))[0]) \
                    and "BUILD SUCCESSFUL" in text and "BUILD FAILED" not in text:
                cur["verified"] = True
        if m.get("role") == "toolResult" and m.get("toolCallId") in calls:
            t0, t1 = calls[m.get("toolCallId")][1], _ts(o.get("timestamp"))
            if t0 and t1:
                cur["tool_s"] += (t1 - t0).total_seconds()   # time the tool ran on this PC, not the model
        if m.get("role") == "assistant" and text.strip():
            cur["final"] = text.strip()
    return phases


def report(root):
    print(f"# FACTS {root}\n\n## Independent gradle build")
    for v in gradle_verdicts(root):
        print(f"- {v}")
    rows = test_cases(root)
    n = {s: sum(1 for x in rows if x[3] == s) for s in ("passed", "FAILED", "skipped")}
    print(f"\n## Test cases: {len(rows)} total, {n['passed']} passed, {n['FAILED']} failed, {n['skipped']} skipped")
    for mod, cls, name, st in sorted(rows):
        print(f"- {st:7} {mod} {cls.split('.')[-1]} > {name}")
    print(f"\n## docker compose config (PII_KEY set to a dummy): {compose_config(root)}")
    print("\n## Agent behaviour (section P; from the Pi session)")
    phases = session_phases(root)
    if not phases:
        print("- no Pi session found")
    for n_, ph in enumerate(phases or [], 1):
        print(f"- phase {n_}: {ph['start'][:16]} -> {ph['end'][:16]} UTC, tool calls {ph['tools']}, own gradle runs "
              f"{ph['gradle']} (failed {ph['gradle_failed']}), compactions {ph['compactions']}, "
              f"verified after last edit: {'yes' if ph['verified'] else 'NO' if ph['edited'] else 'no edits seen'}")
        t0, t1 = _ts(ph["start"]), _ts(ph["end"])
        if t0 and t1:   # tools run on this PC (shared with other work); compare models by the model part
            wall = (t1 - t0).total_seconds() / 60
            stall = sum(s for s, _ in ph["stalls"]) / 60
            print(f"  time: wall {wall:.1f} min = tools {ph['tool_s'] / 60:.1f} + model {wall - ph['tool_s'] / 60 - stall:.1f}"
                  + (f" + stalls {stall:.1f} ({len(ph['stalls'])} response(s) waited > {STALL_S} s, at "
                     + ", ".join(t for _, t in ph["stalls"]) + " UTC)" if ph["stalls"] else ""))
        # whole message: claims worth checking for P3 often sit at the end (29.10: "the environment reverted my files")
        print("  final message: " + ph["final"].replace("\n", " / "))
    print("\n## Hints (pointers, verify the line)")
    for k, v in hints(root).items():
        print(f"- {k}: {len(v)}")
        for x in v[:25]:
            print(f"  - {x}")
    print()


def _selfcheck():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        proj = os.path.join(t, "p")
        tr = os.path.join(proj, "svc", "build", "test-results", "test")
        os.makedirs(tr)
        open(os.path.join(tr, "TEST-a.xml"), "w").write(
            '<testsuite><testcase classname="x.A" name="ok"/><testcase classname="x.A" name="bad"><failure/></testcase>'
            '<testcase classname="x.A" name="sk"><skipped/></testcase></testsuite>')
        open(os.path.join(proj, "docker-compose.yml"), "w").write("PII_KEY: ${PII_KEY:-dev}\n")
        open(os.path.join(t, "_gradle-p.log"), "w").write("BUILD SUCCESSFUL in 9s\n")
        assert sorted(r[3] for r in test_cases(proj)) == ["FAILED", "passed", "skipped"]
        assert hints(proj)["PII_KEY lines"] == ["docker-compose.yml:1: PII_KEY: ${PII_KEY:-dev}"]
        assert gradle_verdicts(proj)[0].startswith("phase 1: BUILD SUCCESSFUL")
        msg = lambda role, content, **k: json.dumps({"type": "message", "timestamp": "t", "message": dict(role=role, content=content, **k)})
        call = lambda i, cmd: [{"type": "toolCall", "id": i, "name": "bash", "arguments": {"command": cmd}}]
        sess = os.path.join(t, "s.jsonl")
        open(sess, "w", encoding="utf-8").write("\n".join([
            msg("user", "Read SPEC.md"), msg("assistant", call("a", "gradle build")),
            msg("toolResult", [{"type": "text", "text": "BUILD FAILED"}], toolCallId="a"),
            msg("assistant", call("b", "./gradlew build")), msg("toolResult", "BUILD SUCCESSFUL", toolCallId="b"),
            msg("assistant", [{"type": "text", "text": "Done, green."}]),
            json.dumps({"type": "compaction", "timestamp": "t"}),
            msg("user", "Phase 2. Read SPEC-2.md"), msg("assistant", [{"type": "text", "text": "Phase 2 done."}])]))
        ph = parse_session(sess)
        assert [(p["gradle"], p["gradle_failed"], p["compactions"], p["final"]) for p in ph] == \
            [(2, 1, 1, "Done, green."), (0, 0, 0, "Phase 2 done.")], ph
        edit = lambda i: [{"type": "toolCall", "id": i, "name": "edit", "arguments": {"path": "A.java"}}]
        open(sess, "w", encoding="utf-8").write("\n".join([
            msg("user", "Read SPEC.md"), msg("assistant", edit("e1")), msg("toolResult", "ok", toolCallId="e1"),
            msg("assistant", call("g1", "gradle build")), msg("toolResult", "BUILD SUCCESSFUL", toolCallId="g1"),
            msg("user", "Phase 2. Read SPEC-2.md"), msg("assistant", call("g2", "gradle build")),
            msg("toolResult", "BUILD SUCCESSFUL", toolCallId="g2"), msg("assistant", edit("e2")),
            msg("toolResult", "ok", toolCallId="e2")]))
        assert [(p["edited"], p["verified"]) for p in parse_session(sess)] == [(True, True), (True, False)]
        at = lambda ts, role, content: json.dumps({"type": "message", "timestamp": ts,
                                                   "message": {"role": role, "content": content}})
        open(sess, "w", encoding="utf-8").write("\n".join([
            at("2026-10-29T09:00:00Z", "user", "Read SPEC.md"),
            at("2026-10-29T09:01:00Z", "assistant", [{"type": "text", "text": "a"}]),      # 60 s: normal
            at("2026-10-29T09:21:00Z", "assistant", [{"type": "text", "text": "b"}])]))   # 1200 s: stall
        assert parse_session(sess)[0]["stalls"] == [(1200.0, "09:21")]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # agents' messages carry arrows etc.; the Windows console is cp1251
    _selfcheck()
    for d in sys.argv[1:]:
        report(os.path.abspath(d))
