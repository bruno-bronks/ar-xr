// COLA UNITY - NAO COMPILADA NEM EXECUTADA NESTA MAQUINA (sem Unity). Ver clients/ar-unity/README.md.
// Implementa o IHttpTransport do nucleo com UnityWebRequest. Deve ser chamada na thread principal.
using System;
using System.Threading;
using System.Threading.Tasks;
using Spatial.Ar.Core;
using UnityEngine;
using UnityEngine.Networking;

namespace Spatial.Ar.Unity
{
    public sealed class UnityWebRequestTransport : IHttpTransport
    {
        private readonly string _baseUrl;

        public UnityWebRequestTransport(string baseUrl) { _baseUrl = baseUrl; }

        public async Task<HttpResponse> GetAsync(string pathAndQuery, string bearerToken, TimeSpan timeout, CancellationToken ct)
        {
            using (var request = UnityWebRequest.Get(_baseUrl + pathAndQuery))
            {
                request.SetRequestHeader("Authorization", "Bearer " + bearerToken);
                request.SetRequestHeader("Accept", "application/json");
                request.timeout = Mathf.Max(1, Mathf.CeilToInt((float)timeout.TotalSeconds));

                var operation = request.SendWebRequest();
                while (!operation.isDone)
                {
                    if (ct.IsCancellationRequested)
                    {
                        request.Abort();
                        throw new OperationCanceledException(ct);
                    }
                    await Task.Yield();   // volta na thread principal a cada quadro
                }

                if (request.result == UnityWebRequest.Result.ConnectionError || request.result == UnityWebRequest.Result.DataProcessingError)
                {
                    var timedOut = request.error != null && request.error.IndexOf("timeout", StringComparison.OrdinalIgnoreCase) >= 0;
                    return timedOut ? HttpResponse.Timeout() : HttpResponse.Network();
                }

                // Success ou ProtocolError (4xx/5xx): ha codigo HTTP e corpo
                int? retryAfter = null;
                var header = request.GetResponseHeader("Retry-After");
                if (!string.IsNullOrEmpty(header) && int.TryParse(header, out var seconds)) retryAfter = seconds;
                return HttpResponse.Ok((int)request.responseCode, request.downloadHandler != null ? request.downloadHandler.text : null, retryAfter);
            }
        }
    }
}
