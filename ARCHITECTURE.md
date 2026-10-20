# Architecture Overview: demo_project

```mermaid
graph TD
  classDef entryNode fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
  classDef apiNode fill:#083344,stroke:#06b6d4,stroke-width:1.5px,color:#f8fafc;
  classDef coreNode fill:#064e3b,stroke:#10b981,stroke-width:1.5px,color:#f8fafc;
  classDef dataNode fill:#451a03,stroke:#f59e0b,stroke-width:1.5px,color:#f8fafc;
  classDef utilNode fill:#1e293b,stroke:#38bdf8,stroke-width:1.5px,color:#f8fafc;
  classDef defaultNode fill:#0f172a,stroke:#64748b,stroke-width:1.5px,color:#f8fafc;
  subgraph layer_Application_Entry["Application Entry"]
    app_py["app.py | Application"]:::entryNode
  end
  style layer_Application_Entry fill:#0b1120,stroke:#1e293b,stroke-width:1px,stroke-dasharray: 4 4,color:#94a3b8
  subgraph layer_API___Interface["API & Interface"]
    api_routes_py["api/routes.py | APIRouter"]:::apiNode
  end
  style layer_API___Interface fill:#0b1120,stroke:#1e293b,stroke-width:1px,stroke-dasharray: 4 4,color:#94a3b8
  subgraph layer_Configuration["Configuration"]
    config_settings_py["config/settings.py | AppConfig"]:::utilNode
  end
  style layer_Configuration fill:#0b1120,stroke:#1e293b,stroke-width:1px,stroke-dasharray: 4 4,color:#94a3b8
  subgraph layer_Core___Domain["Core & Domain"]
    core_engine_py["core/engine.py | WorkflowEngine"]:::coreNode
  end
  style layer_Core___Domain fill:#0b1120,stroke:#1e293b,stroke-width:1px,stroke-dasharray: 4 4,color:#94a3b8
  subgraph layer_Data___Storage["Data & Storage"]
    models_user_py["models/user.py | UserRole, UserModel"]:::dataNode
  end
  style layer_Data___Storage fill:#0b1120,stroke:#1e293b,stroke-width:1px,stroke-dasharray: 4 4,color:#94a3b8
  subgraph layer_Utilities___Shared["Utilities & Shared"]
    utils_crypto_py["utils/crypto.py | hash_secret, generate_token"]:::utilNode
  end
  style layer_Utilities___Shared fill:#0b1120,stroke:#1e293b,stroke-width:1px,stroke-dasharray: 4 4,color:#94a3b8
  app_py --> api_routes_py
  app_py --> config_settings_py
  app_py --> core_engine_py
  api_routes_py --> core_engine_py
  api_routes_py --> models_user_py
  core_engine_py --> models_user_py
  core_engine_py --> utils_crypto_py
```
