export const CREST_URL = `${import.meta.env.BASE_URL}assets/ww-crest.png`;
export const MAX_TOWN_HALL = 19;
export const LAYOUT_TOWN_HALLS = Array.from({ length: MAX_TOWN_HALL - 8 }, (_, i) => MAX_TOWN_HALL - i);
export const hasTownHallImage = (cv: unknown): cv is number =>
  typeof cv === "number" && Number.isInteger(cv) && cv >= 9 && cv <= MAX_TOWN_HALL;
export const TOWN_HALL_FALLBACK = "data:image/svg+xml," + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"><rect x="8" y="8" width="104" height="104" rx="24" fill="#182638" stroke="#d4ab54" stroke-width="3"/><text x="60" y="78" text-anchor="middle" font-family="sans-serif" font-size="56" fill="#d4ab54">?</text></svg>'
);
export const townHallUrl = (cv: number) => hasTownHallImage(cv)
  ? `${import.meta.env.BASE_URL}assets/centros-vila/cv${cv}.${cv === 19 ? "svg" : "webp"}`
  : TOWN_HALL_FALLBACK;
