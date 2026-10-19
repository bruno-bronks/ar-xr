// COLA UNITY (EDITOR) - NAO COMPILADA NEM EXECUTADA NESTA MAQUINA. Ver clients/ar-unity/README.md.
// Menu "Spatial > Configure Android player settings": aplica as configuracoes minimas para ARCore.
// Revise no Player Settings: APIs de editor mudam entre versoes do Unity.
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Spatial.Ar.Unity.Editor
{
    public static class ProjectSetup
    {
        [MenuItem("Spatial/Configure Android player settings")]
        public static void ConfigureAndroid()
        {
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel24;   // ARCore exige API 24+
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.Portrait;

            // HTTP puro SOMENTE para desenvolvimento (adb reverse). Builds de release devem usar https:
            // o nucleo (ClientConfig) tambem recusa http fora de builds de desenvolvimento.
            PlayerSettings.insecureHttpOption = InsecureHttpOption.DevelopmentOnly;

            Debug.Log("[spatial] Android player settings aplicadas. Falta: habilitar o plug-in ARCore em "
                      + "Project Settings > XR Plug-in Management > Android.");
        }
    }
}
#endif
