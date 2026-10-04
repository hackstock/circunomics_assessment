# Architecture (C4)

These diagrams describe **this implementation**, not a future production mesh. There is no Prometheus server, Grafana, job queue, or auth service in Compose.

| Level | File | What it shows |
| --- | --- | --- |
| 1 — Context | [c4-context.md](c4-context.md) | People and external systems |
| 2 — Container | [c4-container.md](c4-container.md) | Docker Compose processes |
| 3 — Component | [c4-component.md](c4-component.md) | FastAPI modules and Vue screens |
| 4 — Code | [c4-code.md](c4-code.md) | Tables, import sequence, request paths |

Levels 1–3 are [PlantUML](https://plantuml.com/) with [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) **v2.0.1**. Install the **PlantUML** extension (`jebbs.plantuml`), put the cursor in a diagram, and run **PlantUML: Preview Current Diagram** (`Alt+D`). Local rendering needs Java and Graphviz (`dot`). The extension’s bundled PlantUML is 1.2021.0, which cannot load newer C4-PlantUML (`%chr` is missing), so the diagrams pin v2.0.1. To render without a local Java install, set `plantuml.render` to `PlantUMLServer` and `plantuml.server` to `https://www.plantuml.com/plantuml`.

Level 4 (tables, import state, request paths) stays Mermaid.

Run the stack with `make up` or `docker compose up --build` ([SETUP.md](../SETUP.md)).
