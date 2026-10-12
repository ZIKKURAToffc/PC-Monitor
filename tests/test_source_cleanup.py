import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import source_cleanup as c
import build_windows as b

class SourceCleanupTests(unittest.TestCase):
    def setUp(self):
        self.cwd=Path.cwd();self.tmp=tempfile.TemporaryDirectory();self.host=Path(self.tmp.name)
        self.root=self.host/'pc-monitor-desktop-v2.3.32';self.root.mkdir()
        (self.root/c.MARKER).write_text(c.MARKER_CONTENT,encoding='utf-8')
        for name in ('desktop.py','build_windows.py','requirements-build.txt'):(self.root/name).write_text('source')
        (self.root/'assets').mkdir();(self.root/'assets'/'test.gif').write_bytes(b'gif')
        self.target=self.host/'PC-Monitor'/'PC-Monitor.exe';self.target.parent.mkdir();self.target.write_bytes(b'MZ'+b'x'*200)
        self.zip=self.host/'backup.zip';self.zip.write_bytes(b'archive')
    def tearDown(self):os.chdir(self.cwd);self.tmp.cleanup()
    def test_success_removes_entire_marked_source_folder(self):
        c.remove_sources(self.root,self.target,lambda _:None)
        self.assertFalse(self.root.exists());self.assertTrue(self.target.exists());self.assertEqual(self.zip.read_bytes(),b'archive');self.assertEqual(Path.cwd(),self.target.parent)
    def test_missing_exe_keeps_sources(self):
        self.target.unlink()
        with self.assertRaises(ValueError):c.remove_sources(self.root,self.target)
        self.assertTrue((self.root/'desktop.py').exists())
    def test_invalid_exe_keeps_sources(self):
        self.target.write_bytes(b'xx'+b'x'*200)
        with self.assertRaises(ValueError):c.remove_sources(self.root,self.target)
        self.assertTrue(self.root.exists())
    def test_missing_marker_keeps_sources(self):
        (self.root/c.MARKER).unlink()
        with self.assertRaises(ValueError):c.remove_sources(self.root,self.target)
        self.assertTrue(self.root.exists())
    def test_modified_marker_keeps_sources(self):
        (self.root/c.MARKER).write_text('not owned')
        with self.assertRaises(ValueError):c.remove_sources(self.root,self.target)
        self.assertTrue(self.root.exists())
    def test_destination_inside_source_rejected(self):
        inside=self.root/'PC-Monitor.exe';inside.write_bytes(self.target.read_bytes())
        with self.assertRaises(ValueError):c.remove_sources(self.root,inside)
        self.assertTrue(inside.exists())
    def test_drive_root_rejected(self):
        with self.assertRaises(ValueError):c.validate_source_cleanup(Path(self.root.anchor),self.target)
    def test_home_rejected(self):
        with patch('source_cleanup.Path.home',return_value=self.root):
            with self.assertRaises(ValueError):c.remove_sources(self.root,self.target)
    def test_nested_link_keeps_external_files(self):
        outside=self.host/'personal.txt';outside.write_text('keep');(self.root/'link').symlink_to(outside)
        with self.assertRaises(ValueError):c.remove_sources(self.root,self.target)
        self.assertEqual(outside.read_text(),'keep');self.assertTrue(self.root.exists())
    def test_source_symlink_rejected(self):
        link=self.host/'linked-source';link.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):c.remove_sources(link,self.target)
        self.assertTrue(self.root.exists())
    def test_locked_files_retry_and_report_failure(self):
        with patch('source_cleanup.shutil.rmtree',side_effect=PermissionError('locked')) as delete,patch('source_cleanup.time.sleep'):
            with self.assertRaises(PermissionError):c.remove_sources(self.root,self.target)
            self.assertEqual(delete.call_count,3)
        self.assertTrue(self.target.exists());self.assertTrue(self.root.exists())
    def test_transient_lock_retry_succeeds(self):
        original=c.shutil.rmtree;calls=[]
        def delete(root):
            calls.append(root)
            if len(calls)==1:raise PermissionError('locked')
            original(root)
        with patch('source_cleanup.shutil.rmtree',side_effect=delete),patch('source_cleanup.time.sleep'):
            c.remove_sources(self.root,self.target,lambda _:None)
        self.assertFalse(self.root.exists());self.assertEqual(len(calls),2)
    def test_main_removes_sources_only_after_success(self):
        events=[]
        with patch('build_windows.sys.argv',['build_windows.py']),patch('build_windows.build',side_effect=lambda:events.append('build') or self.target),patch('build_windows.remove_sources',side_effect=lambda *a:events.append('cleanup')),patch('build_windows.subprocess.Popen'):
            self.assertEqual(b.main(),0)
        self.assertEqual(events,['build','cleanup'])
    def test_main_failure_never_deletes_sources(self):
        with patch('build_windows.build',side_effect=RuntimeError('failed')),patch('build_windows.remove_sources') as cleanup:
            self.assertEqual(b.main(),1);cleanup.assert_not_called()
    def test_keep_sources_override(self):
        with patch('build_windows.sys.argv',['build_windows.py','--keep-sources']),patch('build_windows.build',return_value=self.target),patch('build_windows.remove_sources') as cleanup,patch('build_windows.subprocess.Popen'):
            self.assertEqual(b.main(),0);cleanup.assert_not_called()
    def test_cleanup_failure_is_warning_and_exe_is_kept(self):
        with patch('build_windows.sys.argv',['build_windows.py']),patch('build_windows.build',return_value=self.target),patch('build_windows.remove_sources',side_effect=PermissionError('locked')),patch('build_windows.subprocess.Popen'):
            self.assertEqual(b.main(),0)
        self.assertTrue(self.target.exists())
    def test_batch_releases_source_directory_and_preserves_cached_final_block(self):
        text=Path('build_windows.bat').read_text();self.assertIn('cd /d "%SystemRoot%"',text);self.assertNotIn('cd /d "%~dp0"',text);self.assertIn('%PY% -B "%PROJECT%build_windows.py" %*',text);self.assertTrue(text.rstrip().endswith(')'))
