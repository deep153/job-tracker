import { useEffect, useState, type DragEvent } from "react";
import {
  getResume,
  listResumeVersions,
  saveResumeMapping,
  saveResumeSkills,
  uploadResume,
  type Resume,
  type ResumeMapping,
  type ResumeParagraph,
  type ResumeVersion,
} from "./api";
import { fullDate, timeAgo } from "./format";
import { AlertIcon, CheckIcon, DownloadIcon, ExternalIcon, FileIcon, UploadIcon } from "./icons";
import { Field, TermInput } from "./SearchSettingsPanel";
import { Topbar } from "./Topbar";

const DOCX_ACCEPT = ".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

type Role = "summary" | "skills";

type Draft = Record<number, Role>;

const ROLE_LABELS: Record<Role, string> = { summary: "Summary", skills: "Skills" };

function draftFrom(mapping: ResumeMapping | null): Draft {
  const draft: Draft = {};
  for (const index of mapping?.summary ?? []) draft[index] = "summary";
  for (const index of mapping?.skills ?? []) draft[index] = "skills";
  return draft;
}

function mappingFrom(draft: Draft): ResumeMapping {
  const indexes = (role: Role) =>
    Object.entries(draft)
      .filter(([, r]) => r === role)
      .map(([index]) => Number(index))
      .sort((a, b) => a - b);
  return { summary: indexes("summary"), skills: indexes("skills") };
}

function pages(count: number): string {
  return `${count} ${count === 1 ? "page" : "pages"}`;
}

