// Modelo de apresentacao (SPEC-008, D-017): o overlay mostra o status do SERVIDOR; o cliente nao recalcula.
using System;
using System.Collections.Generic;
using System.Globalization;

namespace Spatial.Ar.Core
{
    public enum StatusColor { None, Green, Amber, Red, Gray, Purple }

    public sealed class OverlayViewModel
    {
        public string Title { get; private set; }
        public string StatusText { get; private set; }
        public StatusColor Color { get; private set; }
        public IReadOnlyList<string> SensorLines { get; private set; } = new string[0];
        public IReadOnlyList<string> AlertLines { get; private set; } = new string[0];
        public string Banner { get; private set; }
        public bool IsStale { get; private set; }
        public int? StaleSeconds { get; private set; }

        public static OverlayViewModel Build(SessionState state, DateTimeOffset now, SessionOptions options)
        {
            var vm = new OverlayViewModel { Title = "Aponte para o QR do equipamento", StatusText = string.Empty, Color = StatusColor.None };
            switch (state.Phase)
            {
                case Phase.Scanning:
                    return vm;
                case Phase.Resolving:
                    vm.Title = "Identificando equipamento…";
                    return vm;
                case Phase.Rejected:
                    vm.Banner = "Marcador não reconhecido";     // identico para desconhecido e de outra organizacao
                    return vm;
                case Phase.AuthError:
                    vm.Banner = "Sessão inválida. Reautentique.";
                    return vm;
                case Phase.RateLimited:
                    var wait = state.RetryAt.HasValue ? Math.Max(0, (int)Math.Ceiling((state.RetryAt.Value - now).TotalSeconds)) : 0;
                    vm.Banner = "Muitas leituras. Aguarde " + wait + " s.";
                    return vm;
                case Phase.ResolveFailed:
                    vm.Banner = "Sem conexão com o servidor";
                    return vm;
            }

            // Phase.Live
            vm.Title = state.Equipment.Name + " (" + state.Equipment.Id + ")";
            if (state.LastView == null)
            {
                vm.StatusText = "Aguardando dados…";            // nunca "normal" por falta de dado
                vm.Banner = state.ConsecutiveFailures >= options.FailuresBeforeNoConnection
                    ? "Sem conexão com o servidor" : "Carregando…";
                return vm;
            }

            var twin = state.LastView.Twin;
            StatusParser.TryParse(twin.Status, out var status);       // validado no cliente da API
            vm.StatusText = StatusText_(status);
            vm.Color = ColorOf(status);

            var evaluatedAt = ParseTime(twin.EvaluatedAt);
            var lines = new List<string>();
            foreach (var s in twin.Sensors) lines.Add(SensorLine(s, evaluatedAt));
            vm.SensorLines = lines;

            var alerts = new List<string>();
            foreach (var a in state.LastView.Alerts) alerts.Add(AlertLine(a));
            vm.AlertLines = alerts;

            if (state.LastSuccessAt.HasValue && now - state.LastSuccessAt.Value > options.StaleAfter)
            {
                vm.IsStale = true;
                vm.StaleSeconds = (int)Math.Floor((now - state.LastSuccessAt.Value).TotalSeconds);
                var stale = "DESATUALIZADO há " + vm.StaleSeconds + " s";
                vm.Banner = state.ConsecutiveFailures >= options.FailuresBeforeNoConnection
                    ? "Sem conexão com o servidor · " + stale : stale;
            }
            return vm;
        }

        private static string StatusText_(EquipmentStatus status)
        {
            switch (status)
            {
                case EquipmentStatus.Normal: return "Normal";
                case EquipmentStatus.Warning: return "Atenção";
                case EquipmentStatus.Critical: return "Crítico";
                case EquipmentStatus.Offline: return "Offline — sem dados recentes";
                default: return "Desconhecido — dados insuficientes";
            }
        }

        private static StatusColor ColorOf(EquipmentStatus status)
        {
            switch (status)
            {
                case EquipmentStatus.Normal: return StatusColor.Green;
                case EquipmentStatus.Warning: return StatusColor.Amber;
                case EquipmentStatus.Critical: return StatusColor.Red;
                case EquipmentStatus.Offline: return StatusColor.Gray;
                default: return StatusColor.Purple;
            }
        }

        private static string SensorLine(SensorDto s, DateTimeOffset? evaluatedAt)
        {
            if (!s.Value.HasValue) return s.SensorType + ": sem dados";
            var text = s.SensorType + ": " + Num(s.Value.Value) + " " + s.Unit
                       + " · limites " + Num(s.Warn) + "/" + Num(s.Crit);
            var observedAt = ParseTime(s.ObservedAt);
            if (observedAt.HasValue && evaluatedAt.HasValue)
            {
                var age = (int)Math.Max(0, Math.Round((evaluatedAt.Value - observedAt.Value).TotalSeconds, MidpointRounding.AwayFromZero));
                text += " · " + age + " s";
            }
            if (s.Quality == "BAD") text += " · defeito";
            if (!s.Valid) text += " · inválida";
            return text;
        }

        private static string AlertLine(AlertDto a)
        {
            var text = SeverityText(a.Severity) + " · " + a.Rule;
            if (a.Value.HasValue && a.Limit.HasValue) text += " · " + Num(a.Value.Value) + " (limite " + Num(a.Limit.Value) + ")";
            return text;
        }

        private static string SeverityText(string severity)
        {
            switch (severity)
            {
                case "CRITICAL": return "Crítico";
                case "WARNING": return "Atenção";
                case "OFFLINE": return "Offline";
                default: return severity;
            }
        }

        private static string Num(double value) => value.ToString("0.0", CultureInfo.InvariantCulture);

        private static DateTimeOffset? ParseTime(string text)
            => DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.None, out var t) ? t : (DateTimeOffset?)null;
    }
}
