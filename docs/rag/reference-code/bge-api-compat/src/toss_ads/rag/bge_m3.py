"""CPU dense-only adapter for the BGE-M3 embedding model."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any


BGE_M3_MODEL = "BAAI/bge-m3"
BGE_M3_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


class BgeM3Embedder:
    """Encode text with the dense output from FlagEmbedding's BGE-M3 model."""

    dimension = 1024

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        max_length: int = 128,
        batch_size: int = 16,
        *,
        model: Any | None = None,
        model_revision: str | None = None,
        revision: str | None = None,
        cache_dir: str | None = None,
    ) -> None:
        if (
            not model_name.strip()
            or max_length < 1
            or batch_size < 1
            or (revision is not None and not revision.strip())
            or (cache_dir is not None and not cache_dir.strip())
        ):
            raise ValueError("invalid_embedding_configuration")
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        if model is None:
            from FlagEmbedding import BGEM3FlagModel
            from huggingface_hub import snapshot_download
            import torch

            download_args = {"repo_id": model_name}
            if revision is not None:
                download_args["revision"] = revision
            if cache_dir is not None:
                download_args["cache_dir"] = cache_dir
            snapshot_path = Path(snapshot_download(**download_args))
            self.model_revision = snapshot_path.name
            self._model = BGEM3FlagModel(
                str(snapshot_path), use_fp16=False, devices=["cpu"]
            )
            self.cpu_thread_count = torch.get_num_threads()
        else:
            self._model = model
            self.model_revision = model_revision or "injected"
            self.cpu_thread_count = None

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        encoded = self._model.encode(
            list(texts),
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        dense_vectors = encoded["dense_vecs"]
        if hasattr(dense_vectors, "detach"):
            dense_vectors = dense_vectors.detach().cpu()
        if hasattr(dense_vectors, "tolist"):
            dense_vectors = dense_vectors.tolist()
        if len(dense_vectors) != len(texts):
            raise ValueError("embedding_count_mismatch")

        vectors: list[list[float]] = []
        for vector in dense_vectors:
            if hasattr(vector, "tolist"):
                vector = vector.tolist()
            if len(vector) != self.dimension:
                raise ValueError("embedding_dimension_mismatch")
            vectors.append([float(value) for value in vector])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
