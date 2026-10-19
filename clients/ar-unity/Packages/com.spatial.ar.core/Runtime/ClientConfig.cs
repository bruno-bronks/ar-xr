// Configuracao do cliente (SPEC-008, REQ-AR-005): build de release recusa token demo e http puro.
using System;
using System.Collections.Generic;

namespace Spatial.Ar.Core
{
    public sealed class ClientConfig
    {
        public const string DemoTokenPrefix = "demo-";

        public ClientConfig(string baseUrl, string token, bool isDevelopmentBuild)
        {
            BaseUrl = (baseUrl ?? string.Empty).Trim().TrimEnd('/');
            Token = token;
            IsDevelopmentBuild = isDevelopmentBuild;
        }

        public string BaseUrl { get; }
        public string Token { get; }
        public bool IsDevelopmentBuild { get; }

        /// <summary>Codigos de erro estaveis (vazio = valida). Chamar na inicializacao e recusar iniciar se houver.</summary>
        public IReadOnlyList<string> Validate()
        {
            var errors = new List<string>();
            if (string.IsNullOrWhiteSpace(Token)) errors.Add("token-missing");

            if (!Uri.TryCreate(BaseUrl, UriKind.Absolute, out var uri)
                || (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
            {
                errors.Add("base-url-invalid");
            }
            else
            {
                if (!string.IsNullOrEmpty(uri.UserInfo)) errors.Add("base-url-has-credentials");
                if (!IsDevelopmentBuild && uri.Scheme == Uri.UriSchemeHttp) errors.Add("release-requires-https");
            }

            if (!IsDevelopmentBuild && Token != null && Token.StartsWith(DemoTokenPrefix, StringComparison.OrdinalIgnoreCase))
                errors.Add("release-forbids-demo-token");
            return errors;
        }

        /// <summary>Nunca inclui o token (REQ-AR-005).</summary>
        public override string ToString() => "ClientConfig(BaseUrl=" + BaseUrl + ", Token=***, Development=" + IsDevelopmentBuild + ")";
    }
}
