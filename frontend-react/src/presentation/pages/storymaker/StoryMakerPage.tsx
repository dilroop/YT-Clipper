import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toPng } from 'html-to-image';
import { VideoRepository } from '../../../data/VideoRepository';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type BgShape = 'none' | 'rectangle' | 'rounded' | 'side-lines';
type Position = 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right' | 'center';
type WatermarkPosition = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
type AspectRatio = '1:1' | '2:3';
// Alignment is separate from layout position — controls text-align within the block
type TextAlign = 'left' | 'center' | 'right';

const PRESET_FONTS = [
  'Inter', 'Roboto', 'Bebas Neue', 'Montserrat', 'Oswald',
  'Playfair Display', 'Poppins', 'Lato', 'Open Sans', 'Raleway', 'Ubuntu'
];

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
  // Shared position/padding for the alert+title+description group
  bodyPosition: Position;
  bodyPaddingLeft: number;
  bodyPaddingRight: number;
  highlightColor: string;
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
  bodyPaddingLeft: 20,
  bodyPaddingRight: 20,
  highlightColor: '#22DD66',
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
        bodyPaddingLeft: parsed.bodyPaddingLeft ?? parsed.bodyPaddingHorizontal ?? 20,
        bodyPaddingRight: parsed.bodyPaddingRight ?? parsed.bodyPaddingHorizontal ?? 20,
        highlightColor: parsed.highlightColor || '#22DD66',
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

function loadGoogleFont(fontName: string, customFonts: string[] = []) {
  if (!fontName || ['Arial', 'Impact', 'Georgia', 'Times New Roman', 'Courier New', 'Verdana'].includes(fontName) || customFonts.includes(fontName)) return;
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

function renderTextEl(text: string, s: TextElementStyle, align: React.CSSProperties['textAlign'], overrideWeight?: any, hColor?: string): React.ReactNode {
  // 1. Parsing for highlights [text]
  const parts = text.split(/(\[.*?\])/g);
  const contentParts = parts.map((part, i) => {
    if (part.startsWith('[') && part.endsWith(']')) {
      return <span key={i} style={{ color: hColor || s.color }}>{part.slice(1, -1)}</span>;
    }
    return part;
  });

  // 2. Base Style
  const baseStyle: React.CSSProperties = {
    fontFamily: `'${s.font}', ${s.font}, sans-serif`,
    fontSize: s.fontSize,
    color: s.color,
    lineHeight: 1.25,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    textAlign: (s.textAlign as React.CSSProperties['textAlign']) || align,
    fontWeight: overrideWeight || 800,
  };

  // 3. Special Case: Side Lines
  if (s.bgShape === 'side-lines') {
    const lineColor = s.bgColor && s.bgColor.startsWith('#') ? s.bgColor : s.color;
    const lAlign = baseStyle.textAlign;
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%', justifyContent: lAlign === 'center' ? 'center' : (lAlign === 'right' ? 'flex-end' : 'flex-start') }}>
        <div style={{ flex: 1, height: 2, background: lineColor, opacity: 0.8 }} />
        <span style={{ ...baseStyle, whiteSpace: 'nowrap', textAlign: 'center' }}>{contentParts}</span>
        <div style={{ flex: 1, height: 2, background: lineColor, opacity: 0.8 }} />
      </div>
    );
  }

  // 4. Default: optionally applying other shapes
  return (
    <div style={{ display: 'block', ...baseStyle, ...bgShapeStyle(s.bgShape, s.bgColor) }}>
      {contentParts}
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
  // Parse color (hex or rgba) to RGB components
  const parseColorToRgb = (color: string): [number, number, number] => {
    if (color.startsWith('rgba')) {
      const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (match) {
        return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3])];
      }
    }
    const clean = color.replace('#', '');
    const full = clean.length === 3
      ? clean.split('').map(c => c + c).join('')
      : clean;
    return [
      parseInt(full.substring(0, 2), 16) || 0,
      parseInt(full.substring(2, 4), 16) || 0,
      parseInt(full.substring(4, 6), 16) || 0,
    ];
  };

  const [r, g, b] = parseColorToRgb(gradient.color);
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

  // ── Smart Padding: Offset body if it overlaps with bottom-positioned footers ──
  const getFooterHeight = (s: TextElementStyle) => (s.fontSize * 1.5) + 20; // 20 is footer container padding
  let maxBottomFooterHeight = 0;
  if (content.footer1Text && style.footer1.position.includes('bottom')) {
    maxBottomFooterHeight = Math.max(maxBottomFooterHeight, getFooterHeight(style.footer1));
  }
  if (content.footer2Text && style.footer2.position.includes('bottom')) {
    maxBottomFooterHeight = Math.max(maxBottomFooterHeight, getFooterHeight(style.footer2));
  }

  const finalBodyPaddingBottom = bodyPos.includes('bottom') && maxBottomFooterHeight > 0
    ? maxBottomFooterHeight + 20 // footer height + 20px gap
    : 14; // Default padding

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
        padding: `14px ${style.bodyPaddingRight ?? 20}px ${finalBodyPaddingBottom}px ${style.bodyPaddingLeft ?? 20}px`,
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
            {renderTextEl(
              el.text, 
              el.s, 
              (el.s.textAlign as React.CSSProperties['textAlign']) || bodyAlign,
              undefined,
              style.highlightColor
            )}
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
  customFonts?: string[];
}

