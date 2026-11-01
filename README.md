# asahi-gentoo-install

Menu-driven Gentoo installer for Apple Silicon (M1/M2), inspired by
[oddlama/gentoo-install](https://github.com/oddlama/gentoo-install).

## Before you run it
1. macOS: `curl https://alx.sh | sh` -> choose **UEFI environment only**, reserve free space.
2. Boot the Gentoo Asahi live ISO (https://chadmed.au/pub/gentoo/), get online (`net-setup` / `iwctl`).
3. `git clone` or copy this script, then: `sudo ./asahi-gentoo-install`

## What it does
- Pick ESP (mounted, never formatted) and root/swap partitions. Apple-typed partitions are hidden and refused.
- ext4 / btrfs / xfs, optional LUKS2.
- Stage3: openrc, systemd, desktop-*, llvm-* (latest, GPG verified).
- Profile preset, custom path, or pick from `eselect profile list`.
- Hostname, timezone, locale, keymap, root password, user (hashed, never stored in plaintext).
- Options: accept all licenses, binhost, ~arm64, git sync, @world update, -mcpu=native, sudo, sshd, chrony.
- Network: iwd / NetworkManager / none; extra packages and USE flags.
- Asahi setup: official `asahi-gentoosupport` (default) or experimental native mode.

Config is saved to `asahi-gentoo.conf`; reuse with `-c asahi-gentoo.conf -y`.
Re-enter an installed system: `./asahi-gentoo-install --chroot /mnt/gentoo`.

## After install
- `update-m1n1` after every kernel update; `emaint -r asahi sync` to keep the overlay current.

## Caveats
Not tested on hardware. Verify the overlay URI, package names (`sys-apps/asahi-meta`) and the
m1n1 path against the current Gentoo Asahi docs before relying on native mode.
