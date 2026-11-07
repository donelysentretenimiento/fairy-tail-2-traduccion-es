using System.Diagnostics;
using System.Text;

namespace FT2ES.Engine;

/// <summary>
/// Comprobaciones previas. La compatibilidad se decide por ESTRUCTURA de los archivos (no por hash), de modo que
/// cualquier versión del juego con el mismo formato interno es aceptada.
/// </summary>
public static class GameValidator
{
    public const string ExeName = "FAIRY_TAIL_2.exe";
    /// <summary>Versiones del juego con las que se ha probado la traducción (instalar, cancelar y restaurar).</summary>
    internal static readonly HashSet<string> VersionesProbadas = ["1.2.0.0", "1.3.0.0"];
    internal const string MsgRel = "MASTER/ENG/fixed_data/message/message.json.e";

    /// <summary>Analiza la carpeta del juego y devuelve el estado y todas las comprobaciones. No modifica nada del juego.</summary>
    public static ValidationReport Analyze(string gamePath, PatchPackage pkg) => AnalyzeCore(gamePath, pkg, null);

    /// <summary>Versión asíncrona de <see cref="Analyze"/> (no bloquea el hilo de la interfaz).</summary>
    public static Task<ValidationReport> AnalyzeAsync(string gamePath, PatchPackage pkg) => Task.Run(() => Analyze(gamePath, pkg));

    internal static string Abs(string game, string rel) => Path.Combine(game, rel.Replace('/', '\\'));

