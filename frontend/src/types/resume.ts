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

/** `bullets` is null until the experience bullets are chosen (even if none are). */
export type ResumeMapping = { summary: number[]; skills: number[]; bullets: number[] | null };

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
  /** List items after the Summary and Skills: the default experience bullets, once those are marked. */
  proposed_bullets: number[] | null;
  skills: string[] | null;
};
