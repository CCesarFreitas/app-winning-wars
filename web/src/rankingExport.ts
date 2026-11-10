import { CREST_URL, townHallUrl } from "./assets";
import { dataAtividade, temporadaLabel } from "./format";
import type { AdminContributionEntry, AdminContributionRankingResponse, RankingDetailColumn, RankingDetailEntry, RankingEntry } from "./types";

const GOLD = "#f0b735";
const GOLD_LIGHT = "#ffe7a0";
const TEXT = "#f4eee4";
const MUTED = "#9c9387";
const LINE = "#3d352d";

function roundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function fitText(ctx: CanvasRenderingContext2D, value: string, maxWidth: number): string {
  if (ctx.measureText(value).width <= maxWidth) return value;
  let text = value;
  while (text.length > 1 && ctx.measureText(`${text}…`).width > maxWidth) text = text.slice(0, -1);
  return `${text}…`;
}

async function loadImage(url: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => resolve(null);
    image.src = url;
  });
}

function canvasFor(width: number, height: number) {
  const maxPixels = 42_000_000;
  const scale = Math.min(2, Math.max(1, Math.sqrt(maxPixels / (width * height))));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("O navegador não conseguiu criar a imagem.");
  ctx.scale(scale, scale);
  ctx.textBaseline = "middle";
  return { canvas, ctx, scale };
}

function background(ctx: CanvasRenderingContext2D, width: number, height: number) {
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#17131a");
  gradient.addColorStop(.55, "#0e0c11");
  gradient.addColorStop(1, "#24171f");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#7a5926";
  ctx.lineWidth = 4;
  ctx.strokeRect(16, 16, width - 32, height - 32);
}

function header(ctx: CanvasRenderingContext2D, width: number, title: string, subtitle: string, crest: HTMLImageElement | null) {
  ctx.fillStyle = "rgba(43,32,22,.72)";
  ctx.fillRect(20, 20, width - 40, 154);
  if (crest) ctx.drawImage(crest, 42, 34, 116, 116);
  ctx.fillStyle = GOLD;
  ctx.font = "800 18px 'Nunito Sans', sans-serif";
  ctx.fillText("WINNING WARS APP", 184, 55);
  ctx.fillStyle = TEXT;
  ctx.font = "800 38px 'Cinzel', serif";
  ctx.fillText(title, 184, 99);
  ctx.fillStyle = MUTED;
  ctx.font = "700 17px 'Nunito Sans', sans-serif";
  ctx.fillText(subtitle, 184, 137);
  ctx.textAlign = "right";
  ctx.fillStyle = GOLD_LIGHT;
  ctx.font = "800 15px 'Nunito Sans', sans-serif";
  ctx.fillText("Evolução · Alto desempenho · Competitividade", width - 44, 55);
  ctx.textAlign = "left";
}

function footer(ctx: CanvasRenderingContext2D, width: number, y: number) {
  ctx.strokeStyle = LINE;
  ctx.beginPath(); ctx.moveTo(38, y); ctx.lineTo(width - 38, y); ctx.stroke();
  ctx.fillStyle = MUTED;
  ctx.font = "700 14px 'Nunito Sans', sans-serif";
  ctx.fillText("Pontuação validada pelo motor Winning Wars", 42, y + 31);
  ctx.textAlign = "right";
  ctx.fillText("winningwars.com.br", width - 42, y + 31);
  ctx.textAlign = "left";
}

async function download(canvas: HTMLCanvasElement, filename: string) {
  const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(
    (result) => result ? resolve(result) : reject(new Error("Falha ao finalizar a imagem.")),
    "image/png", 1,
  ));
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

