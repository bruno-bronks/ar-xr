// COLA UNITY - NAO COMPILADA NEM EXECUTADA NESTA MAQUINA (sem Unity). Ver clients/ar-unity/README.md.
// Composition root do cliente AR: valida a configuracao (fail closed), liga scanner -> driver -> overlay.
// Nenhuma regra de negocio aqui: tudo vem do nucleo Spatial.Ar.Core.
using System;
using System.Collections.Generic;
using Spatial.Ar.Core;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

namespace Spatial.Ar.Unity
{
    public sealed class SpatialArApp : MonoBehaviour
    {
        [Header("Rede (D-014: adb reverse tcp:8088 tcp:8088)")]
        [SerializeField] private string baseUrl = "http://127.0.0.1:8088";
        [Tooltip("Token DEMO publico. Build de release RECUSA tokens 'demo-' e http.")]
        [SerializeField] private string token = "demo-operator-a";

        [Header("AR Foundation (na cena: XR Origin + AR Session)")]
        [SerializeField] private QrScanner scanner;
        [SerializeField] private ARRaycastManager raycastManager;
        [SerializeField] private ARAnchorManager anchorManager;
        [SerializeField] private Camera arCamera;

        private SessionDriver _driver;
        private MarkerSession _session;
        private readonly SessionOptions _options = new SessionOptions();
        private string _configError;
        private string _anchoredEquipmentId;
        private GameObject _anchorVisual;
        private GUIStyle _titleStyle, _bodyStyle;

        private sealed class UnityLog : IClientLog
        {
            // Somente codigos fixos do nucleo (ex.: "poll:Ok"); nunca token, URL, marker ou corpo.
            public void Info(string message) { Debug.Log("[spatial] " + message); }
        }

        private void Start()
        {
            var config = new ClientConfig(baseUrl, token, Application.isEditor || Debug.isDebugBuild);
            var errors = config.Validate();
            if (errors.Count > 0)
            {
                _configError = "Configuração recusada: " + string.Join(", ", errors);   // fail closed
                Debug.LogError("[spatial] " + _configError);
                enabled = true;       // continua desenhando a mensagem, mas NAO inicia rede nem camera
                return;
            }

            _session = new MarkerSession(_options);
            var client = new SpatialApiClient(new UnityWebRequestTransport(config.BaseUrl), token, TimeSpan.FromSeconds(5));
            _driver = new SessionDriver(_session, client, () => DateTimeOffset.UtcNow, new UnityLog());
            scanner.Detected += _driver.OnQrDetected;
        }

        private void OnDestroy()
        {
            if (_driver != null && scanner != null) scanner.Detected -= _driver.OnQrDetected;
        }

        private void Update()
        {
            if (_driver == null) return;
            _driver.Tick();
            var state = _driver.State;
            if (state.Phase != Phase.Live) { ClearAnchor(); return; }
            if (state.Equipment != null && state.Equipment.Id != _anchoredEquipmentId) PlaceAnchor(state.Equipment.Id);
            UpdateAnchorColor(state);
        }

        // --- ancoragem: melhor esforco; so e comprovada pelo checklist no aparelho (A3/A4) --------------
        private async void PlaceAnchor(string equipmentId)
        {
            _anchoredEquipmentId = equipmentId;
            ClearAnchor(keepId: true);
            try
            {
                // Premissa documentada: o operador centraliza o QR na tela. Raycast no centro; sem hit, 0,6 m a frente.
                var hits = new List<ARRaycastHit>();
                var center = new Vector2(Screen.width / 2f, Screen.height / 2f);
                var pose = raycastManager.Raycast(center, hits, TrackableType.FeaturePoint | TrackableType.PlaneWithinPolygon) && hits.Count > 0
                    ? hits[0].pose
                    : new Pose(arCamera.transform.position + arCamera.transform.forward * 0.6f, Quaternion.identity);

                var result = await anchorManager.TryAddAnchorAsync(pose);
                if (result.status.IsSuccess() && _anchoredEquipmentId == equipmentId)
                {
                    _anchorVisual = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    _anchorVisual.transform.SetParent(result.value.transform, false);
                    _anchorVisual.transform.localPosition = new Vector3(0f, 0.08f, 0f);
                    _anchorVisual.transform.localScale = Vector3.one * 0.05f;
                    Destroy(_anchorVisual.GetComponent<Collider>());
                }
            }
            catch (Exception)
            {
                Debug.Log("[spatial] anchor:error");   // sem detalhes: o overlay HUD continua funcionando
            }
        }

