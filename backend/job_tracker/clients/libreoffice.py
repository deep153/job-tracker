import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

CONVERSION_TIMEOUT_SECONDS = 120

_MAC_APP = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

# One profile per backend process, kept between conversions so LibreOffice starts warm. A profile can't be
# used by two LibreOffice processes at once, so conversions take turns.
_PROFILE = Path(tempfile.gettempdir()) / f"job-tracker-libreoffice-{os.getpid()}"
_CONVERT_LOCK = threading.Lock()

MISSING_MESSAGE = (
    "LibreOffice isn't installed, so resumes can't be converted to PDF. Install it from "
    "https://www.libreoffice.org/download/ (or set JOB_TRACKER_SOFFICE to its soffice program), "
    "then restart the backend."
)


class ConversionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LibreOffice:
    """Converts .docx files to PDF with headless LibreOffice."""

    def __init__(self, executable: str | None) -> None:
        self.executable = executable if executable and Path(executable).is_file() else None

    @classmethod
    def detect(cls) -> "LibreOffice":
        candidates = [os.environ.get("JOB_TRACKER_SOFFICE"), shutil.which("soffice"), shutil.which("libreoffice")]
        candidates.append(_MAC_APP)
        return cls(next((c for c in candidates if c and Path(c).is_file()), None))

    @property
    def available(self) -> bool:
        return self.executable is not None

    def convert_to_pdf(self, docx: Path, out_dir: Path) -> Path:
        if self.executable is None:
            raise ConversionError(MISSING_MESSAGE)
        command = [
            self.executable,
            f"-env:UserInstallation={_PROFILE.as_uri()}",
            "--headless",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(docx),
        ]
        with _CONVERT_LOCK:
            try:
                subprocess.run(command, capture_output=True, timeout=CONVERSION_TIMEOUT_SECONDS, check=False)
            except subprocess.TimeoutExpired:
                raise ConversionError("LibreOffice took too long to convert the resume to PDF.") from None
        pdf = out_dir / f"{docx.stem}.pdf"
        if not pdf.is_file():
            raise ConversionError("LibreOffice couldn't convert the resume to PDF.")
        return pdf
