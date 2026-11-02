"""Construye instalador/paquete.zip a partir del trabajo ya hecho. El paquete NO contiene archivos del juego:
solo textos en español y diferencias (copiar/insertar) respecto a los datos originales del juego."""
import os, sys, json, zlib, struct, hashlib, zipfile, glob
AQUI = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import ft2es

BK = R + '/backups_juego'
TEX_FDATA = ['0a12caf9', 'b766cb46', 'cdce5e37', 'f3ab3808']
FUENTE = 'da2245f2'
# todas las texturas traducidas por tools/texturas/instalar_texturas.py (así no hay que mantener la lista a mano)
TEX_IDS = sorted(os.path.basename(p)[:-4] for p in glob.glob(R + '/traduccion/texturas/trabajo/*.g1t'))


def ops_alineado(old, new):
    ops = []
    i = 0
    n = len(new)
    while i < n:
        j = min(i + 4096, n)
        if new[i:j] == old[i:j]:
            if ops and ops[-1][0] == 'c' and ops[-1][1] + ops[-1][2] == i:
                ops[-1] = ('c', ops[-1][1], ops[-1][2] + j - i)
            else:
                ops.append(('c', i, j - i))
        else:
            if ops and ops[-1][0] == 'd':
                ops[-1] = ('d', ops[-1][1] + new[i:j])
            else:
                ops.append(('d', new[i:j]))
        i = j
    return ops


def ops_generico(old, new, K=32):
    idx = {}
    for i in range(len(old) - K + 1):
        idx.setdefault(old[i:i + K], i)
    ops = []
    lit = bytearray()
    p = 0
    while p < len(new):
        q = idx.get(new[p:p + K]) if p + K <= len(new) else None
        if q is None:
            lit.append(new[p])
            p += 1
            continue
        l = K
        while p + l < len(new) and q + l < len(old) and new[p + l] == old[q + l]:
            l += 1
        if lit:
            ops.append(('d', bytes(lit)))
            lit = bytearray()
        ops.append(('c', q, l))
        p += l
    if lit:
        ops.append(('d', bytes(lit)))
    return ops


def serializar(ops):
    o = bytearray(struct.pack('<I', len(ops)))
    for op in ops:
        if op[0] == 'c':
            o += b'c' + struct.pack('<2I', op[1], op[2])
        else:
            o += b'd' + struct.pack('<I', len(op[1])) + op[1]
    return zlib.compress(bytes(o), 9)


def hacer_parche(old, new):
    ops = ops_alineado(old, new) if len(old) == len(new) else ops_generico(old, new)
    assert ft2es.aplicar_ops(old, ops) == new
    return serializar(ops)


