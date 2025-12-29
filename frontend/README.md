Frontend Migration Workspace (Vue + Vuetify + Plotly.js + Postgres)

Goal
- Build a new frontend in this folder without touching the existing Streamlit app.
- Migrate page-by-page, keeping functional parity.
- Use Docker for local dev and deployment.

Workflow (incremental)
1) Inventory Streamlit pages and features.
2) Design API + DB schema.
3) Scaffold Vue app (Vite + Vuetify + Plotly.js).
4) Migrate page-by-page and test each step.

Tests
- Run basic checks after each implementation step (build, lint, or unit tests as available).
