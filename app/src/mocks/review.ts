import type { ReviewData } from "../core/types/review";

const REVIEW_MARKDOWN = `## Self-Attention Mechanisms

The concept of self-attention has fundamentally transformed sequence modeling in deep learning. Vaswani et al. demonstrated that the Transformer relies entirely on self-attention to compute representations, dispensing with recurrence and convolutions entirely [1](cite:1 "p.1,§1"). This architectural choice enables significantly greater parallelization during training compared to recurrent models.

A key innovation is the multi-head attention mechanism, which allows the model to jointly attend to information from different representation subspaces at different positions [1](cite:1 "p.3,§2"). This capability proved essential for capturing diverse linguistic relationships within a single layer.

Building on this foundation, Devlin et al. introduced BERT, which is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context [2](cite:2 "p.1,§1"). The bidirectional nature of BERT's attention mechanism represents a significant departure from the left-to-right constraints of earlier Transformer variants.

## Scaling and Efficiency

The relationship between model scale and performance has emerged as a central theme in modern deep learning research. Kaplan et al. established that language model performance scales as a power-law with model size, dataset size, and compute budget [3](cite:3 "p.2,§1"). These scaling laws provide a principled framework for allocating computational resources.

Importantly, the research reveals that performance depends strongly on scale and weakly on model shape [3](cite:3 "p.3,§1"), suggesting that practitioners should prioritize increasing overall model size rather than optimizing architectural details. Furthermore, larger models are significantly more sample-efficient than smaller models [3](cite:3 "p.4,§3"), which has profound implications for data collection strategies.

## Transfer Learning and Fine-tuning

The paradigm of pre-training followed by fine-tuning has become the dominant approach in NLP. Fine-tuned BERT models achieve state-of-the-art results on eleven NLP tasks [2](cite:2 "p.1,§2"), demonstrating the broad applicability of pre-trained representations. This success has catalyzed a shift away from task-specific architectures toward general-purpose pre-trained models.

The Transformer architecture itself has proven remarkably versatile, achieving state-of-the-art BLEU scores on WMT 2014 English-to-German translation [1](cite:1 "p.7,§1") while also serving as the backbone for numerous downstream applications beyond machine translation.
`;

export const MOCK_REVIEW: ReviewData = {
  markdown: REVIEW_MARKDOWN,
  papers: [
    {
      index: 1,
      id: "mock-1",
      title: "Attention Is All You Need",
      authors: "Vaswani, A., Shazeer, N., Parmar, N., et al.",
      year: "2017",
      journal: "Advances in Neural Information Processing Systems",
      citedIn: ["Self-Attention Mechanisms", "Transfer Learning and Fine-tuning"],
      claims: [
        { text: "The Transformer relies entirely on self-attention to compute representations, dispensing with recurrence and convolutions.", page: 1, paragraph: 1, themeId: "t1" },
        { text: "Multi-head attention allows the model to jointly attend to information from different representation subspaces.", page: 3, paragraph: 2, themeId: "t1" },
        { text: "The Transformer achieves state-of-the-art BLEU scores on WMT 2014 English-to-German translation.", page: 7, paragraph: 1, themeId: "t2" },
      ],
    },
    {
      index: 2,
      id: "mock-2",
      title: "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
      authors: "Devlin, J., Chang, M.-W., Lee, K., Toutanova, K.",
      year: "2019",
      journal: "Proceedings of NAACL-HLT",
      citedIn: ["Self-Attention Mechanisms", "Transfer Learning and Fine-tuning"],
      claims: [
        { text: "BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context.", page: 1, paragraph: 1, themeId: "t4" },
        { text: "Fine-tuned BERT models achieve state-of-the-art results on eleven NLP tasks.", page: 1, paragraph: 2, themeId: "t5" },
      ],
    },
    {
      index: 3,
      id: "mock-3",
      title: "Scaling Laws for Neural Language Models",
      authors: "Kaplan, J., McCandlish, S., Henighan, T., et al.",
      year: "2020",
      journal: "arXiv preprint arXiv:2001.08361",
      citedIn: ["Scaling and Efficiency"],
      claims: [
        { text: "Language model performance scales as a power-law with model size, dataset size, and compute budget.", page: 2, paragraph: 1, themeId: "t6" },
        { text: "Performance depends strongly on scale and weakly on model shape.", page: 3, paragraph: 1, themeId: "t6" },
        { text: "Larger models are significantly more sample-efficient than smaller models.", page: 4, paragraph: 3, themeId: "t7" },
      ],
    },
  ],
  stats: {
    paperCount: 3,
    themeCount: 3,
    claimCount: 8,
    generationTimeMs: 12_400,
  },
  generatedAt: Date.now(),
};
