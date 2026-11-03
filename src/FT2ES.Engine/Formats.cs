using System.Buffers.Binary;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace FT2ES.Engine;

/// <summary>Utilidades de hash (SHA-256 en minúsculas hexadecimales) y CRC32 compatible con zlib.</summary>
public static class Hashing
{
    /// <summary>SHA-256 de un bloque de bytes, en hexadecimal minúsculo.</summary>
    public static string Sha256(ReadOnlySpan<byte> data) => Convert.ToHexStringLower(SHA256.HashData(data));

    /// <summary>SHA-256 de un archivo, leído en flujo (no carga el archivo entero).</summary>
    public static string Sha256File(string path)
    {
        using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 16);
        return Convert.ToHexStringLower(SHA256.HashData(fs));
    }

    private static readonly uint[] Table = BuildTable();
    private static uint[] BuildTable()
    {
        var t = new uint[256];
        for (uint i = 0; i < 256; i++)
        {
            uint c = i;
            for (int k = 0; k < 8; k++) c = (c & 1) != 0 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            t[i] = c;
        }
        return t;
    }

    /// <summary>CRC32 (mismo resultado que zlib.crc32).</summary>
    public static uint Crc32(ReadOnlySpan<byte> data)
    {
        uint c = 0xFFFFFFFFu;
        foreach (var b in data) c = Table[(c ^ b) & 0xFF] ^ (c >> 8);
        return c ^ 0xFFFFFFFFu;
    }
}

internal static class Zlib
{
    public static byte[] Decompress(ReadOnlySpan<byte> data)
    {
        using var input = new MemoryStream(data.ToArray());
        using var z = new ZLibStream(input, CompressionMode.Decompress);
        using var o = new MemoryStream();
        z.CopyTo(o);
        return o.ToArray();
    }
}

/// <summary>Operaciones copiar/insertar que transforman un recurso original en el traducido.</summary>
internal static class Diff
{
    public static byte[] Apply(byte[] original, byte[] patchFile)
    {
        var d = Zlib.Decompress(patchFile);
        uint n = BinaryPrimitives.ReadUInt32LittleEndian(d);
        int p = 4;
        using var o = new MemoryStream();
        for (uint i = 0; i < n; i++)
        {
            byte t = d[p++];
            if (t == 0x63) // 'c'
            {
                uint a = BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p)); uint l = BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p + 4)); p += 8;
                if ((long)a + l > original.Length) throw new InvalidDataException("Parche corrupto: copia fuera del recurso original.");
                o.Write(original, (int)a, (int)l);
            }
            else
            {
                uint l = BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p)); p += 4;
                o.Write(d, p, (int)l); p += (int)l;
            }
        }
        return o.ToArray();
    }
}

/// <summary>Entrada IDRK de un FDATA.</summary>
internal readonly record struct FdataEntry(long Off, long Es, long Cs, long Us, uint Name);

/// <summary>Lectura/sustitución de entradas FDATA y actualización de los .lang asociados.</summary>
internal static class Fdata
{
    public static List<FdataEntry> Entries(byte[] f)
    {
        var res = new List<FdataEntry>();
        long p = 0x10;
        while (p + 0x30 <= f.Length && f.AsSpan((int)p, 8).SequenceEqual("IDRK0000"u8))
        {
            long es = (long)BinaryPrimitives.ReadUInt64LittleEndian(f.AsSpan((int)p + 8));
            long cs = (long)BinaryPrimitives.ReadUInt64LittleEndian(f.AsSpan((int)p + 16));
            long us = (long)BinaryPrimitives.ReadUInt64LittleEndian(f.AsSpan((int)p + 24));
            uint nh = BinaryPrimitives.ReadUInt32LittleEndian(f.AsSpan((int)p + 0x24));
            res.Add(new FdataEntry(p, es, cs, us, nh));
            p += (es + 15) & ~15L;
        }
        return res;
    }

