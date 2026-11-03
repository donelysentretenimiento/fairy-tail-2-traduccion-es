using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using FT2ES.Engine;
using Microsoft.Web.WebView2.Core;
using Microsoft.Win32;

namespace FT2ES.App;

/// <summary>
/// Ventana principal. La interfaz (HTML/CSS/JS) solo muestra estado y envía órdenes; TODA operación crítica
/// (comprobación, respaldo, parcheo, restauración, hashes) la ejecuta el motor nativo <c>FT2ES.Engine</c>.
/// </summary>
public partial class MainWindow : Window
{
    private readonly string _trabajo = Path.Combine(Path.GetTempPath(), "FT2ES_" + Environment.ProcessId);
    private PatchPackage? _pkg;
    private CancellationTokenSource? _cts;
    private bool _ocupado;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += async (_, _) => await IniciarAsync();
        Closing += (s, e) =>
        {
            if (_ocupado && MessageBox.Show(this, "Hay una operación en curso. Si cierras ahora se cancelará y se revertirá de forma segura. ¿Quieres cancelarla?", "FAIRY TAIL 2 — Traducción", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) { e.Cancel = true; return; }
            _cts?.Cancel();
        };
        Closed += (_, _) => { try { Directory.Delete(_trabajo, true); } catch { /* temporal */ } };
    }

