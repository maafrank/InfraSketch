/**
 * Adds an InfraSketch watermark (logo + text) to the bottom-right corner
 * of an exported PNG data URL.
 */

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

// All sizes are in 2x pixel space (exports use pixelRatio: 2)
const LOGO_SIZE = 48;
const FONT_SIZE = 26;
const EDGE_MARGIN = 24;
const PILL_PADDING_H = 16;
const PILL_PADDING_V = 12;
const LOGO_TEXT_GAP = 8;
const PILL_RADIUS = 12;
const FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif';

export async function addWatermark(dataUrl) {
  const diagramImg = await loadImage(dataUrl);

  let logoImg = null;
  try {
    logoImg = await loadImage('/InfraSketchLogoTransparent_03_256.png');
  } catch {
    // Logo failed to load, will render text-only
  }

  const canvas = document.createElement('canvas');
  canvas.width = diagramImg.width;
  canvas.height = diagramImg.height;
  const ctx = canvas.getContext('2d');

  // Draw original diagram
  ctx.drawImage(diagramImg, 0, 0);

  // Measure text to calculate pill size
  ctx.font = `bold ${FONT_SIZE}px ${FONT_FAMILY}`;
  const textWidth = ctx.measureText('InfraSketch').width;

  const hasLogo = logoImg !== null;
  const contentWidth = (hasLogo ? LOGO_SIZE + LOGO_TEXT_GAP : 0) + textWidth;
  const pillWidth = PILL_PADDING_H * 2 + contentWidth;
  const pillHeight = PILL_PADDING_V * 2 + Math.max(LOGO_SIZE, FONT_SIZE);

  const pillX = canvas.width - pillWidth - EDGE_MARGIN;
  const pillY = canvas.height - pillHeight - EDGE_MARGIN;

  // Draw dark semi-transparent pill background
  ctx.save();
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
  drawRoundedRect(ctx, pillX, pillY, pillWidth, pillHeight, PILL_RADIUS);
  ctx.fill();
  ctx.restore();

  // Draw logo and text
  ctx.save();
  ctx.globalAlpha = 0.85;

  if (hasLogo) {
    const logoX = pillX + PILL_PADDING_H;
    const logoY = pillY + (pillHeight - LOGO_SIZE) / 2;
    ctx.drawImage(logoImg, logoX, logoY, LOGO_SIZE, LOGO_SIZE);
  }

  ctx.fillStyle = '#ffffff';
  ctx.font = `bold ${FONT_SIZE}px ${FONT_FAMILY}`;
  ctx.textBaseline = 'middle';
  const textX = pillX + PILL_PADDING_H + (hasLogo ? LOGO_SIZE + LOGO_TEXT_GAP : 0);
  const textY = pillY + pillHeight / 2;
  ctx.fillText('InfraSketch', textX, textY);

  ctx.restore();

  return canvas.toDataURL('image/png');
}
