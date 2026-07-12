import importlib, os, subprocess, sys, tempfile, unittest
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
   installed_skills = sorted((target/'search-agent').glob('**/SKILL.md'))
   self.assertEqual(installed_skills, [target/'search-agent/SKILL.md'])
   self.assertTrue((target/'search-agent/vendor/marketing/skills/pricing/upstream-skill.md').is_file())
   installed_root=target/'search-agent'; sys.path.insert(0,str(installed_root.parent))
   try:
    registry_module=importlib.import_module('search-agent.lib.specialist_registry')
    router_module=importlib.import_module('search-agent.lib.specialist_router')
    registry=registry_module.SpecialistRegistry(installed_root)
    self.assertEqual(len(registry.list_specialists()),16)
    self.assertTrue(router_module.route_specialists('pricing strategy','marketing_intelligence_hunter','marketing',1,installed_root))
   finally:
    sys.path.remove(str(installed_root.parent))
    for name in list(sys.modules):
     if name == 'search-agent' or name.startswith('search-agent.'):
      sys.modules.pop(name,None)
   self.assertFalse((target/'marketing').exists()); self.assertFalse((target/'finance').exists())
   self.assertTrue(unrelated.is_dir()); self.assertEqual(rc.read_text(),'KEEP\n')
if __name__=='__main__': unittest.main()
