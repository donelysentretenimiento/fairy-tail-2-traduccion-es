"""Instalador reversible de la traducción al español de FAIRY TAIL 2 (Donelys Entretenimiento).
No contiene archivos del juego: aplica textos y diferencias por bloques sobre los archivos ORIGINALES del propio usuario.
Uso:  ft2es.py instalar  "RUTA_DEL_JUEGO"   |   ft2es.py desinstalar "RUTA_DEL_JUEGO"   |   ft2es.py verificar "RUTA_DEL_JUEGO"
Solo toca: Motor/enUS/*.fdata (texturas y fuente), Motor/root.*.enUS.lang, MASTER/ENG/fixed_data/message/message.json.e
y MASTER/ENG/EventMessageData/*.ebm. NO toca el ejecutable, tenoke.ini, steam_api64.* ni ningún archivo de activación."""
import os, sys, json, zlib, struct, shutil, hashlib, zipfile, subprocess, tempfile

AQUI = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__))
RES = getattr(sys, '_MEIPASS', AQUI)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ---------- diferencias (operaciones copiar/insertar) ----------
def aplicar_ops(orig, ops):
    out = bytearray()
    for op in ops:
        out += orig[op[1]:op[1] + op[2]] if op[0] == 'c' else op[1]
    return bytes(out)


def leer_ops(raw):
    d = zlib.decompress(raw)
    n, = struct.unpack_from('<I', d, 0)
    p = 4
    ops = []
    for _ in range(n):
        t = d[p:p + 1]
        p += 1
        if t == b'c':
            a, l = struct.unpack_from('<2I', d, p)
            p += 8
            ops.append(('c', a, l))
        else:
            l, = struct.unpack_from('<I', d, p)
            p += 4
            ops.append(('d', d[p:p + l]))
            p += l
    return ops


# ---------- FDATA ----------
def entradas(f):
    p = 0x10
    out = []
    while p + 0x30 <= len(f) and f[p:p + 8] == b'IDRK0000':
        es, cs, us = struct.unpack_from('<3Q', f, p + 8)
        nh = struct.unpack_from('<I', f, p + 0x24)[0]
        out.append(dict(off=p, es=es, cs=cs, us=us, name=nh))
        p += (es + 15) & ~15
    return out


def datos_entrada(f, e):
    exl = e['es'] - e['cs'] - 0x30
    q = e['off'] + 0x30 + exl
    if e['cs'] == e['us']:
        return f[q:q + e['us']]
    out = bytearray()
    while len(out) < e['us']:
        z, = struct.unpack_from('<H', f, q)
        q += 10
        out += zlib.decompress(f[q:q + z])
        q += z
    return bytes(out)


def sustituir(f, nuevos):
    """nuevos: {name_hash: bytes}. Entradas crudas (sin comprimir, flags 0, CRC32), realineadas a 16 B."""
    ents = entradas(f)
    out = bytearray(f[:0x10])
    recs = {}
    for e in ents:
        blk = f[e['off']:e['off'] + e['es']]
        if e['name'] in nuevos:
            data = nuevos[e['name']]
            exl = e['es'] - e['cs'] - 0x30
            ex = bytearray(blk[0x30:0x30 + exl])
            struct.pack_into('<I', ex, 0, zlib.crc32(data))
            hdr = bytearray(blk[:0x30])
            struct.pack_into('<3Q', hdr, 8, 0x30 + exl + len(data), len(data), len(data))
            struct.pack_into('<I', hdr, 0x2c, 0)
            blk = bytes(hdr) + bytes(ex) + data
        while len(out) % 16:
            out.append(0)
        recs[e['name']] = (len(out), len(blk))
        out += blk
    h = struct.unpack_from('<I', f, 0x0c)[0]
    for e in ents:
        if e['off'] + e['es'] == h:
            o, sz = recs[e['name']]
            struct.pack_into('<I', out, 0x0c, o + sz)
            break
    return bytes(out), recs


def actualizar_lang(lang, recs):
    b = bytearray(lang)
    for i in range(0, len(b), 12):
        k, off, sz = struct.unpack_from('<3I', b, i)
        if k in recs:
            struct.pack_into('<3I', b, i, k, recs[k][0], recs[k][1])
    return bytes(b)


# ---------- EBM ----------
def rd_str(d, p):
    n, = struct.unpack_from('<I', d, p)
    return d[p + 4:p + 4 + n - 1].decode('ascii'), p + 4 + n


