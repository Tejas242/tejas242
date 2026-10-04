// Draws assets/sky.svg: the night from screenager.dev, whose city is the
// last year of GitHub contributions. Every building is a run of weeks, every
// window one day (Sunday on top, like the contribution graph), lit in
// GitHub's greens. Only the windows change from day to day; the rest of the
// night is seeded and stays put.
//
//   GITHUB_TOKEN=… node scripts/sky.mjs [login]       fetch and draw
//   node scripts/sky.mjs [login] calendar.json         draw from a saved query

import { readFile, writeFile } from "node:fs/promises"

const LOGIN = process.argv[2] ?? "Tejas242"
const W = 320
const H = 100
const PX = 4

const C = {
  sky: ["#0a1009", "#0d130c", "#10170f", "#141c13", "#192318", "#1f2b1f"],
  star: "#dfe4d9",
  starDim: "#889484",
  ridgeFar: "#1d291c",
  ridgeMid: "#172116",
  ridgeNear: "#111910",
  city: "#0b100a",
  edge: "#202a1f",
  dark: "#151c14",
  hi: "#efe3c0",
  mid: "#cdb88a",
  lo: "#8f7a52",
  pole: "#9fb59a",
  ring: "#e3d6ae",
  ringDim: "#8f8668",
  shade: "#3a3424",
}
const LEVEL = {
  NONE: C.dark,
  FIRST_QUARTILE: "#0e4429",
  SECOND_QUARTILE: "#006d32",
  THIRD_QUARTILE: "#26a641",
  FOURTH_QUARTILE: "#39d353",
}

function rng(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const rand = rng(242)
const grid = Array.from({ length: H }, () => new Array(W).fill(null))
const paint = (x, y, colour) => {
  if (x >= 0 && x < W && y >= 0 && y < H) grid[y][x] = colour
}

// Value noise with octaves, then terraced: the plateaus of the site's ridges.
function ridge(base, amp, steps, seed) {
  const r = rng(seed)
  const knots = Array.from({ length: 64 }, r)
  const at = (x) => {
    const i = Math.floor(x)
    const t = x - i
    const s = t * t * (3 - 2 * t)
    return knots[i % 64] * (1 - s) + knots[(i + 1) % 64] * s
  }
  return Array.from({ length: W }, (_, x) => {
    let h = 0
    let a = 0.5
    let f = 1 / 40
    for (let o = 0; o < 4; o++, a /= 2, f *= 2) h += a * at(x * f + o * 9)
    return Math.round(base - Math.round((h * amp) / steps) * steps)
  })
}

function drawRidge(heights, colour) {
  heights.forEach((top, x) => {
    for (let y = top; y < H; y++) paint(x, y, colour)
  })
}

function drawSaturn(cx, cy, r) {
  const tilt = (-20 * Math.PI) / 180
  const flat = 0.3
  const ring = (x, y) => {
    const u = x * Math.cos(tilt) + y * Math.sin(tilt)
    const v = (-x * Math.sin(tilt) + y * Math.cos(tilt)) / flat
    const d = Math.hypot(u, v) / r
    if (d < 1.3 || d > 2.2 || (d > 1.74 && d < 1.86)) return null
    return { front: v > 0, colour: d < 1.74 ? C.ring : C.ringDim }
  }
  for (let y = -Math.ceil(r * 1.2); y <= Math.ceil(r * 1.2); y++)
    for (let x = -Math.ceil(r * 2.3); x <= Math.ceil(r * 2.3); x++) {
      const band = ring(x, y)
      const disc = x * x + y * y <= r * r
      if (band && (band.front || !disc)) {
        paint(cx + x, cy + y, band.colour)
        continue
      }
      if (!disc) continue
      const nz = Math.sqrt(Math.max(0, 1 - (x * x + y * y) / (r * r)))
      const light = (-x * 0.5 - y * 0.4) / r + nz * 0.8
      const lat = (x * Math.sin(tilt) * -1 + y * Math.cos(tilt)) / r
      const banded = Math.floor((lat + 1) * 4.5) % 2 ? C.mid : C.hi
      paint(
        cx + x,
        cy + y,
        Math.abs(lat) > 0.8 ? C.pole : light < 0.25 ? C.lo : banded,
      )
    }
}

// A building per run of weeks; data floors share one baseline, so reading
// across the windows is reading the contribution graph left to right.
const glows = []

function drawCity(weeks) {
  const PITCH = 3
  const groundTop = H - 2
  const dataTop = groundTop - 7 * PITCH
  const runs = []
  for (let left = weeks.length; left > 0; ) {
    const size = Math.min(left, 2 + Math.floor(rand() * 4))
    runs.push(size)
    left -= size
  }
  const gaps = runs.length - 1
  const width = weeks.length * PITCH + runs.length + gaps * 2
  let x = Math.floor((W - width) / 2)
  let week = 0
  for (const size of runs) {
    const w = size * PITCH + 1
    const extra = Math.floor(rand() * 6)
    const top = dataTop - extra * PITCH - 1
    for (let yy = top; yy < groundTop; yy++)
      for (let xx = x; xx < x + w; xx++)
        paint(xx, yy, yy === top || xx === x || xx === x + w - 1 ? C.edge : C.city)
    for (let f = 0; f < extra; f++)
      for (let i = 0; i < size; i++)
        if (rand() < 0.5) {
          const wx = x + 1 + i * PITCH
          const wy = top + 1 + f * PITCH
          paint(wx, wy, C.dark)
          paint(wx + 1, wy, C.dark)
        }
    if (rand() < 0.55) {
      const ax = x + 1 + Math.floor(rand() * (w - 2))
      const tall = 2 + Math.floor(rand() * 4)
      for (let k = 1; k <= tall; k++) paint(ax, top - k, C.edge)
    } else if (rand() < 0.5 && w > 6) {
      const tx = x + 2 + Math.floor(rand() * (w - 6))
      for (let k = 0; k < 3; k++) {
        paint(tx + k, top - 1, C.edge)
        paint(tx + k, top - 2, C.edge)
      }
    }
    for (let i = 0; i < size; i++, week++)
      weeks[week].forEach((day, d) => {
        const wx = x + 1 + i * PITCH
        const wy = dataTop + d * PITCH
        const colour = LEVEL[day] ?? C.dark
        paint(wx, wy, colour)
        paint(wx + 1, wy, colour)
        paint(wx, wy + 1, colour)
        paint(wx + 1, wy + 1, colour)
        if (day === "THIRD_QUARTILE" || day === "FOURTH_QUARTILE")
          glows.push(`<rect x="${wx - 1}" y="${wy - 1}" width="4" height="4" fill="${colour}" opacity=".3"/>`)
      })
    x += w + 2
  }
  for (let xx = 0; xx < W; xx++)
    for (let yy = groundTop; yy < H; yy++) paint(xx, yy, C.city)
}

function rects() {
  const byColour = new Map()
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; ) {
      const colour = grid[y][x]
      let end = x + 1
      while (end < W && grid[y][end] === colour) end++
      if (colour) {
        const d = byColour.get(colour) ?? []
        d.push(`M${x} ${y}h${end - x}v1h-${end - x}z`)
        byColour.set(colour, d)
      }
      x = end
    }
  return [...byColour]
    .map(([colour, d]) => `<path fill="${colour}" d="${d.join("")}"/>`)
    .join("\n")
}

