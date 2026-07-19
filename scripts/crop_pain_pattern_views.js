#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

const paeth = (a, b, c) => {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  return pa <= pb && pa <= pc ? a : (pb <= pc ? b : c);
};

const decodePng = (filePath) => {
  const file = fs.readFileSync(filePath);
  if (!file.subarray(0, 8).equals(PNG_SIGNATURE)) throw new Error(`No es un PNG válido: ${filePath}`);
  let offset = 8;
  let width;
  let height;
  let bitDepth;
  let colorType;
  let interlace;
  const idat = [];
  while (offset < file.length) {
    const length = file.readUInt32BE(offset);
    const type = file.toString('ascii', offset + 4, offset + 8);
    const data = file.subarray(offset + 8, offset + 8 + length);
    if (type === 'IHDR') {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
      interlace = data[12];
    } else if (type === 'IDAT') {
      idat.push(data);
    } else if (type === 'IEND') {
      break;
    }
    offset += 12 + length;
  }
  if (bitDepth !== 8 || ![2, 6].includes(colorType) || interlace !== 0) {
    throw new Error(`PNG no compatible (${bitDepth} bits, color ${colorType}, entrelazado ${interlace}): ${filePath}`);
  }
  const channels = colorType === 2 ? 3 : 4;
  const stride = width * channels;
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const pixels = Buffer.alloc(width * height * channels);
  let sourceOffset = 0;
  for (let y = 0; y < height; y += 1) {
    const filter = raw[sourceOffset];
    sourceOffset += 1;
    const rowOffset = y * stride;
    for (let x = 0; x < stride; x += 1) {
      const source = raw[sourceOffset + x];
      const left = x >= channels ? pixels[rowOffset + x - channels] : 0;
      const above = y > 0 ? pixels[rowOffset + x - stride] : 0;
      const upperLeft = y > 0 && x >= channels ? pixels[rowOffset + x - stride - channels] : 0;
      let value;
      if (filter === 0) value = source;
      else if (filter === 1) value = source + left;
      else if (filter === 2) value = source + above;
      else if (filter === 3) value = source + Math.floor((left + above) / 2);
      else if (filter === 4) value = source + paeth(left, above, upperLeft);
      else throw new Error(`Filtro PNG desconocido ${filter}: ${filePath}`);
      pixels[rowOffset + x] = value & 255;
    }
    sourceOffset += stride;
  }
  return { width, height, channels, pixels };
};

const crcTable = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    table[n] = c >>> 0;
  }
  return table;
})();

const crc32 = (buffer) => {
  let crc = 0xffffffff;
  for (const byte of buffer) crc = crcTable[(crc ^ byte) & 255] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
};

const pngChunk = (type, data) => {
  const name = Buffer.from(type, 'ascii');
  const chunk = Buffer.alloc(data.length + 12);
  chunk.writeUInt32BE(data.length, 0);
  name.copy(chunk, 4);
  data.copy(chunk, 8);
  chunk.writeUInt32BE(crc32(Buffer.concat([name, data])), data.length + 8);
  return chunk;
};

const encodePng = ({ width, height, channels, pixels }) => {
  const stride = width * channels;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y += 1) {
    const rawOffset = y * (stride + 1);
    raw[rawOffset] = 0;
    pixels.copy(raw, rawOffset + 1, y * stride, (y + 1) * stride);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = channels === 4 ? 6 : 2;
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;
  return Buffer.concat([
    PNG_SIGNATURE,
    pngChunk('IHDR', ihdr),
    pngChunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
    pngChunk('IEND', Buffer.alloc(0))
  ]);
};

const cropImage = (image, view) => {
  if (view.x < 0 || view.y < 0 || view.x + view.width > image.width || view.y + view.height > image.height) {
    throw new Error(`Recorte inválido: ${JSON.stringify(view)}`);
  }
  const stride = image.width * image.channels;
  const croppedStride = view.width * image.channels;
  const pixels = Buffer.alloc(croppedStride * view.height);
  for (let row = 0; row < view.height; row += 1) {
    const start = (view.y + row) * stride + view.x * image.channels;
    image.pixels.copy(pixels, row * croppedStride, start, start + croppedStride);
  }
  return { width: view.width, height: view.height, channels: image.channels, pixels };
};

const countPainPixels = (template, drawing) => {
  if (template.width !== drawing.width || template.height !== drawing.height || template.channels !== drawing.channels) return 0;
  let count = 0;
  for (let index = 0; index < drawing.pixels.length; index += drawing.channels) {
    const r = drawing.pixels[index];
    const g = drawing.pixels[index + 1];
    const b = drawing.pixels[index + 2];
    const delta = Math.max(
      Math.abs(r - template.pixels[index]),
      Math.abs(g - template.pixels[index + 1]),
      Math.abs(b - template.pixels[index + 2])
    );
    if (delta >= 12 && r >= 145 && r - g >= 16 && r - b >= 16) count += 1;
  }
  return count;
};

const main = () => {
  if (process.argv.length !== 3) throw new Error('Uso: node crop_pain_pattern_views.js <config.json>');
  const config = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  fs.mkdirSync(config.outputDirectory, { recursive: true });
  const report = { items: [] };
  for (const item of config.items) {
    const drawing = decodePng(item.drawing);
    const template = decodePng(item.template);
    const generated = { id: item.id, views: [] };
    for (const view of item.views) {
      const drawingCrop = cropImage(drawing, view);
      const templateCrop = cropImage(template, view);
      const changedPixels = countPainPixels(templateCrop, drawingCrop);
      const minimumPixels = Math.max(40, Math.floor((view.width * view.height) / 18000));
      if (changedPixels < minimumPixels) continue;
      const file = `${item.outputStem}--${view.id}.png`;
      fs.writeFileSync(path.join(config.outputDirectory, file), encodePng(drawingCrop));
      generated.views.push({ id: view.id, label: view.label, file, width: view.width, height: view.height, changedPixels });
    }
    report.items.push(generated);
  }
  fs.writeFileSync(config.reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
};

try {
  main();
} catch (error) {
  console.error(error.message || error);
  process.exit(1);
}
