// SPEC-008 A3 / REQ-AR-001, REQ-AR-002, REQ-AR-004, REQ-AR-005: maquina de estados (reducer puro).
using System;
using System.Collections.Generic;
using System.Linq;
using Xunit;

namespace Spatial.Ar.Core.Tests
{
    public class MarkerSessionTests
    {
        private static readonly DateTimeOffset T0 = new DateTimeOffset(2026, 10, 19, 12, 0, 0, TimeSpan.Zero);
        private static DateTimeOffset At(double seconds) => T0.AddSeconds(seconds);

        private static EquipmentDto Equipment(string id = "EQ-001") => new EquipmentDto
        {
            Id = id, Name = "Compressor " + id, Type = "t", Location = "l", Status = "NORMAL",
        };

        private static LiveData Live(string id = "EQ-001", string status = "NORMAL") => new LiveData(
            new TwinDto { EquipmentId = id, Status = status, EvaluatedAt = "2026-10-19T12:00:00Z", OfflineAfterSeconds = 30, Sensors = new List<SensorDto>() },
            new List<AlertDto>());

        private static ApiResult<T> Ok<T>(T v) => ApiResult<T>.Success(v);
        private static ApiResult<T> Fail<T>(ApiOutcome o, int retry = 0) => ApiResult<T>.Fail(o, retry);

        private static MarkerSession Resolving(string marker = "QR-EQ-001", double at = 0)
        {
            var s = new MarkerSession();
            s.OnQrDetected(marker, At(at));
            return s;
        }

        private static MarkerSession LiveSession(double at = 0)
        {
            var s = Resolving("QR-EQ-001", at);
            s.OnResolved("QR-EQ-001", Ok(Equipment()), At(at));
            return s;
        }

        // --- scanning / resolving -----------------------------------------------------------

        [Fact]
        public void Starts_scanning_with_no_commands()
        {
            var s = new MarkerSession();

            Assert.Equal(Phase.Scanning, s.State.Phase);
            Assert.Empty(s.Tick(At(0)));
        }

        [Fact]
        public void Valid_qr_starts_resolving_and_asks_to_resolve_the_marker()
        {
            var s = new MarkerSession();

            var commands = s.OnQrDetected("QR-EQ-001", At(0));

            Assert.Equal(Phase.Resolving, s.State.Phase);
            Assert.Equal("QR-EQ-001", s.State.MarkerId);
            var cmd = Assert.IsType<ResolveCommand>(Assert.Single(commands));
            Assert.Equal("QR-EQ-001", cmd.MarkerId);
        }

        [Theory]
        [InlineData("")]
        [InlineData("https://evil/x")]
        [InlineData("QR EQ")]
        [InlineData(null)]
        public void Invalid_qr_is_ignored_without_commands_or_state_change(string raw)
        {
            var s = new MarkerSession();

            Assert.Empty(s.OnQrDetected(raw, At(0)));
            Assert.Equal(Phase.Scanning, s.State.Phase);
        }

        [Fact]
        public void Invalid_qr_does_not_disturb_a_live_session()
        {
            var s = LiveSession();

            Assert.Empty(s.OnQrDetected("lixo qualquer", At(5)));
            Assert.Equal(Phase.Live, s.State.Phase);
        }

        // --- resolucao ------------------------------------------------------------------------

        [Fact]
        public void Successful_resolution_goes_live_and_polls_immediately()
        {
            var s = Resolving();

            var commands = s.OnResolved("QR-EQ-001", Ok(Equipment()), At(0.3));

            Assert.Equal(Phase.Live, s.State.Phase);
            Assert.Equal("EQ-001", s.State.Equipment.Id);
            Assert.Null(s.State.LastView);
            var poll = Assert.IsType<PollCommand>(Assert.Single(commands));
            Assert.Equal("EQ-001", poll.EquipmentId);
        }

        [Fact]
        public void NotFound_shows_the_generic_rejection_and_clears_everything()
        {
            var s = Resolving();

            Assert.Empty(s.OnResolved("QR-EQ-001", Fail<EquipmentDto>(ApiOutcome.NotFound), At(0.2)));

            Assert.Equal(Phase.Rejected, s.State.Phase);
            Assert.Null(s.State.Equipment);
            Assert.Null(s.State.LastView);
        }

        [Fact]
        public void Rejected_returns_to_scanning_after_two_seconds_and_not_before()
        {
            var s = Resolving();
            s.OnResolved("QR-EQ-001", Fail<EquipmentDto>(ApiOutcome.NotFound), At(1));

            s.Tick(At(2.9));
            Assert.Equal(Phase.Rejected, s.State.Phase);
            s.Tick(At(3.0));
            Assert.Equal(Phase.Scanning, s.State.Phase);
        }

