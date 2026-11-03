using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;

[assembly: InternalsVisibleTo("FT2ES.EngineTests")]

namespace FT2ES.Engine;

/// <summary>Configuración global del motor (útil para pruebas y para que la interfaz fije rutas).</summary>
public static class EngineConfig
{
    /// <summary>Carpeta raíz de las copias de seguridad. Por defecto %LOCALAPPDATA%\Donelys\FairyTail2ES.</summary>
    public static string? BackupRoot { get; set; }

    /// <summary>Ruta de gust_enc.exe (junto a su gust_enc.json). Si es null se busca junto a la aplicación.</summary>
    public static string? GustEncPath { get; set; }

    /// <summary>Codificador de textos alternativo (si es null se usa gust_enc.exe).</summary>
    public static ITextCodec? TextCodec { get; set; }

    internal static string Root => BackupRoot ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Donelys", "FairyTail2ES");

    /// <summary>Identificador corto (16 hex de SHA-256) de la ruta completa normalizada del juego.</summary>
    public static string GameId(string gamePath)
    {
        var norm = Path.GetFullPath(gamePath).TrimEnd('\\', '/').ToUpperInvariant();
        return Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(norm)))[..16];
    }

    /// <summary>Carpeta de copia de seguridad correspondiente a una instalación del juego.</summary>
    public static string BackupDirFor(string gamePath) => Path.Combine(Root, GameId(gamePath));

    /// <summary>Localiza gust_enc.exe (con gust_enc.json al lado) o devuelve null.</summary>
    public static string? FindGustEnc()
    {
        var cands = new List<string>();
        if (!string.IsNullOrEmpty(GustEncPath)) cands.Add(GustEncPath);
        var d = AppContext.BaseDirectory;
        for (int i = 0; i < 8 && d != null; i++, d = Path.GetDirectoryName(d.TrimEnd('\\')))
        {
            cands.Add(Path.Combine(d, "gust_enc.exe"));
            cands.Add(Path.Combine(d, "herramientas", "gust_enc.exe"));
        }
        return cands.FirstOrDefault(c => File.Exists(c) && File.Exists(Path.Combine(Path.GetDirectoryName(c)!, "gust_enc.json")));
    }
}

/// <summary>Gravedad de una comprobación.</summary>
public enum CheckLevel { Ok, Warning, Error }

/// <summary>Resultado de una comprobación previa.</summary>
public sealed record CheckResult(string Id, CheckLevel Level, string Message);

/// <summary>Estado global de la carpeta del juego respecto al parche.</summary>
public enum GameState
{
    /// <summary>La carpeta no existe.</summary>
    NotFound,
    /// <summary>La carpeta existe pero no es una instalación reconocible de FAIRY TAIL 2.</summary>
    InvalidFolder,
    /// <summary>Todos los archivos son los originales esperados.</summary>
    Original,
    /// <summary>Algún archivo coincide con un estado previo reconocido (p. ej. menús ya en español).</summary>
    KnownPartial,
    /// <summary>Todos los archivos coinciden con el resultado de la traducción.</summary>
    TranslationInstalled,
    /// <summary>Versión desconocida o incompatible (algún archivo no coincide con nada conocido).</summary>
    Unknown,
    /// <summary>Mezcla de archivos traducidos y originales (instalación interrumpida o parcial).</summary>
    Mixed
}

/// <summary>Estado de un archivo concreto.</summary>
public enum FileState { Missing, Original, Recognized, Installed, Other }

/// <summary>Información de espacio libre de una carpeta/unidad.</summary>
public sealed record FolderInfo(string Path, long FreeBytes, long TotalBytes)
{
    /// <summary>Obtiene el espacio libre de la unidad que contiene la ruta (null si no se puede determinar).</summary>
    public static FolderInfo? Get(string path)
    {
        try
        {
            var root = System.IO.Path.GetPathRoot(System.IO.Path.GetFullPath(path));
            if (string.IsNullOrEmpty(root)) return null;
            var di = new DriveInfo(root);
            return new FolderInfo(path, di.AvailableFreeSpace, di.TotalSize);
        }
        catch { return null; }
    }
}

/// <summary>Informe de <see cref="GameValidator.Analyze"/>.</summary>
public sealed class ValidationReport
{
    public List<CheckResult> Checks { get; } = [];
    public GameState State { get; internal set; }
    public bool HasBackup { get; internal set; }
    public string BackupDir { get; internal set; } = "";
    /// <summary>Estado de cada archivo del parche (ruta relativa con «/»).</summary>
    public Dictionary<string, FileState> Files { get; } = [];
    /// <summary>SHA-256 actual de cada archivo existente.</summary>
    internal Dictionary<string, string> Hashes { get; } = [];
    public bool HasErrors => Checks.Any(c => c.Level == CheckLevel.Error);
    /// <summary>Primer mensaje de error (o cadena vacía).</summary>
    public string FirstError => Checks.FirstOrDefault(c => c.Level == CheckLevel.Error)?.Message ?? "";
    /// <summary>True si la instalación puede continuar sin riesgo.</summary>
    public bool CanInstall => !HasErrors && State is GameState.Original or GameState.KnownPartial or GameState.TranslationInstalled or GameState.Mixed;
    internal void Add(string id, CheckLevel l, string m) => Checks.Add(new CheckResult(id, l, m));
}

