// Executa os comandos da MarkerSession com o cliente da API e devolve os resultados como eventos.
// Thread-safe: o estado so e tocado dentro de `_gate`. O log recebe SOMENTE codigos fixos.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace Spatial.Ar.Core
{
    public sealed class SessionDriver
    {
        private readonly MarkerSession _session;
        private readonly SpatialApiClient _client;
        private readonly Func<DateTimeOffset> _clock;
        private readonly IClientLog _log;
        private readonly object _gate = new object();
        private readonly List<Task> _pending = new List<Task>();

        public SessionDriver(MarkerSession session, SpatialApiClient client, Func<DateTimeOffset> clock, IClientLog log)
        {
            _session = session ?? throw new ArgumentNullException(nameof(session));
            _client = client ?? throw new ArgumentNullException(nameof(client));
            _clock = clock ?? throw new ArgumentNullException(nameof(clock));
            _log = log ?? new NullClientLog();
        }

        /// <summary>Texto bruto lido do QR. Nunca e registrado em log.</summary>
        public void OnQrDetected(string raw)
        {
            IReadOnlyList<Command> commands;
            lock (_gate) commands = _session.OnQrDetected(raw, _clock());
            Execute(commands);
        }

        /// <summary>Chamar a cada quadro (ou a cada ~200 ms).</summary>
        public void Tick()
        {
            IReadOnlyList<Command> commands;
            lock (_gate) commands = _session.Tick(_clock());
            Execute(commands);
        }

        public SessionState State { get { lock (_gate) return _session.State; } }

        /// <summary>Aguarda todas as requisicoes em andamento (e as que elas dispararem). Uso em testes.</summary>
        public async Task WhenIdleAsync()
        {
            while (true)
            {
                Task[] snapshot;
                lock (_gate)
                {
                    _pending.RemoveAll(t => t.IsCompleted);
                    snapshot = _pending.ToArray();
                }
                if (snapshot.Length == 0) return;
                await Task.WhenAll(snapshot).ConfigureAwait(false);
            }
        }

        private void Execute(IReadOnlyList<Command> commands)
        {
            foreach (var command in commands)
            {
                var task = RunAsync(command);
                lock (_gate) _pending.Add(task);
            }
        }

        private async Task RunAsync(Command command)
        {
            try
            {
                IReadOnlyList<Command> next;
                if (command is ResolveCommand resolve)
                {
                    Log("resolve:start");
                    var result = await _client.ResolveMarkerAsync(resolve.MarkerId);   // sem ConfigureAwait(false): continuar na thread do Unity
                    Log("resolve:" + result.Outcome);
                    lock (_gate) next = _session.OnResolved(resolve.MarkerId, result, _clock());
                }
                else if (command is PollCommand poll)
                {
                    var result = await _client.GetLiveAsync(poll.EquipmentId);          // idem: UnityWebRequest so na thread principal
                    Log("poll:" + result.Outcome);
                    lock (_gate) next = _session.OnPolled(poll.EquipmentId, result, _clock());
                }
                else
                {
                    return;
                }
                Execute(next);
            }
            catch (Exception)
            {
                Log("driver:error");   // nunca inclui a mensagem da excecao (poderia conter URL/token)
            }
        }

        private void Log(string code)
        {
            try { _log.Info(code); } catch (Exception) { /* log com defeito nao pode derrubar a sessao */ }
        }
    }
}
