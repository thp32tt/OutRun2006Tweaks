import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from build_imagegen_prompt import assemble
from stage_controller_policy import configure, render, validate_roles, NAME


def png_bytes():
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))+
            chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff\x00'))+chunk(b'IEND', b''))


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        raw = png_bytes()
        (self.root/'source.png').write_bytes(raw)
        self.manifest = dict(mode='atlas', reference_png='source.png',
                             reference_png_sha256=hashlib.sha256(raw).hexdigest(),
                             source_dds_sha256='a'*64, readable_transform='flip_y',
                             translations=[dict(source='OUT RUN MODE', korean='아웃런 모드')])
        self.compose = {'services': {NAME: {'image': 'outrun-kor-plate-engine:'+'b'*12,
            'environment': {'AUTO_SEND':'false', 'CHAT_SLOTS':'4', 'SCHEDULE_MINUTES':'0,10,20,30,40,50',
                            'CHATGPT_PROJECT_URL':'${CHATGPT_PROJECT_URL}', 'PRIVATE_VALUE':'${PRIVATE_VALUE}'},
            'volumes':['data:/data', 'logs:/logs']},
            'unrelated': {'image':'unrelated:fixed', 'environment':{'KEEP':'yes'}}},
            'volumes':{'data':{'external':True}, 'logs':{'external':True}}}

    def test_prompt_atlas_and_roi_remain_unexecuted(self):
        for mode in ('atlas', 'roi'):
            self.manifest['mode']=mode
            prompt, receipt=assemble(self.manifest, self.root)
            self.assertIn('아웃런 모드', prompt)
            self.assertNotIn('{{', prompt)
            self.assertFalse(receipt['attachment_verified'])
            self.assertIsNone(receipt['generation_id'])
            self.assertEqual(receipt['status'], 'PROMPT_PREPARED_NOT_GENERATED')

    def test_invalid_reference_and_placeholder_blocked(self):
        for key,value in [('reference_png_sha256','b'*64), ('readable_transform','mixed'),
                          ('source_dds_sha256','missing')]:
            manifest=copy.deepcopy(self.manifest); manifest[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): assemble(manifest,self.root)
        self.manifest['translations'][0]['korean']='[승인된 한국어]'
        with self.assertRaises(ValueError): assemble(self.manifest,self.root)

    def test_roi_multi_label_rejected(self):
        self.manifest['mode']='roi'
        self.manifest['translations'] *= 2
        with self.assertRaises(ValueError): assemble(self.manifest,self.root)

    def test_same_image_still_changes_schedule_and_enables_auto_send(self):
        result=configure(self.compose, 'b'*40)
        env=result['services'][NAME]['environment']
        self.assertEqual(env['AUTO_SEND'],'true')
        self.assertEqual(env['CHAT_SLOTS'],'3')
        self.assertEqual(env['SCHEDULE_MINUTES'],'0,10,30,40')
        self.assertEqual(result['services']['unrelated'],self.compose['services']['unrelated'])
        self.assertEqual(result['volumes'],self.compose['volumes'])
        self.assertEqual(result['services'][NAME]['volumes'],self.compose['services'][NAME]['volumes'])
        self.assertEqual(env['PRIVATE_VALUE'],'${PRIVATE_VALUE}')
        self.assertEqual(self.compose['services'][NAME]['environment']['AUTO_SEND'],'false')
        self.assertEqual(configure(result,'b'*40), result)

    def test_updates_existing_owned_image_and_list_environment(self):
        self.compose['services'][NAME]['environment']=['KEEP=value=with=equals','INHERIT','AUTO_SEND=false']
        result=configure(self.compose,'c'*40)
        self.assertEqual(result['services'][NAME]['image'],'outrun-kor-plate-engine:'+'c'*12)
        self.assertEqual(result['services'][NAME]['environment']['KEEP'],'value=with=equals')
        self.assertIsNone(result['services'][NAME]['environment']['INHERIT'])

    def test_foreign_image_and_bad_revision_blocked(self):
        with self.assertRaises(ValueError): configure(self.compose,'branch-name')
        self.compose['services'][NAME]['image']='foreign:tag'
        with self.assertRaises(ValueError): configure(self.compose,'c'*40)

    def test_shared_service_anchor_does_not_modify_other_service(self):
        self.compose['services']['unrelated']=self.compose['services'][NAME]
        result=configure(self.compose,'c'*40)
        self.assertEqual(result['services']['unrelated'],self.compose['services'][NAME])
        self.assertEqual(result['services'][NAME]['environment']['AUTO_SEND'],'true')

    def test_shared_environment_anchor_does_not_modify_other_service(self):
        original=self.compose['services'][NAME]['environment']
        self.compose['services']['unrelated']['environment']=original
        result=configure(self.compose,'c'*40)
        self.assertEqual(result['services']['unrelated']['environment'],original)
        self.assertEqual(result['services']['unrelated']['environment']['AUTO_SEND'],'false')

    def test_staging_script_saves_original_backup_without_lifecycle_commands(self):
        import types
        from unittest.mock import patch
        import yaml
        import deploy_plate_controller as deployer
        revision='b'*40
        checkout=Path(__file__).resolve().parents[2]
        stack=self.root/'stack'
        stack.mkdir()
        (stack/'prompts').mkdir()
        (stack/'prompts/localization_C2.md').write_text('retired evidence')
        self.compose['services'][NAME]['environment']['CHATGPT_PROJECT_URL']='https://chatgpt.com/g/example/project'
        original=yaml.safe_dump(self.compose)
        (stack/'docker-compose.yml').write_text(original)
        calls=[]
        def fake_run(args, **kwargs):
            calls.append(args)
            if args[0]=='git':
                if args[3]=='rev-parse': return revision+'\n'
                return (checkout/args[-1].split(':',1)[1]).read_text()
            if args[1]=='build':
                context=Path(args[-1])
                self.assertTrue((context/'imagegen_prompts/atlas.txt').exists())
                self.assertFalse((context/'localization_C2.md').exists())
                return ''
            if 'portainer_data:/pdata:ro' in args:
                return json.dumps({'compose':(stack/'docker-compose.yml').read_text(),'env':{}})
            if 'portainer_data:/pdata' in args:
                exec(compile(args[-1],'<staged-update>','exec'),{})
                return ''
            raise AssertionError(args)
        with patch.object(deployer,'STACK',str(stack)), patch.object(deployer,'SUBDIR','.'), \
             patch.object(deployer,'run',side_effect=fake_run), \
             patch.object(deployer.subprocess,'run',return_value=types.SimpleNamespace(returncode=1,stdout='')):
            first=deployer.deploy(checkout,revision)
            staged=(stack/'docker-compose.yml').read_text()
            second=deployer.deploy(checkout,revision)
        self.assertEqual(staged,(stack/'docker-compose.yml').read_text())
        self.assertEqual((stack/('docker-compose.yml.before-plate-'+revision[:12])).read_text(),original)
        self.assertEqual(yaml.safe_load(staged)['services'][NAME]['environment']['AUTO_SEND'],'true')
        self.assertFalse((stack/'prompts/localization_C2.md').exists())
        self.assertEqual((stack/('prompts/localization_C2.md.retired-'+revision[:12])).read_text(),'retired evidence')
        self.assertEqual(first['deployment_mode'],'MANUAL_ONLY')
        self.assertTrue(first['auto_send'])
        self.assertFalse(second['runtime_schedule_verified'])
        self.assertTrue(all(args[0]!='docker' or args[1] in ('build','run') for args in calls))

    def test_render_roundtrip_and_policy(self):
        import yaml
        value=yaml.safe_dump(self.compose)
        output=render(value,'d'*40)
        self.assertEqual(render(output,'d'*40),output)
        roles=json.loads((Path(__file__).resolve().parents[2]/'localization/controller_roles.json').read_text())
        validate_roles(roles)
        roles['schedule_dispatch']['minute_to_role']['10']='B'
        with self.assertRaises(ValueError): validate_roles(roles)


if __name__ == '__main__': unittest.main()
