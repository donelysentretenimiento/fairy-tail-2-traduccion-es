namespace FT2ES.Engine;

/// <summary>Desinstalación: devuelve los archivos originales desde la copia de seguridad, sin pisar cambios de terceros.</summary>
public static class Restorer
{
    /// <summary>
    /// Restaura los originales. Si algún archivo actual no coincide ni con el original ni con la traducción instalada
    /// (cambio de terceros), devuelve la lista de conflictos y no toca nada salvo que <paramref name="overwriteConflicts"/> sea true.
    /// El respaldo solo se elimina tras verificar los hashes de todo lo restaurado.
    /// </summary>
    public static Task<RestoreResult> RestoreAsync(string gamePath, IProgress<ProgressInfo>? progress, CancellationToken ct, bool overwriteConflicts = false)
        => Task.Run(() => Run(gamePath, progress, ct, overwriteConflicts), CancellationToken.None);

    private static RestoreResult Fail(string msg, string dir, bool cancelled = false, List<RestoreConflict>? c = null)
        => new() { Success = false, Message = msg, BackupDir = dir, Cancelled = cancelled, Conflicts = c ?? [] };

    private static RestoreResult Run(string gamePath, IProgress<ProgressInfo>? progress, CancellationToken ct, bool overwrite)
    {
        var game = Path.GetFullPath(gamePath);
        var st = BackupStore.Open(game);
        if (!st.Exists || st.Respaldo.Count == 0) return Fail("No hay copia de seguridad de esta instalación del juego: no hay nada que restaurar.", st.Dir);
        if (Directory.Exists(game) == false) return Fail("La carpeta del juego no existe.", st.Dir);
        st.Log("=== Restauración solicitada");
        try
        {
            if (st.RecoverPending(out var rf) && rf.Count > 0) return Fail("Una instalación interrumpida no se pudo revertir: " + rf[0], st.Dir);
            long all = st.Respaldo.Values.Sum(v => v.Size);
            var tr = new Tracker(progress, 4.0 * all);
            int n = st.Respaldo.Count, i = 0;

            // 1) integridad del respaldo
            var bad = st.VerifyIntegrity((f, b) => { tr.Add(b); tr.Report(ProgressPhase.Verification, "Verificación", "Comprobando la copia de seguridad…", f, ++i, n); ct.ThrowIfCancellationRequested(); });
            if (bad.Count > 0)
            {
                st.Log("Respaldo dañado: " + bad[0]);
                return Fail($"La copia de seguridad está dañada ({bad[0]}). No se restaura nada para no empeorar la situación; verifica los archivos desde Steam.", st.Dir);
            }

            // 2) clasificación: ya original / traducido por nosotros / conflicto
            var resultado = st.Info?.Resultado ?? [];
            var toRestore = new List<string>(); var conflicts = new List<RestoreConflict>();
            foreach (var (rel, h) in st.Respaldo)
            {
                var p = GameValidator.Abs(game, rel);
                if (!File.Exists(p)) { toRestore.Add(rel); continue; }
                var cur = Hashing.Sha256File(p);
                if (cur == h.Sha256) continue;
                if (resultado.TryGetValue(rel, out var r) && cur == r) toRestore.Add(rel);
                else { conflicts.Add(new RestoreConflict(rel, cur)); toRestore.Add(rel); }
            }
            tr.Add(all);
            if (conflicts.Count > 0 && !overwrite)
            {
                st.Log($"Conflictos: {conflicts.Count}; no se restaura nada.");
                return Fail($"{conflicts.Count} archivos han sido modificados por otro programa desde la instalación (por ejemplo {conflicts[0].RelPath}). No se han tocado; confirma si quieres sobrescribirlos.", st.Dir, false, conflicts);
            }

            // 3) restaurar solo lo afectado, con verificación
            int d = 0;
            foreach (var rel in toRestore)
            {
                ct.ThrowIfCancellationRequested();
                tr.Report(ProgressPhase.Restoring, "Restauración", "Devolviendo los archivos originales…", rel, d, toRestore.Count);
                FileUtil.CopyVerified(st.PathOf(rel), GameValidator.Abs(game, rel), st.Respaldo[rel].Sha256, replace: true);
                st.Log("Restaurado: " + rel);
                tr.Add(2.0 * st.Respaldo[rel].Size);
                tr.Report(ProgressPhase.Restoring, "Restauración", "Devolviendo los archivos originales…", rel, ++d, toRestore.Count);
            }

            // 4) verificación final de todo el respaldo y solo entonces se limpia
            int v = 0;
            foreach (var (rel, h) in st.Respaldo)
            {
                tr.Report(ProgressPhase.FinalValidation, "Validación final", "Comprobando la restauración…", rel, v++, n, false);
                if (Hashing.Sha256File(GameValidator.Abs(game, rel)) != h.Sha256) throw new InvalidDataException($"La verificación tras restaurar falló en {rel}.");
            }
            st.Log($"Restauración completada: {toRestore.Count} archivos. Se elimina la copia de seguridad.");
            try { Directory.Delete(st.FilesDir, true); } catch { }
            foreach (var f in new[] { st.RespaldoPath, st.InstalacionPath, st.DiarioPath }) try { File.Delete(f); } catch { }
            try { Directory.Delete(st.WorkDir, true); } catch { }
            tr.Finish(ProgressPhase.Done, "Terminado", "Restauración completada.", toRestore.Count);
            return new RestoreResult { Success = true, Message = "Se han restaurado los archivos originales y se ha verificado.", FilesRestored = toRestore.Count, BackupDir = st.Dir, Conflicts = conflicts };
        }
        catch (OperationCanceledException)
        {
            st.Log("Restauración cancelada.");
            return Fail("Restauración cancelada. Los archivos ya restaurados son originales válidos; puedes repetirla cuando quieras.", st.Dir, true);
        }
        catch (Exception ex)
        {
            st.Log("ERROR en la restauración: " + ex.Message);
            return Fail("No se pudo completar la restauración: " + ex.Message + " La copia de seguridad se conserva.", st.Dir);
        }
    }
}
