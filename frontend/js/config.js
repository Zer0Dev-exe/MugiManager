// Configuración de MugiManager.
// - Desarrollo local (python main.py en el puerto 8000): el backend sirve también la web, apiBase vacío.
// - GitHub Pages y app móvil: la API está desplegada en Vercel.
(function () {
  const REMOTE_API = "https://mugimanager.vercel.app";
  const { hostname, port } = window.location;
  const isLocalServer = (hostname === "127.0.0.1" || hostname === "localhost") && port === "8000";
  window.MUGI_CONFIG = { apiBase: isLocalServer ? "" : REMOTE_API };
})();