    public static byte[] DataOf(byte[] f, FdataEntry e)
    {
        long exl = e.Es - e.Cs - 0x30;
        int q = (int)(e.Off + 0x30 + exl);
        if (e.Cs == e.Us) return f.AsSpan(q, (int)e.Us).ToArray();
        using var o = new MemoryStream();
        while (o.Length < e.Us)
        {
            int z = BinaryPrimitives.ReadUInt16LittleEndian(f.AsSpan(q));
            q += 10;
            o.Write(Zlib.Decompress(f.AsSpan(q, z)));
            q += z;
        }
        return o.ToArray();
    }

    /// <summary>Sustituye entradas por datos CRUDOS (cs=us, flags=0, CRC32), realinea a 16 B y devuelve (offset, tamaño) de cada entrada.</summary>
    public static (byte[] File, Dictionary<uint, (long Off, long Size)> Recs) Replace(byte[] f, Dictionary<uint, byte[]> nuevos)
    {
        var ents = Entries(f);
        using var o = new MemoryStream();
        o.Write(f, 0, 0x10);
        var recs = new Dictionary<uint, (long Off, long Size)>();
        foreach (var e in ents)
        {
            byte[] blk;
            if (nuevos.TryGetValue(e.Name, out var data))
            {
                long exl = e.Es - e.Cs - 0x30;
                var ex = f.AsSpan((int)(e.Off + 0x30), (int)exl).ToArray();
                BinaryPrimitives.WriteUInt32LittleEndian(ex, Hashing.Crc32(data));
                var hdr = f.AsSpan((int)e.Off, 0x30).ToArray();
                BinaryPrimitives.WriteUInt64LittleEndian(hdr.AsSpan(8), (ulong)(0x30 + exl + data.Length));
                BinaryPrimitives.WriteUInt64LittleEndian(hdr.AsSpan(16), (ulong)data.Length);
                BinaryPrimitives.WriteUInt64LittleEndian(hdr.AsSpan(24), (ulong)data.Length);
                BinaryPrimitives.WriteUInt32LittleEndian(hdr.AsSpan(0x2c), 0);
                blk = [.. hdr, .. ex, .. data];
            }
            else blk = f.AsSpan((int)e.Off, (int)e.Es).ToArray();
            while (o.Length % 16 != 0) o.WriteByte(0);
            recs[e.Name] = (o.Length, blk.Length);
            o.Write(blk);
        }
        var outb = o.ToArray();
        uint h = BinaryPrimitives.ReadUInt32LittleEndian(f.AsSpan(0x0c));
        foreach (var e in ents)
            if (e.Off + e.Es == h)
            {
                var (off, sz) = recs[e.Name];
                BinaryPrimitives.WriteUInt32LittleEndian(outb.AsSpan(0x0c), (uint)(off + sz));
                break;
            }
        return (outb, recs);
    }

    /// <summary>Actualiza los registros de 12 B (ktid, offset, tamaño) del .lang.</summary>
    public static byte[] UpdateLang(byte[] lang, Dictionary<uint, (long Off, long Size)> recs)
    {
        var b = (byte[])lang.Clone();
        for (int i = 0; i + 12 <= b.Length; i += 12)
        {
            uint k = BinaryPrimitives.ReadUInt32LittleEndian(b.AsSpan(i));
            if (recs.TryGetValue(k, out var r))
            {
                BinaryPrimitives.WriteUInt32LittleEndian(b.AsSpan(i + 4), (uint)r.Off);
                BinaryPrimitives.WriteUInt32LittleEndian(b.AsSpan(i + 8), (uint)r.Size);
            }
        }
        return b;
    }
}

/// <summary>Registro de un archivo de diálogos .ebm.</summary>
internal sealed class EbmRecord
{
    public uint Tipo, Z, X;
    public string A = "", B = "", C = "";
    public uint[] Campos = new uint[15];
    public byte[] T = [];
}

