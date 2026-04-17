import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toPng } from 'html-to-image';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type BgShape = 'none' | 'rectangle' | 'rounded' | 'side-lines';
type Position = 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right' | 'center';
type WatermarkPosition = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
type AspectRatio = '1:1' | '2:3';
// Alignment is separate from layout position — controls text-align within the block
type TextAlign = 'left' | 'center' | 'right';

interface TextElementStyle {
  font: string;
  fontSize: number;
  color: string;
  bgShape: BgShape;
  bgColor: string;
  position: Position;
  textAlign: TextAlign;
}

interface GradientSettings {
  color: string;
  angle: number;
  coverage: number;  // 0–100 — where solid→transparent transition ends
  opacity: number;   // 0–100 — opacity of the solid color block
  feather: number;   // px — width of the transition zone (narrow = sharp edge)
}

interface WatermarkStyle {
  position: WatermarkPosition;
  padding: number;
  font: string;
  fontSize: number;
  color: string;
}

export interface StoryStyle {
  id: string;
  name: string;
  alert: TextElementStyle;
  title: TextElementStyle;
  description: TextElementStyle;
  footer1: TextElementStyle;
  footer2: TextElementStyle;
  gradient: GradientSettings;
  bgColor: string;
  watermark: WatermarkStyle;
  aspectRatio: AspectRatio;
  // Shared position for the alert+title+description group
  bodyPosition: Position;
}

interface StoryContent {
  watermarkText: string;
  watermarkImageUrl: string | null;
  alertText: string;
  titleText: string;
  descriptionText: string;
  footer1Text: string;
  footer2Text: string;
  imageUrl: string | null;
  imageX: number;
  imageY: number;
  imageScale: number;
}

// ─────────────────────────────────────────────
// Storage Keys
// ─────────────────────────────────────────────

const STORAGE_KEY = 'storymaker_styles';
const WATERMARK_KEY = 'storymaker_watermark';
const CURRENT_STYLE_KEY = 'storymaker_current_style';

// ─────────────────────────────────────────────
// Defaults
// ─────────────────────────────────────────────

const defaultTextStyle = (position: Position = 'bottom-left', textAlign: TextAlign = 'left'): TextElementStyle => ({
  font: 'Impact',
  fontSize: 32,
  color: '#ffffff',
  bgShape: 'none',
  bgColor: 'rgba(0,0,0,0.5)',
  position,
  textAlign,
});

const defaultStyle = (): StoryStyle => ({
  id: Date.now().toString(),
  name: 'My Style',
  alert: { ...defaultTextStyle('bottom-left', 'left'), color: '#FF4444', bgShape: 'rounded', bgColor: 'rgba(255,68,68,0.15)', fontSize: 18, font: 'Impact' },
  title: { ...defaultTextStyle('bottom-left', 'left'), fontSize: 36, font: 'Impact' },
  description: { ...defaultTextStyle('bottom-left', 'left'), fontSize: 20, color: '#dddddd' },
  footer1: { ...defaultTextStyle('bottom-left', 'left'), fontSize: 15, color: '#aaaaaa' },
  footer2: { ...defaultTextStyle('bottom-right', 'right'), fontSize: 14, color: '#888888' },
  gradient: { color: '#000000', angle: 180, coverage: 60, opacity: 90, feather: 40 },
  bgColor: '#1a1a1a',
  watermark: { position: 'top-right', padding: 16, font: 'Arial', fontSize: 14, color: '#ffffff' },
  aspectRatio: '2:3',
  bodyPosition: 'bottom-left',
});

const loadSavedCurrentStyle = (): StoryStyle => {
  try {
    const raw = localStorage.getItem(CURRENT_STYLE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      // Merge with defaults to handle missing fields from older versions
      const base = defaultStyle();
      return {
        ...base,
        ...parsed,
        alert:       { ...base.alert,       ...(parsed.alert || {}) },
        title:       { ...base.title,       ...(parsed.title || {}) },
        description: { ...base.description, ...(parsed.description || {}) },
        footer1:     { ...base.footer1,     ...(parsed.footer1 || {}) },
        footer2:     { ...base.footer2,     ...(parsed.footer2 || {}) },
        watermark:   { ...base.watermark,   ...(parsed.watermark || {}) },
        gradient:    { ...base.gradient,    ...(parsed.gradient || {}),
        opacity: parsed.gradient?.opacity ?? 90,
        feather:  parsed.gradient?.feather  ?? 40,
      },
        bodyPosition: parsed.bodyPosition || 'bottom-left',
      };
    }
  } catch {}
  return defaultStyle();
};

const loadSavedWatermark = (): string => {
  try {
    return localStorage.getItem(WATERMARK_KEY) || '@MrSinghExperience';
  } catch {}
  return '@MrSinghExperience';
};

