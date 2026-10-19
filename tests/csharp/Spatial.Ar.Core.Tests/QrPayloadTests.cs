// SPEC-008 A1 / REQ-AR-001, REQ-AR-005: o QR carrega somente o marker opaco; qualquer outra coisa e descartada.
using System;
using System.Linq;
using Xunit;

namespace Spatial.Ar.Core.Tests
{
    public class QrPayloadTests
    {
        [Theory]
        [InlineData("QR-EQ-001")]
        [InlineData("QR-EQ-B01")]
        [InlineData("a")]
        [InlineData("A.b_c:d-9")]
        public void Accepts_valid_marker(string raw)
        {
            Assert.True(QrPayload.TryParse(raw, out var marker));
            Assert.Equal(raw, marker);
        }

        [Fact]
        public void Accepts_exactly_128_characters_and_rejects_129()
        {
            Assert.True(QrPayload.TryParse(new string('a', 128), out _));
            Assert.False(QrPayload.TryParse(new string('a', 129), out _));
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData(" ")]
        [InlineData(" QR-EQ-001")]
        [InlineData("QR-EQ-001 ")]
        [InlineData("QR EQ 001")]
        [InlineData("QR-EQ-001\n")]
        [InlineData("QR-EQ-001\0")]
        [InlineData("QR-EQ-001\t")]
        [InlineData("https://evil.example/QR-EQ-001")]
        [InlineData("{\"id\":\"EQ-001\"}")]
        [InlineData("' OR 1=1 --")]
        [InlineData("../../etc/passwd")]
        [InlineData("QR/EQ/001")]
        [InlineData("QR-EQ-001?x=1")]
        [InlineData("QR-EQ-001#frag")]
        [InlineData("%2e%2e")]
        [InlineData("<script>")]
        [InlineData("QR-ÉQ-001")]
        [InlineData("QR-EQ-００１")] // algarismos de largura total
        [InlineData("😀")]
        public void Rejects_everything_else(string raw)
        {
            Assert.False(QrPayload.TryParse(raw, out var marker));
            Assert.Null(marker);
        }

        [Fact]
        public void Rejects_huge_input_without_scanning_all_of_it()
        {
            Assert.False(QrPayload.TryParse(new string('a', 5_000_000), out _));
        }

        [Fact]
        public void No_ascii_control_or_punctuation_outside_the_allow_list_is_accepted()
        {
            const string allowedPunctuation = "._:-";
            for (var code = 0; code < 256; code++)
            {
                var c = (char)code;
                var expected = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
                               || allowedPunctuation.Contains(c);
                Assert.Equal(expected, QrPayload.TryParse("x" + c, out _));
            }
        }

        [Theory]
        [InlineData("EQ-001", true)]
        [InlineData("", false)]
        [InlineData("x/y", false)]
        public void Equipment_ids_use_the_same_alphabet(string id, bool valid)
        {
            Assert.Equal(valid, QrPayload.IsValidId(id, 64));
        }

        [Fact]
        public void Equipment_ids_are_capped_at_64()
        {
            Assert.True(QrPayload.IsValidId(new string('a', 64), 64));
            Assert.False(QrPayload.IsValidId(new string('a', 65), 64));
        }
    }
}
