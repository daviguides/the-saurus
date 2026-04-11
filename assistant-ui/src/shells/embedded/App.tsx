/**
 * Embedded shell stub — re-exports standalone App.
 *
 * Exposed as federated module `./EmbeddedApp` for host consumption.
 * Task #2 (embedded-shell-adapter) replaces this with the real
 * embedded shell accepting props (isOpen, isDark, onClose, context).
 */
import "../../index.css";
import App from "../standalone/App";

export default App;
