"""Prepare native FTB Russian fallback data. Author locales and quest logic win.

No version/key-count pin: new/changed English safely uses native English fallback.
The full-coverage switch is an explicit one-release review gate, not a future-update default.
"""
from __future__ import annotations
import argparse,copy,hashlib,importlib.util,json,os,re,sys,tempfile
from pathlib import Path,PurePosixPath

SCHEMA=1
QUESTS=Path('config/ftbquests/quests')
KIND='ftb-native-russian-fallbacks'
AUTHOR_KIND='ftb-native-russian-author-source'
FLAT=(QUESTS/'lang/ru_ru.snbt').as_posix()

class UnsupportedSource(ValueError):pass

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def text(value):return '\n'.join(value) if isinstance(value,list) else value
def normalized(value):return re.sub(r'\s+',' ',text(value).replace('\\n','\n')).strip()
def native_value(value):return isinstance(value,str) or isinstance(value,list) and all(isinstance(x,str) for x in value)
def technical(value):
    value=re.sub(r'(?i)[&§][0-9a-fk-or]','',text(value)).strip()
    value=re.sub(r'\{(?:image|item|fluid|entity|icon):[^}]*\}','',value).strip()
    return not re.search('[A-Za-zА-Яа-яЁё]',value) or bool(re.fullmatch(r'(?:https?://\S+|[a-z0-9_.-]+:[a-z0-9_./-]+|\{(?:image|item|fluid|entity|link|icon):[^}]*\})',value))

class FlatSnbt:
    """Only native locale tables: a compound of strings/string lists, with value spans."""
    def __init__(self,source):self.source=source;self.i=0;self.spans={}
    def skip(self):
        while self.i<len(self.source):
            if self.source[self.i].isspace() or self.source[self.i]==',':self.i+=1;continue
            if self.source.startswith('//',self.i) or self.source[self.i]=='#':
                end=self.source.find('\n',self.i);self.i=len(self.source) if end<0 else end+1;continue
            break
    def quote(self):
        start=self.i;quote=self.source[self.i];self.i+=1
        while self.i<len(self.source):
            char=self.source[self.i];self.i+=1
            if char=='\\':self.i+=1;continue
            if char==quote:
                raw=self.source[start:self.i]
                if quote!='"':raise ValueError('Locale parser requires native double-quoted strings')
                return json.loads(raw)
        raise ValueError('Unclosed locale string')
    def value(self):
        self.skip()
        if self.i>=len(self.source):raise ValueError('Missing locale value')
        if self.source[self.i]=='"':return self.quote()
        if self.source[self.i]=='[':
            self.i+=1;out=[]
            while True:
                self.skip()
                if self.i>=len(self.source):raise ValueError('Unclosed locale list')
                if self.source[self.i]==']':self.i+=1;return out
                if self.source[self.i]!='"':raise ValueError('Nonstring locale list member')
                out.append(self.quote())
        raise ValueError('Unsupported native locale value type')
    def parse(self):
        self.skip()
        if self.i>=len(self.source) or self.source[self.i]!='{':raise ValueError('Not a locale compound')
        self.i+=1;out={}
        while True:
            self.skip()
            if self.i>=len(self.source):raise ValueError('Unclosed locale compound')
            if self.source[self.i]=='}':self.close=self.i;self.i+=1;break
            if self.source[self.i]=='"':key=self.quote()
            else:
                start=self.i
                while self.i<len(self.source) and self.source[self.i] not in ': \t\r\n':self.i+=1
                key=self.source[start:self.i]
            self.skip()
            if not key or self.i>=len(self.source) or self.source[self.i]!=':':raise ValueError('Malformed locale key')
            self.i+=1;self.skip();start=self.i;value=self.value()
            if key in out:raise ValueError('Duplicate locale key within one file: '+key)
            out[key]=value;self.spans[key]=(start,self.i)
        self.skip()
        if self.i!=len(self.source):raise ValueError('Trailing locale content')
        self.values=out;return out

def render_value(value):
    if not native_value(value):raise ValueError('Not a native string/string-list')
    return json.dumps(value,ensure_ascii=False,separators=(', ',': '))

