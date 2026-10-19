// Maquina de estados da sessao AR (SPEC-008). Reducer PURO: eventos entram, comandos saem; nao ha
// rede, relogio nem threads aqui. Isso a torna totalmente testavel sem Unity.
using System;
using System.Collections.Generic;

namespace Spatial.Ar.Core
{
    public enum Phase { Scanning, Resolving, Live, Rejected, AuthError, RateLimited, ResolveFailed }

    public sealed class SessionOptions
    {
        public TimeSpan PollInterval { get; set; } = TimeSpan.FromSeconds(2);
        public TimeSpan PollHangTimeout { get; set; } = TimeSpan.FromSeconds(10);
        public TimeSpan QrDebounce { get; set; } = TimeSpan.FromSeconds(1);
        public TimeSpan MessageDisplay { get; set; } = TimeSpan.FromSeconds(2);
        /// <summary>D-017: dado e "desatualizado" apos 1,5x o intervalo de atualizacao.</summary>
        public TimeSpan StaleAfter { get; set; } = TimeSpan.FromSeconds(3);
        public int FailuresBeforeNoConnection { get; set; } = 3;
    }

    public abstract class Command { }

    public sealed class ResolveCommand : Command
    {
        public ResolveCommand(string markerId) { MarkerId = markerId; }
        public string MarkerId { get; }
    }

    public sealed class PollCommand : Command
    {
        public PollCommand(string equipmentId) { EquipmentId = equipmentId; }
        public string EquipmentId { get; }
    }

    /// <summary>Instantaneo imutavel do estado (o MarkerSession cria um novo a cada leitura).</summary>
    public sealed class SessionState
    {
        public Phase Phase { get; internal set; }
        public string MarkerId { get; internal set; }
        public EquipmentDto Equipment { get; internal set; }
        public LiveData LastView { get; internal set; }
        public DateTimeOffset? LastSuccessAt { get; internal set; }
        public int ConsecutiveFailures { get; internal set; }
        public DateTimeOffset? RetryAt { get; internal set; }
    }

    public sealed class MarkerSession
    {
        private static readonly IReadOnlyList<Command> None = new Command[0];

        private readonly SessionOptions _options;

        private Phase _phase = Phase.Scanning;
        private string _markerId;
        private EquipmentDto _equipment;
        private LiveData _lastView;
        private DateTimeOffset? _lastSuccessAt;
        private int _failures;
        private DateTimeOffset? _retryAt;
        private DateTimeOffset? _lastQrAcceptedAt;
        private DateTimeOffset? _nextPollAt;
        private DateTimeOffset? _pollInFlightSince;

        public MarkerSession() : this(new SessionOptions()) { }

        public MarkerSession(SessionOptions options)
        {
            _options = options ?? throw new ArgumentNullException(nameof(options));
        }

        public SessionState State => new SessionState
        {
            Phase = _phase,
            MarkerId = _markerId,
            Equipment = _equipment,
            LastView = _lastView,
            LastSuccessAt = _lastSuccessAt,
            ConsecutiveFailures = _failures,
            RetryAt = _retryAt,
        };

        /// <summary>Apos reautenticar: volta a escanear do zero.</summary>
        public void Reset()
        {
            ClearEquipment();
            _phase = Phase.Scanning;
            _markerId = null;
            _retryAt = null;
            _lastQrAcceptedAt = null;
        }

        public IReadOnlyList<Command> OnQrDetected(string raw, DateTimeOffset now)
        {
            if (!QrPayload.TryParse(raw, out var marker)) return None;            // lixo: descartado, sem efeito
            if (_phase == Phase.AuthError) return None;

            var waiting = _phase == Phase.Rejected || _phase == Phase.RateLimited || _phase == Phase.ResolveFailed;
            if (waiting && _retryAt.HasValue && now < _retryAt.Value) return None;

            if ((_phase == Phase.Resolving || _phase == Phase.Live) && marker == _markerId) return None;
            if (_lastQrAcceptedAt.HasValue && now - _lastQrAcceptedAt.Value < _options.QrDebounce) return None;

            // aceito: nada do equipamento anterior pode sobrar (REQ-AR-005)
            ClearEquipment();
            _phase = Phase.Resolving;
            _markerId = marker;
            _retryAt = null;
            _lastQrAcceptedAt = now;
            return new Command[] { new ResolveCommand(marker) };
        }

