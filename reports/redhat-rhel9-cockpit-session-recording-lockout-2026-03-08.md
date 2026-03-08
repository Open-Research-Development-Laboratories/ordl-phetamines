# Red Hat Bug Report Draft

## Title

RHEL 9.7 / Cockpit 344: enabling session recording can leave local admin login unusable in Cockpit and SSH

## Classification

This looks like a product bug and availability issue, not a security vulnerability, based on current evidence.

## Severity

High operational impact for single-node admin access. The failure mode can lock an administrator out of normal SSH and Cockpit access after enabling session recording.

## Affected Environment

- Product: Red Hat Enterprise Linux 9.7 (Plow)
- Kernel: `5.14.0-611.36.1.el9_7.x86_64`
- Cockpit: `cockpit-ws-344-1.el9.x86_64`
- Cockpit System: `cockpit-system-344-1.el9.noarch`
- Authselect: `authselect-1.2.6-3.el9.x86_64`
- SSSD: `sssd-2.9.7-4.el9_7.1.x86_64`
- Session recording packages installed at the time of failure:
  - `cockpit-session-recording-20-1.el9.noarch`
  - `tlog-14-1.el9.x86_64`

## Summary

After enabling session recording through Cockpit on a RHEL 9.7 host, the system entered a state where:

- Cockpit login returned HTTP 500 with `Authentication failed: unsupported-shell`
- SSH password authentication succeeded, but the user session immediately failed before a usable shell was available
- SSH stderr showed:
  - `Failed loading "/etc/tlog/tlog-rec-session.conf"`
  - `Failed loading system configuration`

The host was still reachable and accepted the password, but normal admin login was effectively broken.

## Observed Evidence

### Cockpit

Direct login request returned:

```text
HTTP/1.1 500 Authentication failed: unsupported-shell
{"command":"init","version":1,"problem":"unsupported-shell"}
```

### SSH

SSH accepted the password, then the session failed with:

```text
Permission denied
Failed loading "/etc/tlog/tlog-rec-session.conf"
Failed loading system configuration
```

### Package and auth state

`dnf history info` shows the relevant session-recording packages were installed on March 7, 2026:

```text
Install tlog-14-1.el9.x86_64
Install cockpit-session-recording-20-1.el9.noarch
```

At the same time, the host auth profile was:

```text
Profile ID: sssd
Enabled features:
- with-files-domain
```

`system-auth` and `password-auth` contained `pam_sss.so` entries even though no working SSSD domain was configured.

## Impact

- Local admin could not reliably log in through Cockpit
- Local admin could not reliably obtain a usable SSH shell
- Recovery required console or rescue access
- This is especially serious on remote systems where Cockpit and SSH are the primary management paths

## Expected Behavior

Enabling session recording should not:

- leave the system dependent on an incomplete or nonfunctional SSSD profile
- leave the user in an unsupported shell state for Cockpit
- break SSH session startup due to `tlog-rec-session.conf` load failure

If extra packages or auth changes are required, the UI should validate prerequisites first and either:

- refuse the change with a clear error, or
- apply a fully working and reversible configuration

## Actual Behavior

The system accepted the session-recording change, but normal login paths became unusable afterward.

## Workaround / Recovery Used

The following actions restored access:

1. Reset the affected admin user shell to `/bin/bash`
2. Remove the session-recording packages:
   - `cockpit-session-recording`
   - `tlog`
3. Disable `sssd`
4. Change authselect from `sssd` to `minimal`

After recovery:

- Cockpit login returned HTTP 200 again
- SSH login worked normally
- `systemctl --failed` returned `0 loaded units listed`

## Notes

- The host was not using a real SSSD-backed identity domain
- The system was functioning before session recording was enabled
- The strongest field evidence is that enabling session recording left the system in a bad auth/session state involving `tlog` and `sssd`
- I cannot prove from retained artifacts whether the user shell itself was rewritten to a `tlog` wrapper or whether the failure came entirely from PAM/session startup, but the user-facing outcome was a full admin login breakage

## Suggested Questions For Engineering

1. Does `cockpit-session-recording` assume an `sssd`-based authselect profile even on local-only systems?
2. Can Cockpit enable recording in a way that leaves the target user with an unsupported shell for Cockpit?
3. Why is a broken or unreadable `tlog-rec-session.conf` able to terminate normal SSH session startup instead of failing safely?
4. Should the Cockpit session-recording UI validate `authselect`, `sssd`, and `tlog` prerequisites before applying changes?

## Minimal Reproduction Outline

1. Start from a RHEL 9.7 system using local users only
2. Install or enable Cockpit session recording
3. Apply recording for an admin user through the Cockpit UI
4. Attempt login via Cockpit and SSH
5. Observe whether:
   - Cockpit returns `unsupported-shell`
   - SSH accepts the password but fails during session startup with `tlog` configuration errors

## Requested Outcome

Please confirm whether this is a known issue and whether Red Hat recommends:

- a supported local-only session-recording configuration without SSSD
- a fix in Cockpit session-recording integration
- a fix in the failure mode so the system does not lock administrators out of SSH and Cockpit