def merge(english,author_russian,manual,old_owned=None,*,fresh_author=False):
    """Pure update contract. No native quest object, reward, progress or other locale is touched."""
    author=copy.deepcopy(author_russian);old_owned=old_owned or {};takeovers=set();stripped=[]
    if not fresh_author:
        for key,owner in old_owned.items():
            if key not in author:continue
            current=fingerprint(author[key])
            if current==owner['generatedFingerprint']:
                same_english=key in english and fingerprint(english[key])==owner['englishFingerprint']
                if same_english and owner.get('originalAuthorPresent'):
                    author[key]=copy.deepcopy(owner['originalAuthorValue'])
                else:author.pop(key,None)
                stripped.append(key)
            elif owner.get('originalAuthorPresent') and current==fingerprint(owner['originalAuthorValue']):
                pass # A fresh base import restored the same original English/empty author value.
            else:takeovers.add(key)
    effective=copy.deepcopy(author);owned={};refresh=[];covered=[];official=[];omitted_stale_english=[]
    for key,english_value in sorted(english.items()):
        if not native_value(english_value):raise ValueError('Unsupported English translation value')
        author_present=key in author
        author_value=author.get(key)
        record=manual.get(key)
        known_untranslated_author=bool(record and author_present and
            record.get('untranslatedAuthorFingerprint')==fingerprint(author_value) and
            not re.search('[А-Яа-яЁё]',text(author_value)))
        if known_untranslated_author and record.get('englishFingerprint')!=fingerprint(english_value):
            # A known untranslated OLD English placeholder must not hide native NEW English fallback.
            effective.pop(key,None);omitted_stale_english.append(key)
        real_author=author_present and native_value(author_value) and bool(normalized(author_value)) and (
            normalized(author_value)!=normalized(english_value) or key in takeovers) and not known_untranslated_author
        if real_author:
            official.append(key);covered.append(key);continue
        if technical(english_value) or not normalized(english_value):covered.append(key);continue
        if record is None:
            refresh.append({'key':key,'reason':'new-or-untranslated-English','englishFingerprint':fingerprint(english_value),'english':english_value});continue
        if record.get('englishFingerprint')!=fingerprint(english_value):
            refresh.append({'key':key,'reason':'changed-English-manual-skipped','englishFingerprint':fingerprint(english_value),'english':english_value});continue
        value=record.get('text');decision=record.get('decision')
        if not native_value(value) or type(value)!=type(english_value):raise ValueError('Manual native type mismatch: '+key)
        if isinstance(value,list) and len(value)!=len(english_value):raise ValueError('Manual paragraph count mismatch: '+key)
        if decision not in {'translated','preserve-brand','preserve-technical'}:raise ValueError('Missing explicit manual decision: '+key)
        if decision=='translated' and (not normalized(value) or normalized(value)==normalized(english_value)):
            raise ValueError('Translated entry is empty/still English: '+key)
        covered.append(key)
        # Preserved brands/technical values can use native English fallback directly.
        if decision!='translated':continue
        effective[key]=copy.deepcopy(value)
        owned[key]={'englishFingerprint':fingerprint(english_value),'generatedFingerprint':fingerprint(value),
            'generatedValue':copy.deepcopy(value),'originalAuthorPresent':author_present,
            'originalAuthorValue':copy.deepcopy(author_value) if author_present else None}
    removed=sorted(set(manual)-set(english))
    return {'effectiveRussian':effective,'ownedEntries':owned,'refreshQueue':refresh,'removedManualKeys':removed,
        'strippedPreviousOwnedKeys':stripped,'officialRussianKeys':official,'coveredKeys':covered,
        'omittedStaleEnglishAuthorKeys':omitted_stale_english,
        'freshAuthorSource':fresh_author,'futureUpdatesBlockedForNewEnglish':False}

