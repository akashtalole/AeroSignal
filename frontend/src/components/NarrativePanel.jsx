import { SpeakableText } from "./SpeakableText.jsx";

export function NarrativePanel({ narrative }) {
  return (
    <div className="panel narrative-panel">
      <h2>Assessment</h2>
      {narrative ? (
        <SpeakableText text={narrative} />
      ) : (
        <p className="muted">Select a corridor to generate an assessment.</p>
      )}
    </div>
  );
}
