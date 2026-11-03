using FT2ES.Engine;

// Pruebas del motor FT2ES. Cada escenario trabaja en su propia copia limpia bajo pruebas\cs_*.
string Trabajo = Environment.GetEnvironmentVariable("FT2_TRABAJO") ?? throw new InvalidOperationException("Define la variable de entorno FT2_TRABAJO con la carpeta que contiene backups_juego (tus propios archivos originales del juego).");
string Inst = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
string Pruebas = Path.Combine(Trabajo, "pruebas");
string Bk = Path.Combine(Trabajo, "backups_juego");
EngineConfig.GustEncPath = Path.Combine(Inst, "third_party", "gust_tools", "gust_enc.exe");
var pkg = PatchPackage.Load(Path.Combine(Inst, "paquete", "paquete.zip"));
var man = pkg.Manifest;

string Abs(string g, string rel) => Path.Combine(g, rel.Replace('/', '\\'));

string MakeGame(string name)
{
    var root = Path.Combine(Pruebas, "cs_" + name);
    if (Directory.Exists(root)) { foreach (var f in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)) File.SetAttributes(f, FileAttributes.Normal); Directory.Delete(root, true); }
    var g = Path.Combine(root, "juego");
    EngineConfig.BackupRoot = Path.Combine(root, "respaldos");
    void Cp(string src, string rel) { var d = Abs(g, rel); Directory.CreateDirectory(Path.GetDirectoryName(d)!); File.Copy(src, d); }
    foreach (var h in new[] { "0x0a12caf9", "0xb766cb46", "0xcdce5e37", "0xf3ab3808", "0xda2245f2" }) Cp(Path.Combine(Bk, $"{h}.enUS.fdata.ORIGINAL"), $"Motor/enUS/{h}.fdata");
    Cp(Path.Combine(Bk, "root.texture.enUS.lang.ORIGINAL"), "Motor/root.texture.enUS.lang");
    Cp(Path.Combine(Bk, "root.font.enUS.lang.ORIGINAL"), "Motor/root.font.enUS.lang");
    Cp(Path.Combine(Bk, "message.json.e.ORIGINAL"), "MASTER/ENG/fixed_data/message/message.json.e");
    foreach (var e in Directory.GetFiles(Path.Combine(Bk, "ebm"), "*.ebm")) Cp(e, "MASTER/ENG/EventMessageData/" + Path.GetFileName(e));
    File.WriteAllBytes(Path.Combine(g, "FAIRY_TAIL_2.exe"), new byte[1024]);
    return g;
}

Dictionary<string, string> Snap(string g) => Directory.EnumerateFiles(g, "*", SearchOption.AllDirectories).ToDictionary(f => Path.GetRelativePath(g, f), f => Hashing.Sha256File(f));
bool Same(Dictionary<string, string> a, Dictionary<string, string> b) => a.Count == b.Count && a.All(kv => b.TryGetValue(kv.Key, out var v) && v == kv.Value);
List<string> Diffs(string g, Func<string, string> expected) =>
    man.Originales.Keys.Where(r => !File.Exists(Abs(g, r)) || Hashing.Sha256File(Abs(g, r)) != expected(r)).ToList();
List<string> NotOriginal(string g) => Diffs(g, r => man.Originales[r].Sha256);
List<string> NotResult(string g) => Diffs(g, r => man.Resultado[r]);
void Req(bool c, string msg) { if (!c) throw new Exception(msg); }

int fails = 0;
async Task Run(string name, Func<Task> body)
{
    try { await body(); Console.WriteLine($"PASS  {name}"); }
    catch (Exception ex) { fails++; Console.WriteLine($"FAIL  {name}: {ex.Message}"); Console.WriteLine(ex.StackTrace); }
}

string gMain = "";
var sw = System.Diagnostics.Stopwatch.StartNew();

await Run("1. Analyze = Original (y comprobaciones OK)", async () =>
{
    gMain = MakeGame("principal");
    var r = GameValidator.Analyze(gMain, pkg);
    Req(r.State == GameState.Original, "estado " + r.State);
    Req(!r.HasErrors, "errores: " + string.Join("|", r.Checks.Where(c => c.Level == CheckLevel.Error).Select(c => c.Message)));
    foreach (var id in new[] { "exe", "master-eng", "recursos", "estructura", "escritura", "espacio", "proceso", "solo-lectura", "herramienta" })
        Req(r.Checks.Any(c => c.Id == id && c.Level == CheckLevel.Ok), "falta comprobación OK: " + id);
    Req(!r.HasBackup, "no debería haber respaldo");
    Req(!gMain.StartsWith("H:", StringComparison.OrdinalIgnoreCase), "ruta en H:");
    await Task.CompletedTask;
});

