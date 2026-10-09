export type ResumeParagraph = {
  index: number;
  text: string;
  style: string | null;
  bold: boolean;
  italic: boolean;
  font: string | null;
  size: number | null;
  alignment: string | null;
  is_list: boolean;
};

export type ResumeMapping = { summary: number[]; skills: number[] };

export type ResumeVersion = {
  version: number;
  filename: string;
  uploaded_at: string;
  page_count: number;
  ready: boolean;
  preview_url: string;
  original_url: string;
};

export type Resume = ResumeVersion & {
  paragraphs: ResumeParagraph[];
  mapping: ResumeMapping | null;
  skills: string[] | null;
};
