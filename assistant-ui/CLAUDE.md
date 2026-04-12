# Assistant UI

Federated chat interface for The Saurus assistant. Runs standalone or embedded in the app via Module Federation 2.0.

## Tech

React 19, Rsbuild, Tailwind v4, Socket.IO client

## Port

5174

## Module Federation

Exposes `./EmbeddedApp` and `./config`. Shared dependencies: `react`, `react-dom`, `socket.io-client` (singleton, eager). Federation is controlled by the `RSBUILD_MF_REMOTE=true` env var.

## Shell Modes

- **Standalone**: Full-screen chat. `pnpm dev` (port 5174)
- **Embedded**: Compact panel for host app. `pnpm dev:federated` (serves `remoteEntry.js`)

## Structure

```
src/
├── shells/
│   ├── standalone/App.tsx    # Full-screen shell
│   └── embedded/App.tsx      # Compact panel shell
├── core/
│   └── hooks/                # useWebSocket, useChat
└── ui/
    ├── chat/                 # MessageBubble
    └── components/           # ChatInput
```

## Backend Connection

Connects to `assistant-ws` on port 8001 via Socket.IO.

## Design

Imports shared tokens from `../../shared/tokens.css`. Inherits `dark` class from host.

## Development

```bash
pnpm dev              # Standalone on :5174
pnpm dev:federated    # With remoteEntry.js for host consumption
pnpm build
pnpm lint
```

## Reference

Uses Module Federation 2.0 architecture for independent build and deployment.