export async function exportCompactRanking(players: RankingEntry[]) {
  if (!players.length) throw new Error("Não há jogadores para exportar.");
  await document.fonts.ready;
  const width = 1200;
  const rowHeight = 64;
  const tableY = 208;
  const height = tableY + 52 + players.length * rowHeight + 82;
  const { canvas, ctx } = canvasFor(width, height);
  background(ctx, width, height);
  const crest = await loadImage(CREST_URL);
  const cvs = new Map<number, HTMLImageElement | null>();
  for (const cv of [...new Set(players.map((player) => player.cv).filter((value): value is number => !!value))]) {
    cvs.set(cv, await loadImage(townHallUrl(cv)));
  }
  header(ctx, width, "Ranking oficial", temporadaLabel(players[0]?.temporada), crest);
  const columns = [38, 135, 250, 985];
  ctx.fillStyle = "#29231f"; ctx.fillRect(32, tableY, width - 64, 52);
  ctx.fillStyle = GOLD; ctx.font = "800 15px 'Nunito Sans', sans-serif";
  ctx.fillText("POS.", columns[0] + 10, tableY + 26);
  ctx.fillText("VILA", columns[1], tableY + 26);
  ctx.fillText("JOGADOR", columns[2], tableY + 26);
  ctx.textAlign = "right"; ctx.fillText("PONTOS", width - 52, tableY + 26); ctx.textAlign = "left";
  players.forEach((player, index) => {
    const y = tableY + 52 + index * rowHeight;
    const podium = player.posicao <= 3;
    ctx.fillStyle = podium ? ["rgba(240,183,53,.19)", "rgba(203,213,225,.12)", "rgba(198,111,61,.14)"][player.posicao - 1] : index % 2 ? "#141116" : "#1a161b";
    ctx.fillRect(32, y, width - 64, rowHeight);
    ctx.strokeStyle = LINE; ctx.beginPath(); ctx.moveTo(32, y + rowHeight); ctx.lineTo(width - 32, y + rowHeight); ctx.stroke();
    ctx.fillStyle = podium ? GOLD_LIGHT : "#c5bdb2"; ctx.font = "800 20px 'Cinzel', serif";
    ctx.fillText(`${player.posicao}º`, columns[0] + 10, y + rowHeight / 2);
    const cvImage = player.cv ? cvs.get(player.cv) : null;
    if (cvImage) ctx.drawImage(cvImage, columns[1] - 7, y + 7, 50, 50);
    ctx.fillStyle = TEXT; ctx.font = "800 19px 'Nunito Sans', sans-serif";
    ctx.fillText(fitText(ctx, player.nome, 620), columns[2], y + 25);
    ctx.fillStyle = MUTED; ctx.font = "700 13px 'Nunito Sans', sans-serif";
    ctx.fillText(`${player.tag}${player.cv ? ` · CV ${player.cv}` : ""}`, columns[2], y + 46);
    ctx.textAlign = "right"; ctx.fillStyle = GOLD_LIGHT; ctx.font = "900 25px 'Cinzel', serif";
    ctx.fillText(String(player.total), width - 52, y + rowHeight / 2); ctx.textAlign = "left";
  });
  footer(ctx, width, height - 68);
  await download(canvas, `ranking_compacto_winning_wars_${players[0]?.temporada || "atual"}.png`);
}

export async function exportDetailedRanking(data: { temporada: string; temporada_nome: string; atualizado_em: string }, columns: RankingDetailColumn[], players: RankingDetailEntry[]) {
  if (!players.length) throw new Error("Não há jogadores para exportar.");
  await document.fonts.ready;
  const nameWidth = 310;
  const activityWidth = 116;
  const width = Math.max(1400, 80 + nameWidth + columns.length * activityWidth + 120);
  const rowHeight = 54;
  const tableY = 220;
  const height = tableY + 78 + players.length * rowHeight + 82;
  const { canvas, ctx } = canvasFor(width, height);
  background(ctx, width, height);
  const crest = await loadImage(CREST_URL);
  header(ctx, width, "Tabela detalhada", `${data.temporada_nome} · ${players.length} jogadores · ${columns.length} atividades`, crest);
  const startX = 38;
  const positionWidth = 70;
  ctx.fillStyle = "#342b24"; ctx.fillRect(32, tableY, width - 64, 34);
  ctx.fillStyle = GOLD; ctx.font = "800 13px 'Nunito Sans', sans-serif";
  ctx.fillText("JOGADORES E PONTUAÇÃO POR ATIVIDADE", 48, tableY + 17);
  ctx.textAlign = "right"; ctx.fillText(`Atualizado: ${dataAtividade(data.atualizado_em)}`, width - 48, tableY + 17); ctx.textAlign = "left";
  const headY = tableY + 34;
  ctx.fillStyle = "#25201e"; ctx.fillRect(32, headY, width - 64, 44);
  const nameX = startX + positionWidth;
  const activitiesX = nameX + nameWidth;
  ctx.fillStyle = GOLD_LIGHT; ctx.font = "800 12px 'Nunito Sans', sans-serif";
  ctx.fillText("POS.", startX + 8, headY + 22); ctx.fillText("JOGADOR", nameX + 8, headY + 22);
  columns.forEach((column, index) => {
    const x = activitiesX + index * activityWidth;
    ctx.textAlign = "center"; ctx.fillText(fitText(ctx, column.rotulo, activityWidth - 10), x + activityWidth / 2, headY + 22);
  });
  ctx.textAlign = "center"; ctx.fillText("TOTAL", activitiesX + columns.length * activityWidth + 55, headY + 22); ctx.textAlign = "left";
  players.forEach((player, index) => {
    const y = tableY + 78 + index * rowHeight;
    ctx.fillStyle = player.posicao <= 3 ? ["rgba(240,183,53,.18)", "rgba(203,213,225,.11)", "rgba(198,111,61,.13)"][player.posicao - 1] : index % 2 ? "#141116" : "#1a161b";
    ctx.fillRect(32, y, width - 64, rowHeight);
    ctx.strokeStyle = LINE; ctx.beginPath(); ctx.moveTo(32, y + rowHeight); ctx.lineTo(width - 32, y + rowHeight); ctx.stroke();
    ctx.fillStyle = player.posicao <= 3 ? GOLD_LIGHT : "#bfb6ab"; ctx.font = "800 16px 'Cinzel', serif";
    ctx.fillText(`${player.posicao}º`, startX + 8, y + rowHeight / 2);
    ctx.fillStyle = TEXT; ctx.font = "800 15px 'Nunito Sans', sans-serif";
    ctx.fillText(fitText(ctx, player.nome, nameWidth - 22), nameX + 8, y + 20);
    ctx.fillStyle = MUTED; ctx.font = "700 11px 'Nunito Sans', sans-serif"; ctx.fillText(player.tag, nameX + 8, y + 38);
    columns.forEach((column, columnIndex) => {
      const x = activitiesX + columnIndex * activityWidth;
      ctx.textAlign = "center"; ctx.fillStyle = "#d5ccc1"; ctx.font = "800 15px 'Nunito Sans', sans-serif";
      ctx.fillText(String(player.pontos[column.chave] ?? 0), x + activityWidth / 2, y + rowHeight / 2);
    });
    ctx.fillStyle = GOLD_LIGHT; ctx.font = "900 18px 'Cinzel', serif";
    ctx.fillText(String(player.total), activitiesX + columns.length * activityWidth + 55, y + rowHeight / 2); ctx.textAlign = "left";
  });
  footer(ctx, width, height - 68);
  await download(canvas, `tabela_detalhada_winning_wars_${data.temporada || "atual"}.png`);
}

