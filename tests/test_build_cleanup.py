import tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
import build_windows as b

class BuildCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'project';self.root.mkdir();self.install=Path(self.tmp.name)/'PC-Monitor'
        self.destination_patch=patch('build_windows.installation_directory',return_value=self.install);self.destination_patch.start()
        for name in ('desktop.py','monitor.ico','requirements-build.txt'):(self.root/name).write_bytes(b'fixture')
        (self.root/'assets').mkdir();(self.root/'assets'/'keep.gif').write_bytes(b'user resource')
        (self.root/'.venv').mkdir();(self.root/'.venv'/'keep.txt').write_text('existing source environment')
        (self.root/'build').mkdir();(self.root/'build'/'user.txt').write_text('not owned by new build')
        self.workspaces=[];self.calls=[];self.messages=[]
    def tearDown(self):self.destination_patch.stop();self.tmp.cleanup()
    def runner(self,args,**kwargs):
        self.calls.append((args,kwargs));self.assertTrue(kwargs['check']);self.assertNotIn('shell',kwargs)
        if 'venv' in args:self.workspaces.append(Path(args[-1]).parent)
        if 'PyInstaller' in args:
            out=Path(args[args.index('--distpath')+1]);out.mkdir();(out/'PC-Monitor.exe').write_bytes(b'MZ'+b'x'*200)
        return subprocess.CompletedProcess(args,0)
    def build(self,runner=None,shortcut=None):
        with patch('build_windows.is_windows',return_value=True),patch('build_windows.subprocess.run',side_effect=runner or self.runner),patch('build_windows.create_shortcut',side_effect=shortcut,return_value='Desktop shortcut') as link:
            result=b.build(self.root,self.messages.append)
        return result,link
    def old_exe(self):
        self.install.mkdir(exist_ok=True);p=self.install/'PC-Monitor.exe';p.write_bytes(b'MZ'+b'OLD'*70);return p
    def test_success_cleans_owned_workspace_and_keeps_only_exe_in_new_installation(self):
        target,link=self.build();self.assertFalse((self.root/'dist').exists());self.assertFalse(target.is_relative_to(self.root));self.assertEqual(list(self.install.iterdir()),[target]);self.assertEqual(target.read_bytes(),b'MZ'+b'x'*200);link.assert_called_once_with(target);self.assertFalse(self.workspaces[0].exists())
    def test_existing_sources_resources_environment_and_user_build_untouched(self):
        self.build();self.assertEqual((self.root/'.venv'/'keep.txt').read_text(),'existing source environment');self.assertEqual((self.root/'build'/'user.txt').read_text(),'not owned by new build');self.assertEqual((self.root/'assets'/'keep.gif').read_bytes(),b'user resource');self.assertEqual((self.root/'desktop.py').read_bytes(),b'fixture')
    def test_failure_cleans_temp_and_preserves_previous_exe(self):
        old=self.old_exe();previous=old.read_bytes()
        def fail(args,**kw):
            self.runner(args,**kw)
            if 'pip' in args:raise subprocess.CalledProcessError(1,args)
        with self.assertRaises(subprocess.CalledProcessError):self.build(runner=fail)
        self.assertEqual(old.read_bytes(),previous);self.assertFalse(self.workspaces[0].exists())
    def test_compile_failure_does_not_create_shortcut_or_publish(self):
        old=self.old_exe();previous=old.read_bytes()
        def fail(args,**kw):
            self.runner(args,**kw)
            if 'PyInstaller' in args:raise subprocess.CalledProcessError(1,args)
        with patch('build_windows.is_windows',return_value=True),patch('build_windows.subprocess.run',side_effect=fail),patch('build_windows.create_shortcut') as link:
            with self.assertRaises(subprocess.CalledProcessError):b.build(self.root,self.messages.append)
            link.assert_not_called()
        self.assertEqual(old.read_bytes(),previous);self.assertFalse(self.workspaces[0].exists())
    def test_shortcut_failure_keeps_built_exe_and_cleans_temp(self):
        target,_=self.build(shortcut=OSError('Shortcut unavailable'));self.assertTrue(target.is_file());self.assertFalse(self.workspaces[0].exists());self.assertTrue(any('shortcut creation failed' in x for x in self.messages))
    def test_all_build_caches_and_temp_environment_are_isolated(self):
        self.build();workspace=self.workspaces[0]
        for args,kw in self.calls:
            env=kw['env'];self.assertEqual(env['PYTHONDONTWRITEBYTECODE'],'1');self.assertEqual(env['PIP_NO_CACHE_DIR'],'1')
            for key in ('TEMP','TMP','PYINSTALLER_CONFIG_DIR'):self.assertTrue(Path(env[key]).is_relative_to(workspace))
        compiler=self.calls[-1][0]
        for flag in ('--workpath','--specpath','--distpath'):self.assertTrue(Path(compiler[compiler.index(flag)+1]).is_relative_to(workspace))
        self.assertIn('--no-cache-dir',self.calls[1][0])
    def test_onefile_assets_and_icon_paths_preserved(self):
        cmd=b.pyinstaller_command(self.root,Path('/scratch'),'python.exe');self.assertIn('--onefile',cmd);self.assertIn('--windowed',cmd);self.assertEqual(cmd[cmd.index('--name')+1],'PC-Monitor');self.assertEqual(cmd[cmd.index('--add-data')+1],str(self.root/'assets')+';assets');self.assertEqual(cmd[cmd.index('--icon')+1],str(self.root/'monitor.ico'))
    def test_incomplete_exe_never_replaces_previous_exe(self):
        old=self.old_exe();before=old.read_bytes();bad=self.root/'bad.exe';bad.write_bytes(b'incomplete')
        with self.assertRaises(ValueError):b.publish_exe(bad,old.parent)
        self.assertEqual(old.read_bytes(),before)
    def test_replace_failure_removes_staging_and_keeps_old_exe(self):
        old=self.old_exe();before=old.read_bytes();source=self.root/'new.exe';source.write_bytes(b'MZ'+b'N'*200)
        with patch('build_windows.os.replace',side_effect=PermissionError('EXE is running')):
            with self.assertRaises(PermissionError):b.publish_exe(source,old.parent)
        self.assertEqual(old.read_bytes(),before);self.assertEqual(list(old.parent.iterdir()),[old])
    def test_unrelated_installation_files_preserved(self):
        old=self.old_exe();other=old.parent/'personal.txt';other.write_text('keep');self.build();self.assertEqual(other.read_text(),'keep')
    def test_nonwindows_build_fails_before_creating_workspace(self):
        with patch('build_windows.is_windows',return_value=False),patch('build_windows.tempfile.mkdtemp') as temp:
            with self.assertRaises(RuntimeError):b.build(self.root)
            temp.assert_not_called()
    def test_cleanup_failure_is_reported_without_losing_exe(self):
        original=b.shutil.rmtree
        with patch('build_windows.shutil.rmtree',side_effect=PermissionError('Temporary file locked')):target,_=self.build()
        try:self.assertTrue(target.is_file());self.assertTrue(any('cleanup incomplete' in x for x in self.messages));self.assertTrue(self.workspaces[0].exists())
        finally:original(self.workspaces[0])

    def test_publish_permission_failure_cleans_workspace_and_keeps_previous_exe(self):
        old=self.old_exe();before=old.read_bytes()
        with patch('build_windows.os.replace',side_effect=PermissionError('Access denied')):
            with self.assertRaises(PermissionError):self.build()
        self.assertEqual(old.read_bytes(),before);self.assertFalse(self.workspaces[0].exists());self.assertEqual(list(self.install.iterdir()),[old])
