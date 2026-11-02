"""Parser/escritor de los EBM de FAIRY TAIL 2 (EventMessageData). Formato verificado sobre los 513 archivos (ver main()).
Archivo: u32 n_registros; n x registro. Tras los registros hay una cola fija de ~82 bytes (se conserva tal cual). Registro:
  u32 tipo | str A (voz/personaje) | u32 0 | str B (nombre) | 15 x u32 | u32 len | texto(len bytes, sin NUL) | str C | u32 x
  str = u32 len(con NUL) + bytes + NUL.   Solo el texto cambia al traducir (len se recalcula): no hay desplazamientos globales."""
import struct, sys, glob, os
def rd_str(d, p):
    n, = struct.unpack_from('<I', d, p); assert 1 <= n < 200 and d[p + 4 + n - 1] == 0, (p, n)
    return d[p + 4:p + 4 + n - 1].decode('ascii'), p + 4 + n
def parse(d):
    n, = struct.unpack_from('<I', d, 0); p = 4; recs = []
    for _ in range(n):
        r = {}; r['tipo'], = struct.unpack_from('<I', d, p); p += 4
        r['A'], p = rd_str(d, p); r['z'], = struct.unpack_from('<I', d, p); p += 4
        r['B'], p = rd_str(d, p); r['campos'] = struct.unpack_from('<15I', d, p); p += 60
        L, = struct.unpack_from('<I', d, p); p += 4; r['texto_b'] = d[p:p + L]; p += L
        r['C'], p = rd_str(d, p); r['x'], = struct.unpack_from('<I', d, p); p += 4; recs.append(r)
    return recs, p
def build(recs, cola=b''):
    o = bytearray(struct.pack('<I', len(recs)))
    def ws(s): b = s.encode('ascii') + b'\0'; return struct.pack('<I', len(b)) + b
    for r in recs:
        o += struct.pack('<I', r['tipo']) + ws(r['A']) + struct.pack('<I', r['z']) + ws(r['B']) + struct.pack('<15I', *r['campos'])
        o += struct.pack('<I', len(r['texto_b'])) + r['texto_b'] + ws(r['C']) + struct.pack('<I', r['x'])
    return bytes(o) + cola
def main(carpeta):
    colas = set(); ok = bad = 0; tot = 0; sin_texto = 0; fallos = []
    for p in sorted(glob.glob(carpeta + '/*.ebm')):
        d = open(p, 'rb').read()
        try:
            recs, end = parse(d)
            cola = d[end:]; colas.add(cola)
            if build(recs, cola) == d: ok += 1; tot += len(recs); sin_texto += sum(1 for r in recs if not r['texto_b'])
            else: bad += 1; fallos.append((os.path.basename(p), 'longitud/rebuild', end, len(d)))
        except Exception as e: bad += 1; fallos.append((os.path.basename(p), repr(e)[:60]))
    print(f'idénticos tras parsear+reconstruir: {ok}/{ok + bad} | registros: {tot} (sin texto: {sin_texto})'); print(fallos[:8]); print('colas distintas:', len(colas), [c.hex()[:40] + '..' + str(len(c)) for c in list(colas)[:3]])
if __name__ == '__main__': main(sys.argv[1])
