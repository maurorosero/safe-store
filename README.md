# Safe Store

![Safe Store](assets/banner.png)

An encryption layer for the credentials of Home Assistant integrations.

Home Assistant keeps every integration password and API token in plain text
inside `.storage/core.config_entries`. That file is readable by any local user,
it is copied into every backup, and the gap has been open upstream since
November 2026 — [home-assistant/core#191977](https://github.com/home-assistant/core/issues/191977),
unassigned and uncommented. Core protects `.storage/auth` with `0600` and leaves
`core.config_entries` at `0644`: the file that holds the credentials is the one
with the loosest permissions.

**Status: 0.2.0, pre-release.** The integration is verified end to end on Home
Assistant OS 18.4 (core 2026.11): it encrypts on save, decrypts at startup,
reloads the affected entries, survives restarts, and `safe_store.dump` restores
plaintext for uninstalling. The companion app is published and builds; the
full path — integration asking the app for the key over HTTP — **has not been
exercised yet**. See [Status](#status) below.

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

Leave it empty and the app generates one on first start, prints it once in its
log, and keeps it in `/data/master.key`. Paste that value back into the
configuration so it survives a restore — `/data` is not the place where a key
should live alone.

For SOPS instead of a plain key, put `age.key` and `secrets.env.enc` (with
`SAFE_STORE_MASTER_KEY`) in `/data` through the SSH or Samba app. The age
identity is excluded from backups on purpose.

### Integration

[![Add repository to HACS][add-hacs-badge]][add-hacs-url]

1. Marketplace → Repositories → add `https://github.com/maurorosero/safe-store`.
2. Install **Safe Store** and restart Home Assistant.
3. Settings → Devices & services → **Add integration** → *Safe Store*.

[add-repo-badge]: https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg
[add-repo-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fmaurorosero%2Fsafe-store
[add-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[add-hacs-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=maurorosero&repository=safe-store&category=integration

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
| `safe_store.dump` | verified |
| Restarts with encrypted file | verified |
| Add-on image | builds, published to ghcr.io |
| Integration ↔ add-on over HTTP | **not exercised** |
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
Log.

**I want to uninstall**
Run `safe_store.dump` first, confirm `.ss_dump.json` has the credentials, then
uninstall.

**I changed the master key**
There is no rotation yet: the file becomes unreadable. Restore the previous key,
run `dump`, and re-encrypt from a clean state.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Workflow is `tema/*` → `devs` → `main`,
and a release is a tag on the merge commit of `main`.

## License

MIT — see [LICENSE](LICENSE).