def ebm_parse(d):
    n, = struct.unpack_from('<I', d, 0)
    p = 4
    recs = []
    for _ in range(n):
        r = {}
        r['tipo'], = struct.unpack_from('<I', d, p)
        p += 4
        r['A'], p = rd_str(d, p)
        r['z'], = struct.unpack_from('<I', d, p)
        p += 4
        r['B'], p = rd_str(d, p)
        r['campos'] = struct.unpack_from('<15I', d, p)
        p += 60
        L, = struct.unpack_from('<I', d, p)
        p += 4
        r['t'] = d[p:p + L]
        p += L
        r['C'], p = rd_str(d, p)
        r['x'], = struct.unpack_from('<I', d, p)
        p += 4
        recs.append(r)
    return recs, d[p:]


def ebm_build(recs, cola):
    o = bytearray(struct.pack('<I', len(recs)))

    def ws(s):
        return struct.pack('<I', len(s) + 1) + s.encode('ascii') + b'\0'
    for r in recs:
        o += struct.pack('<I', r['tipo']) + ws(r['A']) + struct.pack('<I', r['z']) + ws(r['B']) + struct.pack('<15I', *r['campos'])
        o += struct.pack('<I', len(r['t'])) + r['t'] + ws(r['C']) + struct.pack('<I', r['x'])
    return bytes(o) + cola


# ---------- instalación ----------
class Paquete:
    def __init__(self, ruta=None):
        self.z = zipfile.ZipFile(ruta or os.path.join(RES, 'paquete.zip'))
        self.m = json.loads(self.z.read('manifest.json'))
        self.textos = json.loads(self.z.read('textos.json'))
        self.ebm = json.loads(self.z.read('ebm.json'))

    def parche(self, nombre):
        return leer_ops(self.z.read('parches/' + nombre))


def rutas(juego):
    return dict(motor=os.path.join(juego, 'Motor'),
                msg=os.path.join(juego, 'MASTER', 'ENG', 'fixed_data', 'message', 'message.json.e'),
                ebm=os.path.join(juego, 'MASTER', 'ENG', 'EventMessageData'))


def comprobar_juego(juego):
    r = rutas(juego)
    for p in (r['motor'], os.path.join(r['motor'], 'enUS'), r['msg'], r['ebm']):
        if not os.path.exists(p):
            sys.exit(f'No parece la carpeta de FAIRY TAIL 2 (falta {p}).')
    return r


