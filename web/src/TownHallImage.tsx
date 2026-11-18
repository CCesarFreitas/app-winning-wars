import { useState, type ImgHTMLAttributes } from "react";
import { townHallUrl, TOWN_HALL_FALLBACK } from "./assets";

/** Mantém a identificação da vila mesmo se a imagem não estiver disponível. */
export function TownHallImage({ cv, alt, ...props }: Omit<ImgHTMLAttributes<HTMLImageElement>, "src" | "onError"> & { cv: number }) {
  const src = townHallUrl(cv);
  const [failedSource, setFailedSource] = useState<string | null>(null);
  return <img {...props} src={failedSource === src ? TOWN_HALL_FALLBACK : src}
    alt={alt ?? `Centro de Vila ${cv}`} onError={() => setFailedSource(src)} />;
}
