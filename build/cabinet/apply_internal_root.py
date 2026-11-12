"""Stage-to-new-child root changes; run only after explicit human playtest end.

The caller owns NBD mount, fsck and persistent readback. This script cannot mark
the cabinet image ready by itself.
"""
from pathlib import Path
import argparse,json,hashlib,os,shutil,subprocess
R=Path(__file__).resolve().parent;V=Path('/mnt/e/Pump It Up Data/PIU/anime_final_v8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(path,data,mode):
 temp=path.with_name(path.name+'.cabinet-new');assert not temp.exists()
 with temp.open('xb') as out:out.write(data);out.flush();os.fsync(out.fileno())
 os.chmod(temp,mode);os.replace(temp,path)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root-mount',required=True);ap.add_argument('--new-child-server-state',required=True)
 ap.add_argument('--runtime-plan',default=str(R/'CABINET_RUNTIME_PLAN.json'))
 ap.add_argument('--runtime-module',default=str(R/'piu_channels_cabinet.so'))
 ap.add_argument('--expected-installed-runtime-sha256',default='c31252ecd07f3ef81c700e39d48d31c8c6b238375318293c6c3766fc72d28c1d')
 args=ap.parse_args()
 assert json.loads((V/'USER_PLAYTEST_ACTIVE.json').read_text())['active'] is False,'Human is still testing'
 root=Path(args.root_mount).resolve();assert str(root).startswith('/mnt/piu-cabinet-') and subprocess.run(['mountpoint','-q',str(root)]).returncode==0
 state=json.loads(Path(args.new_child_server_state).read_text());assert state['image'].replace('\\','/').rsplit('/',1)[-1]=='PRIME_V363_CABINET.qcow2','Only the new cabinet child may be changed'
 plan_path=Path(args.runtime_plan).resolve();manifest=json.loads(plan_path.read_text());source=Path(args.runtime_module).resolve()
 assert sha(source)==manifest['runtime_sha256'] and manifest['native_engine_constructor_test_pass']
 module=root/'root/game/m.so';current_expected=args.expected_installed_runtime_sha256
 assert len(current_expected)==64 and all(c in '0123456789abcdef' for c in current_expected)
 assert sha(module)==current_expected
 backup=root/'root/cabinet_before';assert not backup.exists();backup.mkdir()
 for relative in ['root/game/m.so','root/.xinitrc','root/.init.sh']:
  path=root/relative;assert path.is_file();shutil.copy2(path,backup/path.name)
 init=root/'root/.init.sh';text=init.read_text();disabled='DETECT="$(false        )"';native='DETECT="$(nvidia-detect)"';assert disabled in text or native in text
 text=text.replace(disabled,native);atomic(init,text.encode(),0o755)
 startup=root/'root/.xinitrc';text=startup.read_text();a=text.index('mount -o remount,rw / || true');z=text.index('cd /root/game/',a)
 text=text[:a]+"# Self-contained MK9 disk: use installed native channel hooks.\nmkdir -p /SETTINGS/PIU\ntest -s /root/game/m.so || exit 1\ntest -s /root/game/p.so || exit 1\n"+text[z:]
 text=text.replace('export MESA_LOADER_DRIVER_OVERRIDE=virtio_gpu\n','').replace('xrandr -s 1280x720 >>$L 2>&1\n','').replace('L=/root/prime_run.log','L=/SETTINGS/PIU/prime_run.log')
 text='\n'.join(line for line in text.splitlines() if '/mnt/mk5' not in line)+'\n';assert '/mnt/mk5' not in text and 'virtio_gpu' not in text
 atomic(startup,text.encode(),0o755);atomic(module,source.read_bytes(),0o755)
 for relative in ['root/.xinitrc','root/.init.sh']:subprocess.run(['bash','-n',str(root/relative)],check=True)
 assert sha(module)==manifest['runtime_sha256']
 (R/'root_changes_applied.json').write_text(json.dumps(dict(applied_to_new_child=True,complete=False,persistent_readback_pending=True,fsck_pending=True,physical_manual_test_pending=True,module_sha256=sha(module),runtime_plan=str(plan_path),runtime_plan_sha256=sha(plan_path),replaced_trial_module_sha256=current_expected,external_runtime_share_removed=True,keyboard_usb_io_emulation_removed=True,nvidia_autodetect_restored=True),indent=2))
if __name__=='__main__':main()