        public IReadOnlyList<Command> OnResolved(string markerId, ApiResult<EquipmentDto> result, DateTimeOffset now)
        {
            if (_phase != Phase.Resolving || markerId != _markerId) return None;  // resposta atrasada de outro QR

            switch (result.Outcome)
            {
                case ApiOutcome.Ok:
                    _phase = Phase.Live;
                    _equipment = result.Value;
                    _pollInFlightSince = now;
                    return new Command[] { new PollCommand(result.Value.Id) };
                case ApiOutcome.NotFound:
                    Wait(Phase.Rejected, now + _options.MessageDisplay);
                    return None;
                case ApiOutcome.Unauthorized:
                    ClearEquipment();
                    _phase = Phase.AuthError;
                    _markerId = null;
                    return None;
                case ApiOutcome.RateLimited:
                    Wait(Phase.RateLimited, now + TimeSpan.FromSeconds(Math.Max(1, result.RetryAfterSeconds)));
                    return None;
                default:
                    Wait(Phase.ResolveFailed, now + _options.MessageDisplay);
                    return None;
            }
        }

        public IReadOnlyList<Command> OnPolled(string equipmentId, ApiResult<LiveData> result, DateTimeOffset now)
        {
            if (_phase != Phase.Live || _equipment == null || equipmentId != _equipment.Id) return None;
            _pollInFlightSince = null;

            switch (result.Outcome)
            {
                case ApiOutcome.Ok:
                    _lastView = result.Value;
                    _lastSuccessAt = now;
                    _failures = 0;
                    _nextPollAt = now + _options.PollInterval;
                    return None;
                case ApiOutcome.Unauthorized:
                    ClearEquipment();
                    _phase = Phase.AuthError;
                    _markerId = null;
                    return None;
                case ApiOutcome.NotFound:                     // equipamento sumiu / mudou de organizacao
                    Wait(Phase.Rejected, now + _options.MessageDisplay);
                    return None;
                default:                                      // mantem a ultima vista; ela envelhece sozinha
                    _failures++;
                    var delay = result.Outcome == ApiOutcome.RateLimited
                        ? TimeSpan.FromSeconds(Math.Max(result.RetryAfterSeconds, _options.PollInterval.TotalSeconds))
                        : _options.PollInterval;
                    _nextPollAt = now + delay;
                    return None;
            }
        }

        public IReadOnlyList<Command> Tick(DateTimeOffset now)
        {
            switch (_phase)
            {
                case Phase.Rejected:
                case Phase.RateLimited:
                case Phase.ResolveFailed:
                    if (_retryAt.HasValue && now >= _retryAt.Value)
                    {
                        _phase = Phase.Scanning;
                        _retryAt = null;
                    }
                    return None;
                case Phase.Live:
                    return TickLive(now);
                default:
                    return None;
            }
        }

        private IReadOnlyList<Command> TickLive(DateTimeOffset now)
        {
            if (_pollInFlightSince.HasValue)
            {
                if (now - _pollInFlightSince.Value < _options.PollHangTimeout) return None;   // ainda em voo
            }
            else if (_nextPollAt.HasValue && now < _nextPollAt.Value)
            {
                return None;
            }
            _pollInFlightSince = now;
            return new Command[] { new PollCommand(_equipment.Id) };
        }

        private void Wait(Phase phase, DateTimeOffset until)
        {
            ClearEquipment();
            _phase = phase;
            _markerId = null;
            _retryAt = until;
        }

        private void ClearEquipment()
        {
            _equipment = null;
            _lastView = null;
            _lastSuccessAt = null;
            _failures = 0;
            _nextPollAt = null;
            _pollInFlightSince = null;
        }
    }
}
