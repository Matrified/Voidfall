/** A short primer on how to play. VOIDFALL takes free-form input, so examples matter. */
export function HelpOverlay({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal help" role="dialog" aria-label="Help" onClick={(e) => e.stopPropagation()}>
        <h2>How to play</h2>
        <p>
          VOIDFALL understands plain English. Don't pick from a menu — just say what you
          want to do. The engine keeps the world honest; the story bends to you.
        </p>
        <div className="help-grid">
          <div>
            <h3 className="panel-title">Try typing</h3>
            <ul className="item-list">
              <li>look in the crack</li>
              <li>search the broken cart</li>
              <li>carefully go north</li>
              <li>draw my longsword</li>
              <li>pray at the altar</li>
              <li>attack the ghoul</li>
            </ul>
          </div>
          <div>
            <h3 className="panel-title">Keys</h3>
            <ul className="item-list">
              <li>↑ / ↓ — command history</li>
              <li>Tab — autocomplete</li>
              <li>Ctrl+S — save · Ctrl+L — load</li>
              <li>? — this help</li>
            </ul>
          </div>
        </div>
        <button className="modal-close" onClick={onClose}>
          close
        </button>
      </div>
    </div>
  );
}
