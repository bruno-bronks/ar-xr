namespace Spatial.Ar.Core
{
    public enum ApiOutcome
    {
        Ok,
        InvalidInput,   // rejeitado localmente, SEM requisicao
        NotFound,       // 404 (desconhecido == de outra organizacao: indistinguiveis)
        Unauthorized,   // 401
        RateLimited,    // 429
        ServerError,    // 5xx
        NetworkError,
        Timeout,
        BadResponse     // JSON invalido, campos faltando, status desconhecido, corpo grande demais, 4xx inesperado
    }

    public sealed class ApiResult<T>
    {
        private ApiResult(ApiOutcome outcome, T value, int retryAfterSeconds)
        {
            Outcome = outcome; Value = value; RetryAfterSeconds = retryAfterSeconds;
        }

        public ApiOutcome Outcome { get; }
        public T Value { get; }
        public int RetryAfterSeconds { get; }
        public bool IsOk => Outcome == ApiOutcome.Ok;

        public static ApiResult<T> Success(T value) => new ApiResult<T>(ApiOutcome.Ok, value, 0);
        public static ApiResult<T> Fail(ApiOutcome outcome, int retryAfterSeconds = 0)
            => new ApiResult<T>(outcome, default(T), retryAfterSeconds);
    }
}