await Run("2. Instalación completa: hashes == resultado, progreso monótono y 100 solo al final", async () =>
{
    var pr = new Prog();
    var res = await Installer.InstallAsync(gMain, pkg, pr, CancellationToken.None);
    Req(res.Success, res.Message);
    Req(res.FilesInstalled == man.Resultado.Count, "FilesInstalled=" + res.FilesInstalled);
    var bad = NotResult(gMain); Req(bad.Count == 0, $"{bad.Count} archivos no coinciden con resultado, p. ej. {bad.FirstOrDefault()}");
    var p = pr.Items.Select(i => i.Percent).ToList();
    for (int i = 1; i < p.Count; i++) Req(p[i] >= p[i - 1], $"no monótono en {i}: {p[i - 1]} -> {p[i]}");
    Req(p[^1] == 100 && p.Count(x => x >= 100) == 1, "100 debe aparecer una sola vez y al final");
    var phases = pr.Items.Select(i => i.Phase).Distinct().ToList();
    foreach (var f in new[] { ProgressPhase.Verification, ProgressPhase.Backup, ProgressPhase.Patching, ProgressPhase.Rebuild, ProgressPhase.Applying, ProgressPhase.FinalValidation })
        Req(phases.Contains(f), "falta fase " + f);
    Req(pr.Items.Where(i => i.Phase == ProgressPhase.FinalValidation).All(i => i.Percent < 100), "100 antes de terminar la validación");
    Req(p.Distinct().Count() > 20, "progreso poco granular");
    Req(File.Exists(Path.Combine(res.BackupDir, "instalador.log")) && File.Exists(Path.Combine(res.BackupDir, "respaldo.json")) && File.Exists(Path.Combine(res.BackupDir, "instalacion.json")), "faltan respaldo.json/instalacion.json/instalador.log");
    Req(Directory.GetFiles(gMain, "*.ft2es.tmp", SearchOption.AllDirectories).Length == 0, "quedan temporales");
    Console.WriteLine($"      ({p.Count} informes de progreso, {sw.Elapsed.TotalSeconds:F1} s)");
});

await Run("3. Analyze = TranslationInstalled", async () =>
{
    var r = GameValidator.Analyze(gMain, pkg);
    Req(r.State == GameState.TranslationInstalled && r.HasBackup, $"estado {r.State}, respaldo {r.HasBackup}");
    await Task.CompletedTask;
});

await Run("4. Reinstalar es idempotente y no cambia el respaldo", async () =>
{
    var bd = EngineConfig.BackupDirFor(gMain);
    string Bkp() => string.Join(";", Directory.EnumerateFiles(Path.Combine(bd, "archivos"), "*", SearchOption.AllDirectories).OrderBy(x => x).Select(Hashing.Sha256File)) + Hashing.Sha256File(Path.Combine(bd, "respaldo.json"));
    var before = Bkp();
    var res = await Installer.InstallAsync(gMain, pkg, null, CancellationToken.None);
    Req(res.Success, res.Message);
    Req(Bkp() == before, "el respaldo cambió");
    Req(NotResult(gMain).Count == 0, "hashes != resultado");
});

await Run("4b. Traducción ya instalada sin respaldo: detectada por muestra de diálogos, sin tocar nada", async () =>
{
    var bd = EngineConfig.BackupDirFor(gMain); var aside = bd + "_aparte";
    Directory.Move(bd, aside);
    try
    {
        var r = GameValidator.Analyze(gMain, pkg);
        Req(r.State == GameState.TranslationInstalled && !r.HasBackup && r.Checks.Any(c => c.Level == CheckLevel.Warning), $"estado {r.State}");
        var snap = Snap(gMain);
        var res = await Installer.InstallAsync(gMain, pkg, null, CancellationToken.None);
        Req(res.Success && res.FilesInstalled == 0 && Same(snap, Snap(gMain)), res.Message);
    }
    finally { if (Directory.Exists(bd)) Directory.Delete(bd, true); Directory.Move(aside, bd); }
});

