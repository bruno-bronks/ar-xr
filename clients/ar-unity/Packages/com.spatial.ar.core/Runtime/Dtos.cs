// DTOs espelham specs/contracts/openapi.yaml. As fixtures de teste sao geradas pela API real.
using System.Collections.Generic;
using Newtonsoft.Json;

namespace Spatial.Ar.Core
{
    public enum EquipmentStatus { Normal, Warning, Critical, Offline, Unknown }

    public sealed class EquipmentDto
    {
        [JsonProperty("id", Required = Required.Always)] public string Id { get; set; }
        [JsonProperty("name", Required = Required.Always)] public string Name { get; set; }
        [JsonProperty("type", Required = Required.Always)] public string Type { get; set; }
        [JsonProperty("location", Required = Required.Always)] public string Location { get; set; }
        [JsonProperty("last_seen_at", Required = Required.AllowNull)] public string LastSeenAt { get; set; }
        [JsonProperty("status", Required = Required.Always)] public string Status { get; set; }
    }

    public sealed class SensorDto
    {
        [JsonProperty("sensor_type", Required = Required.Always)] public string SensorType { get; set; }
        [JsonProperty("unit", Required = Required.Always)] public string Unit { get; set; }
        [JsonProperty("value", Required = Required.AllowNull)] public double? Value { get; set; }
        [JsonProperty("observed_at", Required = Required.AllowNull)] public string ObservedAt { get; set; }
        [JsonProperty("quality", Required = Required.AllowNull)] public string Quality { get; set; }
        [JsonProperty("warn", Required = Required.Always)] public double Warn { get; set; }
        [JsonProperty("crit", Required = Required.Always)] public double Crit { get; set; }
        [JsonProperty("valid", Required = Required.Always)] public bool Valid { get; set; }
    }

    public sealed class TwinDto
    {
        [JsonProperty("equipment_id", Required = Required.Always)] public string EquipmentId { get; set; }
        [JsonProperty("status", Required = Required.Always)] public string Status { get; set; }
        [JsonProperty("evaluated_at", Required = Required.Always)] public string EvaluatedAt { get; set; }
        [JsonProperty("offline_after_seconds", Required = Required.Always)] public int OfflineAfterSeconds { get; set; }
        [JsonProperty("sensors", Required = Required.Always)] public List<SensorDto> Sensors { get; set; }
    }

    public sealed class AlertDto
    {
        [JsonProperty("equipment_id", Required = Required.Always)] public string EquipmentId { get; set; }
        [JsonProperty("severity", Required = Required.Always)] public string Severity { get; set; }
        [JsonProperty("rule", Required = Required.Always)] public string Rule { get; set; }
        [JsonProperty("raised_at", Required = Required.Always)] public string RaisedAt { get; set; }
        [JsonProperty("sensor_type")] public string SensorType { get; set; }
        [JsonProperty("value")] public double? Value { get; set; }
        [JsonProperty("limit")] public double? Limit { get; set; }
    }

    /// <summary>Resultado de um ciclo de atualizacao: twin + alertas obtidos juntos.</summary>
    public sealed class LiveData
    {
        public LiveData(TwinDto twin, IReadOnlyList<AlertDto> alerts) { Twin = twin; Alerts = alerts; }
        public TwinDto Twin { get; }
        public IReadOnlyList<AlertDto> Alerts { get; }
    }

    public static class StatusParser
    {
        /// <summary>Mapeia o texto do servidor. Valor desconhecido => false (violacao de contrato).</summary>
        public static bool TryParse(string raw, out EquipmentStatus status)
        {
            switch (raw)
            {
                case "NORMAL": status = EquipmentStatus.Normal; return true;
                case "WARNING": status = EquipmentStatus.Warning; return true;
                case "CRITICAL": status = EquipmentStatus.Critical; return true;
                case "OFFLINE": status = EquipmentStatus.Offline; return true;
                case "UNKNOWN": status = EquipmentStatus.Unknown; return true;
                default: status = EquipmentStatus.Unknown; return false;
            }
        }
    }
}
