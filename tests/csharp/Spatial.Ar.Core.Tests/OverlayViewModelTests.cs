// SPEC-008 A4 / REQ-AR-002, REQ-AR-003, REQ-AR-004: o overlay exibe o status do SERVIDOR; ausencia de dado nunca vira "normal".
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Xunit;

namespace Spatial.Ar.Core.Tests
{
    public class OverlayViewModelTests
    {
        private static readonly DateTimeOffset T0 = new DateTimeOffset(2026, 10, 19, 12, 0, 0, TimeSpan.Zero);
        private static DateTimeOffset At(double s) => T0.AddSeconds(s);
        private static readonly SessionOptions Opts = new SessionOptions();

        private static LiveData FromFixture(string twin, string alerts) => new LiveData(
            JsonConvert.DeserializeObject<TwinDto>(Fixtures.Read(twin)),
            JsonConvert.DeserializeObject<List<AlertDto>>(Fixtures.Read(alerts)));

        private static MarkerSession LiveWith(LiveData data, double pollAt = 1, string id = "EQ-001")
        {
            var s = new MarkerSession();
            s.OnQrDetected("QR-EQ-001", At(0));
            s.OnResolved("QR-EQ-001", ApiResult<EquipmentDto>.Success(
                new EquipmentDto { Id = id, Name = "Compressor de ar 01", Type = "t", Location = "l", Status = "NORMAL" }), At(0));
            s.OnPolled(id, ApiResult<LiveData>.Success(data), At(pollAt));
            return s;
        }

        private static OverlayViewModel Build(MarkerSession s, double now) => OverlayViewModel.Build(s.State, At(now), Opts);

        // --- fases sem equipamento ------------------------------------------------------------

        [Fact]
        public void Scanning_invites_the_operator_to_aim_at_a_qr()
        {
            var vm = Build(new MarkerSession(), 0);

            Assert.Equal("Aponte para o QR do equipamento", vm.Title);
            Assert.Equal(StatusColor.None, vm.Color);
            Assert.Null(vm.Banner);
            Assert.Empty(vm.SensorLines);
        }

        [Fact]
        public void Resolving_says_so()
        {
            var s = new MarkerSession();
            s.OnQrDetected("QR-EQ-001", At(0));

            Assert.Equal("Identificando equipamento…", Build(s, 0.2).Title);
        }

        [Fact]
        public void Rejected_shows_the_same_generic_message_for_every_not_found()
        {
            var s = new MarkerSession();
            s.OnQrDetected("QR-QUALQUER", At(0));
            s.OnResolved("QR-QUALQUER", ApiResult<EquipmentDto>.Fail(ApiOutcome.NotFound), At(0.1));

            var vm = Build(s, 0.5);

            Assert.Equal("Marcador não reconhecido", vm.Banner);
            Assert.DoesNotContain("QR-QUALQUER", vm.Banner + vm.Title);   // nunca ecoa o conteudo escaneado
            Assert.Empty(vm.SensorLines);
        }

        [Fact]
        public void Auth_error_asks_to_reauthenticate()
        {
            var s = new MarkerSession();
            s.OnQrDetected("QR-EQ-001", At(0));
            s.OnResolved("QR-EQ-001", ApiResult<EquipmentDto>.Fail(ApiOutcome.Unauthorized), At(0.1));

            Assert.Equal("Sessão inválida. Reautentique.", Build(s, 0.5).Banner);
        }

        [Fact]
        public void Rate_limit_shows_the_remaining_wait()
        {
            var s = new MarkerSession();
            s.OnQrDetected("QR-EQ-001", At(0));
            s.OnResolved("QR-EQ-001", ApiResult<EquipmentDto>.Fail(ApiOutcome.RateLimited, 10), At(0));

            Assert.Equal("Muitas leituras. Aguarde 10 s.", Build(s, 0).Banner);
            Assert.Equal("Muitas leituras. Aguarde 4 s.", Build(s, 6).Banner);
        }

        [Fact]
        public void Network_failure_while_resolving_says_no_connection()
        {
            var s = new MarkerSession();
            s.OnQrDetected("QR-EQ-001", At(0));
            s.OnResolved("QR-EQ-001", ApiResult<EquipmentDto>.Fail(ApiOutcome.NetworkError), At(0.1));

            Assert.Equal("Sem conexão com o servidor", Build(s, 0.5).Banner);
        }

