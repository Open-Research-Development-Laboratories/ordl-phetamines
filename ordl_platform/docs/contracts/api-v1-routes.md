# ORDL Backend /v1 Route Contract

Generated from FastAPI OpenAPI source. `/v1` is the source of truth for frontend wiring.

| Method | Path | Operation ID | Tags | Summary |
|---|---|---|---|---|
| POST | `/v1/approvals` | `create_approval_v1_approvals_post` | `approvals` | Create Approval |
| GET | `/v1/audit` | `list_policy_decisions_v1_audit_get` | `audit` | List Policy Decisions |
| GET | `/v1/audit/events` | `list_audit_events_v1_audit_events_get` | `audit` | List Audit Events |
| POST | `/v1/audit/evidence` | `create_evidence_package_v1_audit_evidence_post` | `audit` | Create Evidence Package |
| GET | `/v1/audit/export` | `export_audit_v1_audit_export_get` | `audit` | Export Audit |
| GET | `/v1/audit/verify` | `verify_project_audit_v1_audit_verify_get` | `audit` | Verify Project Audit |
| GET | `/v1/auth/me` | `auth_me_v1_auth_me_get` | `auth` | Auth Me |
| POST | `/v1/auth/token` | `issue_token_v1_auth_token_post` | `auth` | Issue Token |
| POST | `/v1/change-requests/{change_request_id}/decision` | `decide_change_request_v1_change_requests__change_request_id__decision_post` | `programs` | Decide Change Request |
| GET | `/v1/clearance/compartments` | `list_compartments_v1_clearance_compartments_get` | `clearance` | List Compartments |
| POST | `/v1/clearance/compartments` | `create_compartment_v1_clearance_compartments_post` | `clearance` | Create Compartment |
| GET | `/v1/clearance/compartments/{comp_id}` | `get_compartment_v1_clearance_compartments__comp_id__get` | `clearance` | Get Compartment |
| PUT | `/v1/clearance/compartments/{comp_id}` | `patch_compartment_v1_clearance_compartments__comp_id__put` | `clearance` | Patch Compartment |
| POST | `/v1/clearance/evaluate` | `evaluate_clearance_v1_clearance_evaluate_post` | `clearance` | Evaluate Clearance |
| PUT | `/v1/clearance/matrix` | `put_ntk_matrix_v1_clearance_matrix_put` | `clearance` | Put Ntk Matrix |
| GET | `/v1/clearance/matrix/export` | `export_clearance_matrix_v1_clearance_matrix_export_get` | `clearance` | Export Clearance Matrix |
| PUT | `/v1/clearance/ntk-matrix` | `put_ntk_matrix_alias_v1_clearance_ntk_matrix_put` | `clearance` | Put Ntk Matrix Alias |
| GET | `/v1/clearance/tiers` | `list_tiers_v1_clearance_tiers_get` | `clearance` | List Tiers |
| PUT | `/v1/clearance/tiers` | `put_tiers_v1_clearance_tiers_put` | `clearance` | Put Tiers |
| GET | `/v1/clearance/tiers/{tier_id}` | `get_tier_v1_clearance_tiers__tier_id__get` | `clearance` | Get Tier |
| PUT | `/v1/clearance/tiers/{tier_id}` | `patch_tier_v1_clearance_tiers__tier_id__put` | `clearance` | Patch Tier |
| POST | `/v1/digestion/export/{project_id}` | `export_digestion_report_v1_digestion_export__project_id__post` | `digestion` | Export Digestion Report |
| GET | `/v1/digestion/gate/{project_id}` | `digestion_gate_v1_digestion_gate__project_id__get` | `digestion` | Digestion Gate |
| POST | `/v1/digestion/run` | `run_digestion_v1_digestion_run_post` | `digestion` | Run Digestion |
| GET | `/v1/digestion/status/{project_id}` | `digestion_status_v1_digestion_status__project_id__get` | `digestion` | Digestion Status |
| GET | `/v1/dispatch` | `list_dispatch_v1_dispatch_get` | `dispatch` | List Dispatch |
| POST | `/v1/dispatch` | `dispatch_work_v1_dispatch_post` | `dispatch` | Dispatch Work |
| GET | `/v1/dispatch/executions/{execution_id}/events` | `list_execution_events_v1_dispatch_executions__execution_id__events_get` | `dispatch` | List Execution Events |
| GET | `/v1/dispatch/executions/{execution_id}/stream` | `stream_execution_events_v1_dispatch_executions__execution_id__stream_get` | `dispatch` | Stream Execution Events |
| GET | `/v1/dispatch/results` | `list_dispatch_results_v1_dispatch_results_get` | `dispatch` | List Dispatch Results |
| POST | `/v1/dispatch/{dispatch_request_id}/execute` | `execute_dispatch_v1_dispatch__dispatch_request_id__execute_post` | `dispatch` | Execute Dispatch |
| GET | `/v1/dispatch/{dispatch_request_id}/executions` | `list_dispatch_executions_v1_dispatch__dispatch_request_id__executions_get` | `dispatch` | List Dispatch Executions |
| GET | `/v1/extensions` | `list_extensions_v1_extensions_get` | `extensions` | List Extensions |
| POST | `/v1/extensions` | `register_extension_v1_extensions_post` | `extensions` | Register Extension |
| POST | `/v1/extensions/batch` | `batch_extensions_v1_extensions_batch_post` | `extensions` | Batch Extensions |
| POST | `/v1/extensions/verify` | `verify_extensions_v1_extensions_verify_post` | `extensions` | Verify Extensions |
| POST | `/v1/extensions/{extension_id}/status` | `set_extension_status_v1_extensions__extension_id__status_post` | `extensions` | Set Extension Status |
| GET | `/v1/info` | `info_v1_info_get` | `ops` | Info |
| GET | `/v1/jobs/runs` | `list_job_runs_v1_jobs_runs_get` | `orchestration` | List Job Runs |
| POST | `/v1/jobs/runs` | `create_job_run_v1_jobs_runs_post` | `orchestration` | Create Job Run |
| GET | `/v1/jobs/runs/{job_run_id}/artifacts` | `get_job_run_artifacts_v1_jobs_runs__job_run_id__artifacts_get` | `orchestration` | Get Job Run Artifacts |
| POST | `/v1/jobs/runs/{job_run_id}/cancel` | `cancel_job_run_v1_jobs_runs__job_run_id__cancel_post` | `orchestration` | Cancel Job Run |
| GET | `/v1/jobs/runs/{job_run_id}/delivery` | `list_job_delivery_receipts_v1_jobs_runs__job_run_id__delivery_get` | `orchestration` | List Job Delivery Receipts |
| POST | `/v1/jobs/runs/{job_run_id}/delivery` | `record_job_delivery_v1_jobs_runs__job_run_id__delivery_post` | `orchestration` | Record Job Delivery |
| POST | `/v1/jobs/runs/{job_run_id}/state` | `transition_job_run_state_v1_jobs_runs__job_run_id__state_post` | `orchestration` | Transition Job Run State |
| GET | `/v1/jobs/templates` | `list_job_templates_v1_jobs_templates_get` | `orchestration` | List Job Templates |
| POST | `/v1/jobs/templates` | `create_job_template_v1_jobs_templates_post` | `orchestration` | Create Job Template |
| GET | `/v1/messages` | `list_messages_v1_messages_get` | `messages` | List Messages |
| POST | `/v1/messages` | `create_message_v1_messages_post` | `messages` | Create Message |
| DELETE | `/v1/messages/{message_id}` | `delete_message_v1_messages__message_id__delete` | `messages` | Delete Message |
| GET | `/v1/messages/{message_id}` | `get_message_v1_messages__message_id__get` | `messages` | Get Message |
| PATCH | `/v1/messages/{message_id}` | `update_message_v1_messages__message_id__patch` | `messages` | Update Message |
| POST | `/v1/messages/{message_id}/transition` | `transition_message_v1_messages__message_id__transition_post` | `messages` | Transition Message |
| POST | `/v1/models/deployments` | `create_model_deployment_v1_models_deployments_post` | `models` | Create Model Deployment |
| GET | `/v1/models/evals/runs` | `list_eval_runs_v1_models_evals_runs_get` | `models` | List Eval Runs |
| POST | `/v1/models/evals/runs` | `create_eval_run_v1_models_evals_runs_post` | `models` | Create Eval Run |
| GET | `/v1/models/evals/runs/{eval_run_id}` | `get_eval_run_v1_models_evals_runs__eval_run_id__get` | `models` | Get Eval Run |
| GET | `/v1/models/fine-tunes` | `list_fine_tune_runs_v1_models_fine_tunes_get` | `models` | List Fine Tune Runs |
| POST | `/v1/models/fine-tunes` | `create_fine_tune_run_v1_models_fine_tunes_post` | `models` | Create Fine Tune Run |
| GET | `/v1/models/fine-tunes/{fine_tune_run_id}` | `get_fine_tune_run_v1_models_fine_tunes__fine_tune_run_id__get` | `models` | Get Fine Tune Run |
| POST | `/v1/models/fine-tunes/{fine_tune_run_id}/state` | `update_fine_tune_state_v1_models_fine_tunes__fine_tune_run_id__state_post` | `models` | Update Fine Tune State |
| GET | `/v1/models/promotions` | `list_model_promotions_v1_models_promotions_get` | `models` | List Model Promotions |
| POST | `/v1/models/promotions` | `create_model_promotion_v1_models_promotions_post` | `models` | Create Model Promotion |
| GET | `/v1/orchestration/profiles` | `list_orchestration_profiles_v1_orchestration_profiles_get` | `orchestration` | List Orchestration Profiles |
| POST | `/v1/orchestration/profiles` | `create_orchestration_profile_v1_orchestration_profiles_post` | `orchestration` | Create Orchestration Profile |
| GET | `/v1/orgs` | `list_orgs_v1_orgs_get` | `governance` | List Orgs |
| POST | `/v1/orgs` | `create_org_v1_orgs_post` | `governance` | Create Org |
| GET | `/v1/orgs/board` | `list_org_board_v1_orgs_board_get` | `governance` | List Org Board |
| POST | `/v1/orgs/board` | `add_org_board_member_v1_orgs_board_post` | `governance` | Add Org Board Member |
| DELETE | `/v1/orgs/board/{member_id}` | `delete_org_board_member_v1_orgs_board__member_id__delete` | `governance` | Delete Org Board Member |
| PATCH | `/v1/orgs/board/{member_id}` | `patch_org_board_member_v1_orgs_board__member_id__patch` | `governance` | Patch Org Board Member |
| GET | `/v1/orgs/board/{member_id}/history` | `org_board_member_history_v1_orgs_board__member_id__history_get` | `governance` | Org Board Member History |
| GET | `/v1/orgs/current` | `get_current_org_v1_orgs_current_get` | `governance` | Get Current Org |
| PATCH | `/v1/orgs/current` | `patch_current_org_v1_orgs_current_patch` | `governance` | Patch Current Org |
| GET | `/v1/orgs/policy-defaults` | `get_org_policy_defaults_v1_orgs_policy_defaults_get` | `governance` | Get Org Policy Defaults |
| PUT | `/v1/orgs/policy-defaults` | `put_org_policy_defaults_v1_orgs_policy_defaults_put` | `governance` | Put Org Policy Defaults |
| GET | `/v1/orgs/regions` | `list_org_regions_v1_orgs_regions_get` | `governance` | List Org Regions |
| POST | `/v1/orgs/regions` | `add_org_region_v1_orgs_regions_post` | `governance` | Add Org Region |
| PATCH | `/v1/orgs/regions/{code}` | `patch_org_region_v1_orgs_regions__code__patch` | `governance` | Patch Org Region |
| GET | `/v1/orgs/{org_id}` | `get_org_by_id_v1_orgs__org_id__get` | `governance` | Get Org By Id |
| PUT | `/v1/orgs/{org_id}` | `put_org_by_id_v1_orgs__org_id__put` | `governance` | Put Org By Id |
| PUT | `/v1/orgs/{org_id}/defaults` | `put_org_defaults_by_id_v1_orgs__org_id__defaults_put` | `governance` | Put Org Defaults By Id |
| POST | `/v1/orgs/{org_id}/members` | `add_org_member_by_id_v1_orgs__org_id__members_post` | `governance` | Add Org Member By Id |
| POST | `/v1/orgs/{org_id}/regions` | `add_org_region_by_id_v1_orgs__org_id__regions_post` | `governance` | Add Org Region By Id |
| POST | `/v1/policy/decide` | `policy_decide_v1_policy_decide_post` | `policy` | Policy Decide |
| POST | `/v1/policy/validate` | `policy_validate_v1_policy_validate_post` | `policy` | Policy Validate |
| GET | `/v1/programs` | `list_programs_v1_programs_get` | `programs` | List Programs |
| POST | `/v1/programs` | `create_program_v1_programs_post` | `programs` | Create Program |
| GET | `/v1/programs/{program_id}` | `get_program_v1_programs__program_id__get` | `programs` | Get Program |
| GET | `/v1/programs/{program_id}/milestones` | `list_program_milestones_v1_programs__program_id__milestones_get` | `programs` | List Program Milestones |
| POST | `/v1/programs/{program_id}/milestones` | `create_program_milestone_v1_programs__program_id__milestones_post` | `programs` | Create Program Milestone |
| GET | `/v1/programs/{program_id}/risks` | `list_program_risks_v1_programs__program_id__risks_get` | `programs` | List Program Risks |
| POST | `/v1/programs/{program_id}/risks` | `create_program_risk_v1_programs__program_id__risks_post` | `programs` | Create Program Risk |
| GET | `/v1/projects` | `list_projects_v1_projects_get` | `governance` | List Projects |
| POST | `/v1/projects` | `create_project_v1_projects_post` | `governance` | Create Project |
| GET | `/v1/projects/{project_id}` | `get_project_v1_projects__project_id__get` | `governance` | Get Project |
| GET | `/v1/projects/{project_id}/change-requests` | `list_change_requests_v1_projects__project_id__change_requests_get` | `programs` | List Change Requests |
| POST | `/v1/projects/{project_id}/change-requests` | `create_change_request_v1_projects__project_id__change_requests_post` | `programs` | Create Change Request |
| PUT | `/v1/projects/{project_id}/defaults` | `put_project_defaults_v1_projects__project_id__defaults_put` | `governance` | Put Project Defaults |
| GET | `/v1/projects/{project_id}/policy-profiles` | `get_project_policy_profiles_v1_projects__project_id__policy_profiles_get` | `governance` | Get Project Policy Profiles |
| PUT | `/v1/projects/{project_id}/policy-profiles` | `put_project_policy_profiles_v1_projects__project_id__policy_profiles_put` | `governance` | Put Project Policy Profiles |
| POST | `/v1/protocols/bootstrap/adopted` | `bootstrap_adopted_protocols_v1_protocols_bootstrap_adopted_post` | `protocols` | Bootstrap Adopted Protocols |
| GET | `/v1/protocols/compatibility` | `get_protocol_compatibility_v1_protocols_compatibility_get` | `protocols` | Get Protocol Compatibility |
| GET | `/v1/protocols/conformance/runs` | `list_protocol_conformance_runs_v1_protocols_conformance_runs_get` | `protocols` | List Protocol Conformance Runs |
| POST | `/v1/protocols/conformance/runs` | `create_protocol_conformance_run_v1_protocols_conformance_runs_post` | `protocols` | Create Protocol Conformance Run |
| GET | `/v1/protocols/standards` | `list_protocol_standards_v1_protocols_standards_get` | `protocols` | List Protocol Standards |
| POST | `/v1/protocols/standards` | `create_protocol_standard_v1_protocols_standards_post` | `protocols` | Create Protocol Standard |
| GET | `/v1/protocols/standards/{standard_id}/versions` | `list_protocol_standard_versions_v1_protocols_standards__standard_id__versions_get` | `protocols` | List Protocol Standard Versions |
| POST | `/v1/protocols/standards/{standard_id}/versions` | `create_protocol_standard_version_v1_protocols_standards__standard_id__versions_post` | `protocols` | Create Protocol Standard Version |
| POST | `/v1/protocols/validate` | `validate_protocol_requirements_v1_protocols_validate_post` | `protocols` | Validate Protocol Requirements |
| GET | `/v1/providers` | `list_providers_v1_providers_get` | `providers` | List Providers |
| POST | `/v1/providers` | `create_provider_profile_v1_providers_post` | `providers` | Create Provider Profile |
| GET | `/v1/providers/credentials` | `list_credentials_v1_providers_credentials_get` | `providers` | List Credentials |
| POST | `/v1/providers/credentials` | `upsert_credentials_v1_providers_credentials_post` | `providers` | Upsert Credentials |
| GET | `/v1/providers/credentials/{provider}` | `get_credential_v1_providers_credentials__provider__get` | `providers` | Get Credential |
| POST | `/v1/providers/failover` | `force_failover_v1_providers_failover_post` | `providers` | Force Failover |
| GET | `/v1/providers/priority` | `get_provider_priority_v1_providers_priority_get` | `providers` | Get Provider Priority |
| PATCH | `/v1/providers/priority` | `put_provider_priority_v1_providers_priority_patch` | `providers` | Put Provider Priority |
| PUT | `/v1/providers/priority` | `put_provider_priority_v1_providers_priority_put` | `providers` | Put Provider Priority |
| PUT | `/v1/providers/probes` | `put_provider_probes_v1_providers_probes_put` | `providers` | Put Provider Probes |
| PUT | `/v1/providers/{id}/config` | `put_provider_config_alias_v1_providers__id__config_put` | `providers` | Put Provider Config Alias |
| POST | `/v1/providers/{id}/test` | `test_provider_alias_v1_providers__id__test_post` | `providers` | Test Provider Alias |
| DELETE | `/v1/providers/{provider}` | `delete_provider_profile_v1_providers__provider__delete` | `providers` | Delete Provider Profile |
| GET | `/v1/providers/{provider}` | `get_provider_profile_v1_providers__provider__get` | `providers` | Get Provider Profile |
| PATCH | `/v1/providers/{provider}` | `patch_provider_profile_v1_providers__provider__patch` | `providers` | Patch Provider Profile |
| PUT | `/v1/providers/{provider}/config` | `put_provider_config_v1_providers__provider__config_put` | `providers` | Put Provider Config |
| GET | `/v1/providers/{provider}/logs` | `provider_logs_v1_providers__provider__logs_get` | `providers` | Provider Logs |
| GET | `/v1/providers/{provider}/probes` | `get_provider_probes_v1_providers__provider__probes_get` | `providers` | Get Provider Probes |
| POST | `/v1/providers/{provider}/probes` | `create_provider_probe_v1_providers__provider__probes_post` | `providers` | Create Provider Probe |
| PATCH | `/v1/providers/{provider}/probes/{probe_id}` | `patch_provider_probe_v1_providers__provider__probes__probe_id__patch` | `providers` | Patch Provider Probe |
| POST | `/v1/providers/{provider}/test` | `test_provider_v1_providers__provider__test_post` | `providers` | Test Provider |
| GET | `/v1/seats` | `list_seats_v1_seats_get` | `seats` | List Seats |
| POST | `/v1/seats` | `create_seat_v1_seats_post` | `seats` | Create Seat |
| POST | `/v1/seats/bulk` | `bulk_assign_seats_v1_seats_bulk_post` | `seats` | Bulk Assign Seats |
| PUT | `/v1/seats/matrix` | `update_seat_matrix_v1_seats_matrix_put` | `seats` | Update Seat Matrix |
| PUT | `/v1/seats/{seat_id}` | `update_seat_v1_seats__seat_id__put` | `seats` | Update Seat |
| POST | `/v1/seats/{seat_id}/assign` | `assign_seat_v1_seats__seat_id__assign_post` | `seats` | Assign Seat |
| POST | `/v1/seats/{seat_id}/vacate` | `vacate_seat_v1_seats__seat_id__vacate_post` | `seats` | Vacate Seat |
| GET | `/v1/teams` | `list_teams_v1_teams_get` | `governance` | List Teams |
| POST | `/v1/teams` | `create_team_v1_teams_post` | `governance` | Create Team |
| PUT | `/v1/teams/{team_id}/scope` | `put_team_scope_matrix_v1_teams__team_id__scope_put` | `governance` | Put Team Scope Matrix |
| GET | `/v1/worker-groups` | `list_worker_groups_v1_worker_groups_get` | `orchestration` | List Worker Groups |
| POST | `/v1/worker-groups` | `create_worker_group_v1_worker_groups_post` | `orchestration` | Create Worker Group |
| GET | `/v1/workers` | `list_workers_v1_workers_get` | `workers` | List Workers |
| POST | `/v1/workers/actions/{action_id}/ack` | `acknowledge_worker_action_v1_workers_actions__action_id__ack_post` | `workers` | Acknowledge Worker Action |
| GET | `/v1/workers/connectivity` | `list_worker_connectivity_v1_workers_connectivity_get` | `workers` | List Worker Connectivity |
| GET | `/v1/workers/discovery/scans` | `list_discovery_scans_v1_workers_discovery_scans_get` | `workers` | List Discovery Scans |
| POST | `/v1/workers/discovery/scans` | `create_discovery_scan_v1_workers_discovery_scans_post` | `workers` | Create Discovery Scan |
| GET | `/v1/workers/discovery/scans/{scan_id}` | `get_discovery_scan_v1_workers_discovery_scans__scan_id__get` | `workers` | Get Discovery Scan |
| GET | `/v1/workers/monitor/config` | `get_worker_monitor_config_v1_workers_monitor_config_get` | `workers` | Get Worker Monitor Config |
| POST | `/v1/workers/monitor/config` | `upsert_worker_monitor_config_v1_workers_monitor_config_post` | `workers` | Upsert Worker Monitor Config |
| POST | `/v1/workers/monitor/run-once` | `run_worker_monitor_once_v1_workers_monitor_run_once_post` | `workers` | Run Worker Monitor Once |
| POST | `/v1/workers/register` | `register_worker_v1_workers_register_post` | `workers` | Register Worker |
| GET | `/v1/workers/update-bundles` | `list_update_bundles_v1_workers_update_bundles_get` | `workers` | List Update Bundles |
| POST | `/v1/workers/update-bundles` | `create_update_bundle_v1_workers_update_bundles_post` | `workers` | Create Update Bundle |
| GET | `/v1/workers/update-bundles/{bundle_id}` | `get_update_bundle_v1_workers_update_bundles__bundle_id__get` | `workers` | Get Update Bundle |
| GET | `/v1/workers/update-campaigns` | `list_update_campaigns_v1_workers_update_campaigns_get` | `workers` | List Update Campaigns |
| POST | `/v1/workers/update-campaigns` | `create_update_campaign_v1_workers_update_campaigns_post` | `workers` | Create Update Campaign |
| GET | `/v1/workers/update-campaigns/{campaign_id}/executions` | `list_update_campaign_executions_v1_workers_update_campaigns__campaign_id__executions_get` | `workers` | List Update Campaign Executions |
| POST | `/v1/workers/update-campaigns/{campaign_id}/rollback` | `rollback_update_campaign_v1_workers_update_campaigns__campaign_id__rollback_post` | `workers` | Rollback Update Campaign |
| POST | `/v1/workers/update-campaigns/{campaign_id}/start` | `start_update_campaign_v1_workers_update_campaigns__campaign_id__start_post` | `workers` | Start Update Campaign |
| POST | `/v1/workers/{worker_id}/action` | `queue_worker_action_v1_workers__worker_id__action_post` | `workers` | Queue Worker Action |
| GET | `/v1/workers/{worker_id}/actions/pending` | `list_pending_worker_actions_v1_workers__worker_id__actions_pending_get` | `workers` | List Pending Worker Actions |
| POST | `/v1/workers/{worker_id}/heartbeat` | `worker_heartbeat_v1_workers__worker_id__heartbeat_post` | `workers` | Worker Heartbeat |
| POST | `/v1/workers/{worker_id}/probe` | `worker_probe_v1_workers__worker_id__probe_post` | `workers` | Worker Probe |