        [Fact]
        public void Qr_is_ignored_while_rejected_and_accepted_once_scanning_again()
        {
            var s = Resolving();
            s.OnResolved("QR-EQ-001", Fail<EquipmentDto>(ApiOutcome.NotFound), At(1));

            Assert.Empty(s.OnQrDetected("QR-EQ-002", At(2)));
            s.Tick(At(3));
            Assert.Single(s.OnQrDetected("QR-EQ-002", At(3.1)));
        }

        [Fact]
        public void Unauthorized_is_a_terminal_auth_error_that_ignores_further_qr_until_reset()
        {
            var s = Resolving();
            s.OnResolved("QR-EQ-001", Fail<EquipmentDto>(ApiOutcome.Unauthorized), At(0.1));

            Assert.Equal(Phase.AuthError, s.State.Phase);
            s.Tick(At(60));
            Assert.Equal(Phase.AuthError, s.State.Phase);
            Assert.Empty(s.OnQrDetected("QR-EQ-002", At(61)));

            s.Reset();
            Assert.Equal(Phase.Scanning, s.State.Phase);
            Assert.Single(s.OnQrDetected("QR-EQ-002", At(62)));
        }

        [Fact]
        public void Rate_limit_waits_for_retry_after()
        {
            var s = Resolving();
            s.OnResolved("QR-EQ-001", Fail<EquipmentDto>(ApiOutcome.RateLimited, 10), At(1));

            Assert.Equal(Phase.RateLimited, s.State.Phase);
            Assert.Equal(At(11), s.State.RetryAt);
            Assert.Empty(s.OnQrDetected("QR-EQ-002", At(5)));
            s.Tick(At(10.9));
            Assert.Equal(Phase.RateLimited, s.State.Phase);
            s.Tick(At(11));
            Assert.Equal(Phase.Scanning, s.State.Phase);
        }

        [Theory]
        [InlineData(ApiOutcome.NetworkError)]
        [InlineData(ApiOutcome.Timeout)]
        [InlineData(ApiOutcome.ServerError)]
        [InlineData(ApiOutcome.BadResponse)]
        public void Transient_failures_resolve_failed_then_retry_scanning(ApiOutcome outcome)
        {
            var s = Resolving();
            s.OnResolved("QR-EQ-001", Fail<EquipmentDto>(outcome), At(1));

            Assert.Equal(Phase.ResolveFailed, s.State.Phase);
            s.Tick(At(3));
            Assert.Equal(Phase.Scanning, s.State.Phase);
        }

        [Fact]
        public void A_resolution_result_for_a_different_marker_is_ignored()
        {
            var s = Resolving("QR-EQ-001");

            Assert.Empty(s.OnResolved("QR-EQ-999", Ok(Equipment("EQ-999")), At(0.2)));
            Assert.Equal(Phase.Resolving, s.State.Phase);
            Assert.Null(s.State.Equipment);
        }

        // --- sessao ao vivo -------------------------------------------------------------------

        [Fact]
        public void Polls_every_two_seconds_and_never_twice_in_flight()
        {
            var s = LiveSession(0);                       // 1o poll ja emitido em t=0
            Assert.Empty(s.Tick(At(1)));
            Assert.Empty(s.Tick(At(2.5)));                // ainda em voo: nao emite outro

            s.OnPolled("EQ-001", Ok(Live()), At(2.6));
            Assert.Empty(s.Tick(At(2.7)));                // proximo so 2 s depois do poll anterior
            var next = Assert.IsType<PollCommand>(Assert.Single(s.Tick(At(4.6))));
            Assert.Equal("EQ-001", next.EquipmentId);
            Assert.Empty(s.Tick(At(4.7)));                // novo poll em voo
        }

        [Fact]
        public void A_hung_poll_is_retried_after_ten_seconds()
        {
            var s = LiveSession(0);

            Assert.Empty(s.Tick(At(9.9)));
            Assert.Single(s.Tick(At(10.0)));
        }

        [Fact]
        public void Successful_poll_stores_the_view_and_resets_failures()
        {
            var s = LiveSession(0);
            s.OnPolled("EQ-001", Fail<LiveData>(ApiOutcome.NetworkError), At(1));
            Assert.Equal(1, s.State.ConsecutiveFailures);

            s.OnPolled("EQ-001", Ok(Live(status: "CRITICAL")), At(3));

            Assert.Equal(0, s.State.ConsecutiveFailures);
            Assert.Equal("CRITICAL", s.State.LastView.Twin.Status);
            Assert.Equal(At(3), s.State.LastSuccessAt);
        }

        [Fact]
        public void Failed_poll_keeps_the_last_view_and_counts_failures()
        {
            var s = LiveSession(0);
            s.OnPolled("EQ-001", Ok(Live(status: "WARNING")), At(1));

            foreach (var i in Enumerable.Range(1, 3)) s.OnPolled("EQ-001", Fail<LiveData>(ApiOutcome.Timeout), At(1 + i));

            Assert.Equal(3, s.State.ConsecutiveFailures);
            Assert.Equal("WARNING", s.State.LastView.Twin.Status);   // o ultimo estado do SERVIDOR segue visivel
            Assert.Equal(At(1), s.State.LastSuccessAt);
            Assert.Equal(Phase.Live, s.State.Phase);
        }

