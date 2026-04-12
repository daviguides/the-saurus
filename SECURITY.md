# Security

## Security Measures

This project implements the following security practices:

- **Authentication**: Opt-in API key enforcement on all endpoints (REST + WebSocket)
- **Input validation**: PDF magic bytes verification, filename sanitization, upload size limits (50MB), file count limits
- **Path traversal protection**: Job ID and filename validation via `is_relative_to` checks
- **Error sanitization**: Internal details are logged server-side only; clients receive generic messages
- **Safe deserialization**: Only `yaml.safe_load` / `yaml.safe_dump` used; no `pickle`, `eval`, or `exec`
- **Secrets management**: All credentials via environment variables, `.env` files gitignored
- **Security tests**: Automated test suite covering auth, path traversal, upload validation

## Scope

This is an MVP / portfolio project and is not intended for production deployment without additional hardening. Known areas for improvement:

- Rate limiting on API endpoints
- CORS lockdown for production origins
- Prompt injection defense for LLM inputs
- Startup validation for required configuration
