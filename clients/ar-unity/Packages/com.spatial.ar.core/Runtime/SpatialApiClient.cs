// Cliente da API (SPEC-008). Nunca lanca por falha de rede/JSON: devolve ApiOutcome.
using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace Spatial.Ar.Core
{
    public sealed class SpatialApiClient
    {
        public const int MaxBodyChars = 64 * 1024;
        private const int DefaultRetryAfter = 1;
        private const int MaxRetryAfter = 300;

        private static readonly JsonSerializerSettings Json = new JsonSerializerSettings
        {
            DateParseHandling = DateParseHandling.None,        // datas ficam como string ISO
            MissingMemberHandling = MissingMemberHandling.Ignore,
            MaxDepth = 16,
        };

        private readonly IHttpTransport _transport;
        private readonly string _token;
        private readonly TimeSpan _timeout;

        public SpatialApiClient(IHttpTransport transport, string bearerToken, TimeSpan timeout)
        {
            _transport = transport ?? throw new ArgumentNullException(nameof(transport));
            _token = bearerToken ?? throw new ArgumentNullException(nameof(bearerToken));
            _timeout = timeout;
        }

        public Task<ApiResult<EquipmentDto>> ResolveMarkerAsync(string markerId, CancellationToken ct = default(CancellationToken))
        {
            if (!QrPayload.IsValidId(markerId, QrPayload.MaxMarkerLength))
                return Task.FromResult(ApiResult<EquipmentDto>.Fail(ApiOutcome.InvalidInput));
            return GetAsync<EquipmentDto>("/api/v1/spatial/markers/" + markerId, ct, ValidateEquipment);
        }

        public async Task<ApiResult<LiveData>> GetLiveAsync(string equipmentId, CancellationToken ct = default(CancellationToken))
        {
            if (!QrPayload.IsValidId(equipmentId, QrPayload.MaxEquipmentIdLength))
                return ApiResult<LiveData>.Fail(ApiOutcome.InvalidInput);

            var basePath = "/api/v1/equipment/" + equipmentId;
            var twinTask = GetAsync<TwinDto>(basePath + "/twin", ct, ValidateTwin);
            var alertsTask = GetAsync<List<AlertDto>>(basePath + "/alerts", ct, ValidateAlerts);
            await Task.WhenAll(twinTask, alertsTask).ConfigureAwait(false);

            var twin = twinTask.Result;
            var alerts = alertsTask.Result;
            // consistencia: so ha vista nova se AS DUAS chamadas deram certo
            if (!twin.IsOk) return ApiResult<LiveData>.Fail(twin.Outcome, twin.RetryAfterSeconds);
            if (!alerts.IsOk) return ApiResult<LiveData>.Fail(alerts.Outcome, alerts.RetryAfterSeconds);
            if (twin.Value.EquipmentId != equipmentId) return ApiResult<LiveData>.Fail(ApiOutcome.BadResponse);
            return ApiResult<LiveData>.Success(new LiveData(twin.Value, alerts.Value));
        }

        private async Task<ApiResult<T>> GetAsync<T>(string path, CancellationToken ct, Func<T, bool> validate) where T : class
        {
            HttpResponse response;
            try
            {
                response = await _transport.GetAsync(path, _token, _timeout, ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException) { throw; }
            catch (Exception) { return ApiResult<T>.Fail(ApiOutcome.NetworkError); }

            if (response == null) return ApiResult<T>.Fail(ApiOutcome.BadResponse);
            if (response.Error == TransportError.Timeout) return ApiResult<T>.Fail(ApiOutcome.Timeout);
            if (response.Error == TransportError.Network) return ApiResult<T>.Fail(ApiOutcome.NetworkError);

            switch (response.Status)
            {
                case 200: break;
                case 401: return ApiResult<T>.Fail(ApiOutcome.Unauthorized);
                case 404: return ApiResult<T>.Fail(ApiOutcome.NotFound);
                case 429: return ApiResult<T>.Fail(ApiOutcome.RateLimited, ClampRetryAfter(response.RetryAfterSeconds));
                default:
                    return ApiResult<T>.Fail(response.Status >= 500 && response.Status <= 599
                        ? ApiOutcome.ServerError : ApiOutcome.BadResponse);
            }

            if (string.IsNullOrEmpty(response.Body) || response.Body.Length > MaxBodyChars)
                return ApiResult<T>.Fail(ApiOutcome.BadResponse);
            try
            {
                var value = JsonConvert.DeserializeObject<T>(response.Body, Json);
                if (value == null || !validate(value)) return ApiResult<T>.Fail(ApiOutcome.BadResponse);
                return ApiResult<T>.Success(value);
            }
            catch (Exception) // JsonException, campo obrigatorio faltando, tipo errado...
            {
                return ApiResult<T>.Fail(ApiOutcome.BadResponse);
            }
        }

        private static int ClampRetryAfter(int? seconds)
            => seconds.HasValue && seconds.Value >= 1 ? Math.Min(seconds.Value, MaxRetryAfter) : DefaultRetryAfter;

        // --- validacao semantica: status entre os 5 conhecidos; ids no alfabeto seguro
        private static bool ValidateEquipment(EquipmentDto e)
            => QrPayload.IsValidId(e.Id, QrPayload.MaxEquipmentIdLength) && StatusParser.TryParse(e.Status, out _);

        private static bool ValidateTwin(TwinDto t)
        {
            if (!QrPayload.IsValidId(t.EquipmentId, QrPayload.MaxEquipmentIdLength)) return false;
            if (!StatusParser.TryParse(t.Status, out _) || t.Sensors == null || t.OfflineAfterSeconds < 1) return false;
            foreach (var s in t.Sensors) if (s == null) return false;
            return true;
        }

        private static bool ValidateAlerts(List<AlertDto> alerts)
        {
            foreach (var a in alerts) if (a == null) return false;
            return true;
        }
    }
}
