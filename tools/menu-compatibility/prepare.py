"""Offline, exact-pinned preparation of the existing417 menu call-site rewrite.

Does not edit source packs, locks, the launcher, or the original JAR. Unchanged
ZIP entries retain their original raw local records, including compressed data.
"""
from pathlib import Path
import argparse, datetime, hashlib, io, json, struct, subprocess, zipfile, zlib

OUTER_SHA = 'a01d9718667ac13899013e91c5b0b7708b9b9db1da9b8e380772dde54bbe8f41'
INNER_SHA = '1d065b46db71addeb7e04aff4981b424531d40123fe2b0c1d2a2cc9af81319fe'
CLASS_SHA = '87e082cdc0e7738213f2ce26f6656e1655a479dcd546b58d40f368d51109b0a5'
ASM_PINS = {'asm-9.8.jar': (126113, '876eab6a83daecad5ca67eb9fcabb063c97b5aeb8cf1fca7a989ecde17522051'), 'asm-tree-9.8.jar': (51934, '14b7880cb7c85eed101e2710432fc3ffb83275532a6a894dc4c4095d49ad59f1')}
CANDIDATE_SHA = 'e6de8c00a914106d5b343fafdcc14666cc0647c41bf571d8bea8ad3714455281'
INNER = 'META-INF/jarjar/ae2addonlib-1.0.3-1.21.1.jar'
CLASS = 'net/pedroksl/ae2addonlib/registry/MenuRegistry.class'

def sha(data): return hashlib.sha256(data).hexdigest()
def require(value, message):
    if not value: raise ValueError(message)
def exact(data, expected, label): require(sha(data) == expected, label + ' SHA256 differs; no candidate prepared.')

def structure(data):
    """Classic single-disk ZIP only, with no trailing bytes or ZIP64 ambiguity."""
    end = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
    require(end >= 0, 'ZIP EOCD is missing.')
    eocd = struct.unpack_from('<4s4H2LH', data, end)
    _, disk, directory_disk, disk_count, count, size, offset, comment = eocd
    require(disk == directory_disk == 0 and disk_count == count and count < 65535, 'Unsupported multi-disk/ZIP64 archive.')
    require(end + 22 + comment == len(data) and offset + size == end, 'Unexpected ZIP trailing or directory data.')
    records = []; cursor = offset
    for _ in range(count):
        fields = struct.unpack_from('<4s6H3L5H2L', data, cursor)
        require(fields[0] == b'PK\x01\x02', 'Invalid central-directory record.')
        length = 46 + sum(fields[10:13]); raw = data[cursor:cursor + length]
        name = raw[46:46 + fields[10]].decode('utf-8' if fields[3] & 0x800 else 'cp437')
        records.append({'name': name, 'fields': fields, 'raw': raw, 'offset': fields[16]}); cursor += length
    require(cursor == end and len({r['name'] for r in records}) == count, 'Duplicate entries or malformed directory.')
    ordered = sorted(records, key=lambda r: r['offset'])
    require(ordered and ordered[0]['offset'] == 0, 'Archive prefix is unsupported.')
    for index, record in enumerate(ordered):
        finish = ordered[index + 1]['offset'] if index + 1 < len(ordered) else offset
        record['local'] = data[record['offset']:finish]
        require(record['local'].startswith(b'PK\x03\x04'), 'Invalid local record.')
    return records, ordered, data[end:]

