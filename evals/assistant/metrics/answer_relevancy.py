"""Answer relevancy: is the assistant response relevant to the question?"""

from deepeval.metrics import AnswerRelevancyMetric


def create_answer_relevancy_metric(model, threshold: float = 0.70):
    """Create an answer relevancy metric for assistant evaluation."""
    return AnswerRelevancyMetric(
        model=model,
        threshold=threshold,
    )
