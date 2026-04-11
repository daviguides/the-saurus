export const PIPELINE_API_URL =
  import.meta.env.VITE_PIPELINE_URL || "http://localhost:8002";

export interface CreateJobResponse {
  job_id: string;
  paper_count: number;
  status: string;
}

export interface PaperInfo {
  paper_id: string;
  title: string;
  filename: string;
}

export async function fetchPapers(jobId: string): Promise<PaperInfo[]> {
  const res = await fetch(`${PIPELINE_API_URL}/jobs/${jobId}/papers`);
  if (!res.ok) return [];
  const data = await res.json();
  return (data.papers ?? []) as PaperInfo[];
}

export function createJob(
  files: File[],
  onProgress?: (percent: number) => void,
): Promise<CreateJobResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${PIPELINE_API_URL}/jobs`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status === 201) {
        try {
          resolve(JSON.parse(xhr.responseText) as CreateJobResponse);
        } catch {
          reject(new Error("Invalid response from server"));
        }
      } else {
        let message = `Upload failed (${xhr.status})`;
        try {
          const body = JSON.parse(xhr.responseText);
          if (body.detail) message = body.detail;
        } catch {
          // use default message
        }
        reject(new Error(message));
      }
    };

    xhr.onerror = () => {
      reject(new Error("Network error — is the pipeline server running?"));
    };

    xhr.send(formData);
  });
}
