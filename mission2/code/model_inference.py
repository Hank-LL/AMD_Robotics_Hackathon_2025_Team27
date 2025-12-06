import subprocess
import os
from huggingface_hub import snapshot_download

class ModelInference:
    def __init__(self, model_paths, robot_port='/dev/ttyACM0', robot_id='my_awsome_follower_arm',
                cameras=None, run_root=None, cache_dir=None):
        # Dictionary mapping model names to HuggingFace repository IDs
        self.model_paths = model_paths
        self.robot_port = robot_port
        self.robot_id = robot_id
        # Camera configuration (default value)
        self.cameras = cameras or "{top: {type: opencv, index_or_path: 8, width: 640, height: 480, fps: 30}, wrist: {type: opencv, index_or_path: 10, width: 640, height: 480, fps: 30}}"
        # Dataset save directory
        self.run_root = run_root or os.path.join(os.getcwd(), "eval_lerobot_dataset")
        # Model cache directory (uses HuggingFace default cache if None)
        self.cache_dir = cache_dir
        # Local paths for cached models
        self.cached_model_paths = {}

    def cache_models(self, model_names=None):
        """
        Pre-download and cache models from HuggingFace
        model_names: List of model names to cache (all models if None)
        """
        if model_names is None:
            model_names = list(self.model_paths.keys())
        
        for model_name in model_names:
            if model_name not in self.model_paths:
                print(f"Warning: Model {model_name} is not registered")
                continue
            
            hf_repo_id = self.model_paths[model_name]
            print(f"Caching model: {model_name} ({hf_repo_id})")
            
            try:
                # Download model from HuggingFace Hub
                local_path = snapshot_download(
                    repo_id=hf_repo_id,
                    cache_dir=self.cache_dir,
                    local_dir=os.path.join(self.cache_dir, model_name) if self.cache_dir else None,
                )
                self.cached_model_paths[model_name] = local_path
                print(f"✓ Cache complete: {local_path}")
            except Exception as e:
                print(f"✗ Cache failed {model_name}: {e}")
        
        return self.cached_model_paths

    def run_inference(self, model_name, task="Serve ordered sushi", repo_id=None, 
                    episode_time_s=40, num_episodes=1, display_data=True):
        if model_name not in self.model_paths:
            raise ValueError(f"Model {model_name} is not available.")
        
        hf_repo_id = self.model_paths[model_name]
        hf_user = os.environ.get('HF_USER', 'user')
        if repo_id is None:
            repo_id = f"{hf_user}/eval_{model_name}"

        dataset_path = os.path.join(self.run_root, repo_id)
        resume = os.path.exists(dataset_path)

        # Create inference command
        command = [
            "lerobot-record",
            "--robot.type=so101_follower",
            f"--robot.port={self.robot_port}",
            f"--robot.id={self.robot_id}",
            f"--robot.cameras={self.cameras}",
            f"--dataset.single_task={task}",
            f"--dataset.repo_id={repo_id}",
            f"--dataset.root={self.run_root}",
            f"--dataset.episode_time_s={episode_time_s}",
            f"--dataset.num_episodes={num_episodes}",
            f"--policy.path={hf_repo_id}",
            "--dataset.push_to_hub=false",
            f"--display_data={str(display_data).lower()}",
            f"--resume=true"  # {str(resume).lower()}"
        ]
        
        print(f"Running inference for {model_name}...")
        print(f"HuggingFace model: {hf_repo_id}")
        subprocess.run(command, env=os.environ.copy())