    // ---------- arranque ----------
    private async Task IniciarAsync()
    {
        try
        {
            Directory.CreateDirectory(_trabajo);
            ExtraerRecursos();
            EngineConfig.GustEncPath = Path.Combine(_trabajo, "gust_enc.exe");
            _pkg = PatchPackage.Load(Path.Combine(_trabajo, "paquete.zip"));
            var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(_trabajo, "wv2"));
            await web.EnsureCoreWebView2Async(env);
            var s = web.CoreWebView2.Settings;
            s.IsNonClientRegionSupportEnabled = true;   // permite arrastrar la ventana desde la barra dibujada en HTML (app-region: drag)
            s.AreDevToolsEnabled = false; s.AreDefaultContextMenusEnabled = false; s.IsZoomControlEnabled = false; s.IsStatusBarEnabled = false; s.AreBrowserAcceleratorKeysEnabled = false;
            web.CoreWebView2.SetVirtualHostNameToFolderMapping("ft2es.local", Path.Combine(_trabajo, "ui"), CoreWebView2HostResourceAccessKind.Allow);
            web.CoreWebView2.WebMessageReceived += (_, e) => _ = ProcesarAsync(e.WebMessageAsJson);
            web.CoreWebView2.Navigate("https://ft2es.local/index.html");
        }
        catch (WebView2RuntimeNotFoundException)
        {
            MessageBox.Show(this, "Falta el componente «Microsoft Edge WebView2 Runtime», necesario para mostrar la interfaz.\n\nEstá incluido en Windows 11. En Windows 10 puedes instalarlo gratis desde microsoft.com/edge/webview2.", "FAIRY TAIL 2 — Traducción", MessageBoxButton.OK, MessageBoxImage.Error);
            Close();
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, "No se pudo iniciar el instalador:\n" + ex.Message, "FAIRY TAIL 2 — Traducción", MessageBoxButton.OK, MessageBoxImage.Error);
            Close();
        }
    }

    private void ExtraerRecursos()
    {
        var asm = Assembly.GetExecutingAssembly();
        foreach (var nombre in asm.GetManifestResourceNames())
        {
            if (nombre.EndsWith(".g.resources", StringComparison.OrdinalIgnoreCase)) continue;
            var destino = Path.Combine(_trabajo, nombre.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(destino)!);
            using var src = asm.GetManifestResourceStream(nombre)!;
            using var dst = File.Create(destino);
            src.CopyTo(dst);
        }
    }

    // ---------- puente JS <-> motor ----------
    private void Enviar(object msg) => Dispatcher.BeginInvoke(() => web.CoreWebView2?.PostWebMessageAsJson(JsonSerializer.Serialize(msg)));

    private async Task ProcesarAsync(string json)
    {
        try
        {
            var texto = JsonDocument.Parse(json).RootElement;
            using var doc = JsonDocument.Parse(texto.ValueKind == JsonValueKind.String ? texto.GetString()! : json);
            var r = doc.RootElement; var cmd = r.GetProperty("cmd").GetString();
            string Ruta() => r.TryGetProperty("path", out var p) ? (p.GetString() ?? "") : "";
            switch (cmd)
            {
                case "init": await Task.Run(Init); break;
                case "browse": Examinar(r.TryGetProperty("actual", out var a) ? a.GetString() : null); break;
                case "analyze": await Task.Run(() => Analizar(Ruta())); break;
                case "install": await InstalarAsync(Ruta()); break;
                case "restore": await RestaurarAsync(Ruta(), r.TryGetProperty("overwrite", out var o) && o.GetBoolean()); break;
                case "cancel": _cts?.Cancel(); break;
                case "openFolder": if (Directory.Exists(Ruta())) Process.Start(new ProcessStartInfo("explorer.exe", $"\"{Ruta()}\"") { UseShellExecute = true }); break;
                case "launchGame": { var exe = Path.Combine(Ruta(), "FAIRY_TAIL_2.exe"); if (File.Exists(exe)) Process.Start(new ProcessStartInfo(exe) { WorkingDirectory = Ruta(), UseShellExecute = true }); break; }
                case "exit": await Dispatcher.InvokeAsync(Close); break;
                case "close": await Dispatcher.InvokeAsync(Close); break;   // la confirmación de «operación en curso» está en Closing
                case "minimize": await Dispatcher.InvokeAsync(() => WindowState = WindowState.Minimized); break;
            }
        }
        catch (Exception ex) { Enviar(new { type = "error", message = "Error inesperado: " + ex.Message }); }
    }

    private void Init()
    {
        var cand = GameLocator.FindCandidates();
        Enviar(new
        {
            type = "init",
            version = _pkg!.Version,
            detected = cand.Select(c => c.Path).ToArray(),
            hasBackups = cand.Any(c => c.Report?.HasBackup == true),
        });
    }

    private void Examinar(string? actual)
    {
        Dispatcher.Invoke(() =>
        {
            var dlg = new OpenFolderDialog { Title = "Selecciona la carpeta principal de FAIRY TAIL 2", Multiselect = false };
            if (!string.IsNullOrWhiteSpace(actual) && Directory.Exists(actual)) dlg.InitialDirectory = actual;
            var ok = dlg.ShowDialog(this) == true;
            Enviar(new { type = "browse", path = ok ? dlg.FolderName : "" });
        });
    }

    private void Analizar(string ruta)
    {
        var rep = GameValidator.Analyze(ruta, _pkg!);
        Enviar(new
        {
            type = "analysis", path = ruta, state = rep.State.ToString(), hasBackup = rep.HasBackup, canInstall = rep.CanInstall,
            checks = rep.Checks.Select(c => new { id = c.Id, level = c.Level.ToString(), message = c.Message }).ToArray(),
        });
    }

    private static object Prog(ProgressInfo p) => new { type = "progress", percent = p.Percent, phase = p.PhaseName, message = p.Message, file = p.CurrentFile, done = p.FilesDone, total = p.FilesTotal, canCancel = p.CanCancel };

    private async Task InstalarAsync(string ruta)
    {
        _cts = new CancellationTokenSource(); _ocupado = true;
        try
        {
            var res = await Installer.InstallAsync(ruta, _pkg!, new Progress<ProgressInfo>(p => Enviar(Prog(p))), _cts.Token);
            Enviar(new { type = "done", op = "install", success = res.Success, message = res.Message, files = res.FilesInstalled, backupDir = res.BackupDir });
        }
        finally { _ocupado = false; }
    }

    private async Task RestaurarAsync(string ruta, bool sobrescribir)
    {
        _cts = new CancellationTokenSource(); _ocupado = true;
        try
        {
            var res = await Restorer.RestoreAsync(ruta, new Progress<ProgressInfo>(p => Enviar(Prog(p))), _cts.Token, sobrescribir);
            Enviar(new { type = "done", op = "restore", success = res.Success, message = res.Message, files = res.FilesRestored, backupDir = res.BackupDir, conflicts = res.Conflicts.Select(c => c.RelPath).ToArray() });
        }
        finally { _ocupado = false; }
    }
}
