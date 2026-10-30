"""Native language-key aliases for legacy chapter-image hover fields only.

Edits replace exact display-value spans. IDs, images, clicks and quest logic retain
their original bytes. These are preparation data, never a runtime mod or agent.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,re

EN_RESOURCE='kubejs/assets/atm10_quest_language/lang/en_us.json'
RU_RESOURCE='kubejs/assets/atm10_quest_language/lang/ru_ru.json'

class UnsupportedSourceShape(ValueError):pass

def fp(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def native_value(value):return isinstance(value,str) or isinstance(value,list) and all(isinstance(x,str) for x in value)

class Node:
    def __init__(self,value,start,end,children=None):self.value=value;self.start=start;self.end=end;self.children=children

class Reader:
    def __init__(self,text):self.text=text;self.i=0
    def skip(self):
        while self.i<len(self.text):
            if self.text[self.i].isspace() or self.text[self.i]==',' or self.i==0 and self.text[self.i]=='\ufeff':self.i+=1;continue
            if self.text.startswith('//',self.i) or self.text[self.i]=='#':
                end=self.text.find('\n',self.i);self.i=len(self.text) if end<0 else end+1;continue
            break
    def string(self):
        start=self.i;quote=self.text[self.i];self.i+=1
        while self.i<len(self.text):
            char=self.text[self.i];self.i+=1
            if char=='\\':self.i+=1;continue
            if char==quote:
                if quote!='"':raise ValueError('Unsupported single-quoted SNBT source')
                return json.loads(self.text[start:self.i])
        raise ValueError('Unclosed SNBT string')
    def value(self):
        self.skip();start=self.i
        if self.i>=len(self.text):raise ValueError('Missing SNBT value')
        char=self.text[self.i]
        if char=='"':return Node(self.string(),start,self.i)
        if char=='{':
            self.i+=1;children={}
            while True:
                self.skip()
                if self.i>=len(self.text):raise ValueError('Unclosed SNBT compound')
                if self.text[self.i]=='}':self.i+=1;return Node({k:v.value for k,v in children.items()},start,self.i,children)
                if self.text[self.i]=='"':key=self.string()
                else:
                    key_start=self.i
                    while self.i<len(self.text) and self.text[self.i] not in ': \t\r\n':self.i+=1
                    key=self.text[key_start:self.i]
                self.skip()
                if not key or self.i>=len(self.text) or self.text[self.i]!=':':raise ValueError('Malformed SNBT key')
                self.i+=1;children[key]=self.value()
        if char=='[':
            self.i+=1;children=[];typed=None
            self.skip()
            if self.i+1<len(self.text) and self.text[self.i] in 'BIL' and self.text[self.i+1]==';':typed=self.text[self.i];self.i+=2
            while True:
                self.skip()
                if self.i>=len(self.text):raise ValueError('Unclosed SNBT list')
                if self.text[self.i]==']':
                    self.i+=1;values=[x.value for x in children]
                    return Node({'typedArray':typed,'values':values} if typed else values,start,self.i,children)
                children.append(self.value())
        while self.i<len(self.text) and self.text[self.i] not in ' \t\r\n,]}':self.i+=1
        if self.i==start:raise ValueError('Unsupported SNBT token')
        return Node({'nativeToken':self.text[start:self.i]},start,self.i)
    def parse(self):
        result=self.value();self.skip()
        if self.i!=len(self.text):raise ValueError('Trailing SNBT content')
        return result

def locate(root,trail):
    node=root
    for part in trail:
        if node.children is None:return None
        try:node=node.children[part]
        except (KeyError,IndexError,TypeError):return None
    return node

def image_identity(root,trail):
    image=locate(root,trail[:2])
    if image is None or not isinstance(image.value,dict):return None
    return fp({key:value for key,value in image.value.items() if key!='hover'})

def literal_resource(value):return value.replace('%','%%')

def read_source(path):
    source=path.read_bytes().decode('utf-8')
    try:return source,Reader(source).parse()
    except ValueError as error:raise UnsupportedSourceShape('Unrecognized future inline SNBT: '+str(path)) from error

def prepare(pack,document,old_state=None,upstream=None):
    old_state=old_state or {};owned=old_state.get('entries',{});old_hashes=old_state.get('resourceSha256',{})
    records=document.get('entries',[])
    if document.get('schemaVersion')!=1 or document.get('kind')!='ftb-image-hover-language-aliases':raise ValueError('Unknown inline translation schema')
    plans={};new_owned={};english={};russian={};refresh=[];sources={};nodes={};edits={};covered=[]
    for resource in [EN_RESOURCE,RU_RESOURCE]:
        path=pack/resource
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()!=old_hashes.get(resource):
            raise UnsupportedSourceShape('Unowned language resource exists; preserve author data: '+resource)
    for record in records:
        path=record['sourcePath'];trail=record['displayPath'];key=record['key']
        if not path.startswith('config/ftbquests/quests/chapters/') or not path.endswith('.snbt') or any(x in {'.','..'} for x in PurePosixPath(path).parts) or '\\' in path or ':' in path or len(trail)!=3 or trail[0]!='images' or type(trail[1]) is not int or trail[1]<0 or trail[2]!='hover':
            raise ValueError('Inline record must target a native chapter image hover field')
        target=pack/path
        if not target.is_file():refresh.append({'key':key,'reason':'inline-source-removed'});continue
        if path not in sources:
            sources[path],nodes[path]=read_source(target)
        node=locate(nodes[path],trail)
        if node is None or not native_value(node.value):refresh.append({'key':key,'reason':'inline-field-removed-or-native-type-changed'});continue
        previous=owned.get(key)
        was_ours=previous and node.value==previous['aliasValue']
        logical_english=previous['englishValue'] if was_ours else node.value
        if was_ours and upstream is not None and (upstream/path).is_file():
            _,fresh_tree=read_source(upstream/path);fresh_node=locate(fresh_tree,trail)
            if fresh_node is not None and native_value(fresh_node.value):logical_english=fresh_node.value
        reason=None
        if fp(logical_english)!=record['englishFingerprint']:reason='changed-inline-English-manual-skipped'
        elif image_identity(nodes[path],trail)!=record['imageFingerprint']:reason='changed-image-anchor-manual-skipped'
        elif type(record['text'])!=type(logical_english) or not native_value(record['text']):raise ValueError('Inline native value type mismatch')
        elif isinstance(logical_english,list) and len(record['text'])!=len(logical_english):raise ValueError('Inline paragraph count mismatch')
        # Language.loadFromJson normalizes numeric format specifiers; raw legacy text
        # containing one cannot be losslessly moved to I18n without special treatment.
        elif re.search(r'%(?:\d+\$)?[\d.]*[df]',str(logical_english)+str(record['text'])):reason='inline-numeric-format-literal-needs-review'
        if reason:
            refresh.append({'key':key,'reason':reason,'englishFingerprint':fp(logical_english),'english':logical_english})
            if was_ours:edits.setdefault(path,[]).append((node.start,node.end,json.dumps(logical_english,ensure_ascii=False)))
            continue
        covered.append(key)
        if record['decision'] in {'preserve-brand','preserve-technical'}:
            if was_ours:edits.setdefault(path,[]).append((node.start,node.end,json.dumps(logical_english,ensure_ascii=False)))
            continue
        if record['decision']!='translated':raise ValueError('Missing explicit inline translation decision')
        en_values=logical_english if isinstance(logical_english,list) else [logical_english]
        ru_values=record['text'] if isinstance(record['text'],list) else [record['text']]
        aliases=[]
        for i,(en,ru) in enumerate(zip(en_values,ru_values)):
            alias=f'{key}.{i}';english[alias]=literal_resource(en);russian[alias]=literal_resource(ru);aliases.append('{'+alias+'}')
        alias_value=aliases if isinstance(logical_english,list) else aliases[0]
        if node.value!=alias_value:edits.setdefault(path,[]).append((node.start,node.end,json.dumps(alias_value,ensure_ascii=False)))
        new_owned[key]={'sourcePath':path,'displayPath':trail,'englishValue':logical_english,'englishFingerprint':fp(logical_english),
            'imageFingerprint':record['imageFingerprint'],'aliasValue':alias_value}
    # Entries removed from the manual map are also restored when their exact alias survives.
    for key,previous in owned.items():
        if key in {record['key'] for record in records}:continue
        path=previous['sourcePath'];target=pack/path
        if not target.is_file():continue
        if path not in sources:sources[path],nodes[path]=read_source(target)
        node=locate(nodes[path],previous['displayPath'])
        if node is not None and node.value==previous['aliasValue']:
            edits.setdefault(path,[]).append((node.start,node.end,json.dumps(previous['englishValue'],ensure_ascii=False)))
    for path,changes in edits.items():
        source=sources[path]
        previous_start=len(source)+1
        for start,end,replacement in sorted(changes,reverse=True):
            if end>previous_start:raise ValueError('Overlapping inline display spans')
            source=source[:start]+replacement+source[end:];previous_start=start
        Reader(source).parse();plans[path]=source.encode('utf-8')
    hashes={}
    if english:
        for path,value in [(EN_RESOURCE,english),(RU_RESOURCE,russian)]:
            raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8');plans[path]=raw;hashes[path]=hashlib.sha256(raw).hexdigest()
    else:
        for path in [EN_RESOURCE,RU_RESOURCE]:
            if (pack/path).is_file() and path in old_hashes:plans[path]=None
    return plans,{'schemaVersion':1,'entries':new_owned,'resourceSha256':hashes},{
        'inlineEntries':len(records),'coveredInlineEntries':len(covered),'nativeAliasStrings':len(english),'refreshQueue':refresh,
        'englishOriginalResourceFilesChanged':False,'newEnglishAliasResource':EN_RESOURCE,'russianAliasResource':RU_RESOURCE,
        'questIdsImagesClicksRewardsProgressChanged':False}
