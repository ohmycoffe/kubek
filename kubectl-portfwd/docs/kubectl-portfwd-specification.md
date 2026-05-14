# kubectl portfwd — CLI Logic Specification (v1)

This document defines the **simple, deterministic, and understandable** CLI behavior for `kubectl portfwd`.
It is intended to be used **directly as an implementation prompt for an agent**.

---

## Goals

- Keep behavior **simple and understandable**
- Avoid merging, precedence rules, or heuristics
- Prefer configuration when present, but allow fallback
- Fail fast with clear errors
- Be easy to extend later without breaking semantics

---

## Configuration Schema

```yaml
port_forwards:
  - name: auth-service
    namespace: kube-public
    local_port: 50013
    remote_port: 80
  - name: user-service
    namespace: kube-public
    local_port: 50014
    remote_port: 80

groups:
  backend:
    - kube-public/auth-service
    - kube-public/user-service
  ddr:
    - kube-public/auth-service
````

***

## Configuration Rules

*   **Service identity** is `(namespace, name)`
*   A service **may or may not** have a mapping in `port_forwards`

### Port resolution rules

*   If a service **has a mapping** in `port_forwards`:
    *   Use `local_port` and `remote_port` exactly
*   If a service **has no mapping**:
    *   Discover the Kubernetes Service
    *   Use the Service port as `remote_port`
    *   Assign a **random free local port**

***

## CLI Modes (Mutually Exclusive)

Exactly **one** mode is active per invocation.

***

## 1. Base Case — No Options

```bash
kubectl portfwd
```

### Behavior

1.  Show an **interactive group picker** containing:
    *   All defined groups from config
    *   One additional option: `custom`
2.  If a **defined group** is selected:
    *   Start port forwarding for **exactly that group**
3.  If `custom` is selected:
    1.  Prompt for **namespaces** (checkbox)
    2.  Prompt for **services**
        *   Only services from the selected namespaces are shown
    3.  Start port forwarding for **exactly the selected services**

### Notes

*   No flags involved
*   No merging between groups and services
*   Fully interactive

***

## 2. Group Mode

```bash
kubectl portfwd --group <group>
```

### Rules

*   **Exactly one** group must be provided
*   No interactive prompts
*   No service selection

### Behavior

1.  Validate that `<group>` exists in config
2.  Expand the group into service identifiers (`namespace/name`)
3.  For each service:
    *   If a mapping exists in `port_forwards`, use it
    *   Otherwise:
        *   Discover the Kubernetes Service
        *   Use its port as `remote_port`
        *   Assign a **random free local port**
4.  Start port forwarding

### Errors (Hard Fail)

*   Group does not exist
*   Service does not exist in the cluster
*   Configured `local_port` is already in use by any process

***

## 3. Service Mode

```bash
kubectl portfwd --service <namespace/name> [--service <namespace/name> ...]
```

### Rules

*   `--service` may be provided multiple times
*   Each value must be exactly `namespace/name`
*   No interactive prompts
*   No group logic

### Behavior

1.  Parse each `namespace/name`
2.  For each service:
    *   Validate service exists in the cluster
    *   If a mapping exists in `port_forwards`, use it
    *   Otherwise:
        *   Discover the Kubernetes Service
        *   Use its port as `remote_port`
        *   Assign a **random free local port**
3.  Start port forwarding for **exactly the listed services**

### Errors (Hard Fail)

*   Service does not exist in cluster
*   Configured `local_port` is already in use by any process

***

## Forbidden Combinations (Fail Immediately)

*   `--group` and `--service` together
*   More than one `--group`

***

## Namespace Filtering

*   Namespace selection is used **only** in interactive `custom` mode
*   `--group` and `--service` always operate on explicit `namespace/name`
*   No implicit filtering or scoping

***

## Summary

*   One mode per invocation
*   No merging between groups and services
*   Config mappings are preferred but optional
*   Random ports are assigned only when no mapping exists
*   Fail fast on port conflicts (configured ports must be free)
*   No checking for already-running port-forward processes
*   Deterministic control flow
*   Fail fast, fail clearly

This specification intentionally prioritizes **clarity and correctness** over flexibility.
