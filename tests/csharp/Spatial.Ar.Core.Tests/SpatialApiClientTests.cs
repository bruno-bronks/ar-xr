// SPEC-008 A2 / A7 · REQ-AR-001, REQ-AR-003, REQ-AR-004: cliente da API contra JSON REAL gerado pela API.
using System;
using System.Threading.Tasks;
using Xunit;

namespace Spatial.Ar.Core.Tests
{
    public class SpatialApiClientTests
    {
        private const string Token = "demo-operator-a";

        private static (SpatialApiClient client, FakeTransport transport) Make()
        {
            var transport = new FakeTransport();
            return (new SpatialApiClient(transport, Token, TimeSpan.FromSeconds(5)), transport);
        }

        // --- fixtures reais ------------------------------------------------------------------

        [Fact]
        public async Task Resolves_marker_from_real_api_json()
        {
            var (client, transport) = Make();
            transport.Handler = _ => HttpResponse.Ok(200, Fixtures.Read("marker_ok.json"));

            var result = await client.ResolveMarkerAsync("QR-EQ-001");

            Assert.Equal(ApiOutcome.Ok, result.Outcome);
            Assert.Equal("EQ-001", result.Value.Id);
            Assert.Equal("Compressor de ar 01", result.Value.Name);
            Assert.Equal("CRITICAL", result.Value.Status);
            Assert.Equal("/api/v1/spatial/markers/QR-EQ-001", transport.Requests[0].Path);
            Assert.Equal(Token, transport.Requests[0].Token);
        }

        [Fact]
        public async Task Reads_critical_live_data_from_real_api_json()
        {
            var (client, transport) = Make();
            transport.Handler = p => p.EndsWith("/twin")
                ? HttpResponse.Ok(200, Fixtures.Read("twin_critical.json"))
                : HttpResponse.Ok(200, Fixtures.Read("alerts_critical.json"));

            var result = await client.GetLiveAsync("EQ-001");

            Assert.True(result.IsOk);
            Assert.Equal("CRITICAL", result.Value.Twin.Status);
            Assert.Equal(2, result.Value.Twin.Sensors.Count);
            Assert.Equal(101.0, result.Value.Twin.Sensors[0].Value);
            Assert.True(result.Value.Twin.Sensors[0].Valid);
            var alert = Assert.Single(result.Value.Alerts);
            Assert.Equal("temperature>crit", alert.Rule);
            Assert.Equal(100.0, alert.Limit);
        }

        [Theory]
        [InlineData("twin_unknown.json", "alerts_empty.json", "UNKNOWN", "EQ-003")]
        [InlineData("twin_offline.json", "alerts_offline.json", "OFFLINE", "EQ-002")]
        [InlineData("twin_bad_sensor.json", "alerts_empty.json", "UNKNOWN", "EQ-003")]
        public async Task Reads_unknown_offline_and_bad_sensor_data(string twin, string alerts, string status, string id)
        {
            var (client, transport) = Make();
            transport.Handler = p => HttpResponse.Ok(200, Fixtures.Read(p.EndsWith("/twin") ? twin : alerts));

            var result = await client.GetLiveAsync(id);

            Assert.True(result.IsOk);
            Assert.Equal(status, result.Value.Twin.Status);
        }

        [Fact]
        public async Task Sensors_without_data_keep_null_value_and_observed_at()
        {
            var (client, transport) = Make();
            transport.Handler = p => HttpResponse.Ok(200, Fixtures.Read(p.EndsWith("/twin") ? "twin_unknown.json" : "alerts_empty.json"));

            var result = await client.GetLiveAsync("EQ-003");

            Assert.All(result.Value.Twin.Sensors, s => { Assert.Null(s.Value); Assert.Null(s.ObservedAt); Assert.False(s.Valid); });
        }

        // --- mapeamento de erros -------------------------------------------------------------

        [Theory]
        [InlineData(401, ApiOutcome.Unauthorized)]
        [InlineData(404, ApiOutcome.NotFound)]
        [InlineData(500, ApiOutcome.ServerError)]
        [InlineData(503, ApiOutcome.ServerError)]
        [InlineData(400, ApiOutcome.BadResponse)]
        [InlineData(403, ApiOutcome.BadResponse)]
        [InlineData(302, ApiOutcome.BadResponse)]
        public async Task Maps_http_status_to_outcome(int status, ApiOutcome expected)
        {
            var (client, transport) = Make();
            transport.Handler = _ => HttpResponse.Ok(status, "{\"detail\":\"x\"}");

            Assert.Equal(expected, (await client.ResolveMarkerAsync("QR-EQ-001")).Outcome);
        }

        [Theory]
        [InlineData(7, 7)]
        [InlineData(null, 1)]
        [InlineData(0, 1)]
        [InlineData(-5, 1)]
        [InlineData(100000, 300)]
        public async Task Rate_limit_uses_a_clamped_retry_after(int? header, int expected)
        {
            var (client, transport) = Make();
            transport.Handler = _ => HttpResponse.Ok(429, Fixtures.Read("error_429.json"), header);

            var result = await client.ResolveMarkerAsync("QR-EQ-001");

            Assert.Equal(ApiOutcome.RateLimited, result.Outcome);
            Assert.Equal(expected, result.RetryAfterSeconds);
        }