await Run("5. Restore: hashes == originales y respaldo limpiado", async () =>
{
    var pr = new Prog();
    var res = await Restorer.RestoreAsync(gMain, pr, CancellationToken.None);
    Req(res.Success, res.Message);
    Req(NotOriginal(gMain).Count == 0, "no son los originales");
    Req(!GameValidator.Analyze(gMain, pkg).HasBackup, "el respaldo sigue activo");
    Req(!Directory.Exists(Path.Combine(res.BackupDir, "archivos")), "quedan copias");
    var p = pr.Items.Select(i => i.Percent).ToList();
    for (int i = 1; i < p.Count; i++) Req(p[i] >= p[i - 1], "progreso no monótono");
    Req(p[^1] == 100 && p.Count(x => x >= 100) == 1, "100 solo al final");
    Req(GameValidator.Analyze(gMain, pkg).State == GameState.Original, "estado final no es Original");
});

await Run("6. Carpeta inválida / estructura incompatible: rechazo sin tocar nada", async () =>
{
    var inv = Path.Combine(Pruebas, "cs_invalida"); Directory.CreateDirectory(inv); File.WriteAllText(Path.Combine(inv, "algo.txt"), "x");
    Req(GameValidator.Analyze(inv, pkg).State == GameState.InvalidFolder, "no es InvalidFolder");
    Req(GameValidator.Analyze(Path.Combine(Pruebas, "cs_no_existe_xyz"), pkg).State == GameState.NotFound, "no es NotFound");
    Req(!(await Installer.InstallAsync(inv, pkg, null, CancellationToken.None)).Success, "debió rechazar carpeta inválida");
    var casos = new (string Nombre, Action<string> Rompe)[]
    {
        ("EBM truncado a la mitad", g => { var f = Directory.GetFiles(Path.Combine(g, "MASTER", "ENG", "EventMessageData"))[0]; var b = File.ReadAllBytes(f); File.WriteAllBytes(f, b[..(b.Length / 2)]); }),
        ("entrada FDATA con otro tamaño", g => { var f = Abs(g, "Motor/enUS/0xb766cb46.fdata"); var b = File.ReadAllBytes(f); var e = Fdata.Entries(b).First(x => x.Name == 0x13cbe5db); System.Buffers.Binary.BinaryPrimitives.WriteUInt64LittleEndian(b.AsSpan((int)e.Off + 24), (ulong)e.Us + 16); File.WriteAllBytes(f, b); }),
        ("message.json.e corrupto", g => { var f = Abs(g, "MASTER/ENG/fixed_data/message/message.json.e"); var b = File.ReadAllBytes(f); new Random(7).NextBytes(b); File.WriteAllBytes(f, b); }),
        (".lang con otro nº de registros", g => { var f = Abs(g, "Motor/root.font.enUS.lang"); File.WriteAllBytes(f, File.ReadAllBytes(f).Concat(new byte[12]).ToArray()); }),
    };
    foreach (var (nombre, rompe) in casos)
    {
        var g = MakeGame("incompatible");
        rompe(g);
        var rep = GameValidator.Analyze(g, pkg);
        Req(rep.State == GameState.Unknown && rep.Checks.Any(c => c.Id == "estructura" && c.Level == CheckLevel.Error), $"{nombre}: estado {rep.State}");
        var snap = Snap(g);
        var res = await Installer.InstallAsync(g, pkg, null, CancellationToken.None);
        Req(!res.Success && Same(snap, Snap(g)) && !Directory.Exists(res.BackupDir), $"{nombre}: no se rechazó limpiamente");
        Console.WriteLine($"      {nombre}: {res.Message}");
    }
});

await Run("6b. Otra versión (bytes distintos en texto y contenido) se ACEPTA y restaurar devuelve exactamente los bytes del usuario", async () =>
{
    var g = MakeGame("otra_version");
    var ebmF = Directory.GetFiles(Path.Combine(g, "MASTER", "ENG", "EventMessageData")).OrderBy(x => x, StringComparer.Ordinal).First();
    var (recs, cola) = Ebm.Parse(File.ReadAllBytes(ebmF));
    int idx = recs.FindIndex(r => r.T.Length > 3);
    recs[idx].T[1] ^= 0x01; File.WriteAllBytes(ebmF, Ebm.Build(recs, cola)); // texto distinto
    var fd = Abs(g, "Motor/enUS/0xf3ab3808.fdata"); var fb = File.ReadAllBytes(fd);
    var ent = Fdata.Entries(fb).Last(); fb[(int)(ent.Off + ent.Es - 1)] ^= 0x7F; File.WriteAllBytes(fd, fb); // contenido distinto en una entrada no traducida
    var snap = Snap(g);
    var rep = GameValidator.Analyze(g, pkg);
    Req(rep.State == GameState.Original && !rep.HasErrors, $"estado {rep.State}: {rep.FirstError}");
    var res = await Installer.InstallAsync(g, pkg, null, CancellationToken.None);
    Req(res.Success, res.Message);
    Req(GameValidator.Analyze(g, pkg).State == GameState.TranslationInstalled, "tras instalar no es TranslationInstalled");
    var rs = await Restorer.RestoreAsync(g, null, CancellationToken.None);
    Req(rs.Success, rs.Message);
    var after = Snap(g);
    Req(Same(snap, after), "la restauración no devolvió exactamente los bytes del usuario");
});

