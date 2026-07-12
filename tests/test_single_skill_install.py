import os, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SingleSkillInstallTest(unittest.TestCase):
 def test_installs_only_search_agent_without_touching_shell(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'skills'; target.mkdir(); unrelated=target/'other'; unrelated.mkdir()
   home=Path(tmp)/'home'; home.mkdir(); rc=home/'.zshrc'; rc.write_text('KEEP\n')
   env={**os.environ,'TARGET_DIR':str(target),'HOME':str(home),'NON_INTERACTIVE':'1','SKIP_PYTHON_BOOTSTRAP':'1','SKIP_SHELL_RC':'1'}
   subprocess.run(['bash',str(ROOT/'install.sh')],env=env,check=True,capture_output=True,text=True)
   self.assertTrue((target/'search-agent/specialists/catalog.json').is_file())
   self.assertTrue((target/'search-agent/specialists/marketing/pricing/prompt.md').is_file())
   self.assertFalse((target/'marketing').exists()); self.assertFalse((target/'finance').exists())
   self.assertTrue(unrelated.is_dir()); self.assertEqual(rc.read_text(),'KEEP\n')
if __name__=='__main__': unittest.main()