def read_locale(root,locale):
    base=root/QUESTS/'lang'/locale
    tables={};values={};origins={};conflicts=[]
    if not base.is_dir():return tables,values,origins,conflicts
    for path in sorted(base.rglob('*.snbt')):
        relative=path.relative_to(root).as_posix()
        raw=path.read_bytes()
        try:
            source=raw.decode('utf-8-sig');parser=FlatSnbt(source);table=parser.parse()
        except (ValueError,UnicodeError) as error:
            raise UnsupportedSource('Unsupported native locale source '+relative+': '+str(error)) from error
        tables[relative]={'bytes':raw,'source':source,'values':table}
        for key,value in table.items():
            if key in values and values[key]!=value:conflicts.append(key)
            values[key]=value;origins.setdefault(key,[]).append(relative)
    return tables,values,origins,conflicts

def safe_path(root,relative):
    relative=PurePosixPath(relative)
    if relative.is_absolute() or '\\' in str(relative) or ':' in str(relative) or '..' in relative.parts:raise ValueError('Unsafe output path')
    path=root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Output escaped pack')
    for parent in [path,*path.parents]:
        if parent==root.parent:break
        if parent.is_symlink() or hasattr(parent,'is_junction') and parent.is_junction():raise ValueError('Linked output path refused')
    return path

def dump_table(values):
    return ('{\n'+''.join('\t'+json.dumps(key,ensure_ascii=False)+': '+render_value(value)+'\n' for key,value in sorted(values.items()))+'}\n').encode('utf-8')

def atomic_write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.quest-lang-',delete=False) as stream:
            temporary=Path(stream.name);stream.write(value)
        os.replace(temporary,path);temporary=None
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)

def apply_plan(pack,planned):
    """Preflight all exact paths; failed source preparation restores touched bytes."""
    if (pack/'saves').exists() or (pack/'logs/latest.log').exists():raise ValueError('Preparation applies only to source trees, never live/personal game instances')
    paths={relative:safe_path(pack,relative) for relative in planned}
    before={relative:path.read_bytes() if path.is_file() else None for relative,path in paths.items()}
    touched=[]
    try:
        for relative,value in planned.items():
            if before[relative]==value:continue
            path=paths[relative]
            if value is None:path.unlink(missing_ok=True)
            else:atomic_write(path,value)
            touched.append(relative)
    except Exception as failure:
        rollback_failures=[]
        for relative in reversed(touched):
            try:
                if before[relative] is None:paths[relative].unlink(missing_ok=True)
                else:atomic_write(paths[relative],before[relative])
            except Exception as error:rollback_failures.append({'path':relative,'failure':str(error)})
        if rollback_failures:raise RuntimeError('Preparation failed and rollback needs review: '+str(rollback_failures)) from failure
        raise

def capture_author(root,ownership,english,*,fresh=False):
    """Capture pristine native source before generation. Never infer author data from our flat."""
    tables,values,origins,conflicts=read_locale(root,'ru_ru')
    if conflicts:raise UnsupportedSource('Conflicting source RU folder keys; author input remains untouched')
    # Native Splitter ignores empty string/list folder entries while merging.
    values={key:value for key,value in values.items() if value!='' and value!=[]}
    flat_path=root/FLAT
    flat=None
    if flat_path.is_file():
        raw=flat_path.read_bytes()
        ours=ownership and ownership.get('flatSha256')==hashlib.sha256(raw).hexdigest()
        if fresh or not ours:
            try:flat=FlatSnbt(raw.decode('utf-8-sig')).parse()
            except (ValueError,UnicodeError) as error:
                raise UnsupportedSource('Unsupported native flat RU source '+FLAT+': '+str(error)) from error
            if ownership and not fresh:
                # Per-entry provenance still applies when only one part of our flat was edited.
                for key,owner in ownership.get('entries',{}).items():
                    if key not in flat or fingerprint(flat[key])!=owner['generatedFingerprint']:continue
                    if key in english and fingerprint(english[key])==owner['englishFingerprint'] and owner.get('originalAuthorPresent'):
                        flat[key]=copy.deepcopy(owner['originalAuthorValue'])
                    else:flat.pop(key,None)
            merged=dict(flat);merged.update(values);values=merged
            tables[FLAT]={'bytes':raw,'source':raw.decode('utf-8-sig'),'values':flat}
    present=bool(tables) or fresh
    snapshots=[];copies={}
    for relative,table in sorted(tables.items()):
        suffix=relative.split('/lang/',1)[1]
        copy_path='tools/quest-translations/upstream-ru/'+suffix
        copies[copy_path]=table['bytes']
        snapshots.append({'path':relative,'sha256':hashlib.sha256(table['bytes']).hexdigest(),
            'bytes':len(table['bytes']),'sourceCopy':copy_path})
    return present,values,snapshots,copies

