# Frontend — Database Course Assistant

Angular 19 chat interface for the RAG backend. Provides a multi-chat sidebar, markdown rendering, per-message source citations, and a 10-question session limit.

---

## Requirements

- Node.js 18+
- npm 9+
- Backend running at `http://localhost:8000` (see root README)

---

## Development

```bash
npm install      # first time only
npm start        # serves at http://localhost:4200 with live reload
```

Alternatively, using the Angular CLI directly:

```bash
ng serve
```

## Production build

```bash
ng build         # outputs to dist/chat/
```

## Tests

```bash
ng test          # unit tests via Karma
```

---

## Key files

| File | Purpose |
|---|---|
| `src/app/app.component.ts` | All component logic (chat state, HTTP calls, markdown) |
| `src/app/app.component.html` | Template — sidebar + message list + input bar |
| `src/app/app.component.css` | Dark theme styles |
| `src/app/app.config.ts` | Angular providers (HTTP client, PrimeNG theme) |

---

## Notable behaviour

- **Stateless**: conversation history is held in memory and sent to the backend on every request. Refreshing the page clears all chats.
- **Session limit**: 10 questions per browser session, enforced client-side. The dot-row in the input area shows remaining questions.
- **Timeout**: requests time out after 60 seconds — the backend can take a while when the model falls back through the quota chain.
- **Markdown**: assistant responses are rendered through `marked` so the LLM can use bold, lists, code blocks, etc.

---

## UI library

[PrimeNG](https://primeng.org/) v19 with the Aura theme preset. Icons from PrimeIcons.

---

## Additional Angular resources

- [Angular CLI reference](https://angular.dev/tools/cli)
- [PrimeNG docs](https://primeng.org/installation)
