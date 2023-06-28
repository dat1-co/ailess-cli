def get_cuda_version():
    # Try to get CUDA version from PyTorch
    try:
        import torch

        print("CUDA version from PyTorch: ", torch.version.cuda)
        return torch.version.cuda
    except ImportError:
        pass
    # Try to get CUDA version from TensorFlow
    try:
        import tensorflow as tf
        from tensorflow.python.platform.build_info import build_info

        print("CUDA version from TensorFlow: ", build_info["cuda_version"])
        return build_info["cuda_version"]
    except ImportError:
        pass
    print("CUDA version not found within pytorch or tensorflow")
    return None