def prepare(pack,manual_document,ownership,author_cache,*,fresh_author_root=None,require_complete=False,inline_document=None):
    en_tables,english,en_origins,en_conflicts=read_locale(pack,'en_us')
    if not english:raise UnsupportedSource('No supported native English locale tables; preserve native author data')
    if en_conflicts:raise UnsupportedSource('Conflicting source EN locale keys')
    records=manual_document.get('entries',{})
    if manual_document.get('schemaVersion')!=SCHEMA or manual_document.get('kind')!=KIND:raise ValueError('Unknown manual schema')
    if ownership and (ownership.get('schemaVersion')!=SCHEMA or ownership.get('kind')!=KIND):raise ValueError('Unknown ownership schema')
    if author_cache and (author_cache.get('schemaVersion')!=SCHEMA or author_cache.get('kind')!=AUTHOR_KIND):raise ValueError('Unknown author-source schema')
    if fresh_author_root is not None:
        _,upstream_en,_,upstream_conflicts=read_locale(fresh_author_root,'en_us')
        if upstream_conflicts or upstream_en!=english:
            raise ValueError('Import the fresh English/base pack first; upstream and target English differ')
    captured,russian,sources,copies=capture_author(fresh_author_root or pack,ownership,english,fresh=fresh_author_root is not None)
    stale_cached_author=[]
    if not captured:
        russian=(author_cache or {}).get('entries',{})
        sources=(author_cache or {}).get('sources',[])
        captured_fingerprints=(author_cache or {}).get('englishFingerprintsAtCapture',{})
        # On a retry the pristine cache is authoritative only for the English it
        # was captured against. A future import must supply fresh author data,
        # including an explicitly empty/absent RU locale. Never silently carry
        # an old Russian meaning over changed English when that import was missed.
        stale_cached_author=[key for key in russian if key in english and
            captured_fingerprints.get(key)!=fingerprint(english[key])]
        russian={key:value for key,value in russian.items() if key not in stale_cached_author}
    new_cache={'schemaVersion':SCHEMA,'kind':AUTHOR_KIND,'entries':russian,'sources':sources,
        'englishFingerprintsAtCapture':{key:fingerprint(value) for key,value in english.items()} if captured else
            (author_cache or {}).get('englishFingerprintsAtCapture',{})}
    # The authoritative source cache, not managed game output, drives every retry.
    merged=merge(english,russian,records,fresh_author=True)
    flat_bytes=dump_table(merged['effectiveRussian'])
    planned={FLAT:flat_bytes,**copies}
    # These are explicit SOURCE input paths captured above, not unknown runtime configs.
    # Runtime _merged files are neither matched nor deleted.
    native_folders,_,_,_=read_locale(pack,'ru_ru')
    for path in native_folders:planned[path]=None
    new_owner={'schemaVersion':SCHEMA,'kind':KIND,'entries':merged['ownedEntries'],
        'flatPath':FLAT,'flatSha256':hashlib.sha256(flat_bytes).hexdigest(),
        'authorSourceFingerprint':fingerprint(new_cache['entries'])}
    inline_report=None
    if inline_document is not None:
        spec=importlib.util.spec_from_file_location('native_quest_inline',Path(__file__).with_name('inline.py'))
        inline_tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(inline_tool)
        try:
            inline_plan,inline_state,inline_report=inline_tool.prepare(pack,inline_document,(ownership or {}).get('inline'),fresh_author_root)
            if set(planned)&set(inline_plan):raise ValueError('Inline and locale plans overlap')
            planned.update(inline_plan);new_owner['inline']=inline_state
        except inline_tool.UnsupportedSourceShape as error:
            inline_report={'skippedUnsupportedSource':True,'reason':str(error),'refreshQueue':[{'reason':'unsupported-future-inline-source'}]}
            if ownership and 'inline' in ownership:new_owner['inline']=ownership['inline']
    unresolved=len(merged['refreshQueue'])+(len(inline_report['refreshQueue']) if inline_report else 0)
    if require_complete and unresolved:raise ValueError('Current-release manual coverage is incomplete: '+str(unresolved))
    report={key:value for key,value in merged.items() if key not in {'effectiveRussian','ownedEntries','coveredKeys','officialRussianKeys'}}
    report.update({'schemaVersion':SCHEMA,'kind':KIND,'englishKeys':len(english),'authorRussianKeys':len(russian),
        'effectiveRussianKeys':len(merged['effectiveRussian']),'coveredKeys':len(merged['coveredKeys']),'officialRussianKeys':len(merged['officialRussianKeys']),
        'ownedFallbackKeys':len(merged['ownedEntries']),'changedPaths':list(planned),
        'nativeManagedRussianPath':FLAT,'freshAuthorSourceCaptured':captured,
        'sourceOnlyAuthorCacheUsed':True,'nativeMergedInstanceFilesModified':False,
        'sourceEnglishOrOtherLocalesOrQuestLogicChanged':False,'jarOrPlatformChanged':False,
        'currentReleaseRequireComplete':require_complete})
    report['staleCachedAuthorKeysSkippedUntilFreshImport']=sorted(stale_cached_author)
    if inline_report is not None:report['inline']=inline_report
    return planned,new_owner,new_cache,report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['prepare','import-author'])
    parser.add_argument('--pack',type=Path,required=True);parser.add_argument('--manual',type=Path,required=True)
    parser.add_argument('--ownership',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--author-cache',type=Path,required=True)
    parser.add_argument('--inline-manual',type=Path)
    parser.add_argument('--upstream',type=Path);parser.add_argument('--apply',action='store_true')
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args();pack=args.pack.resolve(strict=True)
    if args.mode=='import-author' and args.upstream is None:parser.error('import-author needs a fresh --upstream pack root')
    manual=json.loads(args.manual.read_text(encoding='utf-8-sig'))
    ownership=json.loads(args.ownership.read_text(encoding='utf-8-sig')) if args.ownership.is_file() else None
    author_cache=json.loads(args.author_cache.read_text(encoding='utf-8-sig')) if args.author_cache.is_file() else None
    inline_document=json.loads(args.inline_manual.read_text(encoding='utf-8-sig')) if args.inline_manual else None
    try:
        planned,new_owner,new_cache,report=prepare(pack,manual,ownership,author_cache,fresh_author_root=args.upstream.resolve(strict=True) if args.upstream else None,
            require_complete=args.require_complete,inline_document=inline_document)
    except UnsupportedSource as error:
        # Unknown future native schema is reported, preserving author input and normal updates.
        report={'status':'SKIPPED_UNSUPPORTED_SOURCE','reason':str(error),'manualApplied':False,'futurePackUpdateBlocked':False}
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if args.require_complete:raise
        print(json.dumps(report,ensure_ascii=False));return
    if args.apply:
        for path,value in [(args.ownership,new_owner),(args.author_cache,new_cache)]:
            relative=path.resolve().relative_to(pack).as_posix()
            if not relative.startswith('tools/'):raise ValueError('Author and ownership provenance must remain source-only under tools/')
            planned[relative]=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        apply_plan(pack,planned)
    report['status']='PREPARED' if args.apply else 'PLAN_ONLY'
    report['applied']=args.apply
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({**{key:report[key] for key in ['status','englishKeys','effectiveRussianKeys','ownedFallbackKeys','coveredKeys','changedPaths','futureUpdatesBlockedForNewEnglish']},
        'untranslatedOrChangedKeys':len(report['refreshQueue'])},ensure_ascii=False))
if __name__=='__main__':main()
