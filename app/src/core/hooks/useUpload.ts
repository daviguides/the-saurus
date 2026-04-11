import { useCallback, useRef, useState } from "react";
import { createJob } from "../services/api";

export type UploadStatus = "idle" | "uploading" | "processing" | "error";

const STORAGE_KEY = "answerthis:job_id";

export function useUpload() {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [paperCount, setPaperCount] = useState(0);
  const uploadingRef = useRef(false);

  const upload = useCallback((files: File[]) => {
    if (uploadingRef.current) return;
    uploadingRef.current = true;

    setStatus("uploading");
    setProgress(0);
    setError(null);

    createJob(files, (pct) => setProgress(pct))
      .then((response) => {
        localStorage.setItem(STORAGE_KEY, response.job_id);
        setJobId(response.job_id);
        setPaperCount(response.paper_count);
        setStatus("processing");
      })
      .catch((err: Error) => {
        setError(err.message);
        setStatus("error");
      })
      .finally(() => {
        uploadingRef.current = false;
      });
  }, []);

  const reset = useCallback(() => {
    setStatus("idle");
    setProgress(0);
    setError(null);
  }, []);

  return { status, progress, error, jobId, paperCount, upload, reset };
}
