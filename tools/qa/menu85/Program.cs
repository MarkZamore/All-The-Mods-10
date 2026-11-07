using System.IO;
using Minecraft;
using CmlLib.Core;
using CmlLib.Core.Auth;
using CmlLib.Core.Version;
using CmlLib.Core.ProcessBuilder;
var root = Path.GetFullPath(args[0]);
var source = Path.GetFullPath(args[1]);
var paths = new AppPaths(root); paths.Ensure();
var game = paths.CombineUnderInstances("All The Mods 10");
Directory.CreateDirectory(game);
foreach (var relative in new[] { "config", "kubejs", "mods", "defaultconfigs", "resourcepacks", "shaderpacks", "datapacks", "launcher" })
    foreach (var file in Directory.EnumerateFiles(Path.Combine(source, relative), "*", SearchOption.AllDirectories))
    {
        var dest = Path.Combine(game, Path.GetRelativePath(source, file)); Directory.CreateDirectory(Path.GetDirectoryName(dest)!); File.Copy(file, dest, true);
    }
File.WriteAllText(Path.Combine(game, "options.txt"), "onboardAccessibility:false\nlang:ru_ru\n");
var descriptor = PackManifestService.Load(source);
var java = args[2];
var client = Path.Combine(paths.SharedRuntime, "versions", "1.21.1", "1.21.1.jar");
var prepared = new PreparedRuntime(paths.CombineUnderRuntimes("All The Mods 10"), "neoforge-21.1.265", java, client, descriptor);
using var runtime = new PackRuntimeService(paths, new Logger(paths.LogFile));
var launcher = runtime.CreateLocalLauncher(prepared);
var profile = await launcher.GetVersionAsync(prepared.ProfileId);
var launchPath = new MinecraftPath(game) { Library = launcher.MinecraftPath.Library, Versions = launcher.MinecraftPath.Versions, Assets = launcher.MinecraftPath.Assets, Runtime = launcher.MinecraftPath.Runtime, Resource = launcher.MinecraftPath.Resource };
var options = new MLaunchOption
{
    Path = launchPath,
    JavaPath = java,
    Session = MSession.CreateOfflineSession("LocalQa"),
    MaximumRamMb = 12288,
    MinimumRamMb = 1024,
    FullScreen = false,
    ScreenWidth = 960,
    ScreenHeight = 540,
    ExtraJvmArguments = new List<MArgument> { new("-javaagent:" + Path.Combine(root, "observer.jar") + "=" + Path.Combine(root, "menu.json")), new("-Dmodernfix.config.mixin.perf.dynamic_resources=true"), new("-Dlog4j.configurationFile=config/log4j2.xml") }
};
using var process = launcher.BuildProcess(profile, options);
process.StartInfo.WorkingDirectory = game; process.StartInfo.UseShellExecute = false;
if (!process.Start()) throw new Exception("No process");
using var timeout = new CancellationTokenSource(TimeSpan.FromMinutes(20));
try { await process.WaitForExitAsync(timeout.Token); } finally { if (!process.HasExited) process.Kill(true); }
if (process.ExitCode != 0 || !File.Exists(Path.Combine(root, "menu.json"))) throw new Exception("Client did not pass menu acceptance.");
Console.WriteLine("PASS native title menu, normal exit");