    internal static ValidationReport AnalyzeCore(string gamePath, PatchPackage pkg, Action<string, long>? onFile)
    {
        var r = new ValidationReport();
        var m = pkg.Manifest;
        if (string.IsNullOrWhiteSpace(gamePath) || !Directory.Exists(gamePath))
        {
            r.State = GameState.NotFound;
            r.Add("carpeta", CheckLevel.Error, "La carpeta indicada no existe.");
            return r;
        }
        var game = Path.GetFullPath(gamePath);
        var st = BackupStore.Open(game);
        r.BackupDir = st.Dir; r.HasBackup = st.Exists;

        bool exe = File.Exists(Path.Combine(game, ExeName)) && new FileInfo(Path.Combine(game, ExeName)).Length > 0;
        bool eng = Directory.Exists(Path.Combine(game, "MASTER", "ENG"));
        r.Add("exe", exe ? CheckLevel.Ok : CheckLevel.Error, exe ? $"Se ha encontrado {ExeName}." : $"No se encuentra {ExeName}: esta carpeta no parece ser la de FAIRY TAIL 2.");
        r.Add("master-eng", eng ? CheckLevel.Ok : CheckLevel.Error, eng ? "Existe la carpeta MASTER\\ENG." : "No existe la carpeta MASTER\\ENG.");
        if (exe)
        {
            var ver = FileVersionInfo.GetVersionInfo(Path.Combine(game, ExeName)).FileVersion?.Trim();
            if (!string.IsNullOrEmpty(ver))
            {
                bool probada = VersionesProbadas.Contains(ver);
                r.Add("juego-version", probada ? CheckLevel.Ok : CheckLevel.Warning, probada ? $"Versión del juego: {ver}." : $"Versión del juego: {ver} (no probada con esta traducción; se comprobará la estructura).");
            }
        }
        var missing = m.Originales.Keys.Where(k => !File.Exists(Abs(game, k))).ToList();
        r.Add("recursos", missing.Count == 0 ? CheckLevel.Ok : CheckLevel.Error,
            missing.Count == 0 ? $"Están los {m.Originales.Count} archivos que necesita la traducción."
            : $"Faltan {missing.Count} archivos del juego (por ejemplo {missing[0]}).");
        if (!exe || !eng || missing.Count > 0) { r.State = GameState.InvalidFolder; return r; }

        r.Add("version", CheckLevel.Ok, $"Versión de la traducción: {pkg.Version}.");
        bool tool = EngineConfig.TextCodec != null || EngineConfig.FindGustEnc() != null;
        r.Add("herramienta", tool ? CheckLevel.Ok : CheckLevel.Error, tool ? "Herramienta de textos disponible." : "No se encuentra gust_enc.exe (ni gust_enc.json) junto al instalador.");

        // Copia de seguridad existente
        if (st.Exists)
        {
            var bad = st.VerifyIntegrity();
            r.Add("respaldo", bad.Count == 0 ? CheckLevel.Ok : CheckLevel.Error,
                bad.Count == 0 ? "La copia de seguridad existente es íntegra." : $"La copia de seguridad está dañada ({bad.Count} problemas, por ejemplo {bad[0]}).");
        }

        // Estado (sin hashear los archivos del juego)
        r.State = DetectState(game, st, pkg);
        foreach (var k in m.Originales.Keys) r.Files[k] = r.State == GameState.TranslationInstalled ? FileState.Installed : FileState.Original;

        // Estructura: se comprueba sobre la copia de seguridad si existe (los archivos del juego pueden estar ya traducidos).
        if (r.State == GameState.TranslationInstalled && !st.Exists)
            r.Add("estructura", CheckLevel.Warning, "La traducción ya está instalada y no hay copia de seguridad en este equipo: no se comprueba la estructura.");
        else
        {
            var fail = CheckStructure(game, st, pkg, onFile);
            if (fail == null) r.Add("estructura", CheckLevel.Ok, "Los archivos tienen la estructura que espera la traducción.");
            else { r.Add("estructura", CheckLevel.Error, $"Esta versión del juego no es compatible con la traducción: {fail}."); r.State = GameState.Unknown; }
        }

        if (r.State == GameState.TranslationInstalled && !st.Exists)
            r.Add("estado", CheckLevel.Warning, "La traducción ya parece instalada, pero no hay copia de seguridad en este equipo; no se podrá desinstalar desde aquí.");
        else if (r.State == GameState.Mixed && !st.Exists)
            r.Add("estado", CheckLevel.Error, "Hay una instalación a medias y no existe copia de seguridad: verifica los archivos del juego desde Steam y vuelve a intentarlo.");
        else if (r.State == GameState.Mixed)
            r.Add("estado", CheckLevel.Warning, "La instalación anterior quedó incompleta; se rehará a partir de la copia de seguridad.");
        else if (r.State == GameState.Original) r.Add("estado", CheckLevel.Ok, "El juego está sin traducir y listo para instalar.");

        var ro = m.Originales.Keys.Where(k => (File.GetAttributes(Abs(game, k)) & FileAttributes.ReadOnly) != 0).ToList();
        if (ro.Count > 0) r.Add("solo-lectura", CheckLevel.Warning, $"{ro.Count} archivos son de solo lectura; se quitará el atributo temporalmente y se restaurará después.");
        else r.Add("solo-lectura", CheckLevel.Ok, "Ningún archivo es de solo lectura.");

        // Permisos reales de escritura
        var dirs = m.Originales.Keys.Select(k => Path.GetDirectoryName(Abs(game, k))!).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
        var noWrite = dirs.Where(d => !CanWrite(d)).ToList();
        if (!CanWrite(EngineConfig.Root, create: true)) noWrite.Add(EngineConfig.Root);
        r.Add("escritura", noWrite.Count == 0 ? CheckLevel.Ok : CheckLevel.Error,
            noWrite.Count == 0 ? "Se puede escribir en todas las carpetas necesarias." : $"No hay permiso de escritura en {noWrite[0]}. Prueba a ejecutar el instalador como administrador o a cambiar los permisos de la carpeta.");

        // Espacio libre (tamaños reales)
        long total = m.Originales.Keys.Sum(k => new FileInfo(Abs(game, k)).Length);
        long msg = new FileInfo(Abs(game, MsgRel)).Length;
        long toBackup = m.Originales.Keys.Where(k => !st.Respaldo.ContainsKey(k)).Sum(k => new FileInfo(Abs(game, k)).Length);
        long needGame = (long)(total * 1.1) + 64L * 1024 * 1024;
        long needBackup = toBackup + 8 * msg + 64L * 1024 * 1024;
        var fg = FolderInfo.Get(game); var fb = FolderInfo.Get(EngineConfig.Root);
        if (fg == null || fb == null) r.Add("espacio", CheckLevel.Warning, "No se ha podido determinar el espacio libre en disco.");
        else
        {
            bool same = string.Equals(Path.GetPathRoot(game), Path.GetPathRoot(Path.GetFullPath(EngineConfig.Root)), StringComparison.OrdinalIgnoreCase);
            bool ok = same ? fg.FreeBytes >= needGame + needBackup : fg.FreeBytes >= needGame && fb.FreeBytes >= needBackup;
            long need = same ? needGame + needBackup : Math.Max(needGame, needBackup);
            r.Add("espacio", ok ? CheckLevel.Ok : CheckLevel.Error,
                ok ? $"Espacio libre suficiente (se necesitan unos {need / 1048576} MB)." : $"No hay espacio libre suficiente: se necesitan unos {need / 1048576} MB y hay {Math.Min(fg.FreeBytes, same ? fg.FreeBytes : fb.FreeBytes) / 1048576} MB.");
        }

        bool running = false;
        foreach (var p in Process.GetProcessesByName("FAIRY_TAIL_2")) { running = true; p.Dispose(); }
        r.Add("proceso", running ? CheckLevel.Error : CheckLevel.Ok, running ? "El juego está en ejecución. Ciérralo antes de continuar." : "El juego no está en ejecución.");
        return r;
    }