await Run("7a. Cancelación al ~50 % => juego intacto", async () =>
{
    var g = MakeGame("cancel50"); var snap = Snap(g);
    using var cts = new CancellationTokenSource();
    var pr = new Prog(i => { if (i.Percent >= 50) cts.Cancel(); });
    var res = await Installer.InstallAsync(g, pkg, pr, cts.Token);
    Req(!res.Success && res.Cancelled, "no se canceló: " + res.Message);
    Req(Same(snap, Snap(g)), "el juego cambió");
    Console.WriteLine("      mensaje: " + res.Message);
});

await Run("7b. Cancelación en mitad de la aplicación => rollback total verificado", async () =>
{
    var g = MakeGame("cancelapl");
    using var cts = new CancellationTokenSource();
    var pr = new Prog(i => { if (i.Phase == ProgressPhase.Applying && i.FilesDone >= 250) cts.Cancel(); });
    var res = await Installer.InstallAsync(g, pkg, pr, cts.Token);
    Req(!res.Success && res.Cancelled && res.RolledBack, $"cancelled={res.Cancelled} rolledBack={res.RolledBack}: {res.Message}");
    Req(NotOriginal(g).Count == 0, "no se restauraron los originales");
    Req(Directory.GetFiles(g, "*.ft2es.tmp", SearchOption.AllDirectories).Length == 0, "quedan temporales");
    Req(!File.Exists(Path.Combine(res.BackupDir, "diario.json")), "queda el diario");
    Req(GameValidator.Analyze(g, pkg).State == GameState.Original, "estado no Original");
    Console.WriteLine("      mensaje: " + res.Message);
});

await Run("8. Fallo real a mitad (archivo bloqueado) => rollback", async () =>
{
    var g = MakeGame("bloqueo");
    var last = Directory.GetFiles(Path.Combine(g, "MASTER", "ENG", "EventMessageData"), "*.ebm").OrderBy(x => x, StringComparer.Ordinal).Last();
    FileStream? lk = null;
    var pr = new Prog(i => { if (lk == null && i.Phase == ProgressPhase.Applying && i.FilesDone >= 100) lk = new FileStream(last, FileMode.Open, FileAccess.Read, FileShare.None); });
    InstallResult res;
    try { res = await Installer.InstallAsync(g, pkg, pr, CancellationToken.None); } finally { lk?.Dispose(); }
    Req(lk != null, "no se llegó a bloquear");
    Req(!res.Success && res.RolledBack && !res.Cancelled, $"success={res.Success} rolledBack={res.RolledBack}: {res.Message}");
    Req(NotOriginal(g).Count == 0, "no se restauraron los originales");
    Req(Directory.GetFiles(g, "*.ft2es.tmp", SearchOption.AllDirectories).Length == 0, "quedan temporales");
    Console.WriteLine("      mensaje: " + res.Message);
});

await Run("8b. Archivo de solo lectura: aviso, instala y conserva el atributo", async () =>
{
    var g = MakeGame("solo_lectura");
    var f = Abs(g, "MASTER/ENG/fixed_data/message/message.json.e");
    File.SetAttributes(f, FileAttributes.ReadOnly);
    var rep = GameValidator.Analyze(g, pkg);
    Req(rep.Checks.Any(c => c.Id == "solo-lectura" && c.Level == CheckLevel.Warning), "sin aviso de solo lectura");
    var res = await Installer.InstallAsync(g, pkg, null, CancellationToken.None);
    Req(res.Success, res.Message);
    Req((File.GetAttributes(f) & FileAttributes.ReadOnly) != 0, "se perdió el atributo de solo lectura");
    Req(NotResult(g).Count == 0, "hashes != resultado");
    var rs = await Restorer.RestoreAsync(g, null, CancellationToken.None);
    Req(rs.Success && NotOriginal(g).Count == 0, rs.Message);
});

