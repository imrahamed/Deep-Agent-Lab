# Python bridge for a TypeScript backend engineer

Python type hints, like TypeScript's static types, do not validate a network
payload. `SearchArgs.model_validate(payload)` is the equivalent boundary to a Zod
parse. The course uses strict Pydantic schemas for model-generated arguments;
unknown actions and invalid limits must fail before a backend call.

```python
from deep_agent_lab.foundations import SearchArgs
request = SearchArgs.model_validate({"query": "production restore", "top_k": 3})
assert request.top_k == 3
```

A dataclass is a concise record with a generated initializer. `field(default_factory=set)`
creates a new mutable set for every instance. Reusing one set as a default would
make supposedly independent plans share state. `frozenset` is useful for immutable
permissions and labels, and dictionaries resemble Maps when keyed by evidence ID.

`async def` returns a coroutine when called. It runs when awaited or scheduled,
similar to asynchronous JavaScript work, but a coroutine object itself does not
start executing. `asyncio.gather` resembles Promise.all; a semaphore limits the
number of simultaneously active operations. A timeout requests cooperative
cancellation. It cannot guarantee that an unrelated remote write stopped.

A `with` statement deterministically enters and exits a resource boundary, similar
to an explicit try/finally or disposable resource. This distinction matters for
SQLite: its connection context manager commits or rolls back a transaction but
does not close the connection. The application's context managers explicitly close
connections, which is necessary for temporary-file cleanup on Windows.

Exceptions are part of the domain contract. A successful empty search, a schema
error, a permission denial and a transport timeout mean different things. The
typed tool outcome makes those distinctions visible to orchestration. Catch only
errors the boundary can classify; cancellation must propagate rather than being
silently converted into another retry.

LangGraph state fields can define reducers. `Annotated[dict, operator.or_]` merges
new evidence into the thread's existing evidence map. That is not a general
transaction mechanism: graph checkpoints and the approved brief database have
separate commit boundaries. Exact-action idempotency is still required.

The notebooks show implementations before abstractions so you can inspect which
state belongs to Python, the model input, the graph checkpoint or a durable
application table. That ownership distinction is more important than Python syntax.
