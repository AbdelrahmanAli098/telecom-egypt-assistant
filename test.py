import torch

# 1. Check if CUDA is available
print(f"CUDA Available: {torch.cuda.is_available()}")

# 2. Get the CUDA version bundled with PyTorch
print(f"CUDA Version: {torch.version.cuda}")

# 3. Get your GPU name (if available)
if torch.cuda.is_available():
    print(f"Current Device: {torch.cuda.current_device()}")
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")
