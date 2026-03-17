from datasets import Dataset, load_dataset

DATASET_NAME = "newfacade/LeetCodeDataset"
DATASET_SPLIT = "test"


def get_problems(
    dataset_name: str = DATASET_NAME, split: str = DATASET_SPLIT
) -> Dataset:
    dataset = load_dataset(dataset_name)
    return dataset[split]
