# Asahi Gentoo installer 0.1.8

Corrected copy of mrbubzie/Asahi-Gentoo-Install-Script's asahi-gentoo-install,
reviewed November 10, 2026. This archive does not change the GitHub repository.

## C library choice (0.1.7)

Choose **C library** in the main menu: glibc (default) or musl (experimental).
Changing libc is for a new installation, not conversion of an existing system.
The musl choice switches to musl-openrc, native Asahi setup, C.UTF-8 locale,
resets the profile selection, and disables the glibc binary host. The Stage3
menu offers the published musl OpenRC/systemd, LLVM, and hardened variants.
The Profile menu offers a matching musl profile; in-chroot profile lists filter
by libc and init system. Configuration checks reject mismatched libc/stage/
profile and prevent musl from using the glibc binary host or upstream helper.
The chosen stage listing is checked before formatting. musl skips glibc's
locale-gen and currently supports C.UTF-8, C, or POSIX locales.

Gentoo publishes these musl stages/profiles, but Asahi packages, firmware
utilities, Rust/kernel compilation, graphics, and audio on musl have not been
validated by this project. Native setup remains experimental and package
builds can still require musl-specific work. Select glibc for the tested
installation path in this conversation. Full hardware testing of this release
has not been performed. Other settings including -j4 remain available.

## KDE integration

Install options now includes **ASAHI_KDE — Enable Asahi KDE/KWin integration**,
off by default. When off, a package-specific `sys-apps/asahi-meta -kde` rule
prevents the Asahi metapackage from pulling KWin and its KDE dependencies
merely because a profile enables the global kde USE flag. When selected,
the rule uses `kde` instead. The rule is written before both Asahi setup paths
and does not disable other Asahi features such as audio or Mesa.

This controls only the Asahi metapackage's optional KWin integration. Selecting
a Plasma profile or explicitly installing KDE applications can independently
require KWallet, KDecoration, and other Frameworks packages. The installer does
not remove packages already installed or override separately chosen desktops.

## Build jobs (new in 0.1.5)

The default is now **four compile jobs per package (-j4)** for the entire
installation, with **one package built at a time**. Select **Build jobs** in
the main installer menu to choose any integer from 1 to 256, or `auto` for
the previous memory-based limit. The choice is saved in the configuration
as `BUILD_JOBS=4` and passed into the chroot. Old configs without BUILD_JOBS
inherit the new default of four. Heavy packages use the same selected limit;
there is no longer a hidden single-job override. These settings remain in
the installed system. Reduce the count if the compiler is killed again.
Bash remains the installer runtime; Python is only for optional tests.

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

Fifty regression checks cover valid configurations, root/swap alias and
ESP/swap collisions, unsupported ESP layout, init mismatch, preflight success
and rejection, and both profile filters. Tests do not format, mount, chroot,
install packages, or update firmware. Full installation and first boot have
not been tested on physical Apple Silicon. Native setup remains experimental;
prefer the upstream gentoosupport method. Network access and current Gentoo /
Asahi packages are required. The remote upstream helper remains upstream code
and may change independently.

installer-fixes.patch records all changes against the reviewed original.

## Timezone fix in 0.1.2

America/New_York was incorrectly rejected when the live ISO did not include
/usr/share/zoneinfo/America/New_York. Initial validation now checks the timezone
name syntax without depending on live-media tzdata. Inside the installed Gentoo
system, the installer ensures sys-libs/timezone-data is available and validates
the actual file before writing /etc/timezone and /etc/localtime.
The tests also simulate a live environment with no timezone files.

## Asahi dependency bootstrap in 0.1.3

Both gentoosupport and native setup now prepare the overlay and required
PipeWire lv2/extra and installkernel dracut/grub flags before Asahi setup.
On a fresh system with neither m1n1 package installed, the installer first
installs unzip normally, then bootstraps only the prebuilt m1n1-bin with
--nodeps to break the overlay kernel/m1n1 dependency cycle. An existing
m1n1 package is retained. installkernel is merged with --update --newuse
so existing installs pick up required flags. After setup, a normal dependency
merge of asahi-meta and the Asahi distribution kernel reconciles dependencies
before GRUB configuration is generated. --nodeps is never used for the kernel
or the metapackage. The new tests mock commands and verify bootstrap ordering
and both already-installed m1n1 variants; hardware installation is untested.

For a current installation already stopped at the retry prompt, use the
recovery shell instructions from the conversation. Do not restart this full
installer over an in-progress installation: its root formatting is intentional.

## Memory limits in 0.1.4

The installer no longer builds two packages simultaneously with every CPU
core. It uses one package at a time, budgets 4 GiB of currently available RAM
per ordinary compile job after a 2 GiB reserve, and caps that count at four
and at the CPU count. At least one job is used; low available memory can still
prevent even a single compile from succeeding. Swap is not counted as RAM.
LLVM, Clang, SPIR-V LLVM Translator, Mesa, and the Asahi kernel have persistent
package.env overrides for a single compile job. These settings apply to both
setup methods and are retained after installation. Existing package.env files
or directories are supported and unrelated entries are preserved.

This addresses the observed killed cc1plus failure by reducing peak memory
pressure. It does not claim an OOM event was confirmed from kernel logs and
cannot guarantee a build on an otherwise memory-starved system. No swapfile
is created automatically. All previous timezone and dependency fixes remain.
Tests cover six memory/CPU budgets and both package.env forms, including
repeat setup. Full hardware installation remains untested.

## Job-selection changes in 0.1.5

Supersedes the automatic/default single-job behavior documented in the
0.1.4 history below. MAKEOPTS, NINJAOPTS and CMAKE_BUILD_PARALLEL_LEVEL
for heavy packages all follow the chosen job count. Emerge remains limited
to --jobs=1 (one package at a time). Tests cover valid/invalid counts, menu
selection, config save/load, and explicit limits for heavy packages.

## Desktop-choice fix in 0.1.6

Adds explicit ASAHI_KDE opt-in, persisted through the existing OPTIONS config
field. Older configs without it default to disabled. A dedicated package.use
file overrides inherited profile defaults without changing global USE flags.
Both native and upstream-support installation paths apply it before setup.
Tests verify default-off, opt-in, ordering, and preservation of unrelated rules.
All prior timezone, dependency bootstrap and build-job options remain.

## U-Boot GnuTLS requirement in 0.1.8

Adds `net-libs/gnutls pkcs11` to the shared Asahi package.use configuration
before the m1n1 bootstrap and either Asahi setup path. This covers the USE
requirement reported by U-Boot 2026.07_p3. Existing PipeWire lv2/extra and
installkernel dracut/grub requirements are retained, along with libc choice,
job selection (default -j4), and explicit KDE opt-in. Package requirements
can change in future repository updates; this fixes the reported requirement
and does not guarantee that all future Portage prompts are eliminated.
For an installation already stopped at the retry prompt, apply the recovery
command and retry; do not restart root formatting.
