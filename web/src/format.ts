export function numero(value: number | null | undefined): string {
  return new Intl.NumberFormat("pt-BR").format(value || 0);
}

export function dataAtividade(value: string | null | undefined): string {
  if (!value) return "Data não informada";
  const match = value.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})/);
  if (!match) return value;
  const [, ano, mes, dia, hora, minuto, segundo] = match;
  const date = new Date(`${ano}-${mes}-${dia}T${hora}:${minuto}:${segundo}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  }).format(date);
}

export function rotuloTipo(tipo: string): string {
  const tipos: Record<string, string> = {
    guerra: "Guerra",
    raid: "Raide",
    raide: "Raide",
    liga: "Liga",
    jogos: "Jogos do Clã",
    evento: "Evento",
  };
  return tipos[tipo.toLowerCase()] || tipo;
}

export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  return (partes[0]?.[0] || "W") + (partes[1]?.[0] || partes[0]?.[1] || "W");
}

export function temporadaLabel(value: string | null | undefined): string {
  if (!value || !/^\d{4}-\d{2}$/.test(value)) return "Temporada atual";
  const [ano, mes] = value.split("-").map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, 1));
  const nome = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric", timeZone: "UTC" }).format(data);
  return nome.charAt(0).toUpperCase() + nome.slice(1);
}
