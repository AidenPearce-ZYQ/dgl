import os
import tempfile

import numpy as np
import pydantic
import pytest
import torch

from dgl import graphbolt as gb


def to_on_disk_tensor(test_dir, name, t):
    path = os.path.join(test_dir, name + ".npy")
    t = t.numpy()
    np.save(path, t)
    # The Pytorch tensor is a view of the numpy array on disk, which does not
    # consume memory.
    t = torch.as_tensor(np.load(path, mmap_mode="r+"))
    return t


@pytest.mark.parametrize("in_memory", [True, False])
def test_torch_based_feature(in_memory):
    with tempfile.TemporaryDirectory() as test_dir:
        a = torch.tensor([[1, 2, 3], [4, 5, 6]])
        b = torch.tensor([[[1, 2], [3, 4]], [[4, 5], [6, 7]]])
        if not in_memory:
            a = to_on_disk_tensor(test_dir, "a", a)
            b = to_on_disk_tensor(test_dir, "b", b)

        feature_a = gb.TorchBasedFeature(a)
        feature_b = gb.TorchBasedFeature(b)

        # Read the entire feature.
        assert torch.equal(
            feature_a.read(), torch.tensor([[1, 2, 3], [4, 5, 6]])
        )
        assert torch.equal(
            feature_b.read(), torch.tensor([[[1, 2], [3, 4]], [[4, 5], [6, 7]]])
        )
        # Read the feature with ids.
        assert torch.equal(
            feature_a.read(torch.tensor([0])),
            torch.tensor([[1, 2, 3]]),
        )
        assert torch.equal(
            feature_b.read(torch.tensor([1])),
            torch.tensor([[[4, 5], [6, 7]]]),
        )
        # Update the feature with ids.
        feature_a.update(torch.tensor([[0, 1, 2]]), torch.tensor([0]))
        assert torch.equal(
            feature_a.read(), torch.tensor([[0, 1, 2], [4, 5, 6]])
        )
        feature_b.update(torch.tensor([[[1, 2], [3, 4]]]), torch.tensor([1]))
        assert torch.equal(
            feature_b.read(), torch.tensor([[[1, 2], [3, 4]], [[1, 2], [3, 4]]])
        )

        with pytest.raises(IndexError):
            feature_a.read(torch.tensor([0, 1, 2, 3]))

        # For windows, the file is locked by the numpy.load. We need to delete
        # it before closing the temporary directory.
        a = b = None
        feature_a = feature_b = None


def write_tensor_to_disk(dir, name, t, fmt="torch"):
    if fmt == "torch":
        torch.save(t, os.path.join(dir, name + ".pt"))
    elif fmt == "numpy":
        t = t.numpy()
        np.save(os.path.join(dir, name + ".npy"), t)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


@pytest.mark.parametrize("in_memory", [True, False])
def test_torch_based_feature_store(in_memory):
    with tempfile.TemporaryDirectory() as test_dir:
        a = torch.tensor([[1, 2, 4], [2, 5, 3]])
        b = torch.tensor([[[1, 2], [3, 4]], [[2, 5], [3, 4]]])
        write_tensor_to_disk(test_dir, "a", a, fmt="torch")
        write_tensor_to_disk(test_dir, "b", b, fmt="numpy")
        feature_data = [
            gb.OnDiskFeatureData(
                domain="node",
                type="paper",
                name="a",
                format="torch",
                path=os.path.join(test_dir, "a.pt"),
                in_memory=True,
            ),
            gb.OnDiskFeatureData(
                domain="edge",
                type="paper:cites:paper",
                name="b",
                format="numpy",
                path=os.path.join(test_dir, "b.npy"),
                in_memory=in_memory,
            ),
        ]
        feature_store = gb.TorchBasedFeatureStore(feature_data)
        assert torch.equal(
            feature_store.read("node", "paper", "a"),
            torch.tensor([[1, 2, 4], [2, 5, 3]]),
        )
        assert torch.equal(
            feature_store.read("edge", "paper:cites:paper", "b"),
            torch.tensor([[[1, 2], [3, 4]], [[2, 5], [3, 4]]]),
        )

        # For windows, the file is locked by the numpy.load. We need to delete
        # it before closing the temporary directory.
        a = b = None
        feature_store = None

        # ``domain`` should be enum.
        with pytest.raises(pydantic.ValidationError):
            _ = gb.OnDiskFeatureData(
                domain="invalid",
                type="paper",
                name="a",
                format="torch",
                path=os.path.join(test_dir, "a.pt"),
                in_memory=True,
            )

        # ``type`` could be null.
        feature_data = [
            gb.OnDiskFeatureData(
                domain="node",
                name="a",
                format="torch",
                path=os.path.join(test_dir, "a.pt"),
                in_memory=True,
            ),
        ]
        feature_store = gb.TorchBasedFeatureStore(feature_data)
        assert torch.equal(
            feature_store.read("node", None, "a"),
            torch.tensor([[1, 2, 4], [2, 5, 3]]),
        )
        feature_store = None
