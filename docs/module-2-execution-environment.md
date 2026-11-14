# Module 2 · Execution environment

[Course home](course.md) · [Previous module](module-1-agent-foundations.md) · [Next module](module-3-context-management.md)

A restore-drill report needs a policy excerpt, raw measurements, and somewhere to
draft the report. Give each operation an environment that matches what it needs.
By the end of the module, you should be able to say who runs each operation,
where its data lives, and which permissions apply.

## 2.1 What the agent can do

| Surface | Operations | Example |
| --- | --- | --- |
| Application tool | Calls a function with a defined contract | Search the approved document corpus |
| Virtual filesystem | Lists, reads, and writes paths through a backend | Read the brief skill or keep a draft |
| Shell | Starts programs with environment and filesystem access | Run a spreadsheet converter in an isolated environment |
| Interpreter | Runs scoped JavaScript and configured tool bridges | Calculate drill durations or batch policy lookups |

The model chooses from tools the host app exposes. File tools receive paths such
as `/draft.md`. The backend resolves those paths. The shell and interpreter are
separate capabilities, with separate process and data boundaries.
[Backends](https://docs.langchain.com/oss/python/deepagents/backends)

## 2.2 Route file paths and set permissions

```powershell
uv run python -m deep_agent_lab.labs workspace
```

Follow the four calls in order:

1. `read_file("/reference/policy.md")` resolves into a temporary host directory
   and reads the original sample policy.
2. A write under `/reference/` fails because that prefix is read-only.
3. `write_file("/draft.md", ...)` routes to graph state.
4. Reading `/draft.md` returns the draft. The host listing still contains only
   `policy.md`, while the state listing contains `/draft.md`.

A state backend stores data with the graph. In the checkpointed capstone, that
means it follows the thread. A filesystem backend reads and writes a host
directory according to its configuration. A store backend can provide files
shared across threads within a namespace. A composite backend applies routing
rules by prefix. In the capstone, `/reference/` contains packaged guidance and
skills, and other file paths use state.

**Worked design.** A support assistant reviews a customer's case. Put read-only
policy under `/reference/` and the draft under a thread-local path. Store the
final response through an approved action in the application. Keeping approved
policy and working text in different backends makes it clear which data users
and tools are allowed to change. [Workspace lab](../src/deep_agent_lab/labs.py) ·
[Filesystem permissions](https://docs.langchain.com/oss/python/deepagents/permissions)

### Predict the result before running the lab

| Virtual path | Backend | Expected effect |
| --- | --- | --- |
| `/reference/policy.md` | Host filesystem reached through the reference route | Read the original file |
| `/reference/alternate.md` | Same reference route with writes denied | Reject the write before it reaches the host |
| `/draft.md` | Default state backend | Store the file in the graph's file state |

Check the lab's `host_files` and `state_files` fields against your prediction.
The standalone demo keeps state in memory. The capstone attaches a checkpointer,
so its state-backed files can survive between CLI calls on the same thread.

## 2.3 Compare LocalShell and a sandbox

```powershell
uv run python -m deep_agent_lab.labs shell
```

The Python exercise runs a fixed read command on a temporary file. On Windows
the command is `type policy.txt`. Exit code zero means the command succeeded,
and its output shows “Restore approval recorded.” Read `shell_lab` to see who
chooses the command and how the temporary directory is created.

LocalShell starts a process on the host. Its working directory does not confine
the process to that directory. An isolated sandbox is a separate execution
boundary with its own permitted files, packages, and network. The capstone uses
state and reference file backends. This shell exercise is a standalone lesson.

Think through the same chart job in three designs. A fixed application tool
can compute a known set of statistics from structured input. A scoped
interpreter can group or total supplied values. A sandbox can run a plotting
package that needs files and installed dependencies. The choice is about the
capabilities the job needs and the data those capabilities can reach.

**Real-world example.** An operations team receives a sanitized drill export
and wants a chart. An isolated worker can take the export and a pinned plotting
package, produce a chart, and return it for the brief. It needs the input and
an output location. Its job does not require the production database credentials.
[Deep Agents sandboxes](https://docs.langchain.com/oss/python/deepagents/sandboxes)

## 2.4 Compute with the interpreter

```powershell
uv run python -m deep_agent_lab.labs interpreter
```

QuickJS runs this calculation inside the `eval` tool:

```javascript
const minutes = [30, 15, 45];
const total = minutes.reduce((sum, value) => sum + value, 0);
console.log(total);
```

The tool result contains stdout with `90`. `console.log` outputs a value and
the script's return value is separate. Add an average and maximum to the
snippet for practice. The results should be `30` and `45` minutes:

```javascript
console.log(total / minutes.length);
console.log(Math.max(...minutes));
```

The same arithmetic can be applied to a list of hundreds of durations without asking the
chat model to calculate each one.

Configured bridges can allow interpreter code to invoke certain tools. The
basic interpreter exercise exposes no subagent bridge. Module 4 turns it on for
parallel review. Use a regular Python tool when the calculation is stable and
repeated, or the interpreter when the inputs require flexible grouping and
transformation. [Deep Agents interpreters](https://docs.langchain.com/oss/python/deepagents/interpreters)

## Check your understanding

1. Why does a write to `/draft.md` leave the temporary host directory unchanged?
2. What permission would you give the agent for the signed backup policy?
3. Which surface is appropriate for totaling 30, 15, and 45 minutes?

**Answers.** The draft routes to state. The signed policy needs read access via
a reference path. A small deterministic function or scoped interpreter can
total the durations.