    /// <summary>Estado según el registro de instalación (tamaño y fecha) o, sin registro, una muestra de diálogos.</summary>
    private static GameState DetectState(string game, BackupStore st, PatchPackage pkg)
    {
        var info = st.Info;
        if (info != null && st.Exists)
        {
            if (info.Estado == "en curso") return GameState.Mixed;
            if (info.Estado == "instalado" && info.Archivos.Count > 0 && pkg.Manifest.Originales.Keys.All(k => info.Archivos.TryGetValue(k, out var s) && Matches(Abs(game, k), s)))
                return GameState.TranslationInstalled;
            return GameState.Original;
        }
        return LooksTranslated(game, pkg) ? GameState.TranslationInstalled : GameState.Original;
    }

    private static bool Matches(string path, FileStamp s)
    {
        var fi = new FileInfo(path);
        return fi.Exists && fi.Length == s.Size && fi.LastWriteTimeUtc.Ticks == s.Ticks;
    }

    /// <summary>Muestra de ~40 líneas de diálogo: ¿ya están en el español del paquete (≥ 90 %)?</summary>
    private static bool LooksTranslated(string game, PatchPackage pkg)
    {
        var keys = pkg.Dialogs.Keys.ToList();
        if (keys.Count == 0) return false;
        int step = Math.Max(1, keys.Count / 40), tot = 0, ok = 0;
        var cache = new Dictionary<string, List<EbmRecord>?>();
        for (int i = 0; i < keys.Count && tot < 40; i += step)
        {
            var k = keys[i]; int h = k.LastIndexOf('#');
            var rel = $"MASTER/ENG/EventMessageData/EVENT_MESSAGE_{k[..h]}.ebm";
            if (!cache.TryGetValue(rel, out var recs))
            {
                try { recs = Ebm.Parse(File.ReadAllBytes(Abs(game, rel))).Recs; } catch { recs = null; }
                cache[rel] = recs;
            }
            tot++;
            int idx = int.Parse(k[(h + 1)..]);
            if (recs != null && idx < recs.Count && recs[idx].T.AsSpan().SequenceEqual(Encoding.UTF8.GetBytes(pkg.Dialogs[k]))) ok++;
        }
        return tot > 0 && ok * 10 >= tot * 9;
    }