const TextStyleEditor: React.FC<TextStyleEditorProps> = ({ label, value, onChange, hidePosition, customFonts = [] }) => {
  const [open, setOpen] = useState(false);
  const up = (k: keyof TextElementStyle, v: any) => {
    if (k === 'font') loadGoogleFont(v, customFonts);
    onChange({ ...value, [k]: v });
  };

  const positions: Position[] = ['top-left', 'top-center', 'top-right', 'center', 'bottom-left', 'bottom-center', 'bottom-right'];
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8, padding: '12px', background: '#1a1a1a', borderRadius: 8, border: '1px solid #2a2a2a' }}>
          {!hidePosition && (
            <label style={labelStyle}>Position
              <select value={value.position} onChange={e => up('position', e.target.value as Position)} style={selectStyle}>
                {positions.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </label>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <label style={labelStyle}>Font (preset)
              <select
                value={PRESET_FONTS.includes(value.font) || customFonts.includes(value.font) ? value.font : 'Custom'}
                onChange={e => {
                  if (e.target.value !== 'Custom') up('font', e.target.value);
                }}
                style={selectStyle}
              >
                {!PRESET_FONTS.includes(value.font) && !customFonts.includes(value.font) && <option value="Custom">Custom Font...</option>}
                <optgroup label="Custom Project Fonts">
                  {customFonts.map(f => <option key={f} value={f}>{f}</option>)}
                </optgroup>
                <optgroup label="Preset Google Fonts">
                  {PRESET_FONTS.map(f => <option key={f} value={f}>{f}</option>)}
                </optgroup>
                <option value="Custom">Custom Font...</option>
              </select>
            </label>
            <label style={labelStyle}>Custom Google Font
              <input style={inputStyle} value={value.font} onChange={e => up('font', e.target.value)} placeholder="e.g. Bebas Neue" onBlur={e => loadGoogleFont(e.target.value, customFonts)} />
            </label>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <label style={labelStyle}>Text Align
              <div style={{ display: 'flex', gap: 4 }}>
                {alignments.map(a => (
                  <button key={a} onClick={() => up('textAlign', a)} style={{
                    flex: 1, padding: '4px', border: `1px solid ${value.textAlign === a ? '#cc0000' : '#333'}`,
                    borderRadius: 4, background: value.textAlign === a ? '#cc000022' : '#0d0d0d',
                    color: value.textAlign === a ? '#ff4d4d' : '#888', cursor: 'pointer', fontSize: 11,
                  }}>
                    {a === 'left' ? '⬅' : a === 'center' ? '↔' : '➡'}
                  </button>
                ))}
              </div>
            </label>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <label style={labelStyle}>Size: {value.fontSize}px
              <input type="range" min={10} max={100} value={value.fontSize} onChange={e => up('fontSize', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
            </label>
            <ColorControl label="Text Color" value={value.color} onChange={v => up('color', v)} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, alignItems: 'end' }}>
            <label style={labelStyle}>Bg Style
              <select value={value.bgShape} onChange={e => up('bgShape', e.target.value as BgShape)} style={selectStyle}>
                <option value="none">None</option>
                <option value="rectangle">Rectangle</option>
                <option value="rounded">Rounded</option>
                <option value="side-lines">Side Lines</option>
              </select>
            </label>
            {value.bgShape !== 'none' && (
              <ColorControl label={value.bgShape === 'side-lines' ? 'Line Color' : 'Bg Color'} value={value.bgColor} onChange={v => up('bgColor', v)} />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────
// Color Picker with Alpha Selector
// ─────────────────────────────────────────────

const ColorControl: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
}> = ({ label, value, onChange }) => {
  // Parse #RRGGBB or rgba(...) into [hex, opacity0to1]
  const parse = (v: string): { hex: string; alpha: number } => {
    if (v.startsWith('rgba')) {
      const match = v.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
      if (match) {
        const r = parseInt(match[1]).toString(16).padStart(2, '0');
        const g = parseInt(match[2]).toString(16).padStart(2, '0');
        const b = parseInt(match[3]).toString(16).padStart(2, '0');
        const a = match[4] ? parseFloat(match[4]) : 1;
        return { hex: `#${r}${g}${b}`, alpha: a };
      }
    }
    if (v.startsWith('#')) {
      return { hex: v.substring(0, 7), alpha: 1 };
    }
    return { hex: '#ffffff', alpha: 1 };
  };

  const { hex, alpha } = parse(value);

  const handleChange = (newHex: string, newAlpha: number) => {
    const r = parseInt(newHex.substring(1, 3), 16);
    const g = parseInt(newHex.substring(3, 5), 16);
    const b = parseInt(newHex.substring(5, 7), 16);
    onChange(`rgba(${r}, ${g}, ${b}, ${newAlpha})`);
  };

  return (
    <label style={labelStyle}>{label}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="color" value={hex} onChange={e => handleChange(e.target.value, alpha)} style={colorPickerStyle} />
          <span style={{ fontSize: 11, color: '#777', fontFamily: 'monospace', flex: 1 }}>{value}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#555', minWidth: 40 }}>Alpha</span>
          <input type="range" min={0} max={1} step={0.01} value={alpha} onChange={e => handleChange(hex, parseFloat(e.target.value))} style={{ flex: 1, accentColor: '#cc0000', height: 12 }} />
          <span style={{ fontSize: 10, color: '#555', minWidth: 30 }}>{Math.round(alpha * 100)}%</span>
        </div>
      </div>
    </label>
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
  width: 32, height: 32, padding: 0, border: '1px solid #3e3e3e',
  background: 'none', cursor: 'pointer', borderRadius: 4,
};
const topBtnStyle: React.CSSProperties = {
  padding: '7px 14px', background: '#3e3e3e', border: '1px solid #4e4e4e', borderRadius: 8,
  color: '#ffffff', cursor: 'pointer', fontSize: 13, fontWeight: 600,
  transition: 'background 0.15s',
};
const navCircleBtnStyle: React.CSSProperties = {
  background: '#252525', border: 'none', borderRadius: '8px', width: '40px', height: '40px',
  display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer',
  transition: 'background 0.2s',
};

// ─────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────

export const StoryMakerPage: React.FC = () => {
  const navigate = useNavigate();
  const previewRef = useRef<HTMLDivElement | null>(null);

  const [customFonts, setCustomFonts] = useState<string[]>([]);

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
        bodyPaddingLeft: s.bodyPaddingLeft ?? s.bodyPaddingHorizontal ?? 20,
        bodyPaddingRight: s.bodyPaddingRight ?? s.bodyPaddingHorizontal ?? 20,
        highlightColor: s.highlightColor || '#22DD66',
      }));
    } catch { return []; }
  });
  // 'preview' | 'grid'
  const [rightView, setRightView] = useState<'preview' | 'grid'>('preview');
  const [downloading, setDownloading] = useState<string | null>(null);
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);
  const [watermarkOpen, setWatermarkOpen] = useState(false);

  // Bulk deletion states
  const [isGridEditMode, setIsGridEditMode] = useState(false);
  const [selectedStyleIds, setSelectedStyleIds] = useState<Set<string>>(new Set());

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

  // Fetch custom fonts
  useEffect(() => {
    VideoRepository.getFonts().then(fonts => {
      setCustomFonts(fonts.map(f => f.name));
    }).catch(err => console.error("Failed to load custom fonts:", err));
  }, []);

  // Load Google fonts from saved styles
  useEffect(() => {
    savedStyles.forEach(s => {
      loadGoogleFont(s.alert.font, customFonts);
      loadGoogleFont(s.title.font, customFonts);
      loadGoogleFont(s.description.font, customFonts);
      loadGoogleFont(s.footer1.font, customFonts);
      loadGoogleFont(s.footer2.font, customFonts);
      loadGoogleFont(s.watermark.font, customFonts);
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
    loadGoogleFont(newStyle.title.font, customFonts);
    setSavedStyles(prev => [...prev, newStyle]);
    // Keep current style as-is (do not reset) so user can keep tweaking
    setCurrentStyle(s => ({ ...s, name }));
    setRightView('grid');
  };


  const toggleStyleSelection = (id: string) => {
    setSelectedStyleIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkDelete = () => {
    if (selectedStyleIds.size > 0) {
      setSavedStyles(prev => prev.filter(s => !selectedStyleIds.has(s.id)));
      setSelectedStyleIds(new Set());
    }
    setIsGridEditMode(false);
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#0f0f0f', color: '#fff', fontFamily: 'Roboto, Arial, sans-serif' }}>
      {/* Top Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px', borderBottom: '1px solid #3e3e3e', background: '#0f0f0f' }}>
        <button onClick={() => navigate(-1)} style={navCircleBtnStyle} title="Back">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        </button>
        <button onClick={() => navigate('/')} style={navCircleBtnStyle} title="Home">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        </button>
        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#ffffff', letterSpacing: '0.02em' }}>Story Maker</h2>
        <div style={{ flex: 1 }} />
      </div>

      {/* Body */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* ─── LEFT SIDEBAR ─── */}
        <div style={{
          width: 380, minWidth: 350, overflowY: 'auto', padding: '16px',
          borderRight: '1px solid #3e3e3e', background: '#0f0f0f',
          display: 'flex', flexDirection: 'column', gap: 14,
        }}>

          {/* ── Main Content (Alert, Title, Description) ── */}
          <SectionCard title="Main Content">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <p style={{ ...labelStyle, marginBottom: 6, color: '#cc0000' }}>Alert Text</p>
                <input style={inputStyle} value={content.alertText} onChange={e => updContent('alertText', e.target.value)} placeholder="BREAKING 🚨" />
                <TextStyleEditor label="Alert" value={currentStyle.alert} onChange={v => updStyle('alert', v)} hidePosition customFonts={customFonts} />
              </div>

              <div style={{ borderTop: '1px solid #333', paddingTop: 16 }}>
                <p style={{ ...labelStyle, marginBottom: 6, color: '#cc0000' }}>Title Text</p>
                <textarea style={textareaStyle} value={content.titleText} onChange={e => updContent('titleText', e.target.value)} placeholder="Your main headline..." />
                <TextStyleEditor label="Title" value={currentStyle.title} onChange={v => updStyle('title', v)} hidePosition customFonts={customFonts} />
              </div>

              <div style={{ borderTop: '1px solid #333', paddingTop: 16 }}>
                <p style={{ ...labelStyle, marginBottom: 6, color: '#cc0000' }}>Description Text</p>
                <textarea style={textareaStyle} value={content.descriptionText} onChange={e => updContent('descriptionText', e.target.value)} placeholder="Supporting details..." />
                <TextStyleEditor label="Description" value={currentStyle.description} onChange={v => updStyle('description', v)} hidePosition customFonts={customFonts} />
              </div>

              <div style={{ borderTop: '1px solid #333', paddingTop: 16 }}>
                <p style={{ ...labelStyle, marginBottom: 8, color: '#cc0000' }}>Highlight Color ([text])</p>
                <ColorControl label="Highlight" value={currentStyle.highlightColor} onChange={c => updStyle('highlightColor', c)} />
              </div>

              <div style={{ borderTop: '1px solid #333', paddingTop: 16 }}>
                <p style={{ ...labelStyle, marginBottom: 8, color: '#cc0000' }}>Group (Alert + Title + Desc) Position</p>
                <select value={currentStyle.bodyPosition} onChange={e => updStyle('bodyPosition', e.target.value as Position)} style={{ ...selectStyle, marginTop: 4 }}>
                  {positions.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
                  <label style={labelStyle}>Left Padding: {currentStyle.bodyPaddingLeft}px
                    <input type="range" min={0} max={1000} value={currentStyle.bodyPaddingLeft} onChange={e => updStyle('bodyPaddingLeft', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
                  </label>
                  <label style={labelStyle}>Right Padding: {currentStyle.bodyPaddingRight}px
                    <input type="range" min={0} max={1000} value={currentStyle.bodyPaddingRight} onChange={e => updStyle('bodyPaddingRight', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
                  </label>
                </div>
              </div>
            </div>
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
                    style={{ width: '100%', accentColor: '#cc0000' }} />
                </label>
                <p style={{ fontSize: 11, color: '#555', margin: 0 }}>Drag image in the preview to reposition it.</p>
                <button onClick={() => handleImageUpload(null)} style={{ ...topBtnStyle, color: '#f87171', borderColor: '#f8717130', fontSize: 12, padding: '4px 10px', marginTop: 4 }}>Remove Image</button>
              </>
            )}
          </SectionCard>

          {/* Footers */}
          <SectionCard title="Footers">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <p style={{ ...labelStyle, marginBottom: 6, color: '#cc0000' }}>Footer 1</p>
                <input style={inputStyle} value={content.footer1Text} onChange={e => updContent('footer1Text', e.target.value)} placeholder="Source name..." />
                <TextStyleEditor label="Footer 1" value={currentStyle.footer1} onChange={v => updStyle('footer1', v)} customFonts={customFonts} />
              </div>
              <div style={{ borderTop: '1px solid #333', paddingTop: 16 }}>
                <p style={{ ...labelStyle, marginBottom: 6, color: '#cc0000' }}>Footer 2</p>
                <input style={inputStyle} value={content.footer2Text} onChange={e => updContent('footer2Text', e.target.value)} placeholder="Date / Location..." />
                <TextStyleEditor label="Footer 2" value={currentStyle.footer2} onChange={v => updStyle('footer2', v)} customFonts={customFonts} />
              </div>
            </div>
          </SectionCard>

          {/* Watermark */}
          <SectionCard title="Watermark">
            {!content.watermarkImageUrl && (
              <label style={labelStyle}>Text (persisted)
                <input style={inputStyle} value={content.watermarkText} onChange={e => updContent('watermarkText', e.target.value)} placeholder="@yourhandle" />
              </label>
            )}
            <label style={labelStyle}>Watermark Image
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
                  <input type="range" min={0} max={60} value={currentStyle.watermark.padding} onChange={e => updWatermark('padding', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
                </label>
                <label style={labelStyle}>Google Font
                  <input style={inputStyle} value={currentStyle.watermark.font} onChange={e => updWatermark('font', e.target.value)} onBlur={e => loadGoogleFont(e.target.value, customFonts)} placeholder="e.g. Roboto" />
                </label>
                <label style={labelStyle}>Size: {currentStyle.watermark.fontSize}px
                  <input type="range" min={8} max={36} value={currentStyle.watermark.fontSize} onChange={e => updWatermark('fontSize', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
                </label>
                <ColorControl label="Color" value={currentStyle.watermark.color} onChange={v => updWatermark('color', v)} />
              </div>
            )}
          </SectionCard>

          {/* Background */}
          <SectionCard title="Background">
            <ColorControl label="Base Solid Color" value={currentStyle.bgColor} onChange={v => updStyle('bgColor', v)} />
            <div style={{ borderTop: '1px solid #333', marginTop: 8, paddingTop: 12 }}>
              <p style={{ ...labelStyle, color: '#cc0000', marginBottom: 6 }}>Gradient Overlay</p>
              <ColorControl label="Gradient Color" value={currentStyle.gradient.color} onChange={v => updGradient('color', v)} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <label style={labelStyle}>Angle: {currentStyle.gradient.angle}°
                  <input type="range" min={0} max={360} value={currentStyle.gradient.angle} onChange={e => updGradient('angle', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
                </label>
                <label style={labelStyle}>Opacity: {currentStyle.gradient.opacity ?? 100}%
                  <input type="range" min={0} max={100} value={currentStyle.gradient.opacity ?? 100} onChange={e => updGradient('opacity', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
                </label>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <label style={labelStyle}>Coverage: {currentStyle.gradient.coverage ?? 60}%
                  <input type="range" min={0} max={100} value={currentStyle.gradient.coverage ?? 60} onChange={e => updGradient('coverage', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
                </label>
                <label style={labelStyle}>Feather: {currentStyle.gradient.feather ?? 40}px
                  <input type="range" min={0} max={200} value={currentStyle.gradient.feather ?? 40} onChange={e => updGradient('feather', Number(e.target.value))} style={{ width: '100%', accentColor: '#cc0000' }} />
                </label>
              </div>
              {/* Visual preview bar */}
              <div style={{
                height: 8, borderRadius: 4, marginTop: 8,
                background: (() => {
                  const g = currentStyle.gradient;
                  const sc = g.color.startsWith('#') ? g.color : (g.color.includes('rgba') ? g.color : '#ffffff');
                  const cardDim2 = 540;
                  const fp = Math.min(((g.feather ?? 40) / cardDim2) * 100, g.coverage ?? 60);
                  const se = Math.max(0, (g.coverage ?? 60) - fp);
                  return `linear-gradient(90deg, ${sc} 0%, ${sc} ${se.toFixed(1)}%, rgba(255,255,255,0) ${(g.coverage??60).toFixed(1)}%)`;
                })(),
              }} />
            </div>
          </SectionCard>

          {/* Canvas */}
          <SectionCard title="Canvas">
            <div style={{ display: 'flex', gap: 6 }}>
              {(['1:1', '2:3'] as AspectRatio[]).map(ar => (
                <button key={ar} onClick={() => updStyle('aspectRatio', ar)} style={{
                  flex: 1, padding: '6px',
                  border: `2px solid ${currentStyle.aspectRatio === ar ? '#cc0000' : '#3e3e3e'}`,
                  borderRadius: 8, background: currentStyle.aspectRatio === ar ? '#cc000022' : '#1f1f1f',
                  color: currentStyle.aspectRatio === ar ? '#ff4d4d' : '#888', cursor: 'pointer', fontWeight: 700, fontSize: 12,
                }}>
                  {ar}
                </button>
              ))}
            </div>
          </SectionCard>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, paddingTop: 8, paddingBottom: 24 }}>
            <button onClick={handleSaveStyle} style={{
              flex: 1, padding: '11px', border: '2px solid #cc0000', borderRadius: 10,
              background: '#cc000022', color: '#ff4d4d', cursor: 'pointer', fontWeight: 700, fontSize: 13,
            }}>
              💾 Save Style
            </button>
          </div>
        </div>

        {/* ─── RIGHT PANEL ─── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Toggle bar */}
          <div style={{ display: 'flex', gap: 8, padding: '12px 20px', borderBottom: '1px solid #3e3e3e', background: '#0f0f0f', alignItems: 'center' }}>
            {(['preview', 'grid'] as const).map(v => (
              <button key={v} onClick={() => setRightView(v)} style={{
                padding: '7px 18px', border: `2px solid ${rightView === v ? '#cc0000' : '#4e4e4e'}`,
                borderRadius: 8, background: rightView === v ? '#cc000022' : '#282828',
                color: rightView === v ? '#ff4d4d' : '#888', cursor: 'pointer', fontWeight: 700, fontSize: 13,
                textTransform: 'capitalize',
              }}>
                {v === 'preview' ? '👁 Preview' : `⚡ Grid (${savedStyles.length})`}
              </button>
            ))}
            <div style={{ flex: 1 }} />
            {rightView === 'preview' && (
              <button
                onClick={() => handleDownload(currentStyle)}
                disabled={downloading === currentStyle.id}
                style={{
                  ...topBtnStyle, background: '#cc0000', color: '#fff', border: 'none',
                  padding: '7px 20px', fontSize: 13, fontWeight: 700,
                }}
              >
                {downloading === currentStyle.id ? '⏳ Rendering...' : '⬇ Export Current Preview'}
              </button>
            )}
            {rightView === 'grid' && savedStyles.length > 0 && (
              <button
                onClick={() => {
                  if (isGridEditMode) handleBulkDelete();
                  else setIsGridEditMode(true);
                }}
                style={{
                  ...topBtnStyle,
                  background: isGridEditMode ? (selectedStyleIds.size > 0 ? '#cc0000' : '#3e3e3e') : '#1a1a1a',
                  color: isGridEditMode ? '#fff' : '#888',
                  borderColor: isGridEditMode ? '#ff4d4d' : '#3e3e3e',
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '7px 16px', borderRadius: 8,
                }}
              >
                {isGridEditMode ? (
                  <>✓ {selectedStyleIds.size > 0 ? `Delete (${selectedStyleIds.size})` : 'Done'}</>
                ) : (
                  <>🗑 Edit List</>
                )}
              </button>
            )}
          </div>

          {/* Content area */}
          <div style={{
            flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 20, alignItems: 'center',
            background: rightView === 'preview' ? '#e5e5e5' : '#111',
            transition: 'background 0.3s ease',
          }}>

            {rightView === 'preview' ? (
              <>
                <h3 style={{ margin: 0, color: '#888', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Live Preview — drag image to reframe</h3>
                <div style={{ boxShadow: '0 8px 40px rgba(204,0,0,0.15)', borderRadius: 12, overflow: 'hidden' }}>
                  <StoryCard content={content} style={currentStyle} cardRef={previewRef} interactive onDragImage={handleDragImage} onDropFile={handleImageUpload} />
                </div>
              </>
            ) : (
              <div style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <h2 style={{ margin: '0 0 24px 0', fontSize: 24, fontWeight: 800, color: '#fff' }}>Saved Styles ({savedStyles.length})</h2>
                {savedStyles.length === 0 ? (
                  <div style={{ padding: '60px 20px', textAlign: 'center', background: '#282828', borderRadius: 16, border: '1px dashed #3e3e3e', width: '100%', maxWidth: 500 }}>
                    <p style={{ color: '#888', fontSize: 15, margin: 0 }}>No saved styles yet. Create one in the sidebar! ✨</p>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, width: '100%', maxWidth: 1100 }}>
                    {savedStyles.map(s => {
                      const cW = s.aspectRatio === '1:1' ? 500 : 360;
                      const cH = s.aspectRatio === '1:1' ? 500 : 540;
                      const scale = 0.5;
                      const displayW = cW * scale;
                      const displayH = cH * scale;
                      const isSelected = selectedStyleIds.has(s.id);
                      return (
                        <div
                          key={s.id}
                          onClick={() => { if (isGridEditMode) toggleStyleSelection(s.id); }}
                          style={{
                            display: 'flex', flexDirection: 'column', gap: 10, background: '#282828', padding: 12,
                            borderRadius: 14, border: `1px solid ${isSelected ? '#cc0000' : '#3e3e3e'}`,
                            boxShadow: isSelected ? '0 0 12px rgba(204,0,0,0.3)' : 'none',
                            transition: 'all 0.2s',
                          }}
                        >
                          <p style={{ margin: 0, color: isSelected ? '#ff4d4d' : '#888', fontSize: 12, fontWeight: 700, textAlign: 'center', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{s.name}</p>
                          <div
                            style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', boxShadow: '0 4px 20px rgba(0,0,0,0.5)', cursor: isGridEditMode ? 'pointer' : 'default', width: displayW, height: displayH }}
                            onMouseEnter={() => { if (!isGridEditMode) setHoveredCard(s.id); }}
                            onMouseLeave={() => { if (!isGridEditMode) setHoveredCard(null); }}
                          >
                            <div style={{ position: 'absolute', top: 0, left: 0, transformOrigin: 'top left', transform: `scale(${scale})`, pointerEvents: 'none', opacity: isGridEditMode ? 0.7 : 1 }}>
                              <StoryCard content={content} style={s} />
                            </div>

                            {/* Checkbox overlay in edit mode */}
                            {isGridEditMode && (
                              <div style={{ position: 'absolute', top: 10, right: 10, width: 22, height: 22, borderRadius: '50%', background: isSelected ? '#cc0000' : 'rgba(0,0,0,0.4)', border: `2px solid ${isSelected ? '#cc0000' : '#888'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10 }}>
                                {isSelected && <span style={{ color: '#fff', fontSize: 14, fontWeight: 'bold' }}>✓</span>}
                              </div>
                            )}

                            {!isGridEditMode && hoveredCard === s.id && (
                              <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <button
                                  onClick={() => handleDownload(s)}
                                  disabled={downloading === s.id}
                                  style={{
                                    padding: '10px 20px', border: 'none', borderRadius: 10,
                                    background: downloading === s.id ? '#555' : 'linear-gradient(135deg, #cc0000, #ff4d4d)',
                                    color: '#fff', cursor: downloading === s.id ? 'not-allowed' : 'pointer',
                                    fontWeight: 700, fontSize: 13, boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
                                  }}
                                >
                                  {downloading === s.id ? '⏳ Exporting…' : '⬇ Download 1080p'}
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
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
  <div style={{ background: '#1f1f1f', border: '1px solid #3e3e3e', borderRadius: 12, padding: '14px 14px 12px' }}>
    <p style={{ margin: '0 0 10px 0', fontSize: 11, fontWeight: 800, color: '#cc0000', textTransform: 'uppercase', letterSpacing: '0.1em' }}>{title}</p>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {children}
    </div>
  </div>
);
