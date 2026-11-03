using System.Text.RegularExpressions;
using Microsoft.Win32;

namespace FT2ES.Engine;

/// <summary>Búsqueda de instalaciones legítimas de FAIRY TAIL 2 (Steam no es obligatorio).</summary>
public static partial class GameLocator
{
    /// <summary>
    /// Devuelve las carpetas candidatas: bibliotecas de Steam (registro, libraryfolders.vdf, appmanifest) y carpetas habituales de cada unidad.
    /// Cada una se valida por contenido (ejecutable + MASTER\ENG) y, si se pasa el paquete, con <see cref="GameValidator"/>.
    /// </summary>
    public static List<GameCandidate> FindCandidates(PatchPackage? pkg = null)
    {
        var found = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        void Add(string? p, string src) { if (!string.IsNullOrWhiteSpace(p)) { try { found.TryAdd(Path.GetFullPath(p).TrimEnd('\\'), src); } catch { } } }

        var libs = new List<string>();
        try
        {
            var steam = !OperatingSystem.IsWindows() ? null : Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam", "SteamPath", null) as string;
            if (!string.IsNullOrEmpty(steam))
            {
                steam = steam.Replace('/', '\\'); libs.Add(steam);
                var vdf = Path.Combine(steam, "steamapps", "libraryfolders.vdf");
                if (File.Exists(vdf))
                    foreach (Match mt in LibPath().Matches(File.ReadAllText(vdf))) libs.Add(mt.Groups[1].Value.Replace("\\\\", "\\"));
            }
        }
        catch { }
        foreach (var d in DriveInfo.GetDrives().Where(d => { try { return d.IsReady; } catch { return false; } }))
        {
            var r = d.RootDirectory.FullName;
            libs.Add(Path.Combine(r, "SteamLibrary")); libs.Add(Path.Combine(r, "Steam"));
            libs.Add(Path.Combine(r, "Program Files (x86)", "Steam")); libs.Add(Path.Combine(r, "Program Files", "Steam"));
            foreach (var b in new[] { "", "Games", "Juegos", "Program Files", "Program Files (x86)", "Program Files\\Steam\\steamapps\\common" })
                Add(Path.Combine(r, b, "FAIRY TAIL 2"), "Carpeta habitual");
        }
        foreach (var lib in libs.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            try
            {
                var apps = Path.Combine(lib, "steamapps");
                if (!Directory.Exists(apps)) continue;
                foreach (var acf in Directory.EnumerateFiles(apps, "appmanifest_*.acf"))
                {
                    var t = File.ReadAllText(acf);
                    var name = Acf("name").Match(t); var dir = Acf("installdir").Match(t);
                    if (name.Success && dir.Success && name.Groups[1].Value.Contains("FAIRY TAIL 2", StringComparison.OrdinalIgnoreCase))
                        Add(Path.Combine(apps, "common", dir.Groups[1].Value), "Steam");
                }
                Add(Path.Combine(apps, "common", "FAIRY TAIL 2"), "Steam");
            }
            catch { }
        }

        var res = new List<GameCandidate>();
        foreach (var (p, src) in found)
        {
            if (!Directory.Exists(p)) continue;
            if (!File.Exists(Path.Combine(p, GameValidator.ExeName)) || !Directory.Exists(Path.Combine(p, "MASTER", "ENG"))) continue;
            var rep = pkg == null ? null : GameValidator.Analyze(p, pkg);
            res.Add(new GameCandidate(p, src, rep?.State ?? GameState.Unknown, rep));
        }
        return res;
    }

    [GeneratedRegex("\"path\"\\s+\"([^\"]+)\"", RegexOptions.IgnoreCase)] private static partial Regex LibPath();
    private static Regex Acf(string key) => new($"\"{key}\"\\s+\"([^\"]*)\"", RegexOptions.IgnoreCase);
}