        // --- estados do servidor (tabela da SPEC-008) -----------------------------------------

        [Theory]
        [InlineData("twin_critical.json", "alerts_critical.json", "Crítico", StatusColor.Red)]
        [InlineData("twin_unknown.json", "alerts_empty.json", "Desconhecido — dados insuficientes", StatusColor.Purple)]
        [InlineData("twin_offline.json", "alerts_offline.json", "Offline — sem dados recentes", StatusColor.Gray)]
        [InlineData("twin_bad_sensor.json", "alerts_empty.json", "Desconhecido — dados insuficientes", StatusColor.Purple)]
        public void Shows_the_servers_status_in_text_and_color(string twin, string alerts, string text, StatusColor color)
        {
            var s = LiveWith(FromFixture(twin, alerts), id: JsonConvert.DeserializeObject<TwinDto>(Fixtures.Read(twin)).EquipmentId);

            var vm = Build(s, 1.5);

            Assert.Equal(text, vm.StatusText);
            Assert.Equal(color, vm.Color);
            Assert.False(vm.IsStale);
            Assert.Null(vm.Banner);
        }

        [Theory]
        [InlineData("NORMAL", "Normal", StatusColor.Green)]
        [InlineData("WARNING", "Atenção", StatusColor.Amber)]
        [InlineData("CRITICAL", "Crítico", StatusColor.Red)]
        [InlineData("OFFLINE", "Offline — sem dados recentes", StatusColor.Gray)]
        [InlineData("UNKNOWN", "Desconhecido — dados insuficientes", StatusColor.Purple)]
        public void Maps_every_status_exactly(string status, string text, StatusColor color)
        {
            var twin = JsonConvert.DeserializeObject<TwinDto>(Fixtures.Read("twin_critical.json"));
            twin.Status = status;

            var vm = Build(LiveWith(new LiveData(twin, new List<AlertDto>())), 1.5);

            Assert.Equal(text, vm.StatusText);
            Assert.Equal(color, vm.Color);
        }

        [Fact]
        public void Only_the_normal_status_is_ever_green_and_only_it_says_normal()
        {
            foreach (var status in new[] { "WARNING", "CRITICAL", "OFFLINE", "UNKNOWN" })
            {
                var twin = JsonConvert.DeserializeObject<TwinDto>(Fixtures.Read("twin_critical.json"));
                twin.Status = status;
                var vm = Build(LiveWith(new LiveData(twin, new List<AlertDto>())), 1.5);

                Assert.NotEqual(StatusColor.Green, vm.Color);
                Assert.DoesNotContain("Normal", vm.StatusText);
            }
        }

        [Fact]
        public void Live_without_data_yet_is_never_green_or_normal()
        {
            var s = new MarkerSession();
            s.OnQrDetected("QR-EQ-001", At(0));
            s.OnResolved("QR-EQ-001", ApiResult<EquipmentDto>.Success(
                new EquipmentDto { Id = "EQ-001", Name = "Compressor de ar 01", Type = "t", Location = "l", Status = "NORMAL" }), At(0));

            var vm = Build(s, 0.5);   // o /markers dizia NORMAL, mas ainda nao ha twin

            Assert.Equal("Compressor de ar 01 (EQ-001)", vm.Title);
            Assert.Equal("Aguardando dados…", vm.StatusText);
            Assert.Equal(StatusColor.None, vm.Color);
            Assert.Equal("Carregando…", vm.Banner);
        }

        // --- detalhes ------------------------------------------------------------------------

        [Fact]
        public void Critical_overlay_lists_sensor_lines_and_alerts()
        {
            var vm = Build(LiveWith(FromFixture("twin_critical.json", "alerts_critical.json")), 1.5);

            Assert.Equal("Compressor de ar 01 (EQ-001)", vm.Title);
            Assert.Equal(new[]
            {
                "temperature: 101.0 celsius · limites 85.0/100.0 · 1 s",
                "vibration: 1.0 mm/s · limites 5.0/8.0 · 1 s",
            }, vm.SensorLines.ToArray());
            Assert.Equal(new[] { "Crítico · temperature>crit · 101.0 (limite 100.0)" }, vm.AlertLines.ToArray());
        }

