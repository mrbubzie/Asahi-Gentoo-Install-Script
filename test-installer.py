#!/usr/bin/env python3
"""Non-destructive regression tests: mocked commands; no disk writes or chroots."""
from pathlib import Path
import subprocess
import tempfile
src = Path(__file__).with_name('asahi-gentoo-install').read_text()
# Hardware/root checks are tested on the target; bypass only these in this harness.
src = src.replace('[[ $EUID -eq 0 ]] || die "Run as root."', ':')
src = src.replace("[[ -r /proc/device-tree/compatible ]] && grep -aq 'apple,' /proc/device-tree/compatible || die \"Apple Silicon device tree not detected.\"", ':')
src = src.replace('[[ -r /dev/tty && -w /dev/tty ]] || die "An interactive terminal is required, including with -y."', ':')
# Model block devices with strings, then supply identities through mocked lsblk.
src = src.replace('[[ -b $ESP_PART  ]]', '[[ -n $ESP_PART ]]').replace('[[ -b $ROOT_PART ]]', '[[ -n $ROOT_PART ]]').replace('-b $SWAP_PART', '-n $SWAP_PART').replace('! -b $p', '! -n $p')
base = '''
set_defaults
ui_msg() { printf '%s\\n' "$2"; }
ROOT_PART=/dev/root; ESP_PART=/dev/esp; ROOT_PW_HASH=test
swapon() { :; }
blkid() { echo vfat; }
lsblk() {
 case "$*" in
  *PARTTYPE*) if [[ ${*: -1} == /dev/esp ]]; then echo "$ESP_GUID"; else echo linux; fi ;;
  *MAJ:MIN*) case ${*: -1} in /dev/esp) echo 1:1;; /dev/root|/dev/root-alias) echo 1:2;; *) echo 1:3;; esac ;;
  *TYPE*) echo part ;;
  *MOUNTPOINTS*) : ;;
  *NAME*) printf '%s\\n' "${*: -1}" ;;
 esac
}
'''
cases = [
 ('America/New_York accepted', 'TIMEZONE=America/New_York; validate_config', 0, ''),
 ('timezone traversal rejected', 'TIMEZONE=../etc/passwd; validate_config', 1, 'Invalid timezone'),
 ('timezone spaces rejected', 'TIMEZONE="America/New York"; validate_config', 1, 'Invalid timezone'),
 ('valid partitions', 'validate_config', 0, ''),
 ('root/swap alias rejected', 'SWAP_PART=/dev/root-alias; validate_config', 1, 'overlap'),
 ('ESP/swap collision rejected', 'SWAP_PART=/dev/esp; validate_config', 1, 'overlap'),
 ('unsupported ESP layout rejected', 'ESP_MOUNT=/boot/efi; validate_config', 1, 'requires'),
 ('init mismatch rejected', 'PROFILE=default/linux/arm64/23.0/systemd; validate_config', 1, 'OpenRC'),
 ('preflight succeeds with target unmounted', 'uname() { echo aarch64; }; command() { return 0; }; wget() { return 0; }; findmnt() { return 1; }; preflight; echo PASSED', 0, 'PASSED'),
 ('preflight rejects mounted target', 'uname() { echo aarch64; }; command() { return 0; }; wget() { return 0; }; findmnt() { return 0; }; preflight', 1, 'already mounted'),
]
with tempfile.TemporaryDirectory() as d:
 source=Path(d)/'functions.sh'; source.write_text(src)
 for name, code, status, expected in cases:
  r=subprocess.run(['bash','-c',f'source "{source}"\n'+base+code],capture_output=True,text=True)
  assert r.returncode == status and expected in r.stdout+r.stderr, (name,r.returncode,r.stdout,r.stderr)
  print('PASS:',name)
 for init in ('openrc','systemd'):
  code='''
INIT=INIT_VALUE
eselect() { if [[ $2 == list ]]; then printf '  [1] default/linux/arm64/23.0 (stable)\\n  [2] default/linux/arm64/23.0/systemd (stable)\\n'; fi; }
try() { :; }
ui_menu() { shift 2; printf '%s\\n' "$@"; RET=$1; }
s2_profile
'''.replace('INIT_VALUE',init)
  r=subprocess.run(['bash','-c',f'source "{source}"\n'+base+code],capture_output=True,text=True)
  assert r.returncode==0,(init,r.stderr)
  assert ('23.0/systemd' in r.stdout)==(init=='systemd'),r.stdout
  print('PASS: profile filter',init)
 # Force every zoneinfo path to appear absent in a separate source, proving
 # that live-media tzdata cannot reject valid input; stage2 must fail clearly.
 no_tz=Path(d)/'without-tzdata.sh'
 no_tz.write_text(src.replace('-f /usr/share/zoneinfo/$TIMEZONE', '-f /nonexistent-test-zoneinfo/$TIMEZONE'))
 for code,status,expected in [
  ('TIMEZONE=America/New_York; validate_config',0,''),
  ('TIMEZONE=America/New_York; emerge_pkgs() { echo INSTALL "$@"; }; ensure_target_timezone',1,'sys-libs/timezone-data'),
 ]:
  r=subprocess.run(['bash','-c',f'source "{no_tz}"\n'+base+code],capture_output=True,text=True)
  assert r.returncode==status and expected in r.stdout+r.stderr,(r.stdout,r.stderr)
 print('PASS: live media without tzdata accepts America/New_York')
 print('PASS: missing target tzdata triggers installation and clear failure')
 for installed in ('none','binary','source'):
  code = r'''
portageq() {
 case "INSTALLED:${*: -1}" in binary:sys-boot/m1n1-bin|source:sys-boot/m1n1) return 0;; *) return 1;; esac
}
emerge_pkgs() { printf 'PKGS %s\\n' "$*"; }
try() { printf 'RUN %s\\n' "$*"; }
s2_asahi_bootstrap
'''.replace('INSTALLED',installed)
  r=subprocess.run(['bash','-c',f'source "{source}"\n'+base+code],capture_output=True,text=True)
  assert r.returncode==0,(r.stdout,r.stderr)
  assert ('--nodeps' in r.stdout)==(installed=='none'),r.stdout
  assert '--update --newuse' in r.stdout,r.stdout
  if installed=='none':
   assert r.stdout.index('app-arch/unzip') < r.stdout.index('--nodeps') < r.stdout.index('sys-kernel/installkernel'),r.stdout
  print('PASS: bootstrap order; installed m1n1 =',installed)
 assert src.index('  s2_prepare_asahi\n') < src.index('  if [[ $ASAHI_SETUP == gentoosupport ]]')
 assert 'media-video/pipewire lv2 extra' in src and 'sys-kernel/installkernel dracut grub' in src
 print('PASS: shared preparation runs before setup-method selection')
 for gib,cpus,expected in [(0,8,1),(4,8,1),(8,8,1),(16,8,3),(32,8,4),(64,2,2)]:
  r=subprocess.run(['bash','-c',f'source "{source}"; build_jobs_for_memory {gib*1048576} {cpus}'],capture_output=True,text=True)
  assert r.returncode==0 and r.stdout.strip()==str(expected),(gib,cpus,r.stdout,r.stderr)
  print('PASS: memory budget',gib,'GiB /',cpus,'CPUs =',expected,'jobs')
 for existing_file in (False,True):
  config=Path(d)/('portage-file' if existing_file else 'portage-dir'); config.mkdir()
  if existing_file: (config/'package.env').write_text('app-misc/example other.conf\n')
  code=f'source "{source}"; set_defaults; configure_heavy_build_limits "{config}"; configure_heavy_build_limits "{config}"'
  r=subprocess.run(['bash','-c',code],capture_output=True,text=True)
  assert r.returncode==0,r.stderr
  rules=config/'package.env' if existing_file else config/'package.env/asahi-low-memory'
  text=rules.read_text()
  assert text.count('dev-util/spirv-llvm-translator asahi-low-memory.conf')==1,text
  if existing_file: assert 'app-misc/example other.conf' in text
  assert 'MAKEOPTS="-j4"' in (config/'env/asahi-low-memory.conf').read_text()
  print('PASS: heavy package rules preserve existing config, file =',existing_file)
 assert '--jobs=2' not in src
 for value,expected in [('1',True),('4',True),('256',True),('auto',True),('0',False),('-j4',False),('257',False),('04',False),('2.5',False)]:
  r=subprocess.run(['bash','-c',f'source "{source}"; valid_build_jobs "$1"','test',value],capture_output=True,text=True)
  assert (r.returncode==0)==expected,(value,r.returncode)
 print('PASS: build jobs accepts 1, 4, 256, auto and rejects invalid values')
 config=Path(d)/'saved.conf'
 r=subprocess.run(['bash','-c',f'source "{source}"; set_defaults; BUILD_JOBS=6; save_config "{config}"; BUILD_JOBS=1; load_config "{config}"; echo "$BUILD_JOBS"'],capture_output=True,text=True)
 assert r.returncode==0 and r.stdout.strip()=='6',(r.stdout,r.stderr)
 print('PASS: selected job count survives config save/load')
 r=subprocess.run(['bash','-c',f'source "{source}"; set_defaults; ui_input() {{ RET=3; }}; cfg_build_jobs; echo "$BUILD_JOBS"'],capture_output=True,text=True)
 assert r.returncode==0 and r.stdout.strip()=='3',(r.stdout,r.stderr)
 print('PASS: installer menu changes the job count')
 config=Path(d)/'explicit-jobs'
 r=subprocess.run(['bash','-c',f'source "{source}"; set_defaults; configure_heavy_build_limits "{config}" 6'],capture_output=True,text=True)
 assert r.returncode==0,r.stderr
 assert 'MAKEOPTS="-j6"' in (config/'env/asahi-low-memory.conf').read_text()
 print('PASS: heavy packages use the explicitly selected job count')
 for enabled in (False,True):
  config=Path(d)/('kde-on' if enabled else 'kde-off')
  options='OPTIONS+=" ASAHI_KDE";' if enabled else ''
  r=subprocess.run(['bash','-c',f'source "{source}"; set_defaults; {options} configure_asahi_desktop "{config}"'],capture_output=True,text=True)
  assert r.returncode==0,r.stderr
  flag='kde' if enabled else '-kde'
  assert (config/'package.use/zz-asahi-installer-desktop').read_text()==f'sys-apps/asahi-meta {flag}\n'
  print('PASS: explicit Asahi KDE integration enabled =',enabled)
 config=Path(d)/'desktop-preserve'; (config/'package.use').mkdir(parents=True)
 (config/'package.use/user').write_text('app-misc/example feature\n')
 r=subprocess.run(['bash','-c',f'source "{source}"; set_defaults; configure_asahi_desktop "{config}"'],capture_output=True,text=True)
 assert r.returncode==0 and (config/'package.use/user').read_text()=='app-misc/example feature\n'
 assert src.index('  configure_asahi_desktop\n') < src.index('  s2_asahi_bootstrap\n')
 print('PASS: desktop choice precedes Asahi merges and preserves unrelated USE files')
 musl='LIBC=musl; STAGE_VARIANT=musl-openrc; ASAHI_SETUP=native; LOCALE=C.UTF-8; PROFILE=default/linux/arm64/23.0/musl; '
 for name,code,expected in [
  ('valid musl/OpenRC',musl,0),
  ('valid musl/systemd',musl+'STAGE_VARIANT=musl-systemd; PROFILE+=/systemd; ',0),
  ('musl rejects glibc stage',musl+'STAGE_VARIANT=openrc; ',1),
  ('musl rejects glibc profile',musl+'PROFILE=default/linux/arm64/23.0; ',1),
  ('musl rejects glibc binhost',musl+'OPTIONS+=" BINPKG"; ',1),
  ('musl rejects upstream helper',musl+'ASAHI_SETUP=gentoosupport; ',1),
  ('glibc rejects musl stage', 'STAGE_VARIANT=musl-openrc; ',1),
  ('musl rejects unsupported locale',musl+'LOCALE=en_US.UTF-8; ',1),
 ]:
  r=subprocess.run(['bash','-c',f'source "{source}"\n'+base+code+'validate_config'],capture_output=True,text=True)
  assert r.returncode==expected,(name,r.stdout,r.stderr)
  print('PASS:',name)
 code='ui_menu() { RET=musl; }; OPTIONS+=" BINPKG"; cfg_libc; [[ $LIBC == musl && $STAGE_VARIANT == musl-openrc && $ASAHI_SETUP == native && $LOCALE == C.UTF-8 ]]; ! opt BINPKG'
 r=subprocess.run(['bash','-c',f'source "{source}"\n'+base+code],capture_output=True,text=True)
 assert r.returncode==0,(r.stdout,r.stderr)
 print('PASS: libc menu resets incompatible stage/profile/binhost settings')
print('All 50 regression checks passed.')