    /// <summary>Devuelve null si todo cuadra, o la descripción (en español) de lo que falla.</summary>
    private static string? CheckStructure(string game, BackupStore st, PatchPackage pkg, Action<string, long>? onFile)
    {
        var m = pkg.Manifest; var es = m.Estructura;
        var porf = new Dictionary<string, List<int>>();
        foreach (var k in pkg.Dialogs.Keys)
        {
            int h = k.LastIndexOf('#');
            var rel = $"MASTER/ENG/EventMessageData/EVENT_MESSAGE_{k[..h]}.ebm";
            if (!porf.TryGetValue(rel, out var l)) porf[rel] = l = [];
            l.Add(int.Parse(k[(h + 1)..]));
        }
        foreach (var rel in m.Originales.Keys)
        {
            var path = st.Respaldo.ContainsKey(rel) ? st.PathOf(rel) : Abs(game, rel);
            byte[] b;
            try { b = File.ReadAllBytes(path); }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { return $"no se puede leer {rel} (¿está en uso?)"; }
            try
            {
                var name = Path.GetFileName(rel);
                if (es.Fdata.TryGetValue(name, out var want))
                {
                    var ents = Fdata.Entries(b);
                    if (ents.Count == 0) return $"{name} no tiene el formato esperado";
                    foreach (var (hex, size) in want)
                    {
                        var e = ents.FirstOrDefault(x => x.Name == Convert.ToUInt32(hex, 16));
                        if (e.Es == 0) return $"{name} no contiene el recurso {hex}";
                        if (e.Us != size || Fdata.DataOf(b, e).Length != size) return $"el recurso {hex} de {name} tiene otro tamaño";
                    }
                }
                else if (es.Lang.TryGetValue(rel, out var n))
                {
                    if (b.Length % 12 != 0 || b.Length / 12 < n) return $"{name} tiene menos registros de los esperados"; // una versión nueva puede añadir registros
                }
                else if (es.Ebm.TryGetValue(rel, out var cnt))
                {
                    var (recs, _) = Ebm.Parse(b);
                    if (recs.Count != cnt) return $"{name} no tiene el número de registros esperado";
                    if (porf.TryGetValue(rel, out var idxs) && idxs.Any(i => i < 0 || i >= recs.Count || recs[i].T.Length == 0))
                        return $"{name} no tiene el texto esperado en las líneas que se traducen";
                }
                else if (rel == MsgRel)
                {
                    var codec = EngineConfig.TextCodec ?? new GustEncCodec(EngineConfig.FindGustEnc() ?? throw new FileNotFoundException("gust_enc.exe"));
                    Directory.CreateDirectory(st.WorkDir);
                    List<(string Label, string Message)> items;
                    try { items = MessageJson.Read(codec.Decrypt(b, st.WorkDir, CancellationToken.None)); }
                    finally { try { Directory.Delete(st.WorkDir, true); Directory.Delete(st.Dir); } catch { /* Delete(Dir) falla si no está vacío: es lo deseado */ } }
                    var labels = items.Select(x => x.Label).ToHashSet();
                    int found = pkg.Texts.Keys.Count(labels.Contains);
                    if (found * 100 < pkg.Texts.Count * 90) return $"el archivo de textos solo contiene {found} de las {pkg.Texts.Count} etiquetas esperadas";
                }
            }
            catch (Exception ex) when (ex is not FileNotFoundException)
            { return $"{Path.GetFileName(rel)} no se puede interpretar ({ex.GetType().Name})"; }
            onFile?.Invoke(rel, b.Length);
        }
        return null;
    }

    private static bool CanWrite(string dir, bool create = false)
    {
        try
        {
            if (create) Directory.CreateDirectory(dir);
            var f = Path.Combine(dir, ".ft2es_prueba_" + Guid.NewGuid().ToString("N")[..8] + ".tmp");
            File.WriteAllBytes(f, [0]);
            File.Delete(f);
            return true;
        }
        catch { return false; }
    }
}
