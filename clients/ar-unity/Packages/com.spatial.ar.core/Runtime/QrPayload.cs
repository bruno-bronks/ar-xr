// SPEC-008 / REQ-AR-001: o QR carrega SOMENTE o marker opaco. Qualquer outra coisa e descartada
// antes de qualquer requisicao de rede.
namespace Spatial.Ar.Core
{
    public static class QrPayload
    {
        public const int MaxMarkerLength = 128;
        public const int MaxEquipmentIdLength = 64;

        /// <summary>Aceita apenas [A-Za-z0-9._:-]{1,128} (ASCII estrito; sem espacos, controle ou unicode).</summary>
        public static bool TryParse(string raw, out string markerId)
        {
            markerId = null;
            if (!IsValidId(raw, MaxMarkerLength)) return false;
            markerId = raw;
            return true;
        }

        public static bool IsValidId(string value, int maxLength)
        {
            if (string.IsNullOrEmpty(value) || value.Length > maxLength) return false; // checa o tamanho ANTES de varrer
            foreach (var c in value)
            {
                var ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
                         || c == '.' || c == '_' || c == ':' || c == '-';
                if (!ok) return false;
            }
            return true;
        }
    }
}
