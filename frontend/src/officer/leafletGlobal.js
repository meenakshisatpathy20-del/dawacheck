// leaflet.heat attaches to a global `L`; set it before the plugin module runs.
import L from "leaflet";

window.L = L;
export default L;