internal static class Ebm
{
    private static string Str(byte[] d, ref int p)
    {
        int n = (int)BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p));
        var s = Encoding.Latin1.GetString(d, p + 4, Math.Max(0, n - 1));
        p += 4 + n;
        return s;
    }

    public static (List<EbmRecord> Recs, byte[] Tail) Parse(byte[] d)
    {
        int n = (int)BinaryPrimitives.ReadUInt32LittleEndian(d);
        int p = 4;
        var recs = new List<EbmRecord>(n);
        for (int i = 0; i < n; i++)
        {
            var r = new EbmRecord();
            r.Tipo = BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p)); p += 4;
            r.A = Str(d, ref p);
            r.Z = BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p)); p += 4;
            r.B = Str(d, ref p);
            for (int k = 0; k < 15; k++) r.Campos[k] = BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p + 4 * k));
            p += 60;
            int l = (int)BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p)); p += 4;
            r.T = d.AsSpan(p, l).ToArray(); p += l;
            r.C = Str(d, ref p);
            r.X = BinaryPrimitives.ReadUInt32LittleEndian(d.AsSpan(p)); p += 4;
            recs.Add(r);
        }
        return (recs, d.AsSpan(p).ToArray());
    }

    public static byte[] Build(List<EbmRecord> recs, byte[] tail)
    {
        using var o = new MemoryStream();
        void U(uint v) { var w = new byte[4]; BinaryPrimitives.WriteUInt32LittleEndian(w, v); o.Write(w); }
        void S(string s) { U((uint)s.Length + 1); o.Write(Encoding.Latin1.GetBytes(s)); o.WriteByte(0); }
        U((uint)recs.Count);
        foreach (var r in recs)
        {
            U(r.Tipo); S(r.A); U(r.Z); S(r.B);
            foreach (var c in r.Campos) U(c);
            U((uint)r.T.Length); o.Write(r.T); S(r.C); U(r.X);
        }
        o.Write(tail);
        return o.ToArray();
    }
}

/// <summary>Lectura/escritura de message.json idéntica byte a byte a json.dumps(ensure_ascii=False, separators=(',',':')) de Python.</summary>
internal static class MessageJson
{
    public static List<(string Label, string Message)> Read(byte[] json)
    {
        var span = json.AsSpan();
        if (span.Length >= 3 && span[0] == 0xEF && span[1] == 0xBB && span[2] == 0xBF) span = span[3..];
        using var doc = JsonDocument.Parse(span.ToArray());
        var root = doc.RootElement;
        if (root.ValueKind != JsonValueKind.Object || root.EnumerateObject().Count() != 1 || !root.TryGetProperty("message_message", out var arr))
            throw new InvalidDataException("El archivo de textos del juego no tiene el formato esperado.");
        var list = new List<(string, string)>();
        foreach (var it in arr.EnumerateArray())
        {
            if (it.EnumerateObject().Count() != 2 || !it.TryGetProperty("NAME_LABEL", out var l) || !it.TryGetProperty("MESSAGE", out var m))
                throw new InvalidDataException("Un mensaje del archivo de textos no tiene el formato esperado.");
            list.Add((l.GetString()!, m.GetString()!));
        }
        return list;
    }

    private static void Esc(StringBuilder sb, string s)
    {
        sb.Append('"');
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                case '\b': sb.Append("\\b"); break;
                case '\f': sb.Append("\\f"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4")); else sb.Append(c);
                    break;
            }
        }
        sb.Append('"');
    }

    public static byte[] Write(List<(string Label, string Message)> items)
    {
        var sb = new StringBuilder("{\"message_message\":[");
        for (int i = 0; i < items.Count; i++)
        {
            if (i > 0) sb.Append(',');
            sb.Append("{\"NAME_LABEL\":"); Esc(sb, items[i].Label);
            sb.Append(",\"MESSAGE\":"); Esc(sb, items[i].Message);
            sb.Append('}');
        }
        sb.Append("]}");
        return [0xEF, 0xBB, 0xBF, .. new UTF8Encoding(false).GetBytes(sb.ToString())];
    }
}