const sky = () => `<rect width="${W}" height="${H}" fill="url(#sky)"/>`

const gradient = () =>
  `<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">${C.sky
    .map(
      (colour, i) =>
        `<stop offset="${(i / (C.sky.length - 1)).toFixed(2)}" stop-color="${colour}"/>`,
    )
    .join("")}</linearGradient>`

function stars(horizon) {
  const out = []
  for (let i = 0; i < 150; i++) {
    const x = Math.floor(rand() * W)
    const y = Math.floor(rand() ** 1.6 * horizon[x] * 0.92)
    const bright = rand() < 0.12
    const twinkle = rand() < 0.3
    const attrs = twinkle
      ? ` class="tw" style="animation-delay:-${(rand() * 6).toFixed(1)}s"`
      : ""
    out.push(
      `<rect x="${x}" y="${y}" width="1" height="1" fill="${bright ? C.star : C.starDim}"${attrs}/>`,
    )
    if (bright && rand() < 0.4)
      for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]])
        out.push(`<rect x="${x + dx}" y="${y + dy}" width="1" height="1" fill="${C.starDim}" opacity=".6"${attrs}/>`)
  }
  return out.join("\n")
}

async function calendar() {
  const saved = process.argv[3]
  const body = saved
    ? JSON.parse(await readFile(saved, "utf8"))
    : await fetch("https://api.github.com/graphql", {
        method: "POST",
        headers: { authorization: `bearer ${process.env.GITHUB_TOKEN}` },
        body: JSON.stringify({
          query: `query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { contributionLevel } } } } } }`,
          variables: { login: LOGIN },
        }),
      }).then((r) => r.json())
  const cal = body?.data?.user?.contributionsCollection?.contributionCalendar
  if (!cal) throw new Error(`no calendar: ${JSON.stringify(body).slice(0, 200)}`)
  // The newest week is partial: pad the days that haven't happened yet.
  const weeks = cal.weeks.map(({ contributionDays }) => {
    const days = contributionDays.map((d) => d.contributionLevel)
    while (days.length < 7) days.push("NONE")
    return days
  })
  return { total: cal.totalContributions, weeks: weeks.slice(-53) }
}

const { total, weeks } = await calendar()
const far = ridge(60, 30, 3, 7)
const mid = ridge(70, 20, 2, 13)
const near = ridge(80, 12, 2, 19)
drawSaturn(232, 26, 9)
drawRidge(far, C.ridgeFar)
drawRidge(mid, C.ridgeMid)
drawRidge(near, C.ridgeNear)
drawCity(weeks)

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W * PX}" height="${H * PX}" shape-rendering="crispEdges" role="img" aria-label="A pixel-art night city whose lit windows are ${total} GitHub contributions from the last year">
<defs>${gradient()}<style>.tw{animation:tw 5s ease-in-out infinite}@keyframes tw{50%{opacity:.2}}@media (prefers-reduced-motion:reduce){.tw{animation:none}}</style></defs>
${sky()}
${stars(far)}
${rects()}
${glows.join("\n")}
</svg>
`
await writeFile(new URL("../assets/sky.svg", import.meta.url), svg)
console.log(`sky.svg: ${total} contributions, ${(svg.length / 1024).toFixed(1)} KB`)
