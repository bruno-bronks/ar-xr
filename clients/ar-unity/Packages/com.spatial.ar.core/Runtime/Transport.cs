using System;
using System.Threading;
using System.Threading.Tasks;

namespace Spatial.Ar.Core
{
    public enum TransportError { None, Network, Timeout }

    public sealed class HttpResponse
    {
        private HttpResponse(int status, string body, int? retryAfterSeconds, TransportError error)
        {
            Status = status; Body = body; RetryAfterSeconds = retryAfterSeconds; Error = error;
        }

        public int Status { get; }
        public string Body { get; }
        public int? RetryAfterSeconds { get; }
        public TransportError Error { get; }

        public static HttpResponse Ok(int status, string body, int? retryAfterSeconds = null)
            => new HttpResponse(status, body, retryAfterSeconds, TransportError.None);
        public static HttpResponse Network() => new HttpResponse(0, null, null, TransportError.Network);
        public static HttpResponse Timeout() => new HttpResponse(0, null, null, TransportError.Timeout);
    }

    /// <summary>Implementado na cola Unity com UnityWebRequest; nos testes, por um transporte falso.</summary>
    public interface IHttpTransport
    {
        Task<HttpResponse> GetAsync(string pathAndQuery, string bearerToken, TimeSpan timeout, CancellationToken ct);
    }

    /// <summary>Log do cliente. O nucleo so envia CODIGOS FIXOS (nunca token, URL, marker ou corpo) - REQ-AR-005.</summary>
    public interface IClientLog
    {
        void Info(string message);
    }

    public sealed class NullClientLog : IClientLog
    {
        public void Info(string message) { }
    }
}