def main():
    z = zipfile.ZipFile(AQUI + '/paquete.zip', 'w', zipfile.ZIP_STORED)
    man = dict(originales={}, fdata={}, sha_resultado={}, fuente_fdata='0x%s.fdata' % FUENTE, version='1.0')
    # compatibilidad ESTRUCTURAL (sin hashes de los archivos del juego): tamaños de los recursos que se parchean y nº de registros esperados
    est = man['estructura'] = dict(fdata={}, ebm={}, lang={})
    # --- texturas
    for fd in TEX_FDATA:
        orig_path = f'{BK}/0x{fd}.enUS.fdata.ORIGINAL'
        f = open(orig_path, 'rb').read()
        ents = {e['name']: e for e in ft2es.entradas(f)}
        rec = {}
        for tid in TEX_IDS:
            nh = int(tid, 16)
            if nh not in ents:
                continue
            nuevo = open(f'{R}/traduccion/texturas/trabajo/{tid}.g1t', 'rb').read()
            orig = ft2es.datos_entrada(f, ents[nh])
            nombre = f'{tid}.bin'
            z.writestr('parches/' + nombre, hacer_parche(orig, nuevo))
            man['sha_resultado'][nombre] = hashlib.sha256(nuevo).hexdigest()
            rec['%08x' % nh] = nombre
            est['fdata'].setdefault(f'0x{fd}.fdata', {})['%08x' % nh] = len(orig)
            print('textura', tid, len(orig), '->', len(nuevo))
        if rec:
            man['fdata'][f'0x{fd}.fdata'] = rec
            man['originales'][f'Motor/enUS/0x{fd}.fdata'] = dict(sha256=hashlib.sha256(f).hexdigest(), size=len(f))
    # --- fuente
    f = open(f'{BK}/0x{FUENTE}.enUS.fdata.ORIGINAL', 'rb').read()
    e = ft2es.entradas(f)[0]
    orig = ft2es.datos_entrada(f, e)
    nuevo = open(R + '/traduccion/fuente/e876b7f0_es.g1n', 'rb').read()
    z.writestr('parches/fuente.bin', hacer_parche(orig, nuevo))
    man['sha_resultado']['fuente.bin'] = hashlib.sha256(nuevo).hexdigest()
    man['fdata'][f'0x{FUENTE}.fdata'] = {'%08x' % e['name']: 'fuente.bin'}
    est['fdata'].setdefault(f'0x{FUENTE}.fdata', {})['%08x' % e['name']] = len(orig)
    man['originales'][f'Motor/enUS/0x{FUENTE}.fdata'] = dict(sha256=hashlib.sha256(f).hexdigest(), size=len(f))
    print('fuente', len(orig), '->', len(nuevo))
    for lang in ('root.texture.enUS.lang', 'root.font.enUS.lang'):
        b = open(f'{BK}/{lang}.ORIGINAL', 'rb').read(); man['originales']['Motor/' + lang] = dict(sha256=hashlib.sha256(b).hexdigest(), size=len(b)); est['lang']['Motor/' + lang] = len(b) // 12
    # --- textos
    src = {r['NAME_LABEL']: r['MESSAGE'] for r in json.load(open(R + '/pruebas/gust_enc/06_decode_message/message.json', encoding='utf-8-sig'))['message_message']}
    cand = json.load(open(R + '/traduccion/candidato_ia/message.json', encoding='utf-8-sig'))['message_message']
    textos = {r['NAME_LABEL']: r['MESSAGE'] for r in cand if r['MESSAGE'] != src.get(r['NAME_LABEL'])}
    z.writestr('textos.json', json.dumps(textos, ensure_ascii=False))
    b = open(BK + '/message.json.e.ORIGINAL', 'rb').read(); man['originales']['MASTER/ENG/fixed_data/message/message.json.e'] = dict(sha256=hashlib.sha256(b).hexdigest(), size=len(b))
    prev = open(R + '/traduccion/candidato_menu/message.json.e', 'rb').read()
    man['reconocidos'] = {'MASTER/ENG/fixed_data/message/message.json.e': {hashlib.sha256(prev).hexdigest(): 'Menús ya en español (versión previa de esta traducción)'}}
    print('textos', len(textos))
    # --- diálogos
    ebm = {}
    for p in sorted(glob.glob(R + '/traduccion/ebm/*.ebm')):
        nombre = os.path.basename(p)
        o = open(f'{BK}/ebm/{nombre}', 'rb').read()
        ro, _ = ft2es.ebm_parse(o)
        rn, _ = ft2es.ebm_parse(open(p, 'rb').read())
        key = nombre[len('EVENT_MESSAGE_'):-4]
        for i, (a, b) in enumerate(zip(ro, rn)):
            if a['t'] != b['t']:
                ebm[f'{key}#{i}'] = b['t'].decode('utf-8')
        man['originales'][f'MASTER/ENG/EventMessageData/{nombre}'] = dict(sha256=hashlib.sha256(o).hexdigest(), size=len(o))
        est['ebm'][f'MASTER/ENG/EventMessageData/{nombre}'] = len(ro)
    z.writestr('ebm.json', json.dumps(ebm, ensure_ascii=False))
    print('diálogos', len(ebm))
    z.writestr('manifest.json', json.dumps(man, indent=1))
    z.close()
    # segunda pasada: se instala (motor Python de referencia) sobre una copia con los originales y se anotan los SHA-256 resultantes
    import shutil, tempfile
    tmp = tempfile.mkdtemp()
    for rel, info in man['originales'].items():
        dst = os.path.join(tmp, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
        name = os.path.basename(rel)
        if rel.startswith('Motor/enUS/'): src = f'{BK}/{name[:-6]}.enUS.fdata.ORIGINAL'
        elif rel.startswith('Motor/root.'): src = f'{BK}/{name}.ORIGINAL'
        elif rel.endswith('message.json.e'): src = f'{BK}/message.json.e.ORIGINAL'
        else: src = f'{BK}/ebm/{name}'
        shutil.copy(src, dst)
    os.makedirs(os.path.join(tmp, 'MASTER/ENG/fixed_data/message'), exist_ok=True)
    shutil.copy(R + '/tools/gust_tools/gust_enc.exe', AQUI); shutil.copy(R + '/tools/gust_tools/gust_enc.json', AQUI)
    ft2es.instalar(tmp, ft2es.Paquete(AQUI + '/paquete.zip'))
    man['resultado'] = {rel: ft2es.sha(os.path.join(tmp, rel)) for rel in man['originales']}
    z2 = zipfile.ZipFile(AQUI + '/paquete.zip'); items = {n: z2.read(n) for n in z2.namelist()}; z2.close()
    items['manifest.json'] = json.dumps(man, indent=1).encode()
    with zipfile.ZipFile(AQUI + '/paquete.zip', 'w', zipfile.ZIP_STORED) as z3:
        for n, b in items.items(): z3.writestr(n, b)
    shutil.rmtree(tmp, ignore_errors=True)
    print('paquete.zip:', os.path.getsize(AQUI + '/paquete.zip') // 1024, 'KB; resultados anotados:', len(man['resultado']))


main()
