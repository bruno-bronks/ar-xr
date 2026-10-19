using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace Spatial.Ar.Core.Tests
{
    /// <summary>Transporte falso: respostas por caminho, com registro das requisicoes.</summary>
    public sealed class FakeTransport : IHttpTransport
    {
        public readonly List<(string Path, string Token)> Requests = new List<(string, string)>();
        public Func<string, HttpResponse> Handler = _ => HttpResponse.Network();
        public Func<string, Task> Gate;   // permite atrasar a resposta de um caminho

        public async Task<HttpResponse> GetAsync(string pathAndQuery, string bearerToken, TimeSpan timeout, CancellationToken ct)
        {
            lock (Requests) Requests.Add((pathAndQuery, bearerToken));
            if (Gate != null) await Gate(pathAndQuery).ConfigureAwait(false);
            return Handler(pathAndQuery);
        }

        public int Count(string prefix)
        {
            lock (Requests) { var n = 0; foreach (var r in Requests) if (r.Path.StartsWith(prefix, StringComparison.Ordinal)) n++; return n; }
        }
    }

    public sealed class FakeClock
    {
        public DateTimeOffset Now = new DateTimeOffset(2026, 10, 19, 12, 0, 0, TimeSpan.Zero);
        public DateTimeOffset Get() => Now;
        public void Advance(double seconds) => Now = Now.AddSeconds(seconds);
    }

    public sealed class RecordingLog : IClientLog
    {
        public readonly List<string> Lines = new List<string>();
        public void Info(string message) { lock (Lines) Lines.Add(message); }
    }

    public static class Fixtures
    {
        public static string Read(string name)
        {
            var path = Path.Combine(AppContext.BaseDirectory, "fixtures", name);
            return File.ReadAllText(path);
        }
    }
}