        [Fact]
        public void Unauthorized_during_polling_drops_all_data()
        {
            var s = LiveSession(0);
            s.OnPolled("EQ-001", Ok(Live()), At(1));

            s.OnPolled("EQ-001", Fail<LiveData>(ApiOutcome.Unauthorized), At(3));

            Assert.Equal(Phase.AuthError, s.State.Phase);
            Assert.Null(s.State.Equipment);
            Assert.Null(s.State.LastView);
        }

        [Fact]
        public void NotFound_during_polling_means_the_equipment_is_gone_and_data_is_dropped()
        {
            var s = LiveSession(0);
            s.OnPolled("EQ-001", Ok(Live()), At(1));

            s.OnPolled("EQ-001", Fail<LiveData>(ApiOutcome.NotFound), At(3));

            Assert.Equal(Phase.Rejected, s.State.Phase);
            Assert.Null(s.State.LastView);
        }

        [Fact]
        public void Rate_limited_poll_counts_as_a_failure_but_keeps_the_session()
        {
            var s = LiveSession(0);

            s.OnPolled("EQ-001", Fail<LiveData>(ApiOutcome.RateLimited, 5), At(1));

            Assert.Equal(Phase.Live, s.State.Phase);
            Assert.Equal(1, s.State.ConsecutiveFailures);
        }

        [Fact]
        public void A_poll_result_for_another_equipment_is_ignored()
        {
            var s = LiveSession(0);

            Assert.Empty(s.OnPolled("EQ-002", Ok(Live("EQ-002")), At(1)));
            Assert.Null(s.State.LastView);
        }

        // --- troca de QR, debounce e vazamento ----------------------------------------------

        [Fact]
        public void Rescanning_the_same_marker_is_ignored_while_resolving_or_live()
        {
            var s = Resolving();
            Assert.Empty(s.OnQrDetected("QR-EQ-001", At(5)));
            s.OnResolved("QR-EQ-001", Ok(Equipment()), At(5));
            Assert.Empty(s.OnQrDetected("QR-EQ-001", At(9)));
            Assert.Equal(Phase.Live, s.State.Phase);
        }

        [Fact]
        public void Switching_marker_discards_the_previous_equipment_view_immediately()
        {
            var s = LiveSession(0);
            s.OnPolled("EQ-001", Ok(Live(status: "CRITICAL")), At(1));

            var commands = s.OnQrDetected("QR-EQ-002", At(5));

            Assert.Equal(Phase.Resolving, s.State.Phase);
            Assert.Null(s.State.Equipment);            // REQ-AR-005: nada do EQ-001 sobra
            Assert.Null(s.State.LastView);
            Assert.Equal("QR-EQ-002", Assert.IsType<ResolveCommand>(Assert.Single(commands)).MarkerId);
        }

        [Fact]
        public void A_different_marker_within_one_second_of_the_last_accepted_qr_is_debounced()
        {
            var s = Resolving("QR-EQ-001", 0);

            Assert.Empty(s.OnQrDetected("QR-EQ-002", At(0.5)));
            Assert.Equal("QR-EQ-001", s.State.MarkerId);
            Assert.Single(s.OnQrDetected("QR-EQ-002", At(1.0)));
        }

        [Fact]
        public void Late_results_of_the_previous_marker_cannot_resurrect_old_data()
        {
            var s = LiveSession(0);
            s.OnQrDetected("QR-EQ-002", At(5));                          // trocou para EQ-002

            Assert.Empty(s.OnResolved("QR-EQ-001", Ok(Equipment()), At(5.1)));   // resolve atrasado do antigo
            Assert.Empty(s.OnPolled("EQ-001", Ok(Live(status: "CRITICAL")), At(5.2)));  // poll atrasado
            Assert.Equal(Phase.Resolving, s.State.Phase);
            Assert.Null(s.State.LastView);
            Assert.Null(s.State.Equipment);
        }

        [Fact]
        public void Late_poll_result_after_switch_and_resolution_is_still_ignored()
        {
            var s = LiveSession(0);
            s.OnQrDetected("QR-EQ-002", At(5));
            s.OnResolved("QR-EQ-002", Ok(Equipment("EQ-002")), At(5.3));

            Assert.Empty(s.OnPolled("EQ-001", Ok(Live("EQ-001", "CRITICAL")), At(5.4)));
            Assert.Null(s.State.LastView);
            Assert.Equal("EQ-002", s.State.Equipment.Id);
        }

        [Fact]
        public void Tick_never_emits_commands_outside_live()
        {
            var s = Resolving();
            Assert.Empty(s.Tick(At(100)));
        }
    }
}
