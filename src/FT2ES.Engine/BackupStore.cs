using System.Text.Encodings.Web;
using System.Text.Json;

namespace FT2ES.Engine;

/// <summary>Contenido de instalacion.json.</summary>
internal sealed class InstallationInfo
{
    public string Version { get; set; } = "";
    public string Fecha { get; set; } = "";
    public string RutaJuego { get; set; } = "";
    /// <summary>«Original» o «KnownPartial» (el estado del usuario antes de instalar).</summary>
    public string EstadoPrevio { get; set; } = "Original";
    public Dictionary<string, string> Reconocidos { get; set; } = [];
    /// <summary>SHA-256 que tendrá cada archivo al terminar la instalación.</summary>
    public Dictionary<string, string> Resultado { get; set; } = [];
    /// <summary>«en curso», «instalado» o «revertido».</summary>
    public string Estado { get; set; } = "en curso";
    /// <summary>Tamaño y fecha de modificación (UTC, ticks) de cada archivo al terminar la instalación.</summary>
    public Dictionary<string, FileStamp> Archivos { get; set; } = [];
}

internal sealed class FileStamp { public long Size { get; set; } public long Ticks { get; set; } }

internal sealed class JournalEntry { public string Ruta { get; set; } = ""; public string Estado { get; set; } = "pendiente"; }
internal sealed class JournalDto { public string Operacion { get; set; } = "instalar"; public List<JournalEntry> Entradas { get; set; } = []; }

/// <summary>Carpeta de copia de seguridad de una instalación: respaldo.json, instalacion.json, diario y registro.</summary>
internal sealed class BackupStore
{
    internal static readonly JsonSerializerOptions Json = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };
    private static readonly object LogLock = new();

    public string Game { get; }
    public string Dir { get; }
    public string FilesDir => Path.Combine(Dir, "archivos");
    public string RespaldoPath => Path.Combine(Dir, "respaldo.json");
    public string InstalacionPath => Path.Combine(Dir, "instalacion.json");
    public string DiarioPath => Path.Combine(Dir, "diario.json");
    public string LogPath => Path.Combine(Dir, "instalador.log");
    public string WorkDir => Path.Combine(Dir, "trabajo");
    public Dictionary<string, FileHash> Respaldo { get; private set; } = [];
    public InstallationInfo? Info { get; private set; }
    public bool Exists => File.Exists(RespaldoPath);

    private BackupStore(string game) { Game = game; Dir = EngineConfig.BackupDirFor(game); }

    public static BackupStore Open(string game)
    {
        var s = new BackupStore(game);
        s.Reload();
        return s;
    }

    public void Reload()
    {
        Respaldo = []; Info = null;
        if (File.Exists(RespaldoPath))
            Respaldo = JsonSerializer.Deserialize<Dictionary<string, FileHash>>(File.ReadAllText(RespaldoPath), Json) ?? [];
        if (File.Exists(InstalacionPath))
            Info = JsonSerializer.Deserialize<InstallationInfo>(File.ReadAllText(InstalacionPath), Json);
    }

    public string PathOf(string rel) => Path.Combine(FilesDir, rel.Replace('/', '\\'));

    public void SaveRespaldo() { Directory.CreateDirectory(Dir); FileUtil.WriteAtomic(RespaldoPath, JsonSerializer.SerializeToUtf8Bytes(Respaldo, Json)); }
    public void SaveInfo() { Directory.CreateDirectory(Dir); FileUtil.WriteAtomic(InstalacionPath, JsonSerializer.SerializeToUtf8Bytes(Info, Json)); }
    public void SetInfo(InstallationInfo i) => Info = i;

    public void Log(string msg)
    {
        try
        {
            lock (LogLock)
            {
                Directory.CreateDirectory(Dir);
                File.AppendAllText(LogPath, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} {msg}{Environment.NewLine}");
            }
        }
        catch { /* el registro nunca debe romper una operación */ }
    }

    /// <summary>Comprueba que cada copia existe y coincide con respaldo.json. Devuelve la lista de problemas.</summary>
    public List<string> VerifyIntegrity(Action<string, long>? onFile = null)
    {
        var bad = new List<string>();
        foreach (var (rel, h) in Respaldo)
        {
            var p = PathOf(rel);
            if (!File.Exists(p)) { bad.Add($"{rel} (falta la copia)"); continue; }
            try { if (Hashing.Sha256File(p) != h.Sha256) bad.Add($"{rel} (la copia está alterada)"); }
            catch (IOException) { bad.Add($"{rel} (no se puede leer la copia)"); }
            onFile?.Invoke(rel, h.Size);
        }
        return bad;
    }

    // ----- diario -----
    public JournalDto? ReadJournal() => File.Exists(DiarioPath) ? JsonSerializer.Deserialize<JournalDto>(File.ReadAllText(DiarioPath), Json) : null;
    public void SaveJournal(JournalDto j) { Directory.CreateDirectory(Dir); FileUtil.WriteAtomic(DiarioPath, JsonSerializer.SerializeToUtf8Bytes(j, Json)); }
    public void DeleteJournal() { try { File.Delete(DiarioPath); } catch { } }

    /// <summary>
    /// Devuelve a su estado original los archivos que el diario marca como aplicados o dudosos, desde la copia verificada.
    /// Devuelve la lista de fallos (vacía si todo quedó verificado).
    /// </summary>
    public List<string> Rollback(JournalDto j)
    {
        var fails = new List<string>();
        foreach (var en in j.Entradas.Where(x => x.Estado is "aplicado" or "iniciado"))
        {
            try
            {
                var dest = Path.Combine(Game, en.Ruta.Replace('/', '\\'));
                var want = Respaldo[en.Ruta].Sha256;
                if (File.Exists(dest) && Hashing.Sha256File(dest) == want) { en.Estado = "revertido"; continue; }
                FileUtil.CopyVerified(PathOf(en.Ruta), dest, want, replace: true);
                en.Estado = "revertido";
                Log("Revertido: " + en.Ruta);
            }
            catch (Exception ex) { fails.Add($"{en.Ruta}: {ex.Message}"); Log($"ERROR al revertir {en.Ruta}: {ex.Message}"); }
        }
        return fails;
    }

    /// <summary>Si quedó un diario sin cerrar (cierre brusco), revierte lo que hubiera. Devuelve true si había algo que revertir.</summary>
    public bool RecoverPending(out List<string> fails)
    {
        fails = [];
        var j = ReadJournal();
        if (j == null) return false;
        Log("Se encontró un diario de una instalación interrumpida; se revierte.");
        fails = Rollback(j);
        if (fails.Count == 0) DeleteJournal();
        return true;
    }
}

