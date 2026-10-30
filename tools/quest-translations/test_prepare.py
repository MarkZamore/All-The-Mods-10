import importlib.util,json,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path

spec=importlib.util.spec_from_file_location('quest_prepare',Path(__file__).with_name('prepare.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
K='quest.0000000000000001.title'
L='quest.0000000000000002.quest_desc'

def record(english,russian,decision='translated',original=None):
    result={'englishFingerprint':p.fingerprint(english),'text':russian,'decision':decision}
    if original is not None:result['untranslatedAuthorFingerprint']=p.fingerprint(original)
    return result
def manual(entries):return {'schemaVersion':1,'kind':p.KIND,'entries':entries}
def write_locale(root,locale,values):
    path=root/p.QUESTS/'lang'/locale/'chapter.snbt';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(p.dump_table(values));return path
def apply(root,plan):
    for relative,value in plan.items():
        path=root/relative
        if value is None:path.unlink(missing_ok=True)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)

class MergeTests(unittest.TestCase):
    def test_missing_russian_gets_matching_manual(self):
        r=p.merge({K:'Gear'}, {}, {K:record('Gear','Шестерня')})
        self.assertEqual(r['effectiveRussian'][K],'Шестерня');self.assertFalse(r['refreshQueue'])
    def test_author_russian_always_wins(self):
        r=p.merge({K:'Gear'},{K:'Авторская шестерня'},{K:record('Gear','Наш перевод')})
        self.assertEqual(r['effectiveRussian'][K],'Авторская шестерня');self.assertNotIn(K,r['ownedEntries'])
    def test_still_english_author_can_be_filled(self):
        r=p.merge({K:'Gear'},{K:'Gear'},{K:record('Gear','Шестерня')})
        self.assertEqual(r['effectiveRussian'][K],'Шестерня')
    def test_reviewed_english_variant_can_be_filled(self):
        r=p.merge({K:'Disenchanting Methods'},{K:'Dis-Enchanting Table'},
            {K:record('Disenchanting Methods','Способы снятия чар',original='Dis-Enchanting Table')})
        self.assertEqual(r['effectiveRussian'][K],'Способы снятия чар')
    def test_new_author_russian_replaces_reviewed_english(self):
        r=p.merge({K:'Disenchanting Methods'},{K:'Авторские способы'},
            {K:record('Disenchanting Methods','Наши способы',original='Dis-Enchanting Table')})
        self.assertEqual(r['effectiveRussian'][K],'Авторские способы')
    def test_fingerprint_cannot_authorize_overriding_russian(self):
        r=p.merge({K:'Gear'},{K:'Авторский перевод'},
            {K:record('Gear','Наш перевод',original='Авторский перевод')})
        self.assertEqual(r['effectiveRussian'][K],'Авторский перевод')
    def test_new_english_uses_native_fallback_without_blocking(self):
        r=p.merge({K:'New chapter'}, {}, {})
        self.assertNotIn(K,r['effectiveRussian']);self.assertEqual(len(r['refreshQueue']),1)
        self.assertFalse(r['futureUpdatesBlockedForNewEnglish'])
    def test_changed_english_skips_stale_manual(self):
        r=p.merge({K:'New machine'}, {}, {K:record('Old machine','Старая машина')})
        self.assertNotIn(K,r['effectiveRussian']);self.assertEqual(r['refreshQueue'][0]['reason'],'changed-English-manual-skipped')
    def test_changed_english_does_not_restore_old_untranslated_author(self):
        r=p.merge({K:'New machine'}, {K:'Old machine'},
            {K:record('Old machine','Старая машина',original='Old machine')})
        self.assertNotIn(K,r['effectiveRussian']);self.assertIn(K,r['omittedStaleEnglishAuthorKeys'])
    def test_removed_english_drops_only_owned_generated_value(self):
        old=p.merge({K:'Gear'}, {}, {K:record('Gear','Шестерня')})
        r=p.merge({},old['effectiveRussian'],{K:record('Gear','Шестерня')},old['ownedEntries'])
        self.assertNotIn(K,r['effectiveRussian']);self.assertEqual(r['removedManualKeys'],[K])
    def test_retry_does_not_mistake_manual_for_author(self):
        records={K:record('Gear','Шестерня')};first=p.merge({K:'Gear'},{K:'Gear'},records)
        retry=p.merge({K:'Gear'},first['effectiveRussian'],records,first['ownedEntries'])
        self.assertEqual(first['effectiveRussian'],retry['effectiveRussian']);self.assertEqual(first['ownedEntries'],retry['ownedEntries'])
    def test_explicit_fresh_author_same_as_old_manual_is_official(self):
        first=p.merge({K:'Gear'}, {}, {K:record('Gear','Шестерня')})
        new=p.merge({K:'New gear'},{K:'Шестерня'},{K:record('Gear','Шестерня')},first['ownedEntries'],fresh_author=True)
        self.assertEqual(new['effectiveRussian'][K],'Шестерня');self.assertFalse(new['ownedEntries'])
    def test_preserve_brand_is_explicit_coverage_without_fake_ru(self):
        r=p.merge({K:'Create'}, {}, {K:record('Create','Create','preserve-brand')})
        self.assertIn(K,r['coveredKeys']);self.assertNotIn(K,r['effectiveRussian'])
    def test_string_list_shape_is_enforced(self):
        with self.assertRaises(ValueError):p.merge({L:['a']},{},{L:record(['a'],'Неверный тип')})
    def test_list_paragraph_count_is_enforced(self):
        with self.assertRaises(ValueError):p.merge({L:['a','b']},{},{L:record(['a','b'],['Один абзац'])})

class PreparationTests(unittest.TestCase):
    def test_managed_flat_removes_source_folders_only_after_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);en=write_locale(root,'en_us',{K:'Gear'});ru=write_locale(root,'ru_ru',{})
            fr=write_locale(root,'fr_fr',{K:'Engrenage'});en_before=en.read_bytes();fr_before=fr.read_bytes()
            plan,owner,cache,report=p.prepare(root,manual({K:record('Gear','Шестерня')}),None,None,require_complete=True)
            self.assertIn(ru.relative_to(root).as_posix(),plan);self.assertIsNone(plan[ru.relative_to(root).as_posix()])
            apply(root,plan)
            self.assertFalse(ru.exists());self.assertTrue((root/p.FLAT).is_file())
            self.assertEqual(en.read_bytes(),en_before);self.assertEqual(fr.read_bytes(),fr_before)
            self.assertEqual(p.FlatSnbt((root/p.FLAT).read_text(encoding='utf-8')).parse()[K],'Шестерня')
            retry,owner2,cache2,report2=p.prepare(root,manual({K:record('Gear','Шестерня')}),owner,cache)
            self.assertEqual(plan[p.FLAT],retry[p.FLAT]);self.assertEqual(owner,owner2)
    def test_future_new_keys_do_not_fail_default_preparation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_locale(root,'en_us',{K:'New chapter'})
            plan,owner,cache,report=p.prepare(root,manual({}),None,None)
            self.assertEqual(len(report['refreshQueue']),1);self.assertFalse(report['futureUpdatesBlockedForNewEnglish'])
            self.assertEqual(p.FlatSnbt(plan[p.FLAT].decode()).parse(),{})
    def test_current_full_coverage_gate_is_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_locale(root,'en_us',{K:'New chapter'})
            with self.assertRaises(ValueError):p.prepare(root,manual({}),None,None,require_complete=True)
    def test_explicit_fresh_import_can_remove_all_author_russian(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'target';upstream=Path(temp)/'upstream'
            write_locale(target,'en_us',{K:'Gear'});write_locale(upstream,'en_us',{K:'Gear'})
            plan,owner,cache,report=p.prepare(target,manual({}),None,
                {'schemaVersion':1,'kind':p.AUTHOR_KIND,'entries':{K:'Старый авторский перевод'}},fresh_author_root=upstream)
            self.assertEqual(cache['entries'],{});self.assertNotIn(K,p.FlatSnbt(plan[p.FLAT].decode()).parse())
    def test_fresh_author_import_requires_matching_base_english(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'target';upstream=Path(temp)/'upstream'
            write_locale(target,'en_us',{K:'Old'});write_locale(upstream,'en_us',{K:'New'})
            with self.assertRaises(ValueError):p.prepare(target,manual({}),None,None,fresh_author_root=upstream)
    def test_merged_runtime_leftovers_are_not_source_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_locale(root,'en_us',{K:'Gear'})
            junk=root/p.QUESTS/'lang/ru_ru/chapter.snbt_merged';junk.parent.mkdir(parents=True);junk.write_text('{broken unrelated native leftover')
            plan,_,_,_=p.prepare(root,manual({K:record('Gear','Шестерня')}),None,None)
            self.assertNotIn(junk.relative_to(root).as_posix(),plan);self.assertTrue(junk.exists())
    def test_stale_cached_author_without_fresh_import_is_not_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_locale(root,'en_us',{K:'New machine'})
            cache={'schemaVersion':1,'kind':p.AUTHOR_KIND,'entries':{K:'Старый смысл'},
                'englishFingerprintsAtCapture':{K:p.fingerprint('Old machine')}}
            plan,_,_,report=p.prepare(root,manual({K:record('Old machine','Старый ручной смысл')}),None,cache)
            self.assertNotIn(K,p.FlatSnbt(plan[p.FLAT].decode()).parse())
            self.assertEqual(report['staleCachedAuthorKeysSkippedUntilFreshImport'],[K])
            self.assertEqual(len(report['refreshQueue']),1)
    def test_failed_multi_file_apply_restores_all_previous_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'first').write_bytes(b'old');real=p.atomic_write
            def fail_second(path,value):
                if path.name=='second':raise OSError('simulated preparation write failure')
                real(path,value)
            with patch.object(p,'atomic_write',side_effect=fail_second):
                with self.assertRaises(OSError):p.apply_plan(root,{'first':b'new','second':b'new'})
            self.assertEqual((root/'first').read_bytes(),b'old');self.assertFalse((root/'second').exists())
    def test_edited_flat_keeps_new_author_but_not_unchanged_owned_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_locale(root,'en_us',{K:'Gear',L:'Plate'})
            first,owner,cache,_=p.prepare(root,manual({K:record('Gear','Шестерня'),L:record('Plate','Пластина')}),None,None)
            apply(root,first)
            (root/p.FLAT).write_bytes(p.dump_table({K:'Новый авторский перевод',L:'Пластина'}))
            plan,new_owner,new_cache,_=p.prepare(root,manual({K:record('Gear','Шестерня'),L:record('Plate','Пластина')}),owner,cache)
            self.assertEqual(new_cache['entries'],{K:'Новый авторский перевод'})
            self.assertNotIn(K,new_owner['entries']);self.assertIn(L,new_owner['entries'])
            self.assertEqual(p.FlatSnbt(plan[p.FLAT].decode()).parse(),{K:'Новый авторский перевод',L:'Пластина'})
    def test_unknown_future_flat_default_cli_skips_without_blocking_or_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_locale(root,'en_us',{K:'Gear'})
            raw=("{ "+K+": 'Нативная новая форма' }").encode('utf-8');(root/p.FLAT).write_bytes(raw)
            tool=root/'tools';tool.mkdir();source=tool/'manual.json';source.write_text(json.dumps(manual({K:record('Gear','Шестерня')})),encoding='utf-8')
            report=tool/'report.json'
            result=subprocess.run([sys.executable,str(Path(p.__file__)),'prepare','--pack',str(root),'--manual',str(source),
                '--ownership',str(tool/'ownership.json'),'--author-cache',str(tool/'author.json'),'--report',str(report),'--apply'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(report.read_text('utf-8'))['status'],'SKIPPED_UNSUPPORTED_SOURCE')
            self.assertEqual((root/p.FLAT).read_bytes(),raw);self.assertFalse((tool/'ownership.json').exists())
    def test_unknown_future_flat_explicit_current_gate_still_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_locale(root,'en_us',{K:'Gear'});(root/p.FLAT).write_text("{ "+K+": 'Нативная новая форма' }",encoding='utf-8')
            with self.assertRaises(p.UnsupportedSource):p.prepare(root,manual({K:record('Gear','Шестерня')}),None,None,require_complete=True)

if __name__=='__main__':unittest.main()