await Run("9. Conflicto en restauración: detectado y no sobrescrito", async () =>
{
    var g = MakeGame("conflicto");
    Req((await Installer.InstallAsync(g, pkg, null, CancellationToken.None)).Success, "instalación");
    var victim = Directory.GetFiles(Path.Combine(g, "MASTER", "ENG", "EventMessageData"))[0];
    var b = File.ReadAllBytes(victim); b[^1] ^= 0x5A; File.WriteAllBytes(victim, b);
    var mod = Hashing.Sha256File(victim);
    var rs = await Restorer.RestoreAsync(g, null, CancellationToken.None);
    Req(!rs.Success && rs.Conflicts.Count == 1 && rs.Conflicts[0].CurrentSha256 == mod, $"conflictos={rs.Conflicts.Count}: {rs.Message}");
    Req(Hashing.Sha256File(victim) == mod, "se sobrescribió el archivo en conflicto");
    Req(NotResult(g).Count == 1, "se tocaron otros archivos");
    Req(GameValidator.Analyze(g, pkg).HasBackup, "se borró el respaldo");
    var rs2 = await Restorer.RestoreAsync(g, null, CancellationToken.None, overwriteConflicts: true);
    Req(rs2.Success && NotOriginal(g).Count == 0, rs2.Message);
});

await Run("10. Menús ya en español (versión previa del usuario): instala y el respaldo guarda esos bytes", async () =>
{
    var g = MakeGame("parcial");
    var cand = Path.Combine(Trabajo, "traduccion", "candidato_menu", "message.json.e");
    var msg = Abs(g, "MASTER/ENG/fixed_data/message/message.json.e");
    File.Copy(cand, msg, true);
    var shaCand = Hashing.Sha256File(msg);
    var rep = GameValidator.Analyze(g, pkg);
    Req(rep.State == GameState.Original && !rep.HasErrors, "estado " + rep.State);
    var res = await Installer.InstallAsync(g, pkg, null, CancellationToken.None);
    Req(res.Success, res.Message);
    // Los menús ya traducidos se conservan, así que el .e difiere de lo que sale «desde original»; el resto es idéntico.
    var nr = NotResult(g);
    Req(nr.Count == 1 && nr[0].EndsWith("message.json.e"), $"{nr.Count} archivos != resultado");
    Req(File.ReadAllText(Path.Combine(res.BackupDir, "instalacion.json")).Contains(Hashing.Sha256File(msg)), "instalacion.json no registra el hash real");
    Req(GameValidator.Analyze(g, pkg).State == GameState.TranslationInstalled, "Analyze tras instalar no es TranslationInstalled");
    var bj = System.Text.Json.JsonDocument.Parse(File.ReadAllText(Path.Combine(res.BackupDir, "respaldo.json")));
    Req(bj.RootElement.GetProperty("MASTER/ENG/fixed_data/message/message.json.e").GetProperty("sha256").GetString() == shaCand, "el respaldo no guarda el estado reconocido");
    Req(File.ReadAllText(Path.Combine(res.BackupDir, "instalacion.json")).Contains("instalado"), "instalacion.json sin estado");
    var rs = await Restorer.RestoreAsync(g, null, CancellationToken.None);
    Req(rs.Success && Hashing.Sha256File(msg) == shaCand, "no se devolvió el estado previo del usuario");
});

await Run("11. Ruta fuera de H:, permisos y espacio (comprobaciones reales)", async () =>
{
    var g = MakeGame("permisos");
    Req(!g.StartsWith("H:", StringComparison.OrdinalIgnoreCase), "ruta en H:");
    var r = GameValidator.Analyze(g, pkg);
    Req(r.Checks.Any(c => c.Id == "escritura" && c.Level == CheckLevel.Ok), "escritura");
    Req(r.Checks.Any(c => c.Id == "espacio" && c.Level == CheckLevel.Ok), "espacio");
    var fi = FolderInfo.Get(g); Req(fi != null && fi.FreeBytes > 0, "FolderInfo");
    await Task.CompletedTask;
});

Console.WriteLine(fails == 0 ? $"\nTODO EN VERDE ({sw.Elapsed.TotalSeconds:F1} s)" : $"\n{fails} ESCENARIO(S) FALLIDO(S)");
return fails == 0 ? 0 : 1;

sealed class Prog(Action<ProgressInfo>? on = null) : IProgress<ProgressInfo>
{
    public List<ProgressInfo> Items = [];
    public void Report(ProgressInfo v) { Items.Add(v); on?.Invoke(v); }
}
