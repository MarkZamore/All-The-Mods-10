import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('quest_inline',Path(__file__).with_name('inline.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
PATH='config/ftbquests/quests/chapters/test.snbt'
KEY='atm10quests.manual.inline.sample'

def fixture(root,hover=None):
    hover=['Read this!'] if hover is None else hover
    raw='\ufeff{\r\n\tid: "1234567890ABCDEF"\r\n\timages: [{ x: 1.5d image: "author:texture" hover: '+json.dumps(hover)+' click: "https://example.org" }]\r\n\tquests: [{id: "FEDCBA0987654321" rewards: [{count: 32 type: "item"}]}]\r\n}\r\n'
    path=root/PATH;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw.encode())
    node=p.Reader(raw).parse();trail=['images',0,'hover']
    record={'key':KEY,'sourcePath':PATH,'displayPath':trail,'englishFingerprint':p.fp(hover),
        'imageFingerprint':p.image_identity(node,trail),'text':['Прочитайте это!'],'decision':'translated'}
    return raw,{'schemaVersion':1,'kind':'ftb-image-hover-language-aliases','entries':[record]}

def apply(root,plan):
    for relative,value in plan.items():
        path=root/relative
        if value is None:path.unlink(missing_ok=True)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)

class InlineTests(unittest.TestCase):
    def test_only_hover_span_changes_and_retry_is_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw,doc=fixture(root);before=p.Reader(raw).parse()
            plans,state,report=p.prepare(root,doc)
            after=p.Reader(plans[PATH].decode()).parse()
            before.children['images'].children[0].children['hover'].value=after.value['images'][0]['hover']
            before.value['images'][0]['hover']=after.value['images'][0]['hover']
            self.assertEqual(before.value,after.value);self.assertTrue(plans[PATH].startswith(b'\xef\xbb\xbf'))
            self.assertEqual(plans[PATH].count(b'\r\n'),raw.count('\r\n'))
            apply(root,plans);retry,state2,report2=p.prepare(root,doc,state)
            self.assertNotIn(PATH,retry);self.assertEqual(state,state2);self.assertFalse(report2['refreshQueue'])
    def test_changed_english_skips_stale_manual_and_reports_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);_,doc=fixture(root);plans,state,_=p.prepare(root,doc);apply(root,plans)
            upstream=root/'upstream';fixture(upstream,['A new instruction!'])
            plans,new_state,report=p.prepare(root,doc,state,upstream)
            after=p.Reader(plans[PATH].decode()).parse()
            self.assertEqual(after.value['images'][0]['hover'],['A new instruction!'])
            self.assertFalse(new_state['entries']);self.assertEqual(report['refreshQueue'][0]['reason'],'changed-inline-English-manual-skipped')
    def test_removed_manual_restores_exact_native_english_value(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);_,doc=fixture(root);plans,state,_=p.prepare(root,doc);apply(root,plans)
            doc['entries']=[];plans,new_state,_=p.prepare(root,doc,state)
            self.assertEqual(p.Reader(plans[PATH].decode()).parse().value['images'][0]['hover'],['Read this!'])
            self.assertIsNone(plans[p.EN_RESOURCE]);self.assertIsNone(plans[p.RU_RESOURCE])
    def test_unknown_resource_collision_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);_,doc=fixture(root);path=root/p.EN_RESOURCE;path.parent.mkdir(parents=True);path.write_text('{"author":"value"}')
            with self.assertRaises(p.UnsupportedSourceShape):p.prepare(root,doc)
            self.assertEqual(path.read_text(),'{"author":"value"}')
    def test_changed_image_anchor_skips_translation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw,doc=fixture(root);(root/PATH).write_text(raw.replace('1.5d','2.5d'),encoding='utf-8')
            plans,state,report=p.prepare(root,doc)
            self.assertNotIn(PATH,plans);self.assertFalse(state['entries'])
            self.assertEqual(report['refreshQueue'][0]['reason'],'changed-image-anchor-manual-skipped')
    def test_other_inline_fields_cannot_be_selected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);_,doc=fixture(root);doc['entries'][0]['displayPath']=['images',0,'click']
            with self.assertRaises(ValueError):p.prepare(root,doc)

if __name__=='__main__':unittest.main()
