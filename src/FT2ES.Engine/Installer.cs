namespace FT2ES.Engine;

/// <summary>Instalación segura y reversible de la traducción.</summary>
public static class Installer
{
    /// <summary>
    /// Instala la traducción. Verifica, respalda (nunca pisa un respaldo existente), construye todas las salidas en temporales,
    /// las sustituye atómicamente con diario y valida todos los hashes. Si se cancela o falla tras tocar archivos, revierte todo.
    /// </summary>
    public static Task<InstallResult> InstallAsync(string gamePath, PatchPackage pkg, IProgress<ProgressInfo>? progress, CancellationToken ct)
        => Task.Run(() => Run(gamePath, pkg, progress, ct), CancellationToken.None);

    private static InstallResult Fail(string msg, string dir, ValidationReport? rep = null, bool cancelled = false, bool rolled = false)
        => new() { Success = false, Message = msg, BackupDir = dir, Report = rep, Cancelled = cancelled, RolledBack = rolled };

    private static InstallResult Run(string gamePath, PatchPackage pkg, IProgress<ProgressInfo>? progress, CancellationToken ct)
    {
        var m = pkg.Manifest;
        var game = Path.GetFullPath(gamePath);
        var st = BackupStore.Open(game);
        if (Directory.Exists(st.Dir)) st.Log($"=== Instalación solicitada (versión {pkg.Version}) en {game}");

        // Recuperación de una instalación interrumpida antes de nada.
        if (st.RecoverPending(out var rf) && rf.Count > 0)
            return Fail("Una instalación anterior se interrumpió y no se pudo revertir del todo: " + rf[0], st.Dir);
        st.Reload();

        long Len(string rel) { try { return new FileInfo(GameValidator.Abs(game, rel)).Length; } catch { return 0; } }
        long sizeAll = m.Originales.Keys.Sum(Len);
        long sizeBuilt = m.Originales.Keys.Where(k => k.StartsWith("Motor/")).Sum(Len);
        long sizeMsg = Len(GameValidator.MsgRel);
        long sizeBackup = m.Originales.Keys.Where(k => !st.Respaldo.ContainsKey(k)).Sum(Len);
        var tr = new Tracker(progress, sizeAll + 2.0 * sizeBackup + 2.0 * sizeBuilt + 6.0 * sizeMsg + 2.0 * (sizeAll - sizeBuilt - sizeMsg) + 2.0 * sizeAll);
        int total = m.Originales.Count;

        // ---- Verificación ----
        int vdone = 0;
        tr.Report(ProgressPhase.Verification, "Verificación", "Comprobando la carpeta del juego…", "", 0, total);
        var rep = GameValidator.AnalyzeCore(game, pkg, (f, b) => { tr.Add(b); tr.Report(ProgressPhase.Verification, "Verificación", "Comprobando archivos del juego…", f, ++vdone, total); });
        if (!rep.CanInstall)
        {
            var why = rep.HasErrors ? rep.FirstError : "El estado de la carpeta no permite instalar.";
            if (Directory.Exists(st.Dir)) st.Log("Rechazada: " + why);
            return Fail(why, st.Dir, rep);
        }
        if (rep.State == GameState.TranslationInstalled && !rep.HasBackup)
            return new InstallResult { Success = true, Message = "La traducción ya estaba instalada; no se ha cambiado nada.", BackupDir = st.Dir, Report = rep };

        var tmps = new List<string>();
        JournalDto? journal = null;
        try
        {
            ct.ThrowIfCancellationRequested();
            st.Log($"Estado previo: {rep.State}");

            // ---- Copia de seguridad ----
            int bdone = 0;
            Directory.CreateDirectory(st.Dir);
            var info = st.Info ?? new InstallationInfo { EstadoPrevio = rep.State == GameState.KnownPartial ? "KnownPartial" : "Original" };
            foreach (var (rel, _) in m.Originales)
            {
                ct.ThrowIfCancellationRequested();
                if (st.Respaldo.ContainsKey(rel)) { bdone++; continue; }
                var src = GameValidator.Abs(game, rel);
                var sha = Hashing.Sha256File(src); // hash del archivo REAL del usuario: es el que se restaurará
                tr.Report(ProgressPhase.Backup, "Copia de seguridad", "Guardando copia de seguridad…", rel, bdone, total);
                FileUtil.CopyVerified(src, st.PathOf(rel), sha, replace: false);
                st.Respaldo[rel] = new FileHash(sha, new FileInfo(src).Length);
                tr.Add(2.0 * new FileInfo(src).Length);
                st.Log("Respaldado: " + rel);
                tr.Report(ProgressPhase.Backup, "Copia de seguridad", "Guardando copia de seguridad…", rel, ++bdone, total);
            }
            info.Version = pkg.Version; info.Fecha = DateTime.Now.ToString("o"); info.RutaJuego = game;
            // Sin hashes de referencia: se guarda el SHA-256 de lo que escribimos nosotros, tras construirlo.
            var expect = new Dictionary<string, string>();
            info.Resultado = []; info.Archivos = []; info.Estado = "en curso";
            st.SaveRespaldo(); st.SetInfo(info); st.SaveInfo();

            // ---- Parcheo y reconstrucción: todo a temporales junto al destino ----
            var outs = new List<string>();
            byte[] Base(string rel)
            {
                var b = File.ReadAllBytes(st.PathOf(rel));
                if (Hashing.Sha256(b) != st.Respaldo[rel].Sha256) throw new IOException($"La copia de seguridad de {rel} no es íntegra.");
                return b;
            }
            void Stage(string rel, byte[] data, Action? contentCheck = null)
            {
                var dest = GameValidator.Abs(game, rel);
                var tmp = dest + FileUtil.TmpExt;
                tmps.Add(tmp);
                File.WriteAllBytes(tmp, data);
                try { contentCheck?.Invoke(); }
                catch (Exception ex) when (ex is not OperationCanceledException) { throw new InvalidDataException($"El resultado de {rel} no es válido ({ex.Message}); no se ha modificado nada del juego."); }
                expect[rel] = Hashing.Sha256File(tmp);
                outs.Add(rel);
            }

            var langT = Base("Motor/root.texture.enUS.lang"); var langF = Base("Motor/root.font.enUS.lang");
            int pdone = 0, ptotal = m.Fdata.Count + 2;
            foreach (var (fd, recursos) in m.Fdata)
            {
                ct.ThrowIfCancellationRequested();
                var rel = "Motor/enUS/" + fd;
                tr.Report(ProgressPhase.Patching, "Parcheo", "Aplicando la traducción a los recursos gráficos…", rel, pdone, ptotal);
                var f = Base(rel);
                var ents = Fdata.Entries(f).ToDictionary(e => e.Name);
                var nuevos = new Dictionary<uint, byte[]>();
                foreach (var (nombre, parche) in recursos)
                {
                    uint nh = Convert.ToUInt32(nombre, 16);
                    var data = Diff.Apply(Fdata.DataOf(f, ents[nh]), pkg.ReadPatch(parche));
                    var orig = Fdata.DataOf(f, ents[nh]);
                    bool font = fd == m.FuenteFdata; // la fuente cambia de tamaño; las texturas deben conservar el suyo
                    if (data.Length < 4 || !data.AsSpan(0, 4).SequenceEqual(orig.AsSpan(0, 4)) || (!font && data.Length != orig.Length))
                        throw new InvalidDataException($"Resultado inesperado en el recurso {nombre} (longitud o cabecera no válidas); no se ha modificado nada del juego.");
                    nuevos[nh] = data;
                }
                var (nf, recs) = Fdata.Replace(f, nuevos);
                if (rel == "Motor/enUS/" + m.FuenteFdata || fd == m.FuenteFdata) langF = Fdata.UpdateLang(langF, recs); else langT = Fdata.UpdateLang(langT, recs);
                Stage(rel, nf, () =>
                {
                    var re = Fdata.Entries(nf);
                    if (re.Count != ents.Count) throw new InvalidDataException("número de recursos distinto");
                    foreach (var (k, d) in nuevos) if (!Fdata.DataOf(nf, re.First(x => x.Name == k)).AsSpan().SequenceEqual(d)) throw new InvalidDataException("recurso mal escrito");
                });
                tr.Add(2.0 * f.Length);
                tr.Report(ProgressPhase.Patching, "Parcheo", "Aplicando la traducción a los recursos gráficos…", rel, ++pdone, ptotal);
            }
            void LangOk(byte[] l, string rel) { if (l.Length % 12 != 0 || l.Length != st.Respaldo[rel].Size) throw new InvalidDataException("tamaño de .lang distinto"); }
            Stage("Motor/root.texture.enUS.lang", langT, () => LangOk(langT, "Motor/root.texture.enUS.lang"));
            Stage("Motor/root.font.enUS.lang", langF, () => LangOk(langF, "Motor/root.font.enUS.lang"));
            tr.Add(2.0 * (langT.Length + langF.Length));

            // textos
            ct.ThrowIfCancellationRequested();
            const string msgRel = GameValidator.MsgRel;
            tr.Report(ProgressPhase.Rebuild, "Reconstrucción", "Reconstruyendo los textos del juego…", msgRel, 0, 1 + 0);
            var codec = EngineConfig.TextCodec ?? new GustEncCodec(EngineConfig.FindGustEnc() ?? throw new FileNotFoundException("No se encuentra gust_enc.exe."));
            Directory.CreateDirectory(st.WorkDir);
            var items = MessageJson.Read(codec.Decrypt(Base(msgRel), st.WorkDir, ct));
            tr.Add(2.0 * sizeMsg);
            tr.Report(ProgressPhase.Rebuild, "Reconstrucción", "Reconstruyendo los textos del juego…", msgRel, 0, 1);
            int nt = 0;
            for (int i = 0; i < items.Count; i++)
                if (pkg.Texts.TryGetValue(items[i].Label, out var es)) { items[i] = (items[i].Label, es); nt++; }
            var enc = codec.Encrypt(MessageJson.Write(items), st.WorkDir, ct);
            tr.Add(4.0 * sizeMsg);
            Stage(msgRel, enc, () =>
            {
                var back = MessageJson.Read(codec.Decrypt(enc, st.WorkDir, ct));
                if (back.Count != items.Count || back.Where((b, i) => b != items[i]).Any()) throw new InvalidDataException("Los textos reconstruidos no coinciden con los esperados.");
            });
            st.Log($"Textos: {nt} mensajes");

            // diálogos
            var porf = new SortedDictionary<string, Dictionary<int, string>>(StringComparer.Ordinal);
            foreach (var (k, es) in pkg.Dialogs)
            {
                int h = k.LastIndexOf('#');
                var nombre = k[..h];
                if (!porf.TryGetValue(nombre, out var d)) porf[nombre] = d = [];
                d[int.Parse(k[(h + 1)..])] = es;
            }
            int edone = 0;
            foreach (var (nombre, lin) in porf)
            {
                ct.ThrowIfCancellationRequested();
                var rel = $"MASTER/ENG/EventMessageData/EVENT_MESSAGE_{nombre}.ebm";
                if (!m.Originales.ContainsKey(rel)) throw new InvalidDataException($"El paquete incluye un diálogo ({rel}) que no figura en el manifiesto.");
                var raw = Base(rel);
                var (recs, cola) = Ebm.Parse(raw);
                foreach (var (i, es) in lin)
                    if (i < recs.Count && recs[i].T.Length > 0) recs[i].T = System.Text.Encoding.UTF8.GetBytes(es);
                var built = Ebm.Build(recs, cola);
                Stage(rel, built, () => { var (r2, c2) = Ebm.Parse(built); if (r2.Count != recs.Count || !c2.SequenceEqual(cola)) throw new InvalidDataException("diálogos mal escritos"); });
                tr.Add(2.0 * raw.Length);
                tr.Report(ProgressPhase.Rebuild, "Reconstrucción", "Reconstruyendo los diálogos…", rel, ++edone, porf.Count);
            }
            // Ficheros del manifiesto que nuestro paquete no genera: se rechaza antes de tocar nada.
            var missingOut = m.Originales.Keys.Except(outs).ToList();
            if (missingOut.Count > 0) throw new InvalidDataException($"El paquete no genera {missingOut.Count} archivos del manifiesto (p. ej. {missingOut[0]}).");

            info.Resultado = new Dictionary<string, string>(expect); st.SaveInfo();

            // ---- Aplicación (sustitución atómica con diario) ----
            journal = new JournalDto { Entradas = outs.Select(o => new JournalEntry { Ruta = o }).ToList() };
            st.SaveJournal(journal);
            int adone = 0;
            foreach (var en in journal.Entradas)
            {
                ct.ThrowIfCancellationRequested();
                tr.Report(ProgressPhase.Applying, "Aplicación", "Instalando archivos traducidos…", en.Ruta, adone, outs.Count, canCancel: true);
                en.Estado = "iniciado"; st.SaveJournal(journal);
                var dest = GameValidator.Abs(game, en.Ruta);
                try { FileUtil.ReplaceFile(dest + FileUtil.TmpExt, dest); }
                catch { en.Estado = "sin-cambio"; st.SaveJournal(journal); throw; }
                en.Estado = "aplicado";
                tr.Add(Len(en.Ruta));
                st.Log("Instalado: " + en.Ruta);
                tr.Report(ProgressPhase.Applying, "Aplicación", "Instalando archivos traducidos…", en.Ruta, ++adone, outs.Count);
            }

            // ---- Validación final: re-hash de TODO lo escrito ----
            int fdone = 0;
            foreach (var rel in outs)
            {
                tr.Report(ProgressPhase.FinalValidation, "Validación final", "Comprobando la instalación…", rel, fdone, outs.Count, canCancel: false);
                if (Hashing.Sha256File(GameValidator.Abs(game, rel)) != expect[rel])
                    throw new InvalidDataException($"La validación final falló en {rel}.");
                tr.Add(Len(rel));
                fdone++;
            }
            foreach (var rel in outs) { var fi = new FileInfo(GameValidator.Abs(game, rel)); info.Archivos[rel] = new FileStamp { Size = fi.Length, Ticks = fi.LastWriteTimeUtc.Ticks }; }
            info.Estado = "instalado"; st.SaveInfo(); st.DeleteJournal();
            try { Directory.Delete(st.WorkDir, true); } catch { }
            st.Log($"Instalación completada: {outs.Count} archivos.");
            tr.Finish(ProgressPhase.Done, "Terminado", "Instalación completada.", outs.Count);
            return new InstallResult { Success = true, Message = "Instalación completada y verificada.", FilesInstalled = outs.Count, BackupDir = st.Dir, Report = rep };
        }
        catch (Exception ex)
        {
            bool cancelled = ex is OperationCanceledException;
            st.Log((cancelled ? "CANCELADO: " : "ERROR: ") + ex.Message);
            bool touched = journal != null && journal.Entradas.Any(e => e.Estado is "aplicado" or "iniciado");
            string tail = "";
            if (touched)
            {
                var fails = st.Rollback(journal!);
                if (fails.Count == 0) { st.DeleteJournal(); tail = " Se han restaurado los archivos originales y se ha verificado."; }
                else tail = " ATENCIÓN: no se pudieron restaurar todos los archivos (" + fails[0] + "). Usa «Restaurar» o verifica los archivos desde Steam.";
            }
            if (st.Info != null) { st.Info.Estado = "revertido"; try { st.SaveInfo(); } catch { } }
            var msg = cancelled ? "Instalación cancelada." + tail
                : "La instalación ha fallado y no ha dejado el juego a medias: " + ex.Message + tail;
            return Fail(msg, st.Dir, rep, cancelled, touched);
        }
        finally
        {
            foreach (var t in tmps) try { File.Delete(t); } catch { }
            try { if (Directory.Exists(st.WorkDir)) Directory.Delete(st.WorkDir, true); } catch { }
        }
    }
}
