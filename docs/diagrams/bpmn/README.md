# BPMN diagrams

Standard **BPMN 2.0** - open in [bpmn.io](https://demo.bpmn.io) or [Camunda Modeler](https://camunda.com/download/modeler/).

## Canonical architecture (start here)

| File | What it shows |
|------|----------------|
| **[architecture.bpmn](./architecture.bpmn)** | **Main components:** Frontend · API · Keycloak + **RBAC** · **Taskiq** · **SSE/Redis** · PostgreSQL · **MinIO** · **Inference** |

Short labels on purpose (readable in bpmn.io). Each horizontal band is one component; dashed arrows are calls between them.

## Process diagrams

| File | Process |
|------|---------|
| [local-platform-start.bpmn](./local-platform-start.bpmn) | Start laptop / Mac zip |
| [prod-deploy.bpmn](./prod-deploy.bpmn) | Vendor release -> client Helm |
| [audit-run.bpmn](./audit-run.bpmn) | Single audit run detail |

## View

1. https://demo.bpmn.io -> open `architecture.bpmn`  
2. Or Camunda Modeler -> Open file  

## Related

[CONTEXT.md](../../../CONTEXT.md) · [LOCAL.md](../../LOCAL.md) · [CLUSTER.md](../../CLUSTER.md) · Mermaid sketches: [../README.md](../README.md)
