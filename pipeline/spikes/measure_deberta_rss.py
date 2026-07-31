"""Peak RSS during DeBERTa load + inference (the Helm 1Gi limit is memory, not disk)."""

from __future__ import annotations

import resource

import torch
from sentence_transformers import CrossEncoder

torch.set_num_threads(1)

model = CrossEncoder("cross-encoder/nli-deberta-v3-base")
model.predict([("Exercise improves cognitive function", "Regular physical exercise improves cognitive function")])

peak_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
# macOS reports bytes, Linux reports KB — this dev box is macOS.
peak_rss_mb = peak_rss_kb / (1024 * 1024)
print(f"peak_rss_mb={peak_rss_mb:.1f}")
