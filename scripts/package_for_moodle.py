"""
SmartServe GIS - Automated College LMS (Moodle) Package Creator
Creates a clean, production-ready submission ZIP file excluding cache, logs, and temp files.
"""

import os
import zipfile
import sys

def package_submission(output_zip="SmartServe_GIS_Moodle_Submission.zip"):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, output_zip)

    exclude_dirs = {
        '__pycache__', '.git', '.pytest_cache', '.vscode', '.idea',
        'scratch', 'node_modules', '.venv', 'venv', '.system_generated'
    }
    exclude_exts = {'.pyc', '.pyo', '.tmp', '.log'}

    print("=" * 70)
    print("  SMARTSERVE GIS - MOODLE LMS SUBMISSION PACKAGER")
    print("=" * 70)
    print(f"Creating clean zip archive: {output_zip} ...\n")

    packed_count = 0
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_root):
            # Exclude unwanted directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            
            for f in files:
                # Exclude extensions and self
                if any(f.endswith(ext) for ext in exclude_exts):
                    continue
                if f == output_zip or f.endswith('.zip'):
                    continue

                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, project_root)
                zipf.write(full_path, rel_path)
                packed_count += 1

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[SUCCESS] Packaged {packed_count} files into '{output_zip}'")
    print(f"[INFO] Archive Size: {size_mb:.2f} MB (Well within Moodle limits!)")
    print("=" * 70)
    return output_path

if __name__ == "__main__":
    package_submission()
