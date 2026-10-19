// SPEC-008 A5 / REQ-AR-001, REQ-AR-002, REQ-AR-003, REQ-AR-004, REQ-AR-005: driver completo (sessao + cliente) com transporte e relogio falsos.
using System;
using System.Linq;
using System.Threading.Tasks;
using Xunit;

namespace Spatial.Ar.Core.Tests
{
    public class SessionDriverTests
    {
        private const string Token = "demo-operator-a";

        private sealed class Rig
        {
            public readonly FakeTransport Transport = new FakeTransport();
            public readonly FakeClock Clock = new FakeClock();
            public readonly RecordingLog Log = new RecordingLog();
            public readonly MarkerSession Session = new MarkerSession();
            public readonly SessionDriver Driver;

            public Rig()
            {
                var client = new SpatialApiClient(Transport, Token, TimeSpan.FromSeconds(5));
                Driver = new SessionDriver(Session, client, Clock.Get, Log);
                Transport.Handler = path =>
                {
                    if (path.StartsWith("/api/v1/spatial/markers/QR-EQ-001")) return HttpResponse.Ok(200, Fixtures.Read("marker_ok.json"));
                    if (path.StartsWith("/api/v1/spatial/markers/")) return HttpResponse.Ok(404, Fixtures.Read("error_404.json"));
                    return HttpResponse.Ok(200, Fixtures.Read(path.EndsWith("/twin") ? "twin_critical.json" : "alerts_critical.json"));
                };
            }
        }

        [Fact]
        public async Task Scanning_a_valid_qr_ends_in_a_live_critical_overlay()
        {
            var rig = new Rig();

            rig.Driver.OnQrDetected("QR-EQ-001");
            await rig.Driver.WhenIdleAsync();

            Assert.Equal(Phase.Live, rig.Session.State.Phase);
            var vm = OverlayViewModel.Build(rig.Session.State, rig.Clock.Get(), new SessionOptions());
            Assert.Equal("Crítico", vm.StatusText);
            Assert.Equal(StatusColor.Red, vm.Color);
            Assert.Equal(3, rig.Transport.Requests.Count);          // marker + twin + alerts
            Assert.All(rig.Transport.Requests, r => Assert.Equal(Token, r.Token));
        }

        [Fact]
        public async Task Invalid_qr_makes_no_request_at_all()
        {
            var rig = new Rig();

            foreach (var raw in new[] { "", "https://evil", "QR EQ", "{\"a\":1}", null }) rig.Driver.OnQrDetected(raw);
            await rig.Driver.WhenIdleAsync();

            Assert.Empty(rig.Transport.Requests);
        }

        [Fact]
        public async Task Unknown_marker_is_rejected_without_requesting_equipment_data()
        {
            var rig = new Rig();

            rig.Driver.OnQrDetected("QR-NAO-EXISTE");
            await rig.Driver.WhenIdleAsync();

            Assert.Equal(Phase.Rejected, rig.Session.State.Phase);
            Assert.Single(rig.Transport.Requests);
        }

        [Fact]
        public async Task Ticks_poll_every_two_seconds_but_only_one_request_pair_at_a_time()
        {
            var rig = new Rig();
            rig.Driver.OnQrDetected("QR-EQ-001");
            await rig.Driver.WhenIdleAsync();
            var before = rig.Transport.Count("/api/v1/equipment/EQ-001/twin");

            rig.Clock.Advance(1); rig.Driver.Tick(); await rig.Driver.WhenIdleAsync();
            Assert.Equal(before, rig.Transport.Count("/api/v1/equipment/EQ-001/twin"));   // ainda cedo

            rig.Clock.Advance(1.1); rig.Driver.Tick(); rig.Driver.Tick(); rig.Driver.Tick();
            await rig.Driver.WhenIdleAsync();
            Assert.Equal(before + 1, rig.Transport.Count("/api/v1/equipment/EQ-001/twin"));
        }

        [Fact]
        public async Task Connection_loss_keeps_the_last_view_and_marks_it_stale_then_recovers()
        {
            var rig = new Rig();
            rig.Driver.OnQrDetected("QR-EQ-001");
            await rig.Driver.WhenIdleAsync();
            var good = rig.Transport.Handler;

            rig.Transport.Handler = _ => HttpResponse.Network();
            for (var i = 0; i < 4; i++) { rig.Clock.Advance(2.1); rig.Driver.Tick(); await rig.Driver.WhenIdleAsync(); }
            var offline = OverlayViewModel.Build(rig.Session.State, rig.Clock.Get(), new SessionOptions());
            Assert.True(offline.IsStale);
            Assert.StartsWith("Sem conexão com o servidor", offline.Banner);
            Assert.Equal("Crítico", offline.StatusText);

            rig.Transport.Handler = good;
            rig.Clock.Advance(2.1); rig.Driver.Tick(); await rig.Driver.WhenIdleAsync();
            var back = OverlayViewModel.Build(rig.Session.State, rig.Clock.Get(), new SessionOptions());
            Assert.False(back.IsStale);
            Assert.Null(back.Banner);
        }

