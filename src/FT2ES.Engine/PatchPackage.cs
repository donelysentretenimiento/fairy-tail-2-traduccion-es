using System.IO.Compression;
using System.Text.Json;

namespace FT2ES.Engine;

/// <summary>Hash y tamaño esperados de un archivo.</summary>
public sealed record FileHash(string Sha256, long Size);

/// <summary>Contenido de manifest.json (v2).</summary>
public sealed class PatchManifest
{
    public string Version { get; init; } = "";
    /// <summary>Archivos que el parche modifica y su estado original (ruta relativa con «/»).</summary>
    public Dictionary<string, FileHash> Originales { get; init; } = [];
    /// <summary>Estados previos válidos: ruta → (sha256 → descripción).</summary>
    public Dictionary<string, Dictionary<string, string>> Reconocidos { get; init; } = [];
    /// <summary>SHA-256 esperado de cada archivo tras instalar.</summary>
    public Dictionary<string, string> Resultado { get; init; } = [];
    /// <summary>fichero fdata → (nombre hex del recurso → nombre del parche), en orden.</summary>
    public List<KeyValuePair<string, List<KeyValuePair<string, string>>>> Fdata { get; init; } = [];
    public string FuenteFdata { get; init; } = "";
    public Dictionary<string, string> ShaResultado { get; init; } = [];
    /// <summary>Estructura esperada de los archivos del juego (sustituye a la comprobación por hash).</summary>
    public PatchStructure Estructura { get; init; } = new();
}

/// <summary>Estructura que debe tener una versión compatible del juego.</summary>
public sealed class PatchStructure
{
    /// <summary>fichero fdata → (recurso hex → tamaño en bytes de los datos originales).</summary>
    public Dictionary<string, Dictionary<string, long>> Fdata { get; init; } = [];
    /// <summary>ruta del .ebm → número de registros.</summary>
    public Dictionary<string, int> Ebm { get; init; } = [];
    /// <summary>ruta del .lang → número de registros de 12 bytes.</summary>
    public Dictionary<string, int> Lang { get; init; } = [];
}

/// <summary>Paquete de datos de la traducción (paquete.zip).</summary>
public sealed class PatchPackage
{
    private readonly string _zipPath;
    public string Version => Manifest.Version;
    public PatchManifest Manifest { get; }
    /// <summary>Textos del menú: NAME_LABEL → texto en español.</summary>
    public Dictionary<string, string> Texts { get; }
    /// <summary>Diálogos: «NOMBRE#índice» → texto en español.</summary>
    public Dictionary<string, string> Dialogs { get; }

    private PatchPackage(string zipPath, PatchManifest m, Dictionary<string, string> t, Dictionary<string, string> e)
    { _zipPath = zipPath; Manifest = m; Texts = t; Dialogs = e; }

    /// <summary>Carga y valida el paquete. Lanza <see cref="InvalidDataException"/> con un mensaje en español si está dañado.</summary>
    public static PatchPackage Load(string zipPath)
    {
        try
        {
            using var z = ZipFile.OpenRead(zipPath);
            byte[] Rd(string n)
            {
                var en = z.GetEntry(n) ?? throw new InvalidDataException($"El paquete de la traducción está incompleto (falta {n}).");
                using var s = en.Open(); using var ms = new MemoryStream(); s.CopyTo(ms); return ms.ToArray();
            }
            var m = ParseManifest(Rd("manifest.json"));
            var t = JsonSerializer.Deserialize<Dictionary<string, string>>(Strip(Rd("textos.json")))!;
            var e = JsonSerializer.Deserialize<Dictionary<string, string>>(Strip(Rd("ebm.json")))!;
            foreach (var (_, res) in m.Fdata) foreach (var (_, patch) in res) Rd("parches/" + patch);
            return new PatchPackage(zipPath, m, t, e);
        }
        catch (InvalidDataException) { throw; }
        catch (Exception ex) when (ex is IOException or JsonException or KeyNotFoundException or InvalidOperationException or UnauthorizedAccessException)
        { throw new InvalidDataException("No se pudo leer el paquete de la traducción: " + ex.Message, ex); }
    }

    /// <summary>Lee los bytes de un parche (parches/&lt;nombre&gt;) del paquete.</summary>
    public byte[] ReadPatch(string name)
    {
        using var z = ZipFile.OpenRead(_zipPath);
        var en = z.GetEntry("parches/" + name) ?? throw new InvalidDataException($"Falta el parche {name} en el paquete.");
        using var s = en.Open(); using var ms = new MemoryStream(); s.CopyTo(ms); return ms.ToArray();
    }

    private static byte[] Strip(byte[] b) => b.Length >= 3 && b[0] == 0xEF && b[1] == 0xBB && b[2] == 0xBF ? b[3..] : b;

    private static PatchManifest ParseManifest(byte[] raw)
    {
        using var d = JsonDocument.Parse(Strip(raw));
        var r = d.RootElement;
        var o = new Dictionary<string, FileHash>();
        foreach (var p in r.GetProperty("originales").EnumerateObject())
            o[p.Name] = p.Value.ValueKind == JsonValueKind.String ? new FileHash(p.Value.GetString()!, -1)
                : new FileHash(p.Value.GetProperty("sha256").GetString()!, p.Value.GetProperty("size").GetInt64());
        var rec = new Dictionary<string, Dictionary<string, string>>();
        if (r.TryGetProperty("reconocidos", out var rc))
            foreach (var p in rc.EnumerateObject()) rec[p.Name] = p.Value.EnumerateObject().ToDictionary(x => x.Name, x => x.Value.GetString() ?? "");
        var fd = new List<KeyValuePair<string, List<KeyValuePair<string, string>>>>();
        foreach (var p in r.GetProperty("fdata").EnumerateObject())
            fd.Add(new(p.Name, p.Value.EnumerateObject().Select(x => new KeyValuePair<string, string>(x.Name, x.Value.GetString()!)).ToList()));
        return new PatchManifest
        {
            Version = r.GetProperty("version").GetString() ?? "",
            Originales = o,
            Reconocidos = rec,
            Resultado = r.GetProperty("resultado").EnumerateObject().ToDictionary(x => x.Name, x => x.Value.GetString()!),
            Fdata = fd,
            FuenteFdata = r.GetProperty("fuente_fdata").GetString()!,
            Estructura = !r.TryGetProperty("estructura", out var es) ? throw new InvalidDataException("El paquete no incluye la sección «estructura» del manifiesto.") : new PatchStructure
            {
                Fdata = es.GetProperty("fdata").EnumerateObject().ToDictionary(x => x.Name, x => x.Value.EnumerateObject().ToDictionary(y => y.Name, y => y.Value.GetInt64())),
                Ebm = es.GetProperty("ebm").EnumerateObject().ToDictionary(x => x.Name, x => x.Value.GetInt32()),
                Lang = es.GetProperty("lang").EnumerateObject().ToDictionary(x => x.Name, x => x.Value.GetInt32())
            },
            ShaResultado = r.TryGetProperty("sha_resultado", out var sr) ? sr.EnumerateObject().ToDictionary(x => x.Name, x => x.Value.GetString()!) : []
        };
    }
}
