using System.IO;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using Minecraft;

const string pack = "All The Mods 10";
const string client = "minecraft-1.21.1-client.jar";
const string expectedSha1 = "30C73B1C5DA787909B2F73340419FDF13B9DEF88";
if (args.Length is < 1 or > 2 || (args.Length == 2 && args[1] != "--migration-only"))
    throw new ArgumentException("Pass an owned QA run directory, optionally with --migration-only.");
var migrationOnly = args.Length == 2;
var run = Path.GetFullPath(args[0]);
var directory = new DirectoryInfo(run);
if (directory.LinkTarget is not null || directory.Parent?.Name != "agent-runs" ||
    !File.Exists(Path.Combine(run, "RUN.json")))
    throw new ArgumentException("Expected a reserved QA directory under artifacts/agent-runs.");
var installation = Path.Combine(run, "installation");
var reportPath = Path.Combine(run, "report.json");
if (!migrationOnly && Directory.Exists(installation)) throw new IOException("QA installation must start empty.");
var paths = new AppPaths(installation);
paths.Ensure();
var canonical = paths.CombineUnderPacks(pack);
Directory.CreateDirectory(canonical);
var logger = new Logger(paths.LogFile);
using var handler = new PackAssets(run);
using var http = new HttpClient(handler);
using var runtimeHttp = new HttpClient();
using var runtime = new PackRuntimeService(paths, logger, runtimeHttp);
using var instances = new PackInstanceService(paths, logger);
using var timeout = new CancellationTokenSource(TimeSpan.FromMinutes(35));
var token = timeout.Token;
var report = migrationOnly
    ? JsonSerializer.Deserialize<Dictionary<string, object>>(File.ReadAllText(reportPath))!
    : new Dictionary<string, object>();
if (migrationOnly && (!report.TryGetValue("cleanOfficialRuntime", out var previousResult) ||
    previousResult is not JsonElement { ValueKind: JsonValueKind.String } result || result.GetString() != "PASS"))
    throw new IOException("Migration-only mode requires a completed clean runtime in this fixture.");