        [Fact]
        public async Task Unauthorized_stops_all_further_requests()
        {
            var rig = new Rig();
            rig.Transport.Handler = _ => HttpResponse.Ok(401, Fixtures.Read("error_401.json"));
            rig.Driver.OnQrDetected("QR-EQ-001");
            await rig.Driver.WhenIdleAsync();
            var count = rig.Transport.Requests.Count;

            rig.Clock.Advance(30); rig.Driver.Tick(); rig.Driver.OnQrDetected("QR-EQ-002");
            await rig.Driver.WhenIdleAsync();

            Assert.Equal(Phase.AuthError, rig.Session.State.Phase);
            Assert.Equal(count, rig.Transport.Requests.Count);
        }

        [Fact]
        public async Task Rate_limit_honours_retry_after_before_scanning_again()
        {
            var rig = new Rig();
            rig.Transport.Handler = _ => HttpResponse.Ok(429, Fixtures.Read("error_429.json"), 8);
            rig.Driver.OnQrDetected("QR-EQ-001");
            await rig.Driver.WhenIdleAsync();

            rig.Clock.Advance(5); rig.Driver.OnQrDetected("QR-EQ-002"); await rig.Driver.WhenIdleAsync();
            Assert.Single(rig.Transport.Requests);                           // ainda esperando

            rig.Clock.Advance(3.1); rig.Driver.Tick(); rig.Driver.OnQrDetected("QR-EQ-002"); await rig.Driver.WhenIdleAsync();
            Assert.Equal(2, rig.Transport.Requests.Count);
        }

        [Fact]
        public async Task A_slow_response_for_the_previous_marker_cannot_overwrite_the_new_equipment()
        {
            var rig = new Rig();
            var gate = new TaskCompletionSource<bool>();
            rig.Transport.Gate = path => path.EndsWith("QR-EQ-001") ? gate.Task : Task.CompletedTask;
            rig.Transport.Handler = path =>
            {
                if (path.EndsWith("QR-EQ-001")) return HttpResponse.Ok(200, Fixtures.Read("marker_ok.json"));
                return HttpResponse.Ok(404, Fixtures.Read("error_404.json"));
            };

            rig.Driver.OnQrDetected("QR-EQ-001");            // resposta travada
            rig.Clock.Advance(1.5);
            rig.Driver.OnQrDetected("QR-EQ-777");            // troca de QR (desconhecido)
            await Task.Delay(50);
            gate.SetResult(true);                            // so agora a antiga chega
            await rig.Driver.WhenIdleAsync();

            Assert.Equal(Phase.Rejected, rig.Session.State.Phase);
            Assert.Null(rig.Session.State.Equipment);
            Assert.Null(rig.Session.State.LastView);
        }

        [Fact]
        public async Task The_log_never_contains_token_marker_body_or_urls()
        {
            var rig = new Rig();

            rig.Driver.OnQrDetected("QR-EQ-001");
            await rig.Driver.WhenIdleAsync();
            rig.Driver.OnQrDetected("QR-NAO-EXISTE-SECRETO");
            rig.Clock.Advance(1.5);
            rig.Driver.OnQrDetected("QR-NAO-EXISTE-SECRETO");
            await rig.Driver.WhenIdleAsync();

            Assert.NotEmpty(rig.Log.Lines);
            foreach (var line in rig.Log.Lines)
            {
                Assert.DoesNotContain(Token, line);
                Assert.DoesNotContain("QR-", line);
                Assert.DoesNotContain("EQ-001", line);
                Assert.DoesNotContain("http", line, StringComparison.OrdinalIgnoreCase);
                Assert.DoesNotContain("Compressor", line);
                Assert.DoesNotContain("{", line);
            }
        }

        [Fact]
        public async Task A_throwing_log_or_transport_never_crashes_the_driver()
        {
            var rig = new Rig();
            rig.Transport.Handler = _ => throw new InvalidOperationException("boom");

            rig.Driver.OnQrDetected("QR-EQ-001");
            await rig.Driver.WhenIdleAsync();

            Assert.Equal(Phase.ResolveFailed, rig.Session.State.Phase);
            Assert.True(rig.Log.Lines.Any());
        }
    }
}
