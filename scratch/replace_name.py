import os
import glob

def replace_in_files(root_dir, old_str, new_str, ignore_dirs):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for filename in filenames:
            if not filename.endswith(('.tsx', '.ts', '.js', '.jsx', '.html', '.css', '.md', '.py', '.txt')): 
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if old_str in content:
                    content = content.replace(old_str, new_str)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Replaced in {filepath}")
            except Exception as e:
                pass

if __name__ == "__main__":
    ignore_dirs = {'.git', 'node_modules', '__pycache__', 'venv', 'dist', '.freebuff', '.pytest_cache'}
    replace_in_files(r'D:\Hackathons\SynapseLM', 'SynapseLM', 'SynapseLM', ignore_dirs)
    replace_in_files(r'D:\Hackathons\SynapseLM', 'synapselm', 'synapselm', ignore_dirs)
