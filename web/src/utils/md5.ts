function rotateLeft(value: number, shift: number): number {
  return (value << shift) | (value >>> (32 - shift));
}

function addUnsigned(a: number, b: number): number {
  const aLow = a & 0xffff;
  const aHigh = (a >>> 16) & 0xffff;
  const bLow = b & 0xffff;
  const bHigh = (b >>> 16) & 0xffff;
  const low = aLow + bLow;
  const high = aHigh + bHigh + (low >>> 16);
  return ((high & 0xffff) << 16) | (low & 0xffff);
}

function toWordArray(bytes: Uint8Array): number[] {
  const messageLength = bytes.length;
  const words: number[] = [];

  for (let i = 0; i < messageLength; i += 1) {
    const wordIndex = i >>> 2;
    const shift = (i % 4) * 8;
    words[wordIndex] = (words[wordIndex] ?? 0) | (bytes[i] << shift);
  }

  const wordIndex = messageLength >>> 2;
  const shift = (messageLength % 4) * 8;
  words[wordIndex] = (words[wordIndex] ?? 0) | (0x80 << shift);

  const totalBits = messageLength * 8;
  const totalWordCount = (((messageLength + 8) >>> 6) + 1) * 16;
  words.length = totalWordCount;
  words[totalWordCount - 2] = totalBits & 0xffffffff;
  words[totalWordCount - 1] = Math.floor(totalBits / 0x100000000);

  return words;
}

function toHex(value: number): string {
  const hexChars = '0123456789abcdef';
  let output = '';
  for (let i = 0; i < 4; i += 1) {
    const byte = (value >>> (i * 8)) & 0xff;
    output += hexChars[(byte >>> 4) & 0x0f] + hexChars[byte & 0x0f];
  }
  return output;
}

function f(x: number, y: number, z: number): number {
  return (x & y) | (~x & z);
}
function g(x: number, y: number, z: number): number {
  return (x & z) | (y & ~z);
}
function h(x: number, y: number, z: number): number {
  return x ^ y ^ z;
}
function i(x: number, y: number, z: number): number {
  return y ^ (x | ~z);
}

function round(
  op: (x: number, y: number, z: number) => number,
  a: number,
  b: number,
  c: number,
  d: number,
  x: number,
  s: number,
  ac: number,
): number {
  const tmp = addUnsigned(a, addUnsigned(op(b, c, d), addUnsigned(x, ac)));
  return addUnsigned(rotateLeft(tmp, s), b);
}