internal static class FileUtil
{
    public const string TmpExt = ".ft2es.tmp";

    public static void WriteAtomic(string path, byte[] data)
    {
        var tmp = path + TmpExt;
        File.WriteAllBytes(tmp, data);
        File.Move(tmp, path, true);
    }

    /// <summary>Sustituye dest por tmp de forma atómica (File.Replace), tolerando archivos de solo lectura.</summary>
    public static void ReplaceFile(string tmp, string dest)
    {
        if (!File.Exists(dest)) { File.Move(tmp, dest); return; }
        var attr = File.GetAttributes(dest);
        if ((attr & FileAttributes.ReadOnly) != 0) File.SetAttributes(dest, attr & ~FileAttributes.ReadOnly);
        try { File.Replace(tmp, dest, null, true); }
        finally { if ((attr & FileAttributes.ReadOnly) != 0 && File.Exists(dest)) File.SetAttributes(dest, attr); }
    }

    /// <summary>Copia src a dst pasando por un temporal, verificando el SHA-256 antes de colocarlo.</summary>
    public static void CopyVerified(string src, string dst, string sha, bool replace)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
        var tmp = dst + TmpExt;
        try
        {
            File.Copy(src, tmp, true);
            File.SetAttributes(tmp, FileAttributes.Normal);
            if (Hashing.Sha256File(tmp) != sha) throw new IOException("La copia no coincide con el original (SHA-256).");
            if (replace) ReplaceFile(tmp, dst); else File.Move(tmp, dst, true);
        }
        finally { try { File.Delete(tmp); } catch { } }
    }
}

/// <summary>Cálculo de progreso real, monótono y que solo llega a 100 al terminar.</summary>
internal sealed class Tracker(IProgress<ProgressInfo>? p, double total)
{
    private double _done, _last;
    public void Add(double w) => _done += w;

    public void Report(ProgressPhase ph, string name, string msg, string file = "", int done = 0, int tot = 0, bool canCancel = true)
    {
        var pc = Math.Max(_last, Math.Clamp(total <= 0 ? 0 : _done / total * 100, 0, 99.9));
        _last = pc;
        p?.Report(new ProgressInfo { Percent = pc, Phase = ph, PhaseName = name, Message = msg, CurrentFile = file, FilesDone = done, FilesTotal = tot, CanCancel = canCancel });
    }

    public void Finish(ProgressPhase ph, string name, string msg, int n)
        => p?.Report(new ProgressInfo { Percent = 100, Phase = ph, PhaseName = name, Message = msg, FilesDone = n, FilesTotal = n, CanCancel = false });
}
