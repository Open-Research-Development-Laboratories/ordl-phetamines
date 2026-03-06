# NIST 800-53 Moderate Control Objectives (Initial Mapping)

This map is implementation-oriented and evidence-based.

## Access Control
- AC-2: Account lifecycle via token issuance and tenant-scoped identity records.
- AC-3: Authorization enforcement via RBAC + ABAC evaluation.
- AC-6: Least privilege through seat-level role and compartment scoping.

## Audit and Accountability
- AU-2/AU-3: Event logging for governance and dispatch decisions.
- AU-10: Tamper-evident hash chaining in audit event records.

## Configuration Management
- CM-2: Baseline config in version-controlled infrastructure and app settings.
- CM-6: Security-relevant defaults (zero-trust ingress, signed extensions).

## Identification and Authentication
- IA-2: Bearer token auth with OIDC JWT validation (JWKS) and scoped principal mapping.
- IA-5: Vault-backed secret retrieval and secret-backed token signing/extension verification.

## System and Communications Protection
- SC-7: Ingress policy defaults to zero-trust.
- SC-8: Policy-token-based outbound gating.

## System and Information Integrity
- SI-4: Deterministic policy checks on outbound actions.
- SI-7: Signed extension registry enforcement.

## Evidence Plan
- API tests, authorization matrix tests, policy no-bypass tests, and digestion coverage reports are retained as acceptance artifacts.
