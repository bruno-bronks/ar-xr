// SPEC-008 A8 / REQ-AR-001, REQ-AR-006: os QR gerados por scripts/generate_qr.py decodificam, com ZXing.Net (a MESMA
// biblioteca do app), exatamente para o conteudo esperado - e o nucleo decide corretamente sobre ele.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using Xunit;
using ZXing;

namespace Spatial.Ar.Core.Tests
{
    public class QrRoundTripTests
    {
        private static string QrDir => Path.Combine(AppContext.BaseDirectory, "qr");

        private static (int Size, byte[] Pixels) ReadPgm(string path)
        {
            var raw = File.ReadAllBytes(path);
            var lines = new List<string>();
            var pos = 0;
            while (lines.Count < 3)
            {
                var end = Array.IndexOf(raw, (byte)'\n', pos);
                lines.Add(System.Text.Encoding.ASCII.GetString(raw, pos, end - pos));
                pos = end + 1;
            }
            Assert.Equal("P5", lines[0]);
            var dims = lines[1].Split(' ');
            var size = int.Parse(dims[0]);
            Assert.Equal(size, int.Parse(dims[1]));
            var pixels = new byte[size * size];
            Array.Copy(raw, pos, pixels, 0, pixels.Length);
            return (size, pixels);
        }

        private static string Decode(string pgmPath)
        {
            var (size, pixels) = ReadPgm(pgmPath);
            var source = new RGBLuminanceSource(pixels, size, size, RGBLuminanceSource.BitmapFormat.Gray8);
            var reader = new BarcodeReaderGeneric();
            reader.Options.PossibleFormats = new List<BarcodeFormat> { BarcodeFormat.QR_CODE };
            reader.Options.TryHarder = true;
            return reader.Decode(source)?.Text;
        }

        public static IEnumerable<object[]> Codes()
        {
            var manifest = JObject.Parse(File.ReadAllText(Path.Combine(QrDir, "manifest.json")));
            foreach (var code in manifest["codes"])
                yield return new object[] { (string)code["name"], (string)code["pgm"], (string)code["content"], (string)code["kind"] };
        }

        [Fact]
        public void The_manifest_lists_all_eight_test_codes()
        {
            Assert.Equal(8, Codes().Count());
        }

        [Theory]
        [MemberData(nameof(Codes))]
        public void Zxing_decodes_each_generated_qr_to_exactly_its_content(string name, string pgm, string content, string kind)
        {
            Assert.Equal(content, Decode(Path.Combine(QrDir, pgm)));
        }

        [Theory]
        [MemberData(nameof(Codes))]
        public void The_core_accepts_only_marker_shaped_content_and_discards_the_rest(string name, string pgm, string content, string kind)
        {
            var decoded = Decode(Path.Combine(QrDir, pgm));

            var accepted = QrPayload.TryParse(decoded, out var marker);

            Assert.Equal(kind != "invalid_content", accepted);
            if (accepted) Assert.Equal(content, marker);
        }
    }
}
