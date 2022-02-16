# This file preloads the configured model to the local cache.
import os

from huggingface_hub import snapshot_download

model_name = os.getenv('MODEL', 'google/pegasus-xsum')

print(f"Installing {model_name}...")

snapshot_download(model_name)