        [Fact]
        public async Task Maps_transport_failures()
        {
            var (client, transport) = Make();
            transport.Handler = _ => HttpResponse.Timeout();
            Assert.Equal(ApiOutcome.Timeout, (await client.ResolveMarkerAsync("QR-EQ-001")).Outcome);
            transport.Handler = _ => HttpResponse.Network();
            Assert.Equal(ApiOutcome.NetworkError, (await client.ResolveMarkerAsync("QR-EQ-001")).Outcome);
            transport.Handler = _ => throw new InvalidOperationException("boom");
            Assert.Equal(ApiOutcome.NetworkError, (await client.ResolveMarkerAsync("QR-EQ-001")).Outcome);
            transport.Handler = _ => null;
            Assert.Equal(ApiOutcome.BadResponse, (await client.ResolveMarkerAsync("QR-EQ-001")).Outcome);
        }

        [Theory]
        [InlineData("")]
        [InlineData("not json")]
        [InlineData("[]")]
        [InlineData("null")]
        [InlineData("{}")]
        [InlineData("{\"id\":\"EQ-001\"}")]                                    // campos obrigatorios faltando
        [InlineData("{\"id\":\"EQ-001\",\"name\":\"n\",\"type\":\"t\",\"location\":\"l\",\"last_seen_at\":null,\"status\":\"BANANA\"}")]
        [InlineData("{\"id\":\"../x\",\"name\":\"n\",\"type\":\"t\",\"location\":\"l\",\"last_seen_at\":null,\"status\":\"NORMAL\"}")]
        public async Task Invalid_or_incomplete_bodies_are_bad_responses_never_exceptions(string body)
        {
            var (client, transport) = Make();
            transport.Handler = _ => HttpResponse.Ok(200, body);

            Assert.Equal(ApiOutcome.BadResponse, (await client.ResolveMarkerAsync("QR-EQ-001")).Outcome);
        }

        [Fact]
        public async Task Oversized_body_is_rejected()
        {
            var (client, transport) = Make();
            transport.Handler = _ => HttpResponse.Ok(200, new string(' ', SpatialApiClient.MaxBodyChars + 1));

            Assert.Equal(ApiOutcome.BadResponse, (await client.ResolveMarkerAsync("QR-EQ-001")).Outcome);
        }

        [Fact]
        public async Task Deeply_nested_json_is_a_bad_response()
        {
            var (client, transport) = Make();
            transport.Handler = _ => HttpResponse.Ok(200, new string('[', 2000) + new string(']', 2000));

            Assert.Equal(ApiOutcome.BadResponse, (await client.ResolveMarkerAsync("QR-EQ-001")).Outcome);
        }

        // --- validacao local (sem rede) --------------------------------------------------------

        [Theory]
        [InlineData("")]
        [InlineData("a b")]
        [InlineData("../../x")]
        [InlineData("QR-EQ-001?x=1")]
        public async Task Invalid_marker_never_reaches_the_network(string marker)
        {
            var (client, transport) = Make();

            var result = await client.ResolveMarkerAsync(marker);

            Assert.Equal(ApiOutcome.InvalidInput, result.Outcome);
            Assert.Empty(transport.Requests);
        }

        [Fact]
        public async Task Invalid_equipment_id_never_reaches_the_network()
        {
            var (client, transport) = Make();

            Assert.Equal(ApiOutcome.InvalidInput, (await client.GetLiveAsync("EQ/../x")).Outcome);
            Assert.Empty(transport.Requests);
        }

        // --- consistencia do ciclo ao vivo ----------------------------------------------------

        [Fact]
        public async Task A_live_cycle_is_all_or_nothing()
        {
            var (client, transport) = Make();
            transport.Handler = p => p.EndsWith("/twin")
                ? HttpResponse.Ok(200, Fixtures.Read("twin_critical.json"))
                : HttpResponse.Network();

            var result = await client.GetLiveAsync("EQ-001");

            Assert.Equal(ApiOutcome.NetworkError, result.Outcome);
            Assert.Null(result.Value);
        }

        [Fact]
        public async Task A_twin_for_a_different_equipment_is_rejected()
        {
            var (client, transport) = Make();
            transport.Handler = p => p.EndsWith("/twin")
                ? HttpResponse.Ok(200, Fixtures.Read("twin_critical.json"))   // diz EQ-001
                : HttpResponse.Ok(200, Fixtures.Read("alerts_empty.json"));

            Assert.Equal(ApiOutcome.BadResponse, (await client.GetLiveAsync("EQ-002")).Outcome);
        }

        [Fact]
        public async Task Unauthorized_on_either_call_wins()
        {
            var (client, transport) = Make();
            transport.Handler = p => p.EndsWith("/twin")
                ? HttpResponse.Ok(200, Fixtures.Read("twin_critical.json"))
                : HttpResponse.Ok(401, Fixtures.Read("error_401.json"));

            Assert.Equal(ApiOutcome.Unauthorized, (await client.GetLiveAsync("EQ-001")).Outcome);
        }

        [Fact]
        public void Constructor_rejects_null_arguments()
        {
            Assert.Throws<ArgumentNullException>(() => new SpatialApiClient(null, Token, TimeSpan.FromSeconds(1)));
            Assert.Throws<ArgumentNullException>(() => new SpatialApiClient(new FakeTransport(), null, TimeSpan.FromSeconds(1)));
        }
    }
}