        [Fact]
        public void Sensors_without_data_or_with_bad_quality_are_labelled()
        {
            var unknown = Build(LiveWith(FromFixture("twin_unknown.json", "alerts_empty.json"), id: "EQ-003"), 1.5);
            Assert.Equal(new[] { "temperature: sem dados", "vibration: sem dados" }, unknown.SensorLines.ToArray());

            var bad = Build(LiveWith(FromFixture("twin_bad_sensor.json", "alerts_empty.json"), id: "EQ-003"), 1.5);
            Assert.Contains("temperature: 50.0 celsius · limites 80.0/95.0 · 1 s · defeito · inválida", bad.SensorLines);
        }

        [Fact]
        public void Offline_overlay_has_the_offline_alert_and_no_stale_normal()
        {
            var vm = Build(LiveWith(FromFixture("twin_offline.json", "alerts_offline.json"), id: "EQ-002"), 1.5);

            Assert.Equal(new[] { "Offline · offline" }, vm.AlertLines.ToArray());
        }

        [Fact]
        public void Numbers_use_invariant_culture_regardless_of_the_device_locale()
        {
            var previous = System.Globalization.CultureInfo.CurrentCulture;
            System.Globalization.CultureInfo.CurrentCulture = new System.Globalization.CultureInfo("pt-BR");
            try
            {
                var vm = Build(LiveWith(FromFixture("twin_critical.json", "alerts_critical.json")), 1.5);
                Assert.Contains("101.0", vm.SensorLines[0]);
                Assert.DoesNotContain("101,0", vm.SensorLines[0]);
            }
            finally { System.Globalization.CultureInfo.CurrentCulture = previous; }
        }

        // --- desatualizado (D-017) -------------------------------------------------------------

        [Fact]
        public void Data_is_fresh_for_three_seconds_and_stale_after()
        {
            var s = LiveWith(FromFixture("twin_critical.json", "alerts_critical.json"), pollAt: 1);

            Assert.False(Build(s, 4.0).IsStale);          // exatamente 3 s: ainda fresco
            var stale = Build(s, 4.5);
            Assert.True(stale.IsStale);
            Assert.Equal(3, stale.StaleSeconds);
            Assert.Equal("DESATUALIZADO há 3 s", stale.Banner);
            Assert.Equal("Crítico", stale.StatusText);    // mantem o ULTIMO status do servidor, marcado
        }

        [Fact]
        public void Three_consecutive_failures_say_no_connection_and_keep_the_stale_view()
        {
            var s = LiveWith(FromFixture("twin_critical.json", "alerts_critical.json"), pollAt: 1);
            foreach (var i in new[] { 3, 5, 7 }) s.OnPolled("EQ-001", ApiResult<LiveData>.Fail(ApiOutcome.NetworkError), At(i));

            var vm = Build(s, 9);

            Assert.True(vm.IsStale);
            Assert.Equal("Sem conexão com o servidor · DESATUALIZADO há 8 s", vm.Banner);
            Assert.Equal("Crítico", vm.StatusText);
            Assert.NotEmpty(vm.SensorLines);
        }

        [Fact]
        public void A_single_failure_shows_stale_only_after_the_threshold_not_immediately()
        {
            var s = LiveWith(FromFixture("twin_critical.json", "alerts_critical.json"), pollAt: 1);
            s.OnPolled("EQ-001", ApiResult<LiveData>.Fail(ApiOutcome.Timeout), At(2));

            Assert.False(Build(s, 2.5).IsStale);
            Assert.Null(Build(s, 2.5).Banner);
        }

        [Fact]
        public void A_successful_poll_clears_the_stale_mark()
        {
            var s = LiveWith(FromFixture("twin_critical.json", "alerts_critical.json"), pollAt: 1);
            Assert.True(Build(s, 10).IsStale);

            s.OnPolled("EQ-001", ApiResult<LiveData>.Success(FromFixture("twin_critical.json", "alerts_critical.json")), At(10));

            Assert.False(Build(s, 10.5).IsStale);
            Assert.Null(Build(s, 10.5).Banner);
        }
    }
}
