# Asahi Gentoo installer 0.1.1

Corrected copy of mrbubzie/Asahi-Gentoo-Install-Script's asahi-gentoo-install,
reviewed November 10, 2026. This archive does not change the GitHub repository.

## Run

Use the Gentoo Asahi live environment on your Apple Silicon Mac, after the
Asahi installer has created the UEFI environment and reserved Linux space.
Create/select your intended Linux root partition carefully.

    chmod +x asahi-gentoo-install
    sudo ./asahi-gentoo-install

The selected root and optional swap partitions WILL be erased. The existing
Asahi ESP is mounted at /boot and is never formatted. Its boot files are
updated during installation. Configuration files contain password hashes;
keep them private and only load configuration files you trust (they are Bash).

    sudo ./asahi-gentoo-install -c asahi-gentoo.conf
    sudo ./asahi-gentoo-install -c asahi-gentoo.conf -y

-y skips the destructive confirmation only. A terminal is still required for
LUKS, profile selection, upstream support setup, and retry prompts. This is an
interactive installer, not a headless deployment tool.

## Changes

- Fix preflight's erroneous failure when the target is not mounted.
- Recheck configuration immediately before installation.
- Reject duplicate device identities, including aliases, whole disks, active
  swap, mounted devices, device-mapper children, Apple partitions, and non-ESP
  partition types or non-FAT ESP filesystems.
- Inspect Asahi boot.bin and vendor firmware read-only before erasing root.
- Require ESP-as-/boot for both setup methods; reject old /boot/efi configs.
- Native setup explicitly installs virtual/dist-kernel:asahi and linux-firmware,
  extracts Asahi firmware, and generates GRUB configuration unconditionally.
- Pass the chosen ESP's boot.bin explicitly to update-m1n1.
- Match profile choices and explicit profile settings to the stage init system.
- Report service activation failures; install OpenSSH when SSHD is requested.
- Configure iwd DNS through openresolv, enable D-Bus for OpenRC networking.
- Essential commands can be retried, investigated in a shell, or aborted, but
  cannot be skipped and subsequently reported as successful.
- Preserve failure status through cleanup and report unmount failures.
- Create saved configs with private permissions from the start.
- Validate common config fields and missing CLI arguments.
- Avoid obsolete Python crypt fallback; require openssl or mkpasswd for hashing.
- Source /etc/profile without nounset, and construct useradd arguments as an array.
- Clarify that -y still permits prompts.

Correction to the earlier review: Gentoo's OpenRC service really is named
NetworkManager. That name was retained. The important correction is to stop
silently ignoring service failures. update-m1n1 supports an explicit target;
this is retained to avoid relying on automatic ESP selection.

## Verification and limits

    bash -n asahi-gentoo-install
    python3 test-installer.py

Nine mocked regression checks cover valid configurations, root/swap alias and
ESP/swap collisions, unsupported ESP layout, init mismatch, preflight success
and rejection, and both profile filters. Tests do not format, mount, chroot,
install packages, or update firmware. Full installation and first boot have
not been tested on physical Apple Silicon. Native setup remains experimental;
prefer the upstream gentoosupport method. Network access and current Gentoo /
Asahi packages are required. The remote upstream helper remains upstream code
and may change independently.

installer-fixes.patch records all changes against the reviewed original.