export function ResumePage() {
  const [resume, setResume] = useState<Resume | null | undefined>(undefined);
  const [versions, setVersions] = useState<ResumeVersion[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function load() {
    setLoadError(null);
    try {
      const [current, all] = await Promise.all([getResume(), listResumeVersions()]);
      setResume(current);
      setVersions(all);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function update(next: Resume) {
    setResume(next);
    listResumeVersions().then(setVersions, () => {});
  }

  async function upload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      update(await uploadResume(file));
    } catch (e) {
      setUploadError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="app">
      <Topbar page="resume" />
      <main className="page">
        <div className="page-heading">
          <h1>Resume</h1>
          <p className="subtitle">
            Your master resume. When you apply, only the Summary is rewritten and your Skills reordered; everything
            else stays exactly as it is.
          </p>
        </div>

        {loadError && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{loadError}</span>
            <button className="button button-ghost" onClick={load}>
              Retry
            </button>
          </div>
        )}
        {uploadError && (
          <div className="notice notice-error" role="alert">
            <AlertIcon />
            <span className="notice-text">{uploadError}</span>
            <button className="icon-button" onClick={() => setUploadError(null)} aria-label="Dismiss">
              ×
            </button>
          </div>
        )}

        {resume === undefined ? (
          !loadError && <div className="skeleton resume-skeleton" aria-busy="true" aria-label="Loading resume" />
        ) : resume === null ? (
          <UploadCard uploading={uploading} onFile={upload} />
        ) : (
          <>
            <ResumeFile resume={resume} uploading={uploading} onFile={upload} />
            <ReadyNotice resume={resume} />
            <div className="resume-layout">
              <div className="resume-main">
                <MappingEditor key={resume.version} resume={resume} onSaved={update} />
                <SkillsEditor key={`skills-${resume.version}`} resume={resume} onSaved={update} />
                <VersionList versions={versions} current={resume.version} />
              </div>
              <Preview resume={resume} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function FileButton({
  label,
  busyLabel,
  busy,
  primary,
  onFile,
}: {
  label: string;
  busyLabel: string;
  busy: boolean;
  primary?: boolean;
  onFile: (file: File) => void;
}) {
  return (
    <label
      className={`button ${primary ? "button-primary" : "button-secondary button-small"} file-button`}
      aria-disabled={busy}
    >
      <input
        type="file"
        accept={DOCX_ACCEPT}
        className="visually-hidden"
        disabled={busy}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) onFile(file);
        }}
      />
      {busy ? <span className={`spinner${primary ? "" : " spinner-dark"}`} aria-hidden="true" /> : <UploadIcon />}
      {busy ? busyLabel : label}
    </label>
  );
}

function UploadCard({ uploading, onFile }: { uploading: boolean; onFile: (file: File) => void }) {
  const [over, setOver] = useState(false);

  function drop(event: DragEvent) {
    event.preventDefault();
    setOver(false);
    const file = event.dataTransfer.files[0];
    if (file && !uploading) onFile(file);
  }

  return (
    <section
      className={`empty dropzone${over ? " is-over" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={drop}
    >
      <div className="empty-icon" aria-hidden="true">
        <FileIcon size={28} />
      </div>
      <h2>Upload your resume</h2>
      <p>
        Drop your resume here as a Word document (.docx). It becomes the template for every tailored resume, so use
        the version you'd send today.
      </p>
      <FileButton label="Choose .docx file" busyLabel="Importing…" busy={uploading} primary onFile={onFile} />
    </section>
  );
}

function ResumeFile({
  resume,
  uploading,
  onFile,
}: {
  resume: Resume;
  uploading: boolean;
  onFile: (file: File) => void;
}) {
  return (
    <section className="panel resume-file">
      <div className="resume-file-icon" aria-hidden="true">
        <FileIcon size={20} />
      </div>
      <div className="resume-file-main">
        <h2 className="resume-file-name">{resume.filename}</h2>
        <p className="resume-file-meta">
          Version {resume.version} · {pages(resume.page_count)} · Uploaded{" "}
          <time dateTime={resume.uploaded_at} title={fullDate(resume.uploaded_at)}>
            {timeAgo(resume.uploaded_at)}
          </time>
        </p>
      </div>
      <a className="button button-ghost" href={resume.original_url} download>
        <DownloadIcon />
        .docx
      </a>
      <FileButton label="Replace resume" busyLabel="Importing…" busy={uploading} onFile={onFile} />
    </section>
  );
}

function ReadyNotice({ resume }: { resume: Resume }) {
  if (resume.ready) {
    return (
      <div className="notice notice-success" role="status">
        <CheckIcon />
        <span className="notice-text">
          Ready for tailoring: {resume.mapping!.summary.length} Summary and {resume.mapping!.skills.length} Skills{" "}
          {resume.mapping!.skills.length === 1 ? "paragraph" : "paragraphs"} marked, {resume.skills!.length} skills in
          your master list.
        </span>
      </div>
    );
  }
  return (
    <div className="notice notice-info" role="status">
      <span className="notice-text">
        Check the preview, then mark which paragraphs are your <strong>Summary</strong> and which are your{" "}
        <strong>Skills</strong> section and save.
        {resume.version > 1 && " Each new version is marked on its own."}
      </span>
    </div>
  );
}

function MappingEditor({ resume, onSaved }: { resume: Resume; onSaved: (resume: Resume) => void }) {
  const saved = draftFrom(resume.mapping);
  const [draft, setDraft] = useState(saved);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = JSON.stringify(mappingFrom(draft)) !== JSON.stringify(mappingFrom(saved));
  const counts = mappingFrom(draft);
  const visible = resume.paragraphs.filter((p) => p.text);

  function mark(index: number, role: Role) {
    setError(null);
    setDraft((current) => {
      const next = { ...current };
      if (next[index] === role) delete next[index];
      else next[index] = role;
      return next;
    });
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const next = await saveResumeMapping(mappingFrom(draft));
      setDraft(draftFrom(next.mapping));
      onSaved(next);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel" aria-labelledby="mapping-heading">
      <div className="panel-header mapping-header">
        <div className="mapping-title">
          <h2 className="panel-title" id="mapping-heading">
            Summary and Skills
          </h2>
          <p className="mapping-counts">
            <span className="legend legend-summary" /> {counts.summary.length} Summary
            <span className="legend legend-skills" /> {counts.skills.length} Skills
          </p>
        </div>
        <span className="save-status" aria-live="polite">
          {dirty ? "Unsaved changes" : resume.mapping ? "Saved" : ""}
        </span>
        {dirty && (
          <button type="button" className="button button-ghost" onClick={() => setDraft(saved)}>
            Discard
          </button>
        )}
        <button
          type="button"
          className="button button-primary button-small"
          onClick={save}
          disabled={(!dirty && resume.mapping !== null) || saving}
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
      {error && (
        <p className="field-error mapping-error" role="alert">
          {error}
        </p>
      )}
      <ol className="paragraphs">
        {visible.map((paragraph) => (
          <ParagraphRow
            key={paragraph.index}
            paragraph={paragraph}
            role={draft[paragraph.index]}
            onMark={(role) => mark(paragraph.index, role)}
          />
        ))}
      </ol>
    </section>
  );
}

function ParagraphRow({
  paragraph,
  role,
  onMark,
}: {
  paragraph: ResumeParagraph;
  role: Role | undefined;
  onMark: (role: Role) => void;
}) {
  const heading = /^(Title|Heading)/.test(paragraph.style ?? "");
  const details = [
    paragraph.size !== null && `${paragraph.size} pt`,
    paragraph.bold && !heading && "Bold",
    paragraph.italic && "Italic",
    paragraph.alignment === "center" && "Centered",
  ].filter((d): d is string => Boolean(d));
  return (
    <li className={`paragraph${role ? ` is-${role}` : ""}`}>
      <div className="paragraph-body">
        <p
          className={[
            "paragraph-text",
            heading && "is-heading",
            paragraph.bold && "is-bold",
            paragraph.italic && "is-italic",
            paragraph.is_list && "is-list",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {paragraph.text}
        </p>
        <div className="paragraph-meta">
          {paragraph.style && <span className="badge">{paragraph.style}</span>}
          {details.length > 0 && <span>{details.join(" · ")}</span>}
        </div>
      </div>
      <div className="paragraph-roles" role="group" aria-label="Mark this paragraph as">
        {(["summary", "skills"] as Role[]).map((r) => (
          <button
            key={r}
            type="button"
            className={`paragraph-role role-${r}`}
            aria-pressed={role === r}
            onClick={() => onMark(r)}
          >
            {ROLE_LABELS[r]}
          </button>
        ))}
      </div>
    </li>
  );
}

function SkillsEditor({ resume, onSaved }: { resume: Resume; onSaved: (resume: Resume) => void }) {
  const savedSkills = resume.skills ?? [];
  const [draft, setDraft] = useState(savedSkills);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = JSON.stringify(draft) !== JSON.stringify(savedSkills);

  useEffect(() => {
    setDraft(resume.skills ?? []);
  }, [JSON.stringify(resume.skills)]);

  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 2500);
    return () => clearTimeout(timer);
  }, [saved]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      onSaved(await saveResumeSkills(draft));
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel" aria-labelledby="skills-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="skills-heading">
          Master skills list
        </h2>
        {resume.skills && <span className="count count-small">{draft.length}</span>}
      </div>
      <div className="panel-body">
        {resume.skills === null ? (
          <p className="panel-empty">Save your Summary and Skills to fill this list from your Skills section.</p>
        ) : (
          <>
            <Field
              label="Skills"
              hint="Pre-filled from your Skills section. Tailoring can only ever use skills from this list, so add any you have that aren't on your resume yet."
            >
              <TermInput
                label="Skills"
                terms={draft}
                placeholder="e.g. Python"
                onChange={(skills) => {
                  setDraft(skills);
                  setSaved(false);
                }}
              />
            </Field>
            {error && (
              <p className="field-error" role="alert">
                {error}
              </p>
            )}
            <div className="panel-actions">
              <span className="save-status" aria-live="polite">
                {saved ? "Saved" : dirty ? "Unsaved changes" : ""}
              </span>
              {dirty && (
                <button type="button" className="button button-ghost" onClick={() => setDraft(savedSkills)}>
                  Discard
                </button>
              )}
              <button
                type="button"
                className="button button-primary button-small"
                onClick={save}
                disabled={!dirty || saving}
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}

function Preview({ resume }: { resume: Resume }) {
  return (
    <section className="panel resume-preview-panel" aria-labelledby="preview-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="preview-heading">
          PDF preview
        </h2>
        <span className="count count-small">{pages(resume.page_count)}</span>
        <a className="button button-ghost" href={resume.preview_url} target="_blank" rel="noreferrer">
          Open
          <ExternalIcon />
          <span className="visually-hidden">(opens in a new tab)</span>
        </a>
      </div>
      <iframe className="resume-preview" src={`${resume.preview_url}#view=FitH`} title="PDF preview of your resume" />
    </section>
  );
}

function VersionList({ versions, current }: { versions: ResumeVersion[]; current: number }) {
  if (versions.length < 2) return null;
  return (
    <section className="panel" aria-labelledby="versions-heading">
      <div className="panel-header">
        <h2 className="panel-title" id="versions-heading">
          Versions
        </h2>
        <span className="count count-small">{versions.length}</span>
      </div>
      <ul className="version-list">
        {versions.map((v) => (
          <li className="version" key={v.version}>
            <div className="version-main">
              <span className="version-name">
                Version {v.version}
                {v.version === current && <span className="badge badge-green">Current</span>}
              </span>
              <span className="version-meta">
                {v.filename} · {pages(v.page_count)} ·{" "}
                <time dateTime={v.uploaded_at} title={fullDate(v.uploaded_at)}>
                  {timeAgo(v.uploaded_at)}
                </time>
              </span>
            </div>
            <a className="button button-ghost button-tiny" href={v.preview_url} target="_blank" rel="noreferrer">
              PDF
            </a>
            <a className="button button-ghost button-tiny" href={v.original_url} download>
              .docx
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