        private void UpdateAnchorColor(SessionState state)
        {
            if (_anchorVisual == null) return;
            var vm = OverlayViewModel.Build(state, DateTimeOffset.UtcNow, _options);
            _anchorVisual.GetComponent<Renderer>().material.color = ToColor(vm.Color, vm.IsStale);
        }

        private void ClearAnchor(bool keepId = false)
        {
            if (_anchorVisual != null) Destroy(_anchorVisual.transform.parent != null ? _anchorVisual.transform.parent.gameObject : _anchorVisual);
            _anchorVisual = null;
            if (!keepId) _anchoredEquipmentId = null;
        }

        // --- HUD (IMGUI: nao exige Canvas/fontes no projeto). Renderiza SOMENTE o OverlayViewModel. ------
        private void OnGUI()
        {
            if (_titleStyle == null)
            {
                var scale = Mathf.Max(1f, Screen.dpi / 160f);
                _titleStyle = new GUIStyle(GUI.skin.label) { fontSize = Mathf.RoundToInt(22 * scale), fontStyle = FontStyle.Bold, wordWrap = true };
                _bodyStyle = new GUIStyle(GUI.skin.label) { fontSize = Mathf.RoundToInt(16 * scale), wordWrap = true };
            }

            var width = Screen.width - 32f;
            var y = 16f;
            if (_configError != null)
            {
                GUI.color = Color.red;
                GUI.Label(new Rect(16, y, width, 200), _configError, _titleStyle);
                return;
            }

            if (_driver == null) return;
            var vm = OverlayViewModel.Build(_driver.State, DateTimeOffset.UtcNow, _options);
            GUI.color = Color.white;
            y = Line(vm.Title, _titleStyle, y, width);
            if (!string.IsNullOrEmpty(vm.StatusText))
            {
                GUI.color = ToColor(vm.Color, vm.IsStale);
                y = Line(vm.StatusText, _titleStyle, y, width);   // estado em TEXTO e cor (nunca so cor)
            }
            GUI.color = vm.IsStale ? new Color(1f, 0.6f, 0.2f) : Color.white;
            if (vm.Banner != null) y = Line(vm.Banner, _bodyStyle, y, width);
            GUI.color = Color.white;
            foreach (var line in vm.SensorLines) y = Line(line, _bodyStyle, y, width);
            foreach (var line in vm.AlertLines) y = Line("⚠ " + line, _bodyStyle, y, width);
        }

        private static float Line(string text, GUIStyle style, float y, float width)
        {
            var height = style.CalcHeight(new GUIContent(text), width);
            GUI.Label(new Rect(16, y, width, height), text, style);
            return y + height + 4f;
        }

        private static Color ToColor(StatusColor color, bool stale)
        {
            Color c;
            switch (color)
            {
                case StatusColor.Green: c = new Color(0.2f, 0.8f, 0.4f); break;
                case StatusColor.Amber: c = new Color(1f, 0.75f, 0.1f); break;
                case StatusColor.Red: c = new Color(0.95f, 0.25f, 0.25f); break;
                case StatusColor.Gray: c = new Color(0.7f, 0.7f, 0.75f); break;
                case StatusColor.Purple: c = new Color(0.7f, 0.55f, 1f); break;
                default: c = Color.white; break;
            }
            if (stale) c.a = 0.5f;   // atenuado quando desatualizado
            return c;
        }
    }
}