def replace_entry(data, target, replacement):
    records, ordered, ending = structure(data); found = [r for r in records if r['name'] == target]
    require(len(found) == 1, 'Expected exactly one replacement entry.')
    changed = found[0]; header = struct.unpack_from('<4s5H3L2H', changed['local'])
    # These exact author archives have flags0x800 and DEFLATE, without data descriptors.
    require(header[2] == 0x800 and header[3] == 8 and changed['fields'][3:5] == (0x800, 8), 'Unexpected compression/encryption/descriptor flags.')
    name_extra_end = 30 + header[9] + header[10]
    require(name_extra_end + header[7] == len(changed['local']), 'Unexpected data after changed local entry.')
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = compressor.compress(replacement) + compressor.flush()
    crc = zlib.crc32(replacement); updated_header = list(header)
    updated_header[6:9] = [crc, len(compressed), len(replacement)]
    replacement_local = struct.pack('<4s5H3L2H', *updated_header) + changed['local'][30:name_extra_end] + compressed
    output = bytearray(); offsets = {}
    for record in ordered:
        offsets[record['name']] = len(output)
        output.extend(replacement_local if record is changed else record['local'])
    directory_offset = len(output)
    for record in records:
        central = bytearray(record['raw'])
        struct.pack_into('<L', central, 42, offsets[record['name']])
        if record is changed: struct.pack_into('<3L', central, 16, crc, len(compressed), len(replacement))
        output.extend(central)
    updated_ending = bytearray(ending)
    struct.pack_into('<2L', updated_ending, 12, len(output) - directory_offset, directory_offset)
    output.extend(updated_ending)
    result = bytes(output)
    # All contents and central metadata, plus all other original raw compressed
    # entry records, must survive. Only absolute directory offsets may shift.
    after, _, _ = structure(result); pairs = zip(records, after, strict=True)
    old_zip = zipfile.ZipFile(io.BytesIO(data)); new_zip = zipfile.ZipFile(io.BytesIO(result))
    entries = []
    for before, now in pairs:
        require(before['name'] == now['name'], 'Entry ordering changed.')
        old_meta = bytearray(before['raw']); new_meta = bytearray(now['raw'])
        old_meta[42:46] = new_meta[42:46] = b'\0' * 4
        if before['name'] == target:
            old_meta[16:28] = new_meta[16:28] = b'\0' * 12
            require(new_zip.read(target) == replacement, 'Replacement content differs.')
        else:
            require(before['local'] == now['local'], 'Unchanged compressed local entry changed.')
            require(old_zip.read(before['name']) == new_zip.read(now['name']), 'Unchanged uncompressed content changed.')
        require(old_meta == new_meta, 'ZIP metadata changed beyond CRC/sizes/offsets.')
        entries.append({'path': before['name'], 'beforeSha256': sha(old_zip.read(before['name'])),
                        'afterSha256': sha(new_zip.read(now['name'])), 'rawUnchangedLocalRecordPreserved': before['name'] != target})
    return result, entries

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--asm-directory', type=Path, default=Path(__file__).resolve().parent/'lib')
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); here = Path(__file__).resolve().parent
    require((args.output / args.source.name).resolve() != args.source.resolve(), 'Output must not overwrite the original source JAR.')
    original = args.source.read_bytes(); exact(original, OUTER_SHA, 'AdvancedAE outer JAR')
    libraries = []
    for name, (size, digest) in ASM_PINS.items():
        path = args.asm_directory/name; raw = path.read_bytes()
        require(len(raw) == size and sha(raw) == digest, 'ASM dependency differs: ' + name)
        libraries.append(str(path))
    class_path = ';'.join(libraries)
    with zipfile.ZipFile(io.BytesIO(original)) as outer:
        require(not any(i.filename.upper().endswith(('.SF', '.RSA', '.DSA', '.EC')) for i in outer.infolist()), 'Signed JAR is outside this recipe.')
        nested = outer.read(INNER)
    exact(nested, INNER_SHA, 'Nested ae2addonlib JAR')
    with zipfile.ZipFile(io.BytesIO(nested)) as inner:
        require(not any(i.filename.upper().endswith(('.SF', '.RSA', '.DSA', '.EC')) for i in inner.infolist()), 'Signed nested JAR is outside this recipe.')
        original_class = inner.read(CLASS)
    exact(original_class, CLASS_SHA, 'MenuRegistry class')
    args.output.mkdir(parents=True, exist_ok=True)
    original_class_file = args.output/'MenuRegistry.original.class'; original_class_file.write_bytes(original_class)
    classes = args.output/'tool-classes'; classes.mkdir(exist_ok=True)
    subprocess.run([str(args.jdk/'bin/javac.exe'), '--release', '17', '-cp', class_path, '-d', str(classes), str(here/'ExactMenuClassPrep.java')], check=True)
    run = subprocess.run([str(args.jdk/'bin/java.exe'), '-cp', str(classes) + ';' + class_path, 'ExactMenuClassPrep', str(original_class_file), str(args.output)], check=True, capture_output=True, text=True, encoding='utf-8')
    (args.output/'class-preparation.log').write_text(run.stdout + run.stderr, encoding='utf-8')
    candidate_class = (args.output/'MenuRegistry.prepared.class').read_bytes()
    candidate_inner, inner_entries = replace_entry(nested, CLASS, candidate_class)
    candidate_outer, outer_entries = replace_entry(original, INNER, candidate_inner)
    inner_file = args.output/'ae2addonlib-1.0.3-1.21.1.prepared.jar'; inner_file.write_bytes(candidate_inner)
    exact(candidate_outer, CANDIDATE_SHA, 'Prepared outer JAR')
    candidate_file = args.output/args.source.name; candidate_file.write_bytes(candidate_outer)
    (args.output/'entry-provenance.json').write_text(json.dumps({'outer': outer_entries, 'nested': inner_entries}, indent=2) + '\n', encoding='utf-8')
    class_proof = json.loads((args.output/'class-preparation-proof.json').read_text())
    report = {
        'schemaVersion':1, 'capturedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'OFFLINE_EXACT_DERIVATIVE_BYTE_PROOF_ONLY_NOT_PUBLISHED_OR_NATIVE_CLIENT_PASS',
        'sourceRepo':'MarkZamore/All-The-Mods-10', 'sourceRevision':'7640f4df9c381ce7575425ef4f607ad00aa80725',
        'sourceOuter':{'path':args.source.name,'sha256':sha(original),'sizeBytes':len(original)},
        'sourceNested':{'path':INNER,'sha256':sha(nested),'sizeBytes':len(nested)},
        'candidateOuter':{'path':candidate_file.name,'sha256':sha(candidate_outer),'sizeBytes':len(candidate_outer)},
        'candidateNested':{'path':INNER,'sha256':sha(candidate_inner),'sizeBytes':len(candidate_inner)},
        'classProof':class_proof, 'approvedReferenceProof':'reference-proof.json',
        'caller':{'class':CLASS[:-6], 'method':'lambda$create$0', 'opcode':'INVOKEVIRTUAL', 'owner':'appeng/menu/implementations/MenuTypeBuilder', 'before':'build','after':'buildUnregistered','expectedCount':1,'callerDescriptor':'(Lappeng/menu/implementations/MenuTypeBuilder$MenuFactory;Ljava/lang/Class;Ljava/lang/String;Ljava/lang/String;)Lnet/minecraft/world/inventory/MenuType;','callDescriptor':'(Lnet/minecraft/resources/ResourceLocation;)Lnet/minecraft/world/inventory/MenuType;'},
        'changeScope':{'outerEntryCount':len(outer_entries),'outerChangedEntries':[e['path'] for e in outer_entries if e['beforeSha256']!=e['afterSha256']],
                       'nestedEntryCount':len(inner_entries),'nestedChangedEntries':[e['path'] for e in inner_entries if e['beforeSha256']!=e['afterSha256']],
                       'allOtherContentsAndRawCompressedRecordsPreserved':True,'allOtherZipMetadataPreserved':True,'manifestAndJarJarMetadataUnchanged':True,'newClassesOrResources':0},
        'nativeBehaviorBoundary':'Prepared class and outer JAR match the approved exact reference hashes. The separate reference proof compared actual417 transformer bytes; this preparation does not run a launcher agent or native client.',
        'originalInputJarChanged':False,
        'toolSha256':{'prepare.py':sha(Path(__file__).read_bytes()),'ExactMenuClassPrep.java':sha((here/'ExactMenuClassPrep.java').read_bytes())}
    }
    (args.output/'candidate-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'candidateSha256':sha(candidate_outer),'candidateSizeBytes':len(candidate_outer),'nestedSha256':sha(candidate_inner),'classSha256':sha(candidate_class),'scope':report['changeScope']},ensure_ascii=False))

if __name__ == '__main__': main()
