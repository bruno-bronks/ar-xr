// COLA UNITY - NAO COMPILADA NEM EXECUTADA NESTA MAQUINA (sem Unity). Ver clients/ar-unity/README.md.
// Camera (ARCore) -> imagem de luminancia -> ZXing.Net -> texto bruto do QR. Toda decisao sobre o texto
// e do nucleo (QrPayload); aqui nao ha regra de negocio.
using System;
using System.Collections.Generic;
using Unity.Collections;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using ZXing;

namespace Spatial.Ar.Unity
{
    public sealed class QrScanner : MonoBehaviour
    {
        [SerializeField] private ARCameraManager cameraManager;
        [Tooltip("Decodifica 1 a cada N quadros (economia de CPU/bateria).")]
        [SerializeField] private int everyNthFrame = 6;

        private BarcodeReaderGeneric _reader;
        private int _frame;

        /// <summary>Texto bruto lido. NUNCA registrar em log.</summary>
        public event Action<string> Detected;

        private void Awake()
        {
            _reader = new BarcodeReaderGeneric();
            _reader.Options.PossibleFormats = new List<BarcodeFormat> { BarcodeFormat.QR_CODE };
            _reader.Options.TryHarder = false;
        }

        private void OnEnable() { if (cameraManager != null) cameraManager.frameReceived += OnFrame; }
        private void OnDisable() { if (cameraManager != null) cameraManager.frameReceived -= OnFrame; }

        private void OnFrame(ARCameraFrameEventArgs args)
        {
            if (++_frame % Mathf.Max(1, everyNthFrame) != 0) return;
            if (!cameraManager.TryAcquireLatestCpuImage(out XRCpuImage image)) return;

            using (image)
            {
                var width = image.width / 2;     // meia resolucao: suficiente para QR a 30-60 cm e 4x mais rapido
                var height = image.height / 2;
                var conversion = new XRCpuImage.ConversionParams
                {
                    inputRect = new RectInt(0, 0, image.width, image.height),
                    outputDimensions = new Vector2Int(width, height),
                    outputFormat = TextureFormat.R8,                    // luminancia
                    transformation = XRCpuImage.Transformation.None,
                };

                var buffer = new NativeArray<byte>(image.GetConvertedDataSize(conversion), Allocator.Temp);
                try
                {
                    image.Convert(conversion, buffer);
                    var source = new RGBLuminanceSource(buffer.ToArray(), width, height, RGBLuminanceSource.BitmapFormat.Gray8);
                    var result = _reader.Decode(source);
                    if (result != null && Detected != null) Detected(result.Text);
                }
                finally
                {
                    buffer.Dispose();
                }
            }
        }
    }
}
