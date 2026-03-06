# Revision 8 Contract Review

Comparison between declared Rev8 contract matrix and generated backend `/v1` contract.

- required routes parsed: `37`
- present routes: `37`
- missing routes: `0`

## Missing Routes

| Method | Path |
|---|---|

## Present Routes

| Method | Path |
|---|---|
| `GET` | `/v1/audit/events` |
| `GET` | `/v1/audit/export` |
| `GET` | `/v1/clearance/compartments` |
| `GET` | `/v1/clearance/compartments/{comp_id}` |
| `GET` | `/v1/clearance/matrix/export` |
| `GET` | `/v1/clearance/tiers` |
| `GET` | `/v1/clearance/tiers/{tier_id}` |
| `GET` | `/v1/orgs/{org_id}` |
| `POST` | `/v1/audit/evidence` |
| `POST` | `/v1/clearance/compartments` |
| `POST` | `/v1/extensions` |
| `POST` | `/v1/extensions/batch` |
| `POST` | `/v1/extensions/verify` |
| `POST` | `/v1/orgs/{org_id}/members` |
| `POST` | `/v1/orgs/{org_id}/regions` |
| `POST` | `/v1/policy/decide` |
| `POST` | `/v1/projects` |
| `POST` | `/v1/providers` |
| `POST` | `/v1/providers/{id}/test` |
| `POST` | `/v1/seats` |
| `POST` | `/v1/seats/bulk` |
| `POST` | `/v1/seats/{seat_id}/assign` |
| `POST` | `/v1/seats/{seat_id}/vacate` |
| `POST` | `/v1/teams` |
| `PUT` | `/v1/clearance/compartments/{comp_id}` |
| `PUT` | `/v1/clearance/matrix` |
| `PUT` | `/v1/clearance/tiers` |
| `PUT` | `/v1/clearance/tiers/{tier_id}` |
| `PUT` | `/v1/orgs/{org_id}` |
| `PUT` | `/v1/orgs/{org_id}/defaults` |
| `PUT` | `/v1/projects/{project_id}/defaults` |
| `PUT` | `/v1/providers/priority` |
| `PUT` | `/v1/providers/probes` |
| `PUT` | `/v1/providers/{id}/config` |
| `PUT` | `/v1/seats/matrix` |
| `PUT` | `/v1/seats/{seat_id}` |
| `PUT` | `/v1/teams/{team_id}/scope` |
