"""
ORDL Command Post - Dataset Loader
Handles dataset ingestion from multiple sources with format conversion.
"""

import os
import json
import requests
from typing import Iterator, Dict, List, Optional, Callable, Any, Union
from pathlib import Path
from dataclasses import dataclass
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import datasets library
try:
    from datasets import Dataset, load_dataset, load_from_disk
    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False
    logger.warning("HuggingFace datasets library not available. Some features will be limited.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@dataclass
class DatasetInfo:
    """Dataset metadata"""
    name: str
    source: str
    format: str
    num_samples: int
    columns: List[str]
    size_bytes: Optional[int] = None
    description: Optional[str] = None


class DatasetLoader:
    """
    Universal dataset loader supporting multiple sources and formats.
    """
    
    # Format-specific prompt templates
    ALPACA_TEMPLATE = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Response:
{output}"""
    
    ALPACA_WITH_INPUT_TEMPLATE = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Input:
{input}

### Response:
{output}"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/ordl/datasets")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._format_converters = {
            'alpaca': self._convert_alpaca,
            'sharegpt': self._convert_sharegpt,
            'openai': self._convert_openai,
            'raw': self._convert_raw,
            'conversation': self._convert_conversation
        }
    
    def load_from_huggingface(
        self,
        dataset_name: str,
        subset: Optional[str] = None,
        split: str = "train",
        streaming: bool = False,
        token: Optional[str] = None,
        **kwargs
    ) -> Union[Dataset, Iterator[Dict]]:
        """
        Load dataset from HuggingFace Hub.
        
        Args:
            dataset_name: HuggingFace dataset name (e.g., 'yahma/alpaca-cleaned')
            subset: Dataset subset/config name
            split: Dataset split (train/validation/test)
            streaming: Whether to stream the dataset
            token: HuggingFace API token for private datasets
            **kwargs: Additional arguments for load_dataset
        
        Returns:
            Dataset object or iterator for streaming
        """
        if not DATASETS_AVAILABLE:
            raise ImportError("HuggingFace datasets library is required. Install with: pip install datasets")
        
        logger.info(f"Loading dataset from HuggingFace: {dataset_name}")
        
        try:
            dataset = load_dataset(
                dataset_name,
                subset,
                split=split,
                streaming=streaming,
                token=token,
                cache_dir=self.cache_dir,
                **kwargs
            )
            
            logger.info(f"Successfully loaded dataset with {len(dataset) if not streaming else 'streaming'} samples")
            return dataset
            
        except Exception as e:
            logger.error(f"Failed to load dataset from HuggingFace: {e}")
            raise
    
    def load_from_file(
        self,
        file_path: Union[str, Path],
        format: str = "json"
    ) -> Union[Dataset, List[Dict]]:
        """
        Load dataset from local file (JSON, JSONL, CSV, Parquet).
        
        Args:
            file_path: Path to the dataset file
            format: File format (json, jsonl, csv, parquet)
        
        Returns:
            Dataset or list of dictionaries
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        
        logger.info(f"Loading dataset from file: {file_path}")
        
        try:
            if format == "json" or file_path.suffix == ".json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle both list and dict formats
                if isinstance(data, dict):
                    # Try common keys
                    for key in ['data', 'examples', 'samples', 'train']:
                        if key in data:
                            data = data[key]
                            break
                
                if DATASETS_AVAILABLE:
                    return Dataset.from_list(data)
                return data
            
            elif format == "jsonl" or file_path.suffix in [".jsonl", ".jsonlines"]:
                data = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
                
                if DATASETS_AVAILABLE:
                    return Dataset.from_list(data)
                return data
            
            elif format == "csv" or file_path.suffix == ".csv":
                if not PANDAS_AVAILABLE:
                    raise ImportError("pandas is required for CSV loading")
                
                df = pd.read_csv(file_path)
                if DATASETS_AVAILABLE:
                    return Dataset.from_pandas(df)
                return df.to_dict('records')
            
            elif format == "parquet" or file_path.suffix == ".parquet":
                if not PANDAS_AVAILABLE:
                    raise ImportError("pandas is required for Parquet loading")
                
                df = pd.read_parquet(file_path)
                if DATASETS_AVAILABLE:
                    return Dataset.from_pandas(df)
                return df.to_dict('records')
            
            else:
                raise ValueError(f"Unsupported file format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to load dataset from file: {e}")
            raise
    
    def load_from_url(
        self,
        url: str,
        format: str = "json",
        timeout: int = 300
    ) -> Union[Dataset, List[Dict]]:
        """
        Download and load dataset from URL.
        
        Args:
            url: URL to the dataset
            format: Expected file format
            timeout: Download timeout in seconds
        
        Returns:
            Dataset or list of dictionaries
        """
        logger.info(f"Downloading dataset from URL: {url}")
        
        try:
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Generate cache filename from URL
            cache_filename = url.split('/')[-1].split('?')[0] or "dataset.json"
            cache_path = Path(self.cache_dir) / cache_filename
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")
            
            logger.info(f"Downloaded to: {cache_path}")
            
            # Load from cache
            return self.load_from_file(cache_path, format)
            
        except Exception as e:
            logger.error(f"Failed to download dataset from URL: {e}")
            raise
    
    def convert_format(
        self,
        dataset: Union[Dataset, List[Dict]],
        source_format: str,
        target_format: str = "text",
        **format_kwargs
    ) -> Union[Dataset, List[Dict]]:
        """
        Convert dataset from one format to another.
        
        Args:
            dataset: Source dataset
            source_format: Source format (alpaca, sharegpt, raw, etc.)
            target_format: Target format (usually 'text' for training)
            **format_kwargs: Additional format-specific arguments
        
        Returns:
            Converted dataset
        """
        if source_format not in self._format_converters:
            raise ValueError(f"Unsupported source format: {source_format}. "
                           f"Supported: {list(self._format_converters.keys())}")
        
        converter = self._format_converters[source_format]
        
        if DATASETS_AVAILABLE and isinstance(dataset, Dataset):
            return dataset.map(
                lambda x: {"text": converter(x, **format_kwargs)},
                remove_columns=dataset.column_names
            )
        else:
            # Handle list of dicts
            return [{"text": converter(item, **format_kwargs)} for item in dataset]
    
    def _convert_alpaca(self, example: Dict, **kwargs) -> str:
        """Convert Alpaca format to text"""
        instruction = example.get('instruction', '')
        input_text = example.get('input', '')
        output = example.get('output', '')
        
        if input_text and input_text.strip():
            return self.ALPACA_WITH_INPUT_TEMPLATE.format(
                instruction=instruction,
                input=input_text,
                output=output
            )
        else:
            return self.ALPACA_TEMPLATE.format(
                instruction=instruction,
                output=output
            )
    
    def _convert_sharegpt(self, example: Dict, **kwargs) -> str:
        """Convert ShareGPT format to text"""
        conversations = example.get('conversations', example.get('messages', []))
        
        # Handle different role names
        role_mapping = kwargs.get('role_mapping', {
            'human': 'user',
            'user': 'user',
            'gpt': 'assistant',
            'assistant': 'assistant',
            'system': 'system'
        })
        
        formatted = []
        for turn in conversations:
            role = role_mapping.get(turn.get('from', turn.get('role', '')), 'user')
            content = turn.get('value', turn.get('content', ''))
            
            if role == 'system':
                formatted.append(f"System: {content}")
            elif role == 'user':
                formatted.append(f"User: {content}")
            elif role == 'assistant':
                formatted.append(f"Assistant: {content}")
        
        return "\n\n".join(formatted)
    
    def _convert_openai(self, example: Dict, **kwargs) -> str:
        """Convert OpenAI format to text"""
        messages = example.get('messages', [])
        formatted = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                formatted.append(f"System: {content}")
            elif role == 'user':
                formatted.append(f"User: {content}")
            elif role == 'assistant':
                formatted.append(f"Assistant: {content}")
        
        return "\n\n".join(formatted)
    
    def _convert_raw(self, example: Dict, text_column: str = "text", **kwargs) -> str:
        """Extract raw text from specified column"""
        return example.get(text_column, "")
    
    def _convert_conversation(self, example: Dict, **kwargs) -> str:
        """Convert conversation format to text"""
        turns = example.get('turns', example.get('conversation', []))
        formatted = []
        
        for turn in turns:
            speaker = turn.get('speaker', turn.get('role', 'Unknown'))
            text = turn.get('text', turn.get('content', ''))
            formatted.append(f"{speaker}: {text}")
        
        return "\n\n".join(formatted)
    
    def preprocess_dataset(
        self,
        dataset: Union[Dataset, List[Dict]],
        tokenizer: Any,
        max_length: int = 2048,
        truncation: bool = True,
        padding: bool = False,
        add_special_tokens: bool = True
    ) -> Union[Dataset, List[Dict]]:
        """
        Preprocess and tokenize dataset.
        
        Args:
            dataset: Input dataset
            tokenizer: HuggingFace tokenizer
            max_length: Maximum sequence length
            truncation: Whether to truncate sequences
            padding: Whether to pad sequences
            add_special_tokens: Whether to add special tokens
        
        Returns:
            Preprocessed dataset
        """
        def tokenize_function(examples):
            texts = examples.get('text', [])
            
            # Tokenize
            tokenized = tokenizer(
                texts,
                truncation=truncation,
                max_length=max_length,
                padding='max_length' if padding else False,
                add_special_tokens=add_special_tokens,
                return_tensors=None
            )
            
            # Add labels for language modeling
            tokenized['labels'] = tokenized['input_ids'].copy()
            
            return tokenized
        
        if DATASETS_AVAILABLE and isinstance(dataset, Dataset):
            return dataset.map(
                tokenize_function,
                batched=True,
                remove_columns=dataset.column_names,
                desc="Tokenizing"
            )
        else:
            # Manual tokenization for list
            result = []
            for item in dataset:
                text = item.get('text', '')
                tokenized = tokenizer(
                    text,
                    truncation=truncation,
                    max_length=max_length,
                    padding='max_length' if padding else False,
                    add_special_tokens=add_special_tokens,
                    return_tensors='pt'
                )
                result.append({
                    'input_ids': tokenized['input_ids'].squeeze().tolist(),
                    'attention_mask': tokenized['attention_mask'].squeeze().tolist(),
                    'labels': tokenized['input_ids'].squeeze().tolist()
                })
            return result
    
    def split_dataset(
        self,
        dataset: Union[Dataset, List[Dict]],
        train_ratio: float = 0.9,
        val_ratio: float = 0.1,
        test_ratio: float = 0.0,
        seed: int = 42
    ) -> Dict[str, Union[Dataset, List[Dict]]]:
        """
        Split dataset into train/validation/test sets.
        
        Args:
            dataset: Input dataset
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            test_ratio: Test set ratio
            seed: Random seed
        
        Returns:
            Dictionary with split datasets
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
            "Ratios must sum to 1.0"
        
        if DATASETS_AVAILABLE and isinstance(dataset, Dataset):
            dataset = dataset.shuffle(seed=seed)
            total = len(dataset)
            
            train_end = int(train_ratio * total)
            val_end = train_end + int(val_ratio * total)
            
            splits = {
                'train': dataset.select(range(0, train_end))
            }
            
            if val_ratio > 0:
                splits['validation'] = dataset.select(range(train_end, val_end))
            
            if test_ratio > 0:
                splits['test'] = dataset.select(range(val_end, total))
            
            return splits
        else:
            import random
            random.seed(seed)
            shuffled = dataset.copy()
            random.shuffle(shuffled)
            
            total = len(shuffled)
            train_end = int(train_ratio * total)
            val_end = train_end + int(val_ratio * total)
            
            splits = {
                'train': shuffled[:train_end]
            }
            
            if val_ratio > 0:
                splits['validation'] = shuffled[train_end:val_end]
            
            if test_ratio > 0:
                splits['test'] = shuffled[val_end:]
            
            return splits
    
    def get_dataset_info(self, dataset: Union[Dataset, List[Dict]]) -> DatasetInfo:
        """Get dataset information"""
        if DATASETS_AVAILABLE and isinstance(dataset, Dataset):
            return DatasetInfo(
                name="Loaded Dataset",
                source="unknown",
                format="huggingface",
                num_samples=len(dataset),
                columns=list(dataset.column_names),
                description="HuggingFace Dataset"
            )
        else:
            return DatasetInfo(
                name="Loaded Dataset",
                source="unknown",
                format="list",
                num_samples=len(dataset),
                columns=list(dataset[0].keys()) if dataset else [],
                description="List of dictionaries"
            )


def load_dataset_for_training(
    config: Any,
    tokenizer: Any = None
) -> Union[Dataset, List[Dict]]:
    """
    Convenience function to load dataset based on training config.
    
    Args:
        config: TrainingConfig object
        tokenizer: Optional tokenizer for preprocessing
    
    Returns:
        Loaded and preprocessed dataset
    """
    loader = DatasetLoader()
    
    # Load based on source
    if config.dataset_source == "huggingface":
        dataset = loader.load_from_huggingface(config.dataset_path)
    elif config.dataset_source == "url":
        dataset = loader.load_from_url(config.dataset_path)
    else:  # local
        dataset = loader.load_from_file(config.dataset_path)
    
    # Convert format if needed
    if config.dataset_format.value != "raw":
        dataset = loader.convert_format(
            dataset,
            config.dataset_format.value,
            "text"
        )
    
    # Tokenize if tokenizer provided
    if tokenizer:
        dataset = loader.preprocess_dataset(
            dataset,
            tokenizer,
            max_length=config.max_seq_length
        )
    
    return dataset


# Example usage
if __name__ == "__main__":
    loader = DatasetLoader()
    
    # Example: Load from HuggingFace
    # dataset = loader.load_from_huggingface("yahma/alpaca-cleaned")
    
    # Example: Convert Alpaca format
    # converted = loader.convert_format(dataset, "alpaca", "text")
    
    print("DatasetLoader initialized successfully")
