export interface IngestionFile {
  file: File;
  documentType: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;
}
