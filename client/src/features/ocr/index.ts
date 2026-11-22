// OCR Feature Module
export interface OcrResult {
  pages: Record<number, string>;
  totalCharacters: number;
}
