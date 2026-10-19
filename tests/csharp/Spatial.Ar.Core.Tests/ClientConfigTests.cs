// SPEC-008 A6 / REQ-AR-005: build de release recusa token demo e http; dev permite.
using System.Linq;
using Xunit;

namespace Spatial.Ar.Core.Tests
{
    public class ClientConfigTests
    {
        private static string[] Errors(string url, string token, bool dev)
            => new ClientConfig(url, token, dev).Validate().ToArray();

        [Fact]
        public void Development_allows_demo_token_over_plain_http()
        {
            Assert.Empty(Errors("http://127.0.0.1:8088", "demo-operator-a", dev: true));
        }

        [Fact]
        public void Release_refuses_demo_token()
        {
            Assert.Contains("release-forbids-demo-token", Errors("https://api.example.com", "demo-operator-a", dev: false));
        }

        [Fact]
        public void Release_refuses_plain_http()
        {
            Assert.Contains("release-requires-https", Errors("http://api.example.com", "real-token-123", dev: false));
        }

        [Fact]
        public void Release_accepts_https_with_a_real_token()
        {
            Assert.Empty(Errors("https://api.example.com", "real-token-123", dev: false));
        }

        [Theory]
        [InlineData("")]
        [InlineData(null)]
        [InlineData("   ")]
        public void Empty_token_is_always_an_error(string token)
        {
            Assert.Contains("token-missing", Errors("http://127.0.0.1:8088", token, dev: true));
            Assert.Contains("token-missing", Errors("https://api.example.com", token, dev: false));
        }

        [Theory]
        [InlineData("")]
        [InlineData(null)]
        [InlineData("not a url")]
        [InlineData("ftp://host/x")]
        [InlineData("file:///etc/passwd")]
        [InlineData("javascript:alert(1)")]
        [InlineData("/relative/path")]
        public void Invalid_base_url_is_always_an_error(string url)
        {
            Assert.Contains("base-url-invalid", Errors(url, "demo-operator-a", dev: true));
        }

        [Fact]
        public void Credentials_embedded_in_the_url_are_refused()
        {
            Assert.Contains("base-url-has-credentials", Errors("https://user:pass@api.example.com", "t", dev: true));
        }

        [Fact]
        public void Base_url_is_normalised_without_trailing_slash()
        {
            Assert.Equal("http://127.0.0.1:8088", new ClientConfig("http://127.0.0.1:8088/", "t", true).BaseUrl);
        }

        [Fact]
        public void Debug_string_never_contains_the_token()
        {
            var text = new ClientConfig("http://127.0.0.1:8088", "demo-operator-a", true).ToString();

            Assert.DoesNotContain("demo-operator-a", text);
        }
    }
}