/// <summary>Fases de una operación.</summary>
public enum ProgressPhase { Verification, Backup, Patching, Rebuild, Applying, FinalValidation, Restoring, Done }

/// <summary>Progreso real de una operación.</summary>
public sealed class ProgressInfo
{
    /// <summary>0..100, ponderado por trabajo (bytes). Solo vale 100 al terminar la validación final.</summary>
    public double Percent { get; init; }
    public ProgressPhase Phase { get; init; }
    /// <summary>Nombre de la fase en español.</summary>
    public string PhaseName { get; init; } = "";
    public string Message { get; init; } = "";
    public string CurrentFile { get; init; } = "";
    /// <summary>Archivos procesados en la fase actual.</summary>
    public int FilesDone { get; init; }
    /// <summary>Archivos totales de la fase actual.</summary>
    public int FilesTotal { get; init; }
    /// <summary>True si todavía es seguro cancelar (antes de aplicar archivos al juego; después se revierte).</summary>
    public bool CanCancel { get; init; }
}

/// <summary>Resultado de la instalación.</summary>
public sealed class InstallResult
{
    public bool Success { get; init; }
    public string Message { get; init; } = "";
    public int FilesInstalled { get; init; }
    public string BackupDir { get; init; } = "";
    public bool Cancelled { get; init; }
    /// <summary>True si se tuvo que revertir cambios ya aplicados.</summary>
    public bool RolledBack { get; init; }
    public ValidationReport? Report { get; init; }
}

/// <summary>Archivo cuyo contenido actual no coincide ni con el original ni con la traducción instalada.</summary>
public sealed record RestoreConflict(string RelPath, string CurrentSha256);

/// <summary>Resultado de la restauración.</summary>
public sealed class RestoreResult
{
    public bool Success { get; init; }
    public string Message { get; init; } = "";
    public int FilesRestored { get; init; }
    public List<RestoreConflict> Conflicts { get; init; } = [];
    public bool Cancelled { get; init; }
    public string BackupDir { get; init; } = "";
}

/// <summary>Candidato a carpeta de juego.</summary>
public sealed record GameCandidate(string Path, string Source, GameState State, ValidationReport? Report);

/// <summary>Convierte textos cifrados del juego (message.json.e) a JSON y viceversa.</summary>
public interface ITextCodec
{
    /// <summary>Descifra message.json.e y devuelve el message.json resultante.</summary>
    byte[] Decrypt(byte[] encrypted, string workDir, CancellationToken ct);
    /// <summary>Cifra un message.json y devuelve el message.json.e resultante.</summary>
    byte[] Encrypt(byte[] json, string workDir, CancellationToken ct);
}

/// <summary>Implementación mediante gust_enc.exe -FT.</summary>
public sealed class GustEncCodec(string exePath) : ITextCodec
{
    public byte[] Decrypt(byte[] encrypted, string workDir, CancellationToken ct)
    {
        var w = Prepare(workDir);
        try
        {
            File.WriteAllBytes(Path.Combine(w, "message.json.e"), encrypted);
            Run(w, "message.json.e", ct);
            return File.ReadAllBytes(Path.Combine(w, "message.json"));
        }
        finally { TryDelete(w); }
    }

    public byte[] Encrypt(byte[] json, string workDir, CancellationToken ct)
    {
        var w = Prepare(workDir);
        try
        {
            File.WriteAllBytes(Path.Combine(w, "message.json"), json);
            Run(w, "message.json", ct);
            return File.ReadAllBytes(Path.Combine(w, "message.json.e"));
        }
        finally { TryDelete(w); }
    }

    private string Prepare(string workDir)
    {
        var w = Path.Combine(workDir, "trabajo-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(w);
        var src = Path.GetDirectoryName(exePath)!;
        File.Copy(exePath, Path.Combine(w, "gust_enc.exe"));
        File.Copy(Path.Combine(src, "gust_enc.json"), Path.Combine(w, "gust_enc.json"));
        return w;
    }

    private static void TryDelete(string w) { try { Directory.Delete(w, true); } catch { } }

    private static void Run(string w, string file, CancellationToken ct)
    {
        var psi = new System.Diagnostics.ProcessStartInfo(Path.Combine(w, "gust_enc.exe")) { WorkingDirectory = w, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true, UseShellExecute = false };
        psi.ArgumentList.Add("-FT"); psi.ArgumentList.Add(Path.Combine(w, file));
        using var p = System.Diagnostics.Process.Start(psi) ?? throw new IOException("No se pudo iniciar la herramienta de textos.");
        var so = p.StandardOutput.ReadToEndAsync(); var se = p.StandardError.ReadToEndAsync();
        using (ct.Register(() => { try { p.Kill(true); } catch { } }))
        {
            // Un archivo de textos corrupto puede dejar colgada la herramienta: límite de tiempo.
            if (!p.WaitForExit(TimeSpan.FromSeconds(60))) { try { p.Kill(true); } catch { } throw new IOException("La herramienta de textos no responde (archivo de textos inválido)."); }
        }
        ct.ThrowIfCancellationRequested();
        if (p.ExitCode != 0) throw new IOException($"La herramienta de textos falló (código {p.ExitCode}): {se.Result}{so.Result}".Trim());
    }
}
