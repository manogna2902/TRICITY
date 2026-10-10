import pytest
import pandas as pd
from services.data_analyzer import DataAnalyzer
from services.quality_score import QualityScoreEngine


def test_perfect_dataset_score():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "age": [25, 30, 35, 40, 45]
    })
    analysis = DataAnalyzer(df).analyze()
    score = QualityScoreEngine.calculate(analysis)

    assert score["overall_score"] == 100.0
    assert score["grade"] == "A"
    assert score["status"] == "Excellent"
    assert score["breakdown"]["missing"]["penalty"] == 0.0
    assert score["breakdown"]["duplicates"]["penalty"] == 0.0


def test_dirty_dataset_penalties():
    df = pd.DataFrame({
        "name": [" Alice ", "Bob", "Bob", None],
        "age": ["twenty", "30", "30", "$45"]
    })
    analysis = DataAnalyzer(df).analyze()
    score = QualityScoreEngine.calculate(analysis)

    assert score["overall_score"] < 100.0
    assert score["breakdown"]["missing"]["penalty"] > 0
    assert score["breakdown"]["duplicates"]["penalty"] > 0
    assert score["breakdown"]["formatting"]["penalty"] > 0
    assert score["breakdown"]["invalid"]["penalty"] > 0


def test_empty_dataset_score():
    df = pd.DataFrame()
    analysis = DataAnalyzer(df).analyze()
    score = QualityScoreEngine.calculate(analysis)

    assert score["overall_score"] == 0.0
    assert score["grade"] == "F"
    assert score["status"] == "Empty Dataset"


def test_weights_sum_to_one():
    weights = QualityScoreEngine.DEFAULT_WEIGHTS
    assert sum(weights.values()) == 1.0