def respaldar(juego, ficheros, bk):
    os.makedirs(bk, exist_ok=True)
    mp = os.path.join(bk, 'respaldo.json')
    man = json.load(open(mp)) if os.path.exists(mp) else {}
    for rel in ficheros:
        if rel in man:
            continue                                   # nunca se pisa un original ya respaldado
        src = os.path.join(juego, rel)
        dst = os.path.join(bk, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        man[rel] = sha(src)
    json.dump(man, open(mp, 'w'), indent=1)


def instalar(juego, pk):
    r = comprobar_juego(juego)
    bk = os.path.join(juego, 'FT2_ES_RESPALDO')
    m = pk.m
    mp = os.path.join(bk, 'respaldo.json')
    ya = json.load(open(mp)) if os.path.exists(mp) else {}
    print('Comprobando que los archivos son los originales esperados...')
    for rel, info in m['originales'].items():
        h = info['sha256'] if isinstance(info, dict) else info
        p = os.path.join(juego, rel)
        if not os.path.exists(p):
            sys.exit(f'Falta {rel}')
        if rel in ya:
            continue                                   # ya instalado antes: se parte del respaldo
        if sha(p) != h:
            sys.exit(f'{rel} no coincide con la versión esperada (SHA-256). Versión distinta del juego o modificado por otro parche. No se toca nada.')
    respaldar(juego, list(m['originales']), bk)

    def base(rel):
        return os.path.join(bk, rel)                   # SIEMPRE se parte del original respaldado
    lang_t = open(base('Motor/root.texture.enUS.lang'), 'rb').read()
    lang_f = open(base('Motor/root.font.enUS.lang'), 'rb').read()
    for fd, recursos in m['fdata'].items():
        f = open(base('Motor/enUS/' + fd), 'rb').read()
        ents = {e['name']: e for e in entradas(f)}
        nuevos = {}
        for nombre, parche in recursos.items():
            nh = int(nombre, 16)
            nuevos[nh] = aplicar_ops(datos_entrada(f, ents[nh]), pk.parche(parche))
            esperado = m['sha_resultado'].get(parche)
            if esperado and hashlib.sha256(nuevos[nh]).hexdigest() != esperado:
                sys.exit(f'Resultado inesperado en {nombre}')
        nf, recs = sustituir(f, nuevos)
        open(os.path.join(r['motor'], 'enUS', fd), 'wb').write(nf)
        if fd == m['fuente_fdata']:
            lang_f = actualizar_lang(lang_f, recs)
        else:
            lang_t = actualizar_lang(lang_t, recs)
        print('  ', fd, 'OK')
    open(os.path.join(r['motor'], 'root.texture.enUS.lang'), 'wb').write(lang_t)
    open(os.path.join(r['motor'], 'root.font.enUS.lang'), 'wb').write(lang_f)
    # textos
    tmp = tempfile.mkdtemp()
    for n in ('gust_enc.exe', 'gust_enc.json'):
        shutil.copy(os.path.join(RES, n), tmp)
    shutil.copy(base('MASTER/ENG/fixed_data/message/message.json.e'), os.path.join(tmp, 'message.json.e'))
    gust = os.path.join(tmp, 'gust_enc.exe')
    subprocess.run([gust, '-FT', os.path.join(tmp, 'message.json.e')], check=True, capture_output=True, cwd=tmp)
    doc = json.loads(open(os.path.join(tmp, 'message.json'), encoding='utf-8-sig').read())
    n = 0
    for it in doc['message_message']:
        es = pk.textos.get(it['NAME_LABEL'])
        if es is not None:
            it['MESSAGE'] = es
            n += 1
    open(os.path.join(tmp, 'message.json'), 'wb').write(b'\xef\xbb\xbf' + json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    os.remove(os.path.join(tmp, 'message.json.e'))
    subprocess.run([gust, '-FT', os.path.join(tmp, 'message.json')], check=True, capture_output=True, cwd=tmp)
    shutil.copy(os.path.join(tmp, 'message.json.e'), r['msg'])
    shutil.rmtree(tmp, ignore_errors=True)
    print('  textos:', n, 'mensajes')
    # diálogos
    porf = {}
    for k, es in pk.ebm.items():
        nombre, idx = k.split('#')
        porf.setdefault(nombre, {})[int(idx)] = es
    for nombre, lin in porf.items():
        rel = f'MASTER/ENG/EventMessageData/EVENT_MESSAGE_{nombre}.ebm'
        recs, cola = ebm_parse(open(base(rel), 'rb').read())
        for i, es in lin.items():
            if i < len(recs) and recs[i]['t']:
                recs[i]['t'] = es.encode('utf-8')
        open(os.path.join(juego, rel), 'wb').write(ebm_build(recs, cola))
    print('  diálogos:', len(pk.ebm), 'líneas en', len(porf), 'archivos')
    print('Instalación completada. Copia de seguridad en:', bk)


def desinstalar(juego):
    bk = os.path.join(juego, 'FT2_ES_RESPALDO')
    mp = os.path.join(bk, 'respaldo.json')
    if not os.path.exists(mp):
        sys.exit('No hay copia de seguridad: nada que restaurar.')
    man = json.load(open(mp))
    bad = 0
    for rel, h in man.items():
        shutil.copy2(os.path.join(bk, rel), os.path.join(juego, rel))
        if sha(os.path.join(juego, rel)) != h:
            bad += 1
            print('  ¡no coincide tras restaurar!', rel)
    print('Restaurados', len(man), 'archivos originales. Verificación:', 'CORRECTA' if not bad else f'{bad} fallos')
    if not bad:
        shutil.rmtree(bk, ignore_errors=True)


def verificar(juego):
    print('Traducción instalada' if os.path.exists(os.path.join(juego, 'FT2_ES_RESPALDO')) else 'Juego original (sin traducción)')


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('instalar', 'desinstalar', 'verificar'):
        sys.exit(__doc__)
    j = sys.argv[2]
    if sys.argv[1] == 'instalar':
        instalar(j, Paquete())
    elif sys.argv[1] == 'desinstalar':
        desinstalar(j)
    else:
        verificar(j)
