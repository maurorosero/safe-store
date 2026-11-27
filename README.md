# Safe Store

![Safe Store](assets/banner.png)

[![CI][ci-badge]][ci-url]
[![Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![HACS Custom][hacs-badge]][hacs-url]

An encryption layer for the credentials of Home Assistant integrations.

Home Assistant keeps every integration password and API token in plain text
inside `.storage/core.config_entries`. That file is readable by any local user,
it is copied into every backup, and the gap has been open upstream since
November 2026 — [home-assistant/core#191977](https://github.com/home-assistant/core/issues/191977),
unassigned and uncommented. Core protects `.storage/auth` with `0600` and leaves
`core.config_entries` at `0644`: the file that holds the credentials is the one
with the loosest permissions.

**Status: 0.2.11.** Installed from this repository on a clean Home Assistant OS
18.4 (core 2026.11) with no manual steps: the app generates the master key, the
integration asks for it over HTTP, and 11 entries came back `loaded` after a
full reboot of the machine. With the app down and the file encrypted, it writes
nothing and stays in `setup_retry` instead of falling back to a new key. See
[Status](#status) for what is and is not exercised.

## What it does

- Encrypts the `data` field of every config entry with AES-256-GCM before it
  reaches the disk, and decrypts it in memory at startup.
- Leaves `entry_id`, `domain`, `title` and `version` readable: Home Assistant
  can still list your integrations without being able to read a single secret.
- Keeps the master key out of Home Assistant. A companion app holds it and
  hands it over the local network with a token.
- Accepts the key from a plain file or from a SOPS-encrypted env file unlocked
  with an age identity that is deliberately excluded from backups.
- Enables through the interface (config flow) — no `configuration.yaml`, no
  changes to any integration.

## How it works

```
boot
  companion app          serves the master key over HTTP, token required
  core reads the file    data arrives encrypted: {"__ss_v1__": "<blob>"}
  Safe Store loads       decrypts the live entries and reloads them
  → integrations come back up

every save
  data is encrypted before writing → no plaintext on disk
```

The component replaces `ConfigEntries` at runtime and overrides how the file is
serialised. Integrations are not modified and do not know it exists.

## Installation

### Companion app

[![Add repository to your instance][add-repo-badge]][add-repo-url]

Settings → Apps → Repositories → add `https://github.com/maurorosero/safe-store`,
then install **Safe Store Unlocker**.

Then open its **Configuration** tab and paste the master key in `master_key`:

```sh
python3 -c "import os;print(os.urandom(32).hex())"
```

Leave it empty and the app generates one on the first request, prints it once in
its log, and keeps it in `/data/master.key`. `/data` is not in Home Assistant
backups, so a restore brings the file back without the key: paste the value into
this field and the key travels with the configuration. See
[The master key](#the-master-key).

For SOPS instead of a plain key, put `age.key` and `secrets.env.enc` (with
`SAFE_STORE_MASTER_KEY`) in `/data` through the SSH or Samba app. The age
identity is excluded from backups on purpose.

### Integration

[![Add repository to HACS][add-hacs-badge]][add-hacs-url]

1. Open **Marketplace**, accept the warning, then **Add from link** and paste
   `https://github.com/maurorosero/safe-store`.
2. The Marketplace asks you to connect GitHub first. It hands you a code to
   enter at `github.com/login/device`; once linked, the repository is added.
3. Install **Safe Store** and restart Home Assistant.
4. Settings → Devices & services → **Add integration** → *Safe Store*. Leave
   the flow empty: the integration finds the app on its own.

Once the integration is set up it creates `/config/.ss.token` (600) and asks the
app for the master key. If the app has none yet, it generates one and keeps it
in `/data/master.key`. There is nothing to paste.

[ci-badge]: https://github.com/maurorosero/safe-store/actions/workflows/ci.yml/badge.svg?branch=main
[ci-url]: https://github.com/maurorosero/safe-store/actions/workflows/ci.yml
[release-badge]: https://img.shields.io/github/v/release/maurorosero/safe-store
[release-url]: https://github.com/maurorosero/safe-store/releases
[license-badge]: https://img.shields.io/github/license/maurorosero/safe-store
[license-url]: LICENSE
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[add-repo-badge]: https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg
[add-repo-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fmaurorosero%2Fsafe-store
[add-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[add-hacs-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=maurorosero&repository=safe-store&category=integration

## The master key

One key protects everything. A few things about it are worth reading twice:

- **Where it lives.** In the app's **Configuration** tab (`master_key`), or in
  `/data/master.key` when you leave that field empty and let the app generate one.
- **You see it once.** The app prints it to its log the first time it generates it,
  with a warning. It is not shown again.
- **It is not in your backups.** `/data` is excluded from Home Assistant backups on
  purpose: a backup carrying both the encrypted file and its key would protect
  nothing. That means a restore brings the encrypted file back **without** the key —
  and if `master_key` is empty, every integration comes back unreadable.
- **Keep a copy outside Home Assistant.** A password manager, or a secrets manager
  such as Infisical. Copy it the moment it appears in the log.

Losing the key is not recoverable here: `safe_store.dump` needs it too. The file on
disk is not a backup of the key in any sense.

### Getting the key out, and back in

The app has a web interface: Settings → Apps → Safe Store Unlocker → **Open web UI**.

- **Your key.** It shows the fingerprint and a **Download QR** button. That PNG *is* the
  key: print it, keep it in a safe, or upload it to a secrets manager such as Infisical.
  You can download it again at any time while the app still holds the key.
- **Restore from a file.** Upload that PNG. The app reads the QR, writes the key into its
  own configuration and restarts. Configuration travels in backups, so after restoring
  once the key no longer lives only in `/data`.

If the page warns that the key has no downloaded copy, that is the one thing to fix
today: `/data` is not in your backups, and the QR is the only way back.

## Services

### `safe_store.dump`

Writes every credential, decrypted, to `/config/.ss_dump.json` with `600`.
**Required before uninstalling**: without the key, the encrypted file cannot be
read by anything.

```yaml
action: safe_store.dump
```

## Status

| Piece | State |
|---|---|
| Encryption, decryption, reload | verified on HAOS 18.4 / core 2026.11 |
| Integration ↔ add-on over HTTP | verified: the app generates the key, the integration fetches it |
| Fresh install from the repository, no manual steps | verified on a clean HAOS 18.4 |
| Full reboot of the machine | verified: 11 of 11 entries `loaded` |
| Save after a restart | verified: the new entry is written encrypted |
| App down with the file encrypted | verified: nothing is written, the entry stays in `setup_retry`, no local key is created |
| `safe_store.dump` | verified on the POC build, **not re-run on 0.2.10** |
| Add-on image | builds, published to ghcr.io |
| Master key rotation | **not implemented** |

If the app is unavailable and the file is encrypted, Safe Store **writes
nothing** and the entries stay in `setup_retry`. A save with half-encrypted data
would corrupt every integration at once.

## What it does not do

- It does not touch `secrets.yaml` — that file does not go through this path.
- It does not defend against root on the machine that holds the key. A process
  that needs a secret in the clear to authenticate cannot be protected by
  encrypting the file next to it.
- It does not encrypt `hassio`: the Supervisor rewrites that entry's `data` on
  every boot.

## Troubleshooting

**Integrations stuck in `setup_retry` after boot**
The app is not delivering the key. Check Settings → Apps → Safe Store Unlocker →
Log. `/config/.ss.key` appearing means the integration fell back to a local key:
that file and the one in the app are not the same, so a file encrypted with one
cannot be read with the other.

**I want to uninstall**
Run `safe_store.dump` first, confirm `.ss_dump.json` has the credentials, then
uninstall.

**I lost the master key**
The file cannot be read by anything, and `dump` needs the key too. The only way
out is a backup of the key you kept outside Home Assistant.

**I changed the master key**
There is no rotation yet: the file becomes unreadable. Restore the previous key,
run `dump`, and re-encrypt from a clean state.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Workflow is `tema/*` → `devs` → `main`,
and a release is a tag on the merge commit of `main`.

## License

MIT — see [LICENSE](LICENSE).
