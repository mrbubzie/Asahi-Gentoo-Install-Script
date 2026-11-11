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
print('All 9 regression checks passed.')