export async function exportContributionRanking(data: AdminContributionRankingResponse, players: AdminContributionEntry[]) {
  if (!players.length) throw new Error("Não há candidatos para exportar.");
  await document.fonts.ready;
  const width = 1500;
  const rowHeight = 62;
  const tableY = 220;
  const height = tableY + 52 + players.length * rowHeight + 92;
  const { canvas, ctx } = canvasFor(width, height);
  background(ctx, width, height);
  const crest = await loadImage(CREST_URL);
  const cvs = new Map<number, HTMLImageElement | null>();
  for (const cv of [...new Set(players.map((player) => player.cv).filter((value): value is number => !!value))]) {
    cvs.set(cv, await loadImage(townHallUrl(cv)));
  }
  header(ctx, width, "Contribuição fora da Liga", `${data.temporada_nome} · prévia administrativa do passe extra`, crest);
  const columns = { position: 48, village: 137, player: 220, war: 900, raids: 1015, games: 1125, events: 1235, total: 1438 };
  ctx.fillStyle = "#29231f"; ctx.fillRect(32, tableY, width - 64, 52);
  ctx.fillStyle = GOLD; ctx.font = "800 14px 'Nunito Sans', sans-serif";
  ctx.fillText("POS.", columns.position, tableY + 26); ctx.fillText("VILA", columns.village, tableY + 26); ctx.fillText("JOGADOR", columns.player, tableY + 26);
  [["GUERRAS", columns.war], ["RAIDES", columns.raids], ["JOGOS", columns.games], ["EVENTOS", columns.events]].forEach(([label, x]) => { ctx.textAlign = "center"; ctx.fillText(String(label), Number(x), tableY + 26); });
  ctx.textAlign = "right"; ctx.fillText("TOTAL", columns.total, tableY + 26); ctx.textAlign = "left";
  players.forEach((player, index) => {
    const y = tableY + 52 + index * rowHeight;
    ctx.fillStyle = player.posicao <= 3 ? ["rgba(240,183,53,.19)", "rgba(203,213,225,.12)", "rgba(198,111,61,.14)"][player.posicao - 1] : index % 2 ? "#141116" : "#1a161b";
    ctx.fillRect(32, y, width - 64, rowHeight);
    ctx.strokeStyle = LINE; ctx.beginPath(); ctx.moveTo(32, y + rowHeight); ctx.lineTo(width - 32, y + rowHeight); ctx.stroke();
    ctx.fillStyle = player.posicao <= 3 ? GOLD_LIGHT : "#c5bdb2"; ctx.font = "800 19px 'Cinzel', serif"; ctx.fillText(`${player.posicao}º`, columns.position, y + rowHeight / 2);
    const cvImage = player.cv ? cvs.get(player.cv) : null;
    if (cvImage) ctx.drawImage(cvImage, columns.village - 5, y + 6, 50, 50);
    ctx.fillStyle = TEXT; ctx.font = "800 17px 'Nunito Sans', sans-serif"; ctx.fillText(fitText(ctx, player.nome, 610), columns.player, y + 23);
    ctx.fillStyle = MUTED; ctx.font = "700 12px 'Nunito Sans', sans-serif"; ctx.fillText(`${player.tag || "Sem tag"}${player.cv ? ` · CV ${player.cv}` : ""}`, columns.player, y + 43);
    [[player.guerra, columns.war], [player.raides, columns.raids], [player.jogos, columns.games], [player.eventos, columns.events]].forEach(([value, x]) => { ctx.textAlign = "center"; ctx.fillStyle = "#d4cbc0"; ctx.font = "800 16px 'Nunito Sans', sans-serif"; ctx.fillText(String(value), Number(x), y + rowHeight / 2); });
    ctx.textAlign = "right"; ctx.fillStyle = GOLD_LIGHT; ctx.font = "900 23px 'Cinzel', serif"; ctx.fillText(String(player.total), columns.total, y + rowHeight / 2); ctx.textAlign = "left";
  });
  footer(ctx, width, height - 70);
  await download(canvas, `ranking_contribuicao_sem_liga_${data.temporada}.png`);
}
