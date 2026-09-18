# Mermaid Cheatsheet — Quick Reference

## Flowchart (graph TD / graph LR)

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
```

Node shapes: `[rect]` `(rounded)` `{diamond}` `([stadium])` `[[subroutine]]` `[(cylinder)]` `((circle))`

## Sequence Diagram

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    participant D as Database
    C->>S: GET /api/users
    S->>D: SELECT * FROM users
    D-->>S: rows
    S-->>C: 200 OK [{users}]
```

Arrows: `->>` solid, `-->>` dotted, `-x` cross, `-)` async

## Class Diagram

```mermaid
classDiagram
    class User {
        +String name
        +String email
        +login() bool
        +logout() void
    }
    class Admin {
        +ban(User) void
    }
    User <|-- Admin
```

Relations: `<|--` inherit, `*--` composition, `o--` aggregation, `-->` association

## State Diagram

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Loading: fetch()
    Loading --> Success: 200
    Loading --> Error: 4xx/5xx
    Error --> Loading: retry()
    Success --> [*]
```

## Entity Relationship

```mermaid
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT ||--o{ LINE_ITEM : "ordered in"
```

Cardinality: `||` one, `o{` zero-many, `|{` one-many, `o|` zero-one

## C4 Context (experimental)

```mermaid
C4Context
    Person(user, "User", "App user")
    System(app, "App", "Main system")
    SystemDb(db, "Database", "PostgreSQL")
    Rel(user, app, "Uses")
    Rel(app, db, "Reads/Writes")
```

## Styling

```mermaid
graph TD
    A:::green --> B:::red
    classDef green fill:#50fa7b,stroke:#333,color:#000
    classDef red fill:#ff5555,stroke:#333,color:#fff
```

## Tips
- Use `graph LR` for horizontal, `graph TD` for vertical
- Escape special chars in labels with quotes: `A["Label with (parens)"]`
- Use `subgraph` to group nodes
- Keep diagrams under 20 nodes for readability