const defaultContent = (): StoryContent => ({
  watermarkText: loadSavedWatermark(),
  watermarkImageUrl: null,
  alertText: 'BREAKING 🚨',
  titleText: 'Your headline goes here in all its bold glory',
  descriptionText: 'Add your supporting description text here to provide more context.',
  footer1Text: 'Source Name',
  footer2Text: 'Location / Date',
  imageUrl: null,
  imageX: 0,
  imageY: 0,
  imageScale: 1,
});

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function loadGoogleFont(fontName: string) {
  if (!fontName || ['Arial', 'Impact', 'Georgia', 'Times New Roman', 'Courier New', 'Verdana'].includes(fontName)) return;
  const id = `gf-${fontName.replace(/\s/g, '-')}`;
  if (document.getElementById(id)) return;
  const link = document.createElement('link');
  link.id = id;
  link.rel = 'stylesheet';
  link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(fontName).replace(/%20/g, '+')}:wght@400;700&display=swap`;
  document.head.appendChild(link);
}

function positionToCSS(pos: Position): React.CSSProperties {
  const map: Record<Position, React.CSSProperties> = {
    'top-left':      { top: 0, left: 0, right: 0 },
    'top-center':    { top: 0, left: 0, right: 0 },
    'top-right':     { top: 0, left: 0, right: 0 },
    'center':        { top: '30%', left: 0, right: 0 },
    'bottom-left':   { bottom: 0, left: 0, right: 0 },
    'bottom-center': { bottom: 0, left: 0, right: 0 },
    'bottom-right':  { bottom: 0, left: 0, right: 0 },
  };
  return map[pos] || map['bottom-left'];
}

function alignFromPosition(pos: Position): React.CSSProperties['textAlign'] {
  if (pos.includes('right')) return 'right';
  if (pos.includes('center')) return 'center';
  return 'left';
}

function watermarkPositionToCSS(pos: WatermarkPosition, padding: number): React.CSSProperties {
  const map: Record<WatermarkPosition, React.CSSProperties> = {
    'top-left':     { top: padding, left: padding },
    'top-right':    { top: padding, right: padding },
    'bottom-left':  { bottom: padding, left: padding },
    'bottom-right': { bottom: padding, right: padding },
    'center':       { top: '50%', left: '50%', transform: 'translate(-50%,-50%)' },
  };
  return map[pos] || map['top-right'];
}

function bgShapeStyle(shape: BgShape, color: string): React.CSSProperties {
  if (shape === 'none' || shape === 'side-lines') return {}; // side-lines handled separately via renderWithBg
  return {
    background: color,
    padding: '4px 10px',
    borderRadius: shape === 'rounded' ? '6px' : '2px',
  };
}

// Renders text element, applying bgShape including side-lines
function renderTextEl(text: string, s: TextElementStyle, align: React.CSSProperties['textAlign']): React.ReactNode {
  const baseStyle: React.CSSProperties = {
    fontFamily: `'${s.font}', ${s.font}, sans-serif`,
    fontSize: s.fontSize,
    color: s.color,
    lineHeight: 1.25,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    textAlign: (s.textAlign as React.CSSProperties['textAlign']) || align,
  };
  if (s.bgShape === 'side-lines') {
    const lineColor = s.bgColor && s.bgColor.startsWith('#') ? s.bgColor : s.color;
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%' }}>
        <div style={{ flex: 1, height: 2, background: lineColor, opacity: 0.8 }} />
        <span style={{ ...baseStyle, whiteSpace: 'nowrap', textAlign: 'center' }}>{text}</span>
        <div style={{ flex: 1, height: 2, background: lineColor, opacity: 0.8 }} />
      </div>
    );
  }
  return (
    <div style={{ display: 'block', ...baseStyle, ...bgShapeStyle(s.bgShape, s.bgColor) }}>
      {text}
    </div>
  );
}

// ─────────────────────────────────────────────
// Story Card Component
// ─────────────────────────────────────────────

interface StoryCardProps {
  content: StoryContent;
  style: StoryStyle;
  cardRef?: React.RefObject<HTMLDivElement | null>;
  interactive?: boolean;
  onDragImage?: (dx: number, dy: number) => void;
  onDropFile?: (file: File) => void;
}

const StoryCard: React.FC<StoryCardProps> = ({ content, style, cardRef, interactive, onDragImage, onDropFile }) => {
  const dragStart = useRef<{ x: number; y: number } | null>(null);
  const [isFileDragOver, setIsFileDragOver] = useState(false);

  const cardW = style.aspectRatio === '1:1' ? 500 : 360;
  const cardH = style.aspectRatio === '1:1' ? 500 : 540;

  const { gradient } = style;

  // Parse hex color to RGBA so we can control opacity independently
  const hexToRgb = (hex: string): [number, number, number] => {
    const clean = hex.replace('#', '');
    const full = clean.length === 3
      ? clean.split('').map(c => c + c).join('')
      : clean;
    return [
      parseInt(full.substring(0, 2), 16) || 0,
      parseInt(full.substring(2, 4), 16) || 0,
      parseInt(full.substring(4, 6), 16) || 0,
    ];
  };

  const [r, g, b] = hexToRgb(gradient.color);
  const opacity = (gradient.opacity ?? 100) / 100;
  // feather is in px; convert to % relative to the card height
  const featherPx = gradient.feather ?? 40;
  const cardDim = (style.aspectRatio === '1:1') ? 500 : 540; // height of card
  const featherPct = Math.min((featherPx / cardDim) * 100, gradient.coverage ?? 60);
  const solidEnd = Math.max(0, (gradient.coverage ?? 60) - featherPct);
  // Result: solid block [0 → solidEnd%]  feather [solidEnd% → coverage%]  transparent [coverage% → 100%]
  const solidColor = `rgba(${r},${g},${b},${opacity})`;
  const gradientCSS = `linear-gradient(${gradient.angle}deg, ${solidColor} 0%, ${solidColor} ${solidEnd.toFixed(1)}%, rgba(${r},${g},${b},0) ${(gradient.coverage ?? 60).toFixed(1)}%)`;

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!interactive || !onDragImage) return;
    // Don't start image-pan drag if a file is being dragged over
    if (isFileDragOver) return;
    dragStart.current = { x: e.clientX, y: e.clientY };
    e.preventDefault();
  };

  // File drag-and-drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    if (!interactive || !onDropFile) return;
    if (e.dataTransfer.types.includes('Files')) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
      setIsFileDragOver(true);
    }
  };
  const handleDragLeave = (e: React.DragEvent) => {
    // Only clear if truly leaving the card (not entering a child)
    if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) {
      setIsFileDragOver(false);
    }
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsFileDragOver(false);
    if (!interactive || !onDropFile) return;
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      onDropFile(file);
    }
  };

  useEffect(() => {
    if (!interactive || !onDragImage) return;
    const handleMove = (e: MouseEvent) => {
      if (!dragStart.current) return;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      dragStart.current = { x: e.clientX, y: e.clientY };
      onDragImage(dx, dy);
    };
    const handleUp = () => { dragStart.current = null; };
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => { window.removeEventListener('mousemove', handleMove); window.removeEventListener('mouseup', handleUp); };
  }, [interactive, onDragImage]);

  // ── Body group: Alert + Title + Description share bodyPosition ──
  // Guard against old saved styles that may not have bodyPosition
  const bodyPos: Position = (style.bodyPosition as Position) || 'bottom-left';
  const bodyAlign = alignFromPosition(bodyPos);
  const bodyCSS = positionToCSS(bodyPos);

  const bodyElems = [
    { text: content.alertText, s: style.alert, key: 'alert' },
    { text: content.titleText, s: style.title, key: 'title' },
    { text: content.descriptionText, s: style.description, key: 'desc' },
  ].filter(el => el.text);

  // ── Footer elements use their own positions ──
  const renderFooter = (text: string, s: TextElementStyle, key: string) => {
    if (!text) return null;
    const pos: Position = (s.position as Position) || 'bottom-left';
    const pCSS = positionToCSS(pos);
    const align: React.CSSProperties['textAlign'] = (s.textAlign as TextAlign) || alignFromPosition(pos);
    return (
      <div key={key} style={{
        position: 'absolute',
        padding: '10px 14px',
        width: '100%',
        boxSizing: 'border-box',
        ...pCSS,
        textAlign: align,
      }}>
        {renderTextEl(text, s, align)}
      </div>
    );
  };

  return (
    <div
      ref={cardRef}
      style={{
        position: 'relative',
        width: cardW,
        height: cardH,
        background: style.bgColor,
        overflow: 'hidden',
        flexShrink: 0,
        cursor: interactive ? (content.imageUrl ? 'grab' : 'copy') : 'default',
        userSelect: 'none',
      }}
      onMouseDown={handleMouseDown}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Layer 1: Image — shown uncropped, card overflow:hidden provides clipping */}
      {content.imageUrl && (
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
          <img
            src={content.imageUrl}
            alt="story"
            draggable={false}
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              // Show at natural aspect via height=100%, let width be auto
              // Card overflow:hidden clips it — user can drag to reframe
              height: `${content.imageScale * 100}%`,
              width: 'auto',
              maxWidth: 'none',
              transform: `translate(calc(-50% + ${content.imageX}px), calc(-50% + ${content.imageY}px))`,
              transformOrigin: 'center center',
            }}
          />
        </div>
      )}

      {/* Layer 2: Gradient overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        background: gradientCSS,
        pointerEvents: 'none',
      }} />

      {/* Layer 3a: Body group (Alert + Title + Description) — single unit, shared position */}
      <div style={{
        position: 'absolute',
        padding: '14px',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        textAlign: bodyAlign,
        width: '100%',
        boxSizing: 'border-box',
        ...bodyCSS,
      }}>
        {bodyElems.map(el => (
          <div key={el.key}>
            {renderTextEl(el.text, el.s, (el.s.textAlign as React.CSSProperties['textAlign']) || bodyAlign)}
          </div>
        ))}
      </div>

      {/* Layer 3b: Footer 1 & Footer 2 — independent positions */}
      {renderFooter(content.footer1Text, style.footer1, 'f1')}
      {renderFooter(content.footer2Text, style.footer2, 'f2')}

      {/* Layer 4: Watermark */}
      {(content.watermarkText || content.watermarkImageUrl) && (
        <div style={{
          position: 'absolute',
          pointerEvents: 'none',
          zIndex: 10,
          ...watermarkPositionToCSS(style.watermark.position, style.watermark.padding),
        }}>
          {content.watermarkImageUrl ? (
            <img src={content.watermarkImageUrl} alt="watermark" style={{ maxHeight: 48, maxWidth: 120, objectFit: 'contain' }} />
          ) : (
            <span style={{
              fontFamily: `'${style.watermark.font}', ${style.watermark.font}, sans-serif`,
              fontSize: style.watermark.fontSize,
              color: style.watermark.color,
              fontWeight: 'bold',
              textShadow: '0 1px 3px rgba(0,0,0,0.8)',
            }}>
              {content.watermarkText}
            </span>
          )}
        </div>
      )}

      {/* Layer 5: File drop zone overlay (interactive only) */}
      {isFileDragOver && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 20,
          border: '3px dashed #7c3aed',
          background: 'rgba(124,58,237,0.25)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 8,
          pointerEvents: 'none',
        }}>
          <div style={{ fontSize: 40 }}>🖼️</div>
          <p style={{ color: '#a78bfa', fontWeight: 700, fontSize: 16, margin: 0, textShadow: '0 1px 4px rgba(0,0,0,0.8)' }}>
            Drop image here
          </p>
        </div>
      )}

      {/* Layer 6: No-image placeholder hint (interactive, no image yet) */}
      {interactive && !content.imageUrl && !isFileDragOver && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 1,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 8,
          pointerEvents: 'none',
        }}>
          <div style={{ fontSize: 32, opacity: 0.25 }}>🖼️</div>
          <p style={{ color: '#555', fontSize: 12, margin: 0, textAlign: 'center' }}>Drag &amp; drop an image here<br/>or use the sidebar uploader</p>
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────
// Text Style Editor (collapsible advanced panel)
// No position control for alert/title/desc — they use bodyPosition
// ─────────────────────────────────────────────

interface TextStyleEditorProps {
  label: string;
  value: TextElementStyle;
  onChange: (v: TextElementStyle) => void;
  hidePosition?: boolean;
}

const TextStyleEditor: React.FC<TextStyleEditorProps> = ({ label, value, onChange, hidePosition }) => {
  const [open, setOpen] = useState(false);
  const up = (k: keyof TextElementStyle, v: any) => {
    if (k === 'font') loadGoogleFont(v);
    onChange({ ...value, [k]: v });
  };

  const positions: Position[] = ['top-left','top-center','top-right','center','bottom-left','bottom-center','bottom-right'];
  const alignments: TextAlign[] = ['left', 'center', 'right'];

  return (
    <div style={{ marginTop: 4 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          background: 'none', border: '1px solid #333', color: '#aaa',
          fontSize: 11, padding: '2px 8px', borderRadius: 4, cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 4,
        }}
      >
        <span style={{ transform: open ? 'rotate(90deg)' : 'rotate(0)', display: 'inline-block', transition: '0.2s' }}>▶</span>
        Advanced {label}
      </button>
      {open && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8, padding: '10px', background: '#1a1a1a', borderRadius: 8, border: '1px solid #2a2a2a' }}>
          {!hidePosition && (
            <label style={labelStyle}>Position
              <select value={value.position} onChange={e => up('position', e.target.value as Position)} style={selectStyle}>
                {positions.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </label>
          )}
          <label style={labelStyle}>Text Align
            <div style={{ display: 'flex', gap: 6 }}>
              {alignments.map(a => (
                <button key={a} onClick={() => up('textAlign', a)} style={{
                  flex: 1, padding: '5px', border: `1px solid ${value.textAlign === a ? '#7c3aed' : '#333'}`,
                  borderRadius: 4, background: value.textAlign === a ? '#7c3aed22' : '#0d0d0d',
                  color: value.textAlign === a ? '#a78bfa' : '#888', cursor: 'pointer', fontSize: 12,
                }}>
                  {a === 'left' ? '⬅' : a === 'center' ? '↔' : '➡'}
                </button>
              ))}
            </div>
          </label>
          <label style={labelStyle}>Google Font
            <input style={inputStyle} value={value.font} onChange={e => up('font', e.target.value)} placeholder="e.g. Bebas Neue" onBlur={e => loadGoogleFont(e.target.value)} />
          </label>
          <label style={labelStyle}>Size: {value.fontSize}px
            <input type="range" min={10} max={80} value={value.fontSize} onChange={e => up('fontSize', Number(e.target.value))} style={{ width: '100%', accentColor: '#7c3aed' }} />
          </label>
          <label style={labelStyle}>Text Color
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="color" value={value.color} onChange={e => up('color', e.target.value)} style={colorPickerStyle} />
              <span style={{ fontSize: 11, color: '#777', fontFamily: 'monospace' }}>{value.color}</span>
            </div>
          </label>
          <label style={labelStyle}>Background Style
            <select value={value.bgShape} onChange={e => up('bgShape', e.target.value as BgShape)} style={selectStyle}>
              <option value="none">None</option>
              <option value="rectangle">Rectangle (fill)</option>
              <option value="rounded">Rounded (fill)</option>
              <option value="side-lines">Side Lines ——text——</option>
            </select>
          </label>
          {(value.bgShape === 'rectangle' || value.bgShape === 'rounded' || value.bgShape === 'side-lines') && (
            <label style={labelStyle}>{value.bgShape === 'side-lines' ? 'Line Color' : 'Background Color'}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="color" value={value.bgColor.startsWith('#') ? value.bgColor : '#ffffff'} onChange={e => up('bgColor', e.target.value)} style={colorPickerStyle} />
                <span style={{ fontSize: 11, color: '#777', fontFamily: 'monospace' }}>{value.bgColor}</span>
              </div>
            </label>
          )}
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────
// Style constants
// ─────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 4,
  fontSize: 12, color: '#888', fontWeight: 600,
};
const inputStyle: React.CSSProperties = {
  background: '#0d0d0d', border: '1px solid #333', borderRadius: 6,
  color: '#ddd', padding: '6px 10px', fontSize: 13, outline: 'none', width: '100%',
};
const textareaStyle: React.CSSProperties = { ...inputStyle, resize: 'vertical', minHeight: 56 };
const selectStyle: React.CSSProperties = { ...inputStyle };
const colorPickerStyle: React.CSSProperties = {
  width: 32, height: 32, padding: 0, border: 'none',
  background: 'none', cursor: 'pointer', borderRadius: 4,
};
const topBtnStyle: React.CSSProperties = {
  padding: '7px 14px', background: '#111', border: '1px solid #2a2a2a', borderRadius: 8,
  color: '#aaa', cursor: 'pointer', fontSize: 13, fontWeight: 600,
  transition: 'border-color 0.15s',
};

// ─────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────

export const StoryMakerPage: React.FC = () => {
  const navigate = useNavigate();
  const previewRef = useRef<HTMLDivElement | null>(null);

  const [content, setContent] = useState<StoryContent>(() => defaultContent());
  const [currentStyle, setCurrentStyle] = useState<StoryStyle>(() => loadSavedCurrentStyle());
  const [savedStyles, setSavedStyles] = useState<StoryStyle[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed: any[] = JSON.parse(raw);
      const base = defaultStyle();
      // Migrate old styles — merge with defaults to fill missing fields
      return parsed.map(s => ({
        ...base,
        ...s,
        alert:       { ...base.alert,       ...(s.alert || {}) },
        title:       { ...base.title,       ...(s.title || {}) },
        description: { ...base.description, ...(s.description || {}) },
        footer1:     { ...base.footer1,     ...(s.footer1 || {}) },
        footer2:     { ...base.footer2,     ...(s.footer2 || {}) },
        watermark:   { ...base.watermark,   ...(s.watermark || {}) },
        gradient:    { ...base.gradient,    ...(s.gradient || {}),
          opacity: s.gradient?.opacity ?? 90,
          feather:  s.gradient?.feather  ?? 40,
        },
        bodyPosition: s.bodyPosition || 'bottom-left',
      }));
    } catch { return []; }
  });
  // 'preview' | 'grid'
  const [rightView, setRightView] = useState<'preview' | 'grid'>('preview');
  const [downloading, setDownloading] = useState<string | null>(null);
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);
  const [watermarkOpen, setWatermarkOpen] = useState(false);

  // Persist saved styles list
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(savedStyles)); } catch {}
  }, [savedStyles]);

  // Persist current working style (so tweaks are remembered)
  useEffect(() => {
    try { localStorage.setItem(CURRENT_STYLE_KEY, JSON.stringify(currentStyle)); } catch {}
  }, [currentStyle]);

  // Persist watermark text whenever it changes
  useEffect(() => {
    try { localStorage.setItem(WATERMARK_KEY, content.watermarkText); } catch {}
  }, [content.watermarkText]);

  // Load Google fonts from saved styles
  useEffect(() => {
    savedStyles.forEach(s => {
      loadGoogleFont(s.alert.font);
      loadGoogleFont(s.title.font);
      loadGoogleFont(s.description.font);
      loadGoogleFont(s.footer1.font);
      loadGoogleFont(s.footer2.font);
      loadGoogleFont(s.watermark.font);
    });
  }, [savedStyles]);

  const updContent = (k: keyof StoryContent, v: any) => setContent(c => ({ ...c, [k]: v }));
  const updStyle = (k: keyof StoryStyle, v: any) => setCurrentStyle(s => ({ ...s, [k]: v }));
  const updGradient = (k: keyof GradientSettings, v: any) => setCurrentStyle(s => ({ ...s, gradient: { ...s.gradient, [k]: v } }));
  const updWatermark = (k: keyof WatermarkStyle, v: any) => setCurrentStyle(s => ({ ...s, watermark: { ...s.watermark, [k]: v } }));

  const handleImageUpload = (file: File | null) => {
    if (file) {
      const url = URL.createObjectURL(file);
      updContent('imageUrl', url);
      updContent('imageX', 0);
      updContent('imageY', 0);
      updContent('imageScale', 1);
    } else {
      updContent('imageUrl', null);
    }
  };

  const handleWatermarkImageUpload = (file: File | null) => {
    if (file) {
      updContent('watermarkImageUrl', URL.createObjectURL(file));
    } else {
      updContent('watermarkImageUrl', null);
    }
  };

  const handleDragImage = useCallback((dx: number, dy: number) => {
    setContent(c => ({ ...c, imageX: c.imageX + dx, imageY: c.imageY + dy }));
  }, []);

  const handleSaveStyle = () => {
    const name = prompt('Name this style:', currentStyle.name) || currentStyle.name;
    // Preserve current style name for next time, just update id for uniqueness
    const newStyle = { ...currentStyle, id: Date.now().toString(), name };
    loadGoogleFont(newStyle.title.font);
    setSavedStyles(prev => [...prev, newStyle]);
    // Keep current style as-is (do not reset) so user can keep tweaking
    setCurrentStyle(s => ({ ...s, name }));
    setRightView('grid');
  };

  const handleDeleteStyle = (id: string) => {
    setSavedStyles(prev => prev.filter(s => s.id !== id));
  };

  const handleDownload = async (storyStyle: StoryStyle) => {
    const styleId = storyStyle.id;
    setDownloading(styleId);
    try {
      const cW = storyStyle.aspectRatio === '1:1' ? 500 : 360;
      const cH = storyStyle.aspectRatio === '1:1' ? 500 : 540;

      // Render a fresh card into a temporary offscreen container
      // placed at top:0, left outside viewport (not zIndex:-1) so html-to-image can paint it
      const host = document.createElement('div');
      host.style.cssText = `position:fixed;top:0;left:-${cW + 10}px;width:${cW}px;height:${cH}px;overflow:hidden;z-index:9999;pointer-events:none;`;
      document.body.appendChild(host);

      // Use React 18 createRoot to render the card temporarily
      const { createRoot } = await import('react-dom/client');
      const root = createRoot(host);
      // Render with a static snapshot of content/style (capture current values)
      const snapContent = { ...content };
      root.render(
        React.createElement(StoryCard, { content: snapContent, style: storyStyle })
      );

      // Wait for paint
      await new Promise(r => setTimeout(r, 300));

      const cardEl = host.firstElementChild as HTMLElement;
      if (!cardEl) throw new Error('No card rendered');

      const dataUrl = await toPng(cardEl, { pixelRatio: 3 });
      const link = document.createElement('a');
      link.download = `story_${storyStyle.name.replace(/\s+/g, '_')}.png`;
      link.href = dataUrl;
      link.click();

      root.unmount();
      document.body.removeChild(host);
    } catch (e) {
      console.error('Download failed:', e);
      alert('Download failed. Please try again.');
    }
    setDownloading(null);
  };

  const positions: Position[] = ['top-left','top-center','top-right','center','bottom-left','bottom-center','bottom-right'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#0a0a0a', color: '#fff', fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* Top Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px', borderBottom: '1px solid #1e1e1e', background: '#0d0d0d' }}>
        <button onClick={() => navigate(-1)} style={topBtnStyle}>← Back</button>
        <button onClick={() => navigate('/')} style={topBtnStyle}>🏠 Home</button>
        <div style={{ flex: 1 }} />
        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#7c3aed', letterSpacing: '0.02em' }}>✨ Story Maker</h2>
      </div>

      {/* Body */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* ─── LEFT SIDEBAR ─── */}
        <div style={{
          width: 320, minWidth: 300, overflowY: 'auto', padding: '16px',
          borderRight: '1px solid #1e1e1e', background: '#0d0d0d',
          display: 'flex', flexDirection: 'column', gap: 14,
        }}>

          {/* Canvas */}
          <SectionCard title="Canvas">
            <div style={{ display: 'flex', gap: 8 }}>
              {(['1:1', '2:3'] as AspectRatio[]).map(ar => (
                <button key={ar} onClick={() => updStyle('aspectRatio', ar)} style={{
                  flex: 1, padding: '8px',
                  border: `2px solid ${currentStyle.aspectRatio === ar ? '#7c3aed' : '#333'}`,
                  borderRadius: 8, background: currentStyle.aspectRatio === ar ? '#7c3aed22' : '#111',
                  color: currentStyle.aspectRatio === ar ? '#a78bfa' : '#888', cursor: 'pointer', fontWeight: 700, fontSize: 14,
                }}>
                  {ar}
                </button>
              ))}
            </div>
            <label style={{ ...labelStyle, marginTop: 4 }}>Background Color
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="color" value={currentStyle.bgColor} onChange={e => updStyle('bgColor', e.target.value)} style={colorPickerStyle} />
                <span style={{ color: '#777', fontSize: 11, fontFamily: 'monospace' }}>{currentStyle.bgColor}</span>
              </div>
            </label>
          </SectionCard>

          {/* Gradient */}
          <SectionCard title="Background Gradient">
            <label style={labelStyle}>Color
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="color" value={currentStyle.gradient.color} onChange={e => updGradient('color', e.target.value)} style={colorPickerStyle} />
                <span style={{ color: '#777', fontSize: 11, fontFamily: 'monospace' }}>{currentStyle.gradient.color}</span>
              </div>
            </label>
            <label style={labelStyle}>Angle: {currentStyle.gradient.angle}°
              <input type="range" min={0} max={360} value={currentStyle.gradient.angle} onChange={e => updGradient('angle', Number(e.target.value))} style={{ width: '100%', accentColor: '#7c3aed' }} />
            </label>
            <label style={labelStyle}>Opacity: {currentStyle.gradient.opacity ?? 100}%
              <input type="range" min={0} max={100} value={currentStyle.gradient.opacity ?? 100} onChange={e => updGradient('opacity', Number(e.target.value))} style={{ width: '100%', accentColor: '#7c3aed' }} />
            </label>
            <label style={labelStyle}>Coverage (solid end): {currentStyle.gradient.coverage ?? 60}%
              <input type="range" min={0} max={100} value={currentStyle.gradient.coverage ?? 60} onChange={e => updGradient('coverage', Number(e.target.value))} style={{ width: '100%', accentColor: '#7c3aed' }} />
            </label>
            <label style={labelStyle}>Feather width: {currentStyle.gradient.feather ?? 40}px
              <input type="range" min={0} max={200} value={currentStyle.gradient.feather ?? 40} onChange={e => updGradient('feather', Number(e.target.value))} style={{ width: '100%', accentColor: '#7c3aed' }} />
            </label>
            {/* Visual preview bar */}
            <div style={{
              height: 12, borderRadius: 6, marginTop: 2,
              background: (() => {
                const g = currentStyle.gradient;
                const hex = g.color.replace('#', '');
                const r2 = parseInt(hex.substring(0,2),16)||0;
                const g2 = parseInt(hex.substring(2,4),16)||0;
                const b2 = parseInt(hex.substring(4,6),16)||0;
                const op = (g.opacity ?? 100) / 100;
                const cardDim2 = 540;
                const fp = Math.min(((g.feather ?? 40) / cardDim2) * 100, g.coverage ?? 60);
                const se = Math.max(0, (g.coverage ?? 60) - fp);
                const sc = `rgba(${r2},${g2},${b2},${op})`;
                return `linear-gradient(90deg, ${sc} 0%, ${sc} ${se.toFixed(1)}%, rgba(${r2},${g2},${b2},0) ${(g.coverage??60).toFixed(1)}%)`;
              })(),
            }} />
          </SectionCard>

          {/* Image */}
          <SectionCard title="Image">
            <label style={labelStyle}>Upload Image
              <input type="file" accept="image/*" onChange={e => handleImageUpload(e.target.files?.[0] || null)} style={{ color: '#aaa', fontSize: 12 }} />
            </label>
            {content.imageUrl && (
              <>
                <label style={labelStyle}>Zoom: {content.imageScale.toFixed(2)}×
                  <input type="range" min={0.5} max={3} step={0.01} value={content.imageScale}
                    onChange={e => updContent('imageScale', Number(e.target.value))}
                    style={{ width: '100%', accentColor: '#7c3aed' }} />
                </label>
                <p style={{ fontSize: 11, color: '#555', margin: 0 }}>Drag image in the preview to reposition it.</p>
                <button onClick={() => handleImageUpload(null)} style={{ ...topBtnStyle, color: '#f87171', borderColor: '#f8717130', fontSize: 12, padding: '4px 10px', marginTop: 4 }}>Remove Image</button>
              </>
            )}
          </SectionCard>

          {/* Watermark */}
          <SectionCard title="Watermark">
            {!content.watermarkImageUrl && (
              <label style={labelStyle}>Text (persisted)
                <input style={inputStyle} value={content.watermarkText} onChange={e => updContent('watermarkText', e.target.value)} placeholder="@yourhandle" />
              </label>
            )}
            <label style={labelStyle}>Watermark Image (optional)
              <input type="file" accept="image/*" onChange={e => handleWatermarkImageUpload(e.target.files?.[0] || null)} style={{ color: '#aaa', fontSize: 12 }} />
            </label>
            {content.watermarkImageUrl && (
              <button onClick={() => handleWatermarkImageUpload(null)} style={{ ...topBtnStyle, color: '#f87171', fontSize: 12, padding: '4px 10px' }}>Remove Watermark Image</button>
            )}
            <button onClick={() => setWatermarkOpen(o => !o)} style={{ ...topBtnStyle, fontSize: 11, padding: '2px 8px', marginTop: 4 }}>
              {watermarkOpen ? '▾' : '▸'} Advanced
            </button>
            {watermarkOpen && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 10, background: '#1a1a1a', borderRadius: 8, border: '1px solid #2a2a2a' }}>
                <label style={labelStyle}>Position
                  <select value={currentStyle.watermark.position} onChange={e => updWatermark('position', e.target.value as WatermarkPosition)} style={selectStyle}>
                    {(['top-left','top-right','bottom-left','bottom-right','center'] as WatermarkPosition[]).map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </label>
                <label style={labelStyle}>Padding: {currentStyle.watermark.padding}px
                  <input type="range" min={0} max={60} value={currentStyle.watermark.padding} onChange={e => updWatermark('padding', Number(e.target.value))} style={{ width: '100%', accentColor: '#7c3aed' }} />
                </label>
                <label style={labelStyle}>Google Font
                  <input style={inputStyle} value={currentStyle.watermark.font} onChange={e => updWatermark('font', e.target.value)} onBlur={e => loadGoogleFont(e.target.value)} placeholder="e.g. Roboto" />
                </label>
                <label style={labelStyle}>Font Size: {currentStyle.watermark.fontSize}px
                  <input type="range" min={8} max={36} value={currentStyle.watermark.fontSize} onChange={e => updWatermark('fontSize', Number(e.target.value))} style={{ width: '100%', accentColor: '#7c3aed' }} />
                </label>
                <label style={labelStyle}>Color
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input type="color" value={currentStyle.watermark.color} onChange={e => updWatermark('color', e.target.value)} style={colorPickerStyle} />
                    <span style={{ fontSize: 11, color: '#777', fontFamily: 'monospace' }}>{currentStyle.watermark.color}</span>
                  </div>
                </label>
              </div>
            )}
          </SectionCard>

          {/* ── Body Group: Alert + Title + Description share position ── */}
          <SectionCard title="Body Layout (Alert + Title + Description)">
            <label style={labelStyle}>Group Position
              <select value={currentStyle.bodyPosition} onChange={e => updStyle('bodyPosition', e.target.value as Position)} style={selectStyle}>
                {positions.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </label>
            <p style={{ fontSize: 11, color: '#555', margin: 0 }}>Alert, Title and Description flow together. Use Advanced panels below to tweak each element's individual font, color, and text-align.</p>
          </SectionCard>

          {/* Alert */}
          <SectionCard title="Alert">
            <label style={labelStyle}>Text
              <input style={inputStyle} value={content.alertText} onChange={e => updContent('alertText', e.target.value)} placeholder="BREAKING 🚨" />
            </label>
            <TextStyleEditor label="Alert" value={currentStyle.alert} onChange={v => updStyle('alert', v)} hidePosition />
          </SectionCard>

          {/* Title */}
          <SectionCard title="Title">
            <label style={labelStyle}>Text
              <textarea style={textareaStyle} value={content.titleText} onChange={e => updContent('titleText', e.target.value)} placeholder="Your main headline..." />
            </label>
            <TextStyleEditor label="Title" value={currentStyle.title} onChange={v => updStyle('title', v)} hidePosition />
          </SectionCard>

          {/* Description */}
          <SectionCard title="Description">
            <label style={labelStyle}>Text
              <textarea style={textareaStyle} value={content.descriptionText} onChange={e => updContent('descriptionText', e.target.value)} placeholder="Supporting details..." />
            </label>
            <TextStyleEditor label="Description" value={currentStyle.description} onChange={v => updStyle('description', v)} hidePosition />
          </SectionCard>

          {/* Footer 1 */}
          <SectionCard title="Footer 1">
            <label style={labelStyle}>Text
              <input style={inputStyle} value={content.footer1Text} onChange={e => updContent('footer1Text', e.target.value)} placeholder="Source name..." />
            </label>
            <TextStyleEditor label="Footer 1" value={currentStyle.footer1} onChange={v => updStyle('footer1', v)} />
          </SectionCard>

          {/* Footer 2 */}
          <SectionCard title="Footer 2">
            <label style={labelStyle}>Text
              <input style={inputStyle} value={content.footer2Text} onChange={e => updContent('footer2Text', e.target.value)} placeholder="Date / Location..." />
            </label>
            <TextStyleEditor label="Footer 2" value={currentStyle.footer2} onChange={v => updStyle('footer2', v)} />
          </SectionCard>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, paddingTop: 8, paddingBottom: 24 }}>
            <button onClick={handleSaveStyle} style={{
              flex: 1, padding: '11px', border: '2px solid #7c3aed', borderRadius: 10,
              background: '#7c3aed22', color: '#a78bfa', cursor: 'pointer', fontWeight: 700, fontSize: 13,
            }}>
              💾 Save Style
            </button>
          </div>
        </div>

        {/* ─── RIGHT PANEL ─── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Toggle bar */}
          <div style={{ display: 'flex', gap: 8, padding: '12px 20px', borderBottom: '1px solid #1e1e1e', background: '#0d0d0d', alignItems: 'center' }}>
            {(['preview', 'grid'] as const).map(v => (
              <button key={v} onClick={() => setRightView(v)} style={{
                padding: '7px 18px', border: `2px solid ${rightView === v ? '#7c3aed' : '#2a2a2a'}`,
                borderRadius: 8, background: rightView === v ? '#7c3aed22' : '#111',
                color: rightView === v ? '#a78bfa' : '#666', cursor: 'pointer', fontWeight: 700, fontSize: 13,
                textTransform: 'capitalize',
              }}>
                {v === 'preview' ? '👁 Preview' : `⚡ Grid (${savedStyles.length})`}
              </button>
            ))}
            <div style={{ flex: 1 }} />
            {savedStyles.length > 0 && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {savedStyles.map(s => (
                  <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 4, background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 6, padding: '3px 8px', fontSize: 11, color: '#888' }}>
                    {s.name}
                    <button onClick={() => handleDeleteStyle(s.id)} style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: 13, lineHeight: 1, padding: 0 }}>×</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Content area */}
          <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 20, alignItems: 'center' }}>

            {rightView === 'preview' ? (
              <>
                <h3 style={{ margin: 0, color: '#555', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Live Preview — drag image to reframe</h3>
                <div style={{ boxShadow: '0 8px 40px rgba(124,58,237,0.25)', borderRadius: 12, overflow: 'hidden' }}>
                  <StoryCard content={content} style={currentStyle} cardRef={previewRef} interactive onDragImage={handleDragImage} onDropFile={handleImageUpload} />
                </div>
              </>
            ) : (
              <>
                {savedStyles.length === 0 ? (
                  <div style={{ color: '#555', textAlign: 'center', paddingTop: 60 }}>
                    <p style={{ fontSize: 16, marginBottom: 8 }}>No saved styles yet</p>
                    <p style={{ fontSize: 13 }}>Switch to Preview, tweak your design, then hit "Save Style"</p>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, width: '100%', maxWidth: 1100 }}>
                    {savedStyles.map(s => {
                      // Compute correct scaled dimensions to avoid zero-height containers
                      const cW = s.aspectRatio === '1:1' ? 500 : 360;
                      const cH = s.aspectRatio === '1:1' ? 500 : 540;
                      const scale = 0.5;
                      const displayW = cW * scale;
                      const displayH = cH * scale;
                      return (
                      <div key={s.id} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <p style={{ margin: 0, color: '#777', fontSize: 11, fontWeight: 700, textAlign: 'center', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{s.name}</p>

                        {/* Card container with hover overlay download button */}
                        <div
                          style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', boxShadow: '0 4px 20px rgba(0,0,0,0.5)', cursor: 'pointer', width: displayW, height: displayH }}
                          onMouseEnter={() => setHoveredCard(s.id)}
                          onMouseLeave={() => setHoveredCard(null)}
                        >
                          {/* Scaled thumbnail — must clip correctly */}
                          <div style={{ position: 'absolute', top: 0, left: 0, transformOrigin: 'top left', transform: `scale(${scale})`, pointerEvents: 'none' }}>
                            <StoryCard content={content} style={s} />
                          </div>

                          {/* Download overlay — shows on hover */}
                          {hoveredCard === s.id && (
                            <div style={{
                              position: 'absolute', inset: 0,
                              background: 'rgba(0,0,0,0.55)',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                              <button
                                onClick={() => handleDownload(s)}
                                disabled={downloading === s.id}
                                style={{
                                  padding: '10px 20px', border: 'none', borderRadius: 10,
                                  background: downloading === s.id ? '#555' : 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                                  color: '#fff', cursor: downloading === s.id ? 'not-allowed' : 'pointer',
                                  fontWeight: 700, fontSize: 13, boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
                                }}
                              >
                                {downloading === s.id ? '⏳ Exporting…' : '⬇ Download 1080p'}
                              </button>
                            </div>
                          )}
                        </div>

                        {/* No more hidden offscreen card needed — download renders fresh via createRoot */}
                      </div>)
                    })}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────
// SectionCard helper
// ─────────────────────────────────────────────

const SectionCard: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, padding: '14px 14px 12px' }}>
    <p style={{ margin: '0 0 10px 0', fontSize: 11, fontWeight: 800, color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.1em' }}>{title}</p>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {children}
    </div>
  </div>
);
