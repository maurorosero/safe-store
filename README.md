# Safe Store

![Safe Store](assets/banner.png)

[![CI][ci-badge]][ci-url]
[![Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Marketplace][market-badge]][market-url]

An encryption layer for the credentials of Home Assistant integrations.

Home Assistant keeps every integration password and API token in plain text
inside `.storage/core.config_entries`. That file is readable by any local user,
it is copied into every backup, and the gap has been open upstream since
November 2026 — [home-assistant/core#191977](https://github.com/home-assistant/core/issues/191977),
unassigned and uncommented. Core protects `.storage/auth` with `0600` and leaves
`core.config_entries` at `0644`: the file that holds the credentials is the one
with the loosest permissions.

**Status: 0.2.25.** Running on a real Home Assistant OS 18.4 (core 2026.11.2)
with 24 configuration entries, all `loaded`. The app installs from this
repository pulling a published image, not compiling. See [Status](#status) for
what is and is not exercised.

## Read this first

- **It hooks a private method.** The component replaces `ConfigEntries` at
  runtime and overrides `_data_to_save`. That is not a public interface. **A
  Home Assistant update can break it**, and when that happens the entries stop
  loading instead of coming up unencrypted — by design, but it is still an
  outage you have to fix. If that trade is not acceptable to you, don't run it.
- **The key lives on the same host**, readable by the app at `0600`. A process
  that can read the key can read the credentials. This first scope protects the
  file at rest and in backups; keeping the key off the box is a later problem.
- **It covers config entry `data` only.** `secrets.yaml` is not touched.

If you decide to run it, run `safe_store.dump` before uninstalling, and keep a
copy of the master key outside Home Assistant. Without the key nothing can read
the file, and there is no recovery built in.

## What it does

- Encrypts the `data` field of every config entry with AES-256-GCM before it
  reaches the disk, and decrypts it in memory at startup.
- Leaves `entry_id`, `domain`, `title` and `version` readable: Home Assistant
  can still list your integrations without being able to read a single secret.
- Keeps the master key out of the encrypted file. A companion app holds it in
  `/data/master.key` (`0600`), a path excluded from backups, and hands it to the
  integration over the local network with a token.
- Gives you the key in a form you can store offline: a QR, downloadable from a
  panel, administrator only, restorable by uploading that PNG.
- Installs through the interface: no `configuration.yaml`, no changes to any
  integration.

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

Integrations are not modified and do not know it exists.

## Installation

The app goes first, the integration second: the integration has no key of its
own, it asks the app for one.

### Step 1 · Add the app repository

1. **Settings → Apps**.
2. Open the **Repositories** tab, at the top of the page. This is neither the
   Marketplace nor HACS.
3. Press **+ Add**, paste `https://github.com/maurorosero/safe-store` and
   confirm.
4. The list now shows **Safe Store Apps · Mauro Rosero**.

If that row is not there, the repository was not added and the app will not
exist in the store. This is the step that gets skipped most often.

### Step 2 · Install the app

1. Still in **Apps**, search for **Safe Store Unlocker**.
2. **Install**, then **Start**. The image is downloaded, so it takes seconds.
3. Open the **Log** tab. It must say `secrets-unlocker escuchando en :8099`.

Nothing to paste: on first use the app generates the master key, stores it in
`/data/master.key` with `0600`, and hands it to the integration.

### Step 3 · Install the integration

[![Add repository to HACS][add-hacs-badge]][add-hacs-url]

1. Open **Marketplace**, accept the warning, then **Add from link** and paste
   `https://github.com/maurorosero/safe-store`.
2. Marketplace asks you to connect GitHub first and gives you a code to enter at
   `github.com/login/device`. Once linked, the repository is added.
3. Install **Safe Store** and restart Home Assistant.
4. **Settings → Devices & services → Add integration → Safe Store.** Leave the
   form empty: the integration finds the app on its own.

The integration creates `/config/.ss.token` (`600`) and asks the app for the key.

### Step 4 · Get the key out

1. Open **Safe Store** in the sidebar. It is administrator only.
2. It shows the fingerprint and a **Download QR** button.
3. Press it and keep that PNG **outside** Home Assistant: printed, in a safe, or
   in a password manager.

That PNG is the key. There is no second copy.

### Step 5 · Check it worked

**Settings → Devices & services** should show no integration in *Retry*. If any
is, the app is not delivering the key; see [Troubleshooting](#troubleshooting).

## The master key

One key protects everything.

- **Where it lives.** `/data/master.key` inside the app, `0600`. The app writes
  it there and hands it over on request. The add-on option `master_key` is only
  a landing spot for a restored key: it is written to the file and emptied on
  the next boot, because options *are* included in backups and the key must not
  be.
- **What travels in a backup.** The encrypted `core.config_entries`, and the
  app's configuration with `master_key` empty. `master.key` and `age.key` are
  excluded by name in `backup_exclude`. A restore therefore brings back
  ciphertext and **not** the key.
- **Keep a copy outside Home Assistant.** The QR from step 4. Print it, or put
  it in a secrets manager. It is the only copy that survives a lost disk.
- **You can download it again** at any time while the app still holds it.

Losing the key is not recoverable here: `safe_store.dump` needs it too.

### Restoring a key

Upload the PNG in the panel. The integration reads the QR, writes the key to
`/data/master.key`, empties the option, and restarts the app. Every entry comes
back on the next reload.

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
| Encryption, decryption, reload | verified on HAOS 18.4 / core 2026.11.2 — 24 of 24 entries `loaded` |
| A new integration is encrypted on creation | verified: 23 encrypted entries, 24 total (`hassio` excluded) |
| Deleting that integration returns the file | verified |
| Clean install from the repository | verified on a clean HAOS 18.4 |
| App installs from the published image | verified: `Downloading docker image ... tag 0.2.25`, 22 s |
| Panel: fingerprint and QR | verified: `200 image/png`, decodes to the stored key |
| Panel without the panel token | verified: `403` |
| Restore by uploading the PNG | verified: key written to `/data/master.key`, entries load |
| Option `master_key` after a restore | verified: emptied on the next boot |
| Unit tests | 30, run without Home Assistant installed |
| `safe_store.dump` | verified |
| Master key rotation | **not implemented** |
| `secrets.yaml` | **not covered** |

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
- It does not rotate the master key. Changing it by hand makes the file
  unreadable.

## Uninstalling

The encrypted file is only readable with the key, so the order matters:

1. Run `safe_store.dump` and confirm `/config/.ss_dump.json` has your
   credentials, in plain text, `600`.
2. Keep that file somewhere safe and delete it from `/config` afterwards — it is
   unencrypted.
3. Remove the integration, then the app.
4. If you kept a copy of the key, the encrypted file stays decryptable later.

## Troubleshooting

**Integrations stuck in `setup_retry` after boot**
The app is not delivering the key. Check **Settings → Apps → Safe Store
Unlocker → Log**. A `/config/.ss.key` file would mean an older version fell back
to a local key, which is not the same one the app holds.

**The panel shows "Solo administradores" or nothing**
The panel is administrator only and carries a token generated at startup. A
non-administrator session gets `403` by design. If you are an administrator and
see nothing, restart Home Assistant so the panel is registered again.

**I lost the master key**
Nothing can read the file, and `dump` needs the key too. The only way out is the
QR or the copy you kept outside Home Assistant.

**I changed the master key**
There is no rotation yet: the file becomes unreadable. Restore the previous key,
run `dump`, and re-encrypt from a clean state.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Workflow is `tema/*` → `devs` → `main`,
and a release is a tag on the merge commit of `main`.

## License

MIT — see [LICENSE](LICENSE).

[ci-badge]: https://github.com/maurorosero/safe-store/actions/workflows/ci.yml/badge.svg?branch=main
[ci-url]: https://github.com/maurorosero/safe-store/actions/workflows/ci.yml
[release-badge]: https://img.shields.io/github/v/release/maurorosero/safe-store
[release-url]: https://github.com/maurorosero/safe-store/releases
[license-badge]: https://img.shields.io/github/license/maurorosero/safe-store
[license-url]: LICENSE
[market-badge]: https://img.shields.io/badge/Marketplace-submitted-blue
[market-url]: https://github.com/hacs/default/pull/15100
[add-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[add-hacs-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=maurorosero&repository=safe-store&category=integration
[add-repo-badge]: https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg
[add-repo-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fmaurorosero%2Fsafe-store
