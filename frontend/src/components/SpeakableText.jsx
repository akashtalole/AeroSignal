import { useState } from "react";
import { api } from "../api.js";

// Browser-native multilingual + voice layer: SpeechSynthesis reads the
// current text aloud (no API key needed, works wherever the browser
// supports it — notably Chrome), and the language toggle calls
// POST /api/translate, which itself only really translates in "gemini"
// mode; in "offline" mode it returns a note and we keep showing English
// rather than faking a translation.
const LANGUAGES = [
  { code: "en", label: "English", speechLang: "en-US" },
  { code: "hi", label: "हिंदी", speechLang: "hi-IN" },
  { code: "ta", label: "தமிழ்", speechLang: "ta-IN" },
];

const speechSupported = typeof window !== "undefined" && "speechSynthesis" in window;

export function SpeakableText({ text }) {
  const [lang, setLang] = useState("en");
  const [translated, setTranslated] = useState({});
  const [loading, setLoading] = useState(false);
  const [note, setNote] = useState(null);

  async function selectLang(code) {
    setLang(code);
    setNote(null);
    if (code === "en" || translated[code] || !text) return;
    setLoading(true);
    try {
      const res = await api.translate(text, code);
      if (res.translated_text) {
        setTranslated((prev) => ({ ...prev, [code]: res.translated_text }));
      } else {
        setNote(res.note || "Translation unavailable.");
      }
    } catch (e) {
      setNote(e.message);
    } finally {
      setLoading(false);
    }
  }

  function speak() {
    if (!speechSupported || !text) return;
    const active = LANGUAGES.find((l) => l.code === lang);
    const utterText = lang !== "en" && translated[lang] ? translated[lang] : text;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(utterText);
    utter.lang = active?.speechLang || "en-US";
    window.speechSynthesis.speak(utter);
  }

  if (!text) return null;

  const displayText = lang !== "en" && translated[lang] ? translated[lang] : text;

  return (
    <div className="speakable">
      <div className="speakable-controls">
        <div className="lang-toggle" role="group" aria-label="Language">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              className={lang === l.code ? "active" : ""}
              onClick={() => selectLang(l.code)}
            >
              {l.label}
            </button>
          ))}
        </div>
        {speechSupported && (
          <button type="button" className="speak-btn" onClick={speak} title="Read aloud">
            🔊 Read aloud
          </button>
        )}
      </div>
      {loading && <p className="muted small">Translating…</p>}
      {note && <p className="muted small">{note}</p>}
      <p className="speakable-text">{displayText}</p>
    </div>
  );
}
