from datasets import Dataset, load_dataset

DATASET_NAME = "justindal/leetcode-python-dataset"
DATASET_CONFIG = "benchmark"
DATASET_SPLIT = "benchmark"


def get_problems(
    dataset_name: str = DATASET_NAME,
    config: str = DATASET_CONFIG,
    split: str = DATASET_SPLIT,
    problem_type: str = "test",
) -> Dataset:
    dataset = load_dataset(dataset_name, config)[split]
    return dataset.filter(lambda row: row["type"] == problem_type)