void Record(string key, object value)
{
    report[key] = value;
    File.WriteAllText(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine($"{key}: {value}");
}
void Require(bool condition, string message)
{
    if (!condition) throw new InvalidDataException(message);
}
void VerifyRuntime(PreparedRuntime prepared)
{
    Require(prepared.ProfileId == "neoforge-21.1.265" && File.Exists(prepared.JavaPath), "Wrong runtime.");
    using var jar = File.OpenRead(prepared.ClientJarPath);
    Require(Convert.ToHexString(SHA1.HashData(jar)) == expectedSha1, "Wrong official client digest.");
    Require(Path.GetFullPath(prepared.ClientJarPath).StartsWith(paths.SharedRuntime + Path.DirectorySeparatorChar,
        StringComparison.OrdinalIgnoreCase), "Client is not in shared runtime.");
}

try
{
    File.WriteAllText(Path.Combine(canonical, PortablePackSyncService.SourceMarkerFileName),
        """{"schemaVersion":1,"owner":"MarkZamore","repo":"All-The-Mods-10","tag":"pack-latest"}""");
    var sync = new PortablePackSyncService(paths, logger, http);
    var candidate = Path.Combine(run, "dist", "pack-manifest.json");
    handler.Manifest = candidate;
    if (!migrationOnly)
    {
        Record("cleanPackSync", (await sync.SyncAsync(pack, null, token)).Outcome.ToString());
        PortablePackSyncService.ValidateSnapshot(File.ReadAllText(candidate), canonical, token);
        await instances.PrepareAsync(pack, token);
        Require(!File.Exists(Path.Combine(canonical, client)), "Client was shipped by the candidate.");
    }
    var firstRuntime = await runtime.PrepareAsync(pack, null, token);
    VerifyRuntime(firstRuntime);
    Require(firstRuntime.Descriptor.ClientJar.Length == 0, "Candidate declared a client.");
    if (!migrationOnly) Record("cleanOfficialRuntime", "PASS");

    handler.Manifest = Path.Combine(run, "legacy.json");
    Record("legacyFixtureSync", (await sync.SyncAsync(pack, null, token)).Outcome.ToString());
    var legacyInstance = await instances.PrepareAsync(pack, token);
    Require(File.Exists(Path.Combine(canonical, client)), "Legacy package missing its managed client.");
    if (!migrationOnly) VerifyRuntime(await runtime.PrepareAsync(pack, null, token));

    var options = Path.Combine(legacyInstance.GameDirectory, "options.txt");
    var world = Path.Combine(legacyInstance.GameDirectory, "saves", "OfficialClientQa", "level.dat");
    Directory.CreateDirectory(Path.GetDirectoryName(world)!);
    File.WriteAllText(options, "fov:0.25\n");
    File.WriteAllText(world, "synthetic world sentinel");
    var sharedTimestamp = File.GetLastWriteTimeUtc(firstRuntime.ClientJarPath);

    handler.Manifest = candidate;
    using (var target = JsonDocument.Parse(File.ReadAllBytes(candidate)))
    {
        handler.InterruptAsset = target.RootElement.GetProperty("assets").EnumerateArray()
            .Single(asset => asset.GetProperty("covers").EnumerateArray().Any(path => path.GetString() == "portable-pack.json"))
            .GetProperty("name").GetString();
    }
    try { await sync.SyncAsync(pack, null, token); }
    catch (Exception error) when (error is HttpRequestException or IOException or InvalidOperationException) { }
    finally { handler.InterruptAsset = null; }
    Require(handler.Interrupted > 0, "Descriptor interruption was not exercised.");
    PortablePackSyncService.ValidateSnapshot(File.ReadAllText(Path.Combine(run, "legacy.json")), canonical, token);
    Record("interruptedUpdatePreservedLegacy", "PASS");
    Record("existingPackSync", (await sync.SyncAsync(pack, null, token)).Outcome.ToString());
    PortablePackSyncService.ValidateSnapshot(File.ReadAllText(candidate), canonical, token);
    await instances.PrepareAsync(pack, token);
    Require(!File.Exists(Path.Combine(canonical, client)) && !File.Exists(Path.Combine(legacyInstance.GameDirectory, client)),
        "Old client survived in the managed pack or instance.");
    Require(File.ReadAllText(options) == "fov:0.25\n" && File.ReadAllText(world) == "synthetic world sentinel",
        "Player data changed.");
    var updatedRuntime = await runtime.PrepareAsync(pack, null, token);
    VerifyRuntime(updatedRuntime);
    Require(updatedRuntime.Descriptor.ClientJar.Length == 0, "Updated descriptor still names a client.");
    Require(File.GetLastWriteTimeUtc(updatedRuntime.ClientJarPath) == sharedTimestamp, "Shared client was rewritten.");
    Record("managedRemovalAndPreservation", "PASS");
    Record("sharedOfficialClientReuse", "PASS");
    Record("clientSha1", expectedSha1.ToLowerInvariant());
    Record("status", "PASS");
}
catch (Exception error)
{
    Record("status", "FAIL");
    Record("error", error.Message);
    throw;
}

sealed class PackAssets(string run) : HttpMessageHandler
{
    public string Manifest { get; set; } = "";
    public string? InterruptAsset { get; set; }
    public int Interrupted;
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
    {
        var uri = request.RequestUri!;
        if (uri.Host != "github.com" ||
            !uri.AbsolutePath.StartsWith("/MarkZamore/All-The-Mods-10/releases/download/pack-latest/", StringComparison.Ordinal))
            throw new InvalidOperationException("Unexpected pack release request.");
        var name = Uri.UnescapeDataString(uri.Segments[^1]);
        if (Path.GetFileName(name) != name) throw new InvalidDataException("Invalid asset name.");
        var path = name == PortablePackSyncService.PackManifestAssetName
            ? Manifest : Path.Combine(run, "dist", "assets", name);
        var response = File.Exists(path)
            ? new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(name == InterruptAsset
                ? new BrokenDownload(path, () => Interlocked.Increment(ref Interrupted)) : File.OpenRead(path)) }
            : new HttpResponseMessage(HttpStatusCode.NotFound);
        return Task.FromResult(response);
    }
}


sealed class BrokenDownload(string path, Action interrupted)
    : FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read)
{
    public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken token = default)
    {
        if (Position == 0) return base.ReadAsync(buffer[..Math.Min(1, buffer.Length)], token);
        interrupted();
        throw new IOException("QA descriptor connection lost after the first byte.");
    }
}
