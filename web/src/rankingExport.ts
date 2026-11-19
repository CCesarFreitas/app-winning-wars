import { battlePerformance, leagueRounds, percent } from "./playerPerformance";
import { CREST_URL, townHallUrl, TOWN_HALL_FALLBACK } from "./assets";
import { dataAtividade, temporadaLabel } from "./format";
import type { AdminContributionEntry, AdminContributionRankingResponse, PlayerAuditRecord, PlayerAuditResponse, PlayerFeedback, RankingDetailColumn, RankingDetailEntry, RankingEntry } from "./types";

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

async function loadTownHallImage(cv: number): Promise<HTMLImageElement | null> {
  return (await loadImage(townHallUrl(cv))) ?? loadImage(TOWN_HALL_FALLBACK);
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
    cvs.set(cv, await loadTownHallImage(cv));
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
    cvs.set(cv, await loadTownHallImage(cv));
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

function numeroSeguro(valor: number | undefined | null) {
  return typeof valor === "number" && Number.isFinite(valor) ? valor : 0;
}

function dadosRaide(registros: PlayerAuditRecord[]) {
  const raides = registros.filter((registro) => (registro.tipo === "raide" || registro.tipo === "raid"));
  return {
    atividades: raides.length,
    ataques: raides.reduce((total, registro) => total + (typeof registro.jogador.ataques === "number" ? registro.jogador.ataques : 0), 0),
    saque: raides.reduce((total, registro) => total + numeroSeguro(registro.jogador.capital_resources_looted), 0),
    bonus: raides.reduce((total, registro) => total + numeroSeguro(registro.jogador.bonus_top3), 0),
    pontos: raides.reduce((total, registro) => total + numeroSeguro(registro.jogador.pontos_competicao), 0),
  };
}

export async function exportPlayerFeedback(player: PlayerFeedback, audit: PlayerAuditResponse) {
  if (player.temporada !== audit.temporada || player.tag !== audit.player_tag || audit.registros.some((r) => r.temporada !== audit.temporada)) throw new Error("Período da exportação divergente. Atualize a ficha.");
  await document.fonts.ready;
  const width = 1500;
  const height = 2080;
  const { canvas, ctx } = canvasFor(width, height);
  background(ctx, width, height);
  const [crest, cv] = await Promise.all([loadImage(CREST_URL), player.cv ? loadTownHallImage(player.cv) : Promise.resolve(null)]);
  header(ctx, width, "Feedback individual", `${temporadaLabel(player.temporada)} · atividades encerradas e conferidas`, crest);
  const guerra = battlePerformance(audit.registros, "guerra");
  const liga = battlePerformance(audit.registros, "liga");
  const raide = dadosRaide(audit.registros);
  const card = (x: number, y: number, widthCard: number, label: string, value: string, sub: string, accent: string) => {
    roundedRect(ctx, x, y, widthCard, 132, 16);
    ctx.fillStyle = "#201a1d"; ctx.fill();
    ctx.strokeStyle = accent; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = MUTED; ctx.font = "800 14px 'Nunito Sans', sans-serif"; ctx.fillText(label.toUpperCase(), x + 20, y + 25);
    ctx.fillStyle = GOLD_LIGHT; ctx.font = "900 34px 'Cinzel', serif"; ctx.fillText(value, x + 20, y + 69);
    ctx.fillStyle = TEXT; ctx.font = "700 14px 'Nunito Sans', sans-serif"; ctx.fillText(fitText(ctx, sub, widthCard - 40), x + 20, y + 105);
  };
  const section = (y: number, icon: string, title: string, description: string, rows: Array<[string, string]>, accent: string) => {
    roundedRect(ctx, 42, y, width - 84, 230, 18);
    ctx.fillStyle = "rgba(27,23,27,.94)"; ctx.fill(); ctx.strokeStyle = "#46382d"; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = accent; ctx.font = "900 33px 'Cinzel', serif"; ctx.fillText(icon, 72, y + 47);
    ctx.fillStyle = TEXT; ctx.font = "800 26px 'Cinzel', serif"; ctx.fillText(title, 122, y + 42);
    ctx.fillStyle = MUTED; ctx.font = "700 15px 'Nunito Sans', sans-serif"; ctx.fillText(description, 122, y + 72);
    const col = 3; const rowWidth = (width - 180) / col;
    rows.forEach(([label, value], index) => {
      const x = 74 + (index % col) * rowWidth;
      const lineY = y + 120 + Math.floor(index / col) * 63;
      ctx.fillStyle = MUTED; ctx.font = "800 13px 'Nunito Sans', sans-serif"; ctx.fillText(label.toUpperCase(), x, lineY);
      ctx.fillStyle = GOLD_LIGHT; ctx.font = "900 23px 'Cinzel', serif"; ctx.fillText(value, x, lineY + 29);
    });
  };

  roundedRect(ctx, 42, 205, width - 84, 164, 18); ctx.fillStyle = "rgba(39,30,23,.9)"; ctx.fill(); ctx.strokeStyle = "#805d29"; ctx.lineWidth = 2; ctx.stroke();
  if (cv) ctx.drawImage(cv, 72, 228, 108, 108);
  ctx.fillStyle = GOLD; ctx.font = "800 15px 'Nunito Sans', sans-serif"; ctx.fillText(player.posicao != null ? `${player.posicao}º LUGAR NA TEMPORADA` : "HISTÓRICO DO MÊS SELECIONADO", cv ? 208 : 78, 237);
  ctx.fillStyle = TEXT; ctx.font = "900 35px 'Cinzel', serif"; ctx.fillText(fitText(ctx, player.nome, 760), cv ? 208 : 78, 281);
  ctx.fillStyle = MUTED; ctx.font = "700 16px 'Nunito Sans', sans-serif"; ctx.fillText(`${player.tag}${player.cv ? ` · Centro de Vila ${player.cv}` : ""}`, cv ? 208 : 78, 316);
  ctx.textAlign = "right"; ctx.fillStyle = GOLD_LIGHT; ctx.font = "900 62px 'Cinzel', serif"; ctx.fillText(String(player.total ?? "—"), width - 78, 277);
  ctx.fillStyle = MUTED; ctx.font = "800 15px 'Nunito Sans', sans-serif"; ctx.fillText("PONTOS NA COMPETIÇÃO", width - 78, 316); ctx.textAlign = "left";

  const cardsY = 400;
  card(42, cardsY, 270, "Guerras · pontos", String(guerra.points), "atividades registradas", "#c77f35");
  card(328, cardsY, 270, "Liga · pontos", String(liga.points), "atividades registradas", "#f0b735");
  card(614, cardsY, 270, "Raides", String(player.raides ?? "—"), `${raide.atividades} fim(ns) de semana`, "#478d89");
  card(900, cardsY, 270, "Jogos do Clã", String(player.jogos ?? "—"), "pontos na competição", "#8065b5");
  card(1186, cardsY, 272, "Eventos", String(player.eventos ?? "—"), "pontos na competição", "#9b5365");
  const battleSection = (y: number, title: string, stats: ReturnType<typeof battlePerformance>) => section(y, "⚔", title, "Somente escalações registradas; reservas não contam como falta", [
    ["Escalações / ataques", `${stats.activities.length} / ${stats.attacks.length}`],
    ["Sem atacar / ataques não usados", `${stats.noAttack} / ${stats.missing ?? '—'}`],
    ["Taxa de 3★ por ataque", percent(stats.tripleRate)],
    ["Ataques de 3★ / 2★", `${stats.distribution[3]} / ${stats.distribution[2]}`],
    ["Ataques de 1★ / 0★", `${stats.distribution[1]} / ${stats.distribution[0]}`],
    ["Média de estrelas", stats.average?.toFixed(2) ?? "—"],
  ], "#f0b735");
  battleSection(570, "Liga · desempenho individual", liga);
  ctx.font = "700 15px 'Nunito Sans', sans-serif"; ctx.fillStyle = TEXT;
  leagueRounds(audit.registros, audit.liga_rodadas_disponiveis).forEach((r, i) => {
    ctx.fillText(`R${r.round}: ${r.label}`, 54 + i * 202, 830);
  });
  battleSection(870, "Guerras comuns", guerra);
  section(1130, "☄", "Raides", "Participação e saque na Capital do Clã", [
    ["Raides registrados", String(raide.atividades)], ["Ataques usados", String(raide.ataques)], ["Saque total", raide.saque.toLocaleString("pt-BR")],
    ["Saque por ataque", raide.ataques ? Math.round(raide.saque / raide.ataques).toLocaleString("pt-BR") : "—"], ["Bônus Top 3", String(raide.bonus)], ["Pontos automáticos", String(raide.pontos)],
  ], "#6ac9c1");
  section(1390, "♛", "Jogos do Clã e Eventos", "Lançamentos manuais substituem o total por atividade, sem somar duplicado", [
    ["Pontos em Jogos", String(player.jogos ?? "—")], ["Pontos em Eventos", String(player.eventos ?? "—")], ["Total manual", player.jogos != null && player.eventos != null ? String(player.jogos + player.eventos) : "—"],
    ["Origem", player.origem === "fotografia_fechamento" ? "Fechamento preservado" : player.origem === "ranking_atual" ? "Ranking atual" : "Não disponível"], ["Registro automático", `${audit.total} atividade(s)`], ["Situação", player.total != null ? "Pontuação consolidada" : "Totais indisponíveis"],
  ], "#c786e2");

  ctx.fillStyle = "#4b4038"; ctx.fillRect(42, 1660, width - 84, 2);
  ctx.fillStyle = TEXT; ctx.font = "800 18px 'Cinzel', serif"; ctx.fillText("Leitura responsável do desempenho", 72, 1705);
  ctx.fillStyle = MUTED; ctx.font = "700 15px 'Nunito Sans', sans-serif";
  ctx.fillText("Este feedback usa somente atividades encerradas, preservadas e conferidas. A ausência no histórico não prova falta de participação.", 72, 1742);
  ctx.fillText("Taxas usam ataques com estrelas registradas. Sem registro não significa reserva ou falta. Considere CVs e tamanho da amostra.", 72, 1774);
  ctx.fillText(`Gerado em ${new Date().toLocaleString("pt-BR")} · ${audit.total} registros automáticos analisados.`, 72, 1806);
  footer(ctx, width, height - 72);
  await download(canvas, `feedback_${player.nome.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "").toLowerCase() || "jogador"}_${(player.temporada || "atual").replace("-", "_")}.png`);
}
