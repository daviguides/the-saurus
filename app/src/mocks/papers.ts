import type { Paper } from "../core/types/paper";

export const MOCK_COMPLETE_PAPERS: Paper[] = [
  {
    id: "mock-1",
    title: "Attention Is All You Need",
    fileName: "attention-is-all-you-need.pdf",
    sizeBytes: 2_340_000,
    addedAt: Date.now() - 3600_000,
    themes: [
      { id: "t1", label: "Self-Attention", colorIndex: 0 },
      { id: "t2", label: "Sequence Modeling", colorIndex: 1 },
      { id: "t3", label: "Parallelization", colorIndex: 2 },
    ],
    claims: [
      { id: "c1", text: "The Transformer relies entirely on self-attention to compute representations, dispensing with recurrence and convolutions.", page: 1, paragraph: 1, themeId: "t1" },
      { id: "c2", text: "Multi-head attention allows the model to jointly attend to information from different representation subspaces.", page: 3, paragraph: 2, themeId: "t1" },
      { id: "c3", text: "The Transformer achieves state-of-the-art BLEU scores on WMT 2014 English-to-German translation.", page: 7, paragraph: 1, themeId: "t2" },
    ],
  },
  {
    id: "mock-2",
    title: "BERT Pre-training of Deep Bidirectional Transformers",
    fileName: "bert-pretraining.pdf",
    sizeBytes: 1_890_000,
    addedAt: Date.now() - 3000_000,
    themes: [
      { id: "t4", label: "Pre-training", colorIndex: 3 },
      { id: "t1", label: "Self-Attention", colorIndex: 0 },
      { id: "t5", label: "Transfer Learning", colorIndex: 4 },
    ],
    claims: [
      { id: "c4", text: "BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context.", page: 1, paragraph: 1, themeId: "t4" },
      { id: "c5", text: "Fine-tuned BERT models achieve state-of-the-art results on eleven NLP tasks.", page: 1, paragraph: 2, themeId: "t5" },
    ],
  },
  {
    id: "mock-3",
    title: "Scaling Laws for Neural Language Models",
    fileName: "scaling-laws-neural-lm.pdf",
    sizeBytes: 3_120_000,
    addedAt: Date.now() - 2400_000,
    themes: [
      { id: "t6", label: "Scaling Laws", colorIndex: 5 },
      { id: "t7", label: "Compute Efficiency", colorIndex: 6 },
      { id: "t2", label: "Sequence Modeling", colorIndex: 1 },
    ],
    claims: [
      { id: "c6", text: "Language model performance scales as a power-law with model size, dataset size, and compute budget.", page: 2, paragraph: 1, themeId: "t6" },
      { id: "c7", text: "Larger models are significantly more sample-efficient than smaller models.", page: 4, paragraph: 3, themeId: "t7" },
      { id: "c8", text: "Performance depends strongly on scale and weakly on model shape.", page: 3, paragraph: 1, themeId: "t6" },
    ],
  },
];