export function md5Hex(input: string): string {
  const bytes = new TextEncoder().encode(input);
  const words = toWordArray(bytes);

  let a = 0x67452301;
  let b = 0xefcdab89;
  let c = 0x98badcfe;
  let d = 0x10325476;

  for (let chunkStart = 0; chunkStart < words.length; chunkStart += 16) {
    const aa = a;
    const bb = b;
    const cc = c;
    const dd = d;

    a = round(f, a, b, c, d, words[chunkStart + 0], 7, 0xd76aa478);
    d = round(f, d, a, b, c, words[chunkStart + 1], 12, 0xe8c7b756);
    c = round(f, c, d, a, b, words[chunkStart + 2], 17, 0x242070db);
    b = round(f, b, c, d, a, words[chunkStart + 3], 22, 0xc1bdceee);
    a = round(f, a, b, c, d, words[chunkStart + 4], 7, 0xf57c0faf);
    d = round(f, d, a, b, c, words[chunkStart + 5], 12, 0x4787c62a);
    c = round(f, c, d, a, b, words[chunkStart + 6], 17, 0xa8304613);
    b = round(f, b, c, d, a, words[chunkStart + 7], 22, 0xfd469501);
    a = round(f, a, b, c, d, words[chunkStart + 8], 7, 0x698098d8);
    d = round(f, d, a, b, c, words[chunkStart + 9], 12, 0x8b44f7af);
    c = round(f, c, d, a, b, words[chunkStart + 10], 17, 0xffff5bb1);
    b = round(f, b, c, d, a, words[chunkStart + 11], 22, 0x895cd7be);
    a = round(f, a, b, c, d, words[chunkStart + 12], 7, 0x6b901122);
    d = round(f, d, a, b, c, words[chunkStart + 13], 12, 0xfd987193);
    c = round(f, c, d, a, b, words[chunkStart + 14], 17, 0xa679438e);
    b = round(f, b, c, d, a, words[chunkStart + 15], 22, 0x49b40821);

    a = round(g, a, b, c, d, words[chunkStart + 1], 5, 0xf61e2562);
    d = round(g, d, a, b, c, words[chunkStart + 6], 9, 0xc040b340);
    c = round(g, c, d, a, b, words[chunkStart + 11], 14, 0x265e5a51);
    b = round(g, b, c, d, a, words[chunkStart + 0], 20, 0xe9b6c7aa);
    a = round(g, a, b, c, d, words[chunkStart + 5], 5, 0xd62f105d);
    d = round(g, d, a, b, c, words[chunkStart + 10], 9, 0x02441453);
    c = round(g, c, d, a, b, words[chunkStart + 15], 14, 0xd8a1e681);
    b = round(g, b, c, d, a, words[chunkStart + 4], 20, 0xe7d3fbc8);
    a = round(g, a, b, c, d, words[chunkStart + 9], 5, 0x21e1cde6);
    d = round(g, d, a, b, c, words[chunkStart + 14], 9, 0xc33707d6);
    c = round(g, c, d, a, b, words[chunkStart + 3], 14, 0xf4d50d87);
    b = round(g, b, c, d, a, words[chunkStart + 8], 20, 0x455a14ed);
    a = round(g, a, b, c, d, words[chunkStart + 13], 5, 0xa9e3e905);
    d = round(g, d, a, b, c, words[chunkStart + 2], 9, 0xfcefa3f8);
    c = round(g, c, d, a, b, words[chunkStart + 7], 14, 0x676f02d9);
    b = round(g, b, c, d, a, words[chunkStart + 12], 20, 0x8d2a4c8a);

    a = round(h, a, b, c, d, words[chunkStart + 5], 4, 0xfffa3942);
    d = round(h, d, a, b, c, words[chunkStart + 8], 11, 0x8771f681);
    c = round(h, c, d, a, b, words[chunkStart + 11], 16, 0x6d9d6122);
    b = round(h, b, c, d, a, words[chunkStart + 14], 23, 0xfde5380c);
    a = round(h, a, b, c, d, words[chunkStart + 1], 4, 0xa4beea44);
    d = round(h, d, a, b, c, words[chunkStart + 4], 11, 0x4bdecfa9);
    c = round(h, c, d, a, b, words[chunkStart + 7], 16, 0xf6bb4b60);
    b = round(h, b, c, d, a, words[chunkStart + 10], 23, 0xbebfbc70);
    a = round(h, a, b, c, d, words[chunkStart + 13], 4, 0x289b7ec6);
    d = round(h, d, a, b, c, words[chunkStart + 0], 11, 0xeaa127fa);
    c = round(h, c, d, a, b, words[chunkStart + 3], 16, 0xd4ef3085);
    b = round(h, b, c, d, a, words[chunkStart + 6], 23, 0x04881d05);
    a = round(h, a, b, c, d, words[chunkStart + 9], 4, 0xd9d4d039);
    d = round(h, d, a, b, c, words[chunkStart + 12], 11, 0xe6db99e5);
    c = round(h, c, d, a, b, words[chunkStart + 15], 16, 0x1fa27cf8);
    b = round(h, b, c, d, a, words[chunkStart + 2], 23, 0xc4ac5665);

    a = round(i, a, b, c, d, words[chunkStart + 0], 6, 0xf4292244);
    d = round(i, d, a, b, c, words[chunkStart + 7], 10, 0x432aff97);
    c = round(i, c, d, a, b, words[chunkStart + 14], 15, 0xab9423a7);
    b = round(i, b, c, d, a, words[chunkStart + 5], 21, 0xfc93a039);
    a = round(i, a, b, c, d, words[chunkStart + 12], 6, 0x655b59c3);
    d = round(i, d, a, b, c, words[chunkStart + 3], 10, 0x8f0ccc92);
    c = round(i, c, d, a, b, words[chunkStart + 10], 15, 0xffeff47d);
    b = round(i, b, c, d, a, words[chunkStart + 1], 21, 0x85845dd1);
    a = round(i, a, b, c, d, words[chunkStart + 8], 6, 0x6fa87e4f);
    d = round(i, d, a, b, c, words[chunkStart + 15], 10, 0xfe2ce6e0);
    c = round(i, c, d, a, b, words[chunkStart + 6], 15, 0xa3014314);
    b = round(i, b, c, d, a, words[chunkStart + 13], 21, 0x4e0811a1);
    a = round(i, a, b, c, d, words[chunkStart + 4], 6, 0xf7537e82);
    d = round(i, d, a, b, c, words[chunkStart + 11], 10, 0xbd3af235);
    c = round(i, c, d, a, b, words[chunkStart + 2], 15, 0x2ad7d2bb);
    b = round(i, b, c, d, a, words[chunkStart + 9], 21, 0xeb86d391);

    a = addUnsigned(a, aa);
    b = addUnsigned(b, bb);
    c = addUnsigned(c, cc);
    d = addUnsigned(d, dd);
  }

  return toHex(a) + toHex(b) + toHex(c) + toHex(d);
}

