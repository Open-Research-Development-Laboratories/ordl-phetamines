#!/usr/bin/env python3
"""
ORDL Command Post - Docker Image Builder
=========================================

Build script for all sandbox Docker images.

Usage:
    python build_images.py [--push] [--registry REGISTRY]

Options:
    --push          Push images to registry after build
    --registry      Docker registry URL (default: ordl-sandbox)
    --parallel      Build images in parallel

Classification: TOP SECRET//NOFORN//SCI
"""

import os
import sys
import argparse
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ordl.sandbox.builder')

# Image configurations
IMAGES = [
    {
        'name': 'python',
        'tag': '3.11',
        'dockerfile': 'python.Dockerfile',
        'full_name': 'ordl-sandbox-python:3.11',
        'description': 'Python 3.11 with ML packages'
    },
    {
        'name': 'c23',
        'tag': 'gcc-13',
        'dockerfile': 'c23.Dockerfile',
        'full_name': 'ordl-sandbox-c23:gcc-13',
        'description': 'C23 with GCC 13'
    },
    {
        'name': 'java',
        'tag': '21',
        'dockerfile': 'java.Dockerfile',
        'full_name': 'ordl-sandbox-java:21',
        'description': 'Java 21 (OpenJDK)'
    },
    {
        'name': 'javascript',
        'tag': '20',
        'dockerfile': 'javascript.Dockerfile',
        'full_name': 'ordl-sandbox-javascript:20',
        'description': 'Node.js 20'
    },
    {
        'name': 'rust',
        'tag': '1.75',
        'dockerfile': 'rust.Dockerfile',
        'full_name': 'ordl-sandbox-rust:1.75',
        'description': 'Rust 1.75'
    },
    {
        'name': 'go',
        'tag': '1.21',
        'dockerfile': 'go.Dockerfile',
        'full_name': 'ordl-sandbox-go:1.21',
        'description': 'Go 1.21'
    },
]


def run_command(cmd: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, stderr.
    
    Args:
        cmd: Command to run
        cwd: Working directory
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    logger.debug(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for builds
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out after 600 seconds"
    except Exception as e:
        return -1, "", str(e)


def build_image(image_config: dict, docker_dir: str, no_cache: bool = False) -> Tuple[bool, str]:
    """
    Build a single Docker image.
    
    Args:
        image_config: Image configuration dict
        docker_dir: Directory containing Dockerfiles
        no_cache: Whether to use --no-cache
        
    Returns:
        Tuple of (success, message)
    """
    name = image_config['full_name']
    dockerfile = os.path.join(docker_dir, image_config['dockerfile'])
    
    logger.info(f"Building {name}...")
    logger.info(f"  Description: {image_config['description']}")
    
    if not os.path.exists(dockerfile):
        return False, f"Dockerfile not found: {dockerfile}"
    
    cmd = [
        'docker', 'build',
        '-t', name,
        '-f', dockerfile,
        '--label', f'org.ordl.built-at={os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip()}',
        '--label', 'org.ordl.component=sandbox',
        docker_dir
    ]
    
    if no_cache:
        cmd.insert(2, '--no-cache')
    
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code == 0:
        logger.info(f"✓ Successfully built {name}")
        return True, f"Built successfully"
    else:
        error_msg = stderr or stdout
        logger.error(f"✗ Failed to build {name}: {error_msg}")
        return False, error_msg


def push_image(image_name: str) -> Tuple[bool, str]:
    """
    Push a Docker image to registry.
    
    Args:
        image_name: Name of the image to push
        
    Returns:
        Tuple of (success, message)
    """
    logger.info(f"Pushing {image_name}...")
    
    exit_code, stdout, stderr = run_command(['docker', 'push', image_name])
    
    if exit_code == 0:
        logger.info(f"✓ Successfully pushed {image_name}")
        return True, "Pushed successfully"
    else:
        error_msg = stderr or stdout
        logger.error(f"✗ Failed to push {image_name}: {error_msg}")
        return False, error_msg


def build_all_images(docker_dir: str, no_cache: bool = False, parallel: bool = False) -> dict:
    """
    Build all sandbox images.
    
    Args:
        docker_dir: Directory containing Dockerfiles
        no_cache: Whether to use --no-cache
        parallel: Whether to build in parallel
        
    Returns:
        Dict with results
    """
    results = {
        'success': [],
        'failed': [],
        'total': len(IMAGES)
    }
    
    if parallel:
        logger.info(f"Building {len(IMAGES)} images in parallel...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(build_image, img, docker_dir, no_cache): img 
                for img in IMAGES
            }
            
            for future in as_completed(futures):
                img = futures[future]
                try:
                    success, message = future.result()
                    if success:
                        results['success'].append(img['full_name'])
                    else:
                        results['failed'].append({'name': img['full_name'], 'error': message})
                except Exception as e:
                    results['failed'].append({'name': img['full_name'], 'error': str(e)})
    else:
        logger.info(f"Building {len(IMAGES)} images sequentially...")
        for img in IMAGES:
            success, message = build_image(img, docker_dir, no_cache)
            if success:
                results['success'].append(img['full_name'])
            else:
                results['failed'].append({'name': img['full_name'], 'error': message})
    
    return results


def verify_images() -> dict:
    """Verify all images are available locally."""
    results = {'available': [], 'missing': []}
    
    for img in IMAGES:
        name = img['full_name']
        exit_code, _, _ = run_command(['docker', 'images', '-q', name])
        
        if exit_code == 0:
            results['available'].append(name)
        else:
            results['missing'].append(name)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Build ORDL Code Sandbox Docker Images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Build all images
    python build_images.py
    
    # Build without cache
    python build_images.py --no-cache
    
    # Build and push to registry
    python build_images.py --push --registry myregistry.com
    
    # Build in parallel
    python build_images.py --parallel
        """
    )
    
    parser.add_argument('--push', action='store_true',
                        help='Push images to registry after build')
    parser.add_argument('--registry', type=str, default=None,
                        help='Docker registry URL (e.g., myregistry.com)')
    parser.add_argument('--no-cache', action='store_true',
                        help='Build without using cache')
    parser.add_argument('--parallel', action='store_true',
                        help='Build images in parallel')
    parser.add_argument('--verify-only', action='store_true',
                        help='Only verify images exist, do not build')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Find docker_images directory
    script_dir = Path(__file__).parent.absolute()
    docker_dir = script_dir / 'docker_images'
    
    if not docker_dir.exists():
        logger.error(f"Docker images directory not found: {docker_dir}")
        sys.exit(1)
    
    logger.info("ORDL Command Post - Docker Image Builder")
    logger.info("=" * 50)
    
    if args.verify_only:
        logger.info("Verifying images...")
        results = verify_images()
        
        print(f"\nAvailable images ({len(results['available'])}):")
        for img in results['available']:
            print(f"  ✓ {img}")
        
        if results['missing']:
            print(f"\nMissing images ({len(results['missing'])}):")
            for img in results['missing']:
                print(f"  ✗ {img}")
        
        sys.exit(0 if not results['missing'] else 1)
    
    # Build images
    results = build_all_images(str(docker_dir), args.no_cache, args.parallel)
    
    # Print summary
    print("\n" + "=" * 50)
    print("BUILD SUMMARY")
    print("=" * 50)
    print(f"Total: {results['total']}")
    print(f"Successful: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    
    if results['success']:
        print("\nSuccessful builds:")
        for name in results['success']:
            print(f"  ✓ {name}")
    
    if results['failed']:
        print("\nFailed builds:")
        for item in results['failed']:
            print(f"  ✗ {item['name']}: {item['error']}")
    
    # Push images if requested
    if args.push and results['success']:
        print("\n" + "=" * 50)
        print("PUSHING IMAGES")
        print("=" * 50)
        
        for name in results['success']:
            # Tag with registry if specified
            if args.registry:
                registry_name = f"{args.registry}/{name}"
                logger.info(f"Tagging {name} as {registry_name}")
                run_command(['docker', 'tag', name, registry_name])
                push_image(registry_name)
            else:
                push_image(name)
    
    # Exit with error code if any builds failed
    sys.exit(0 if not results['failed'] else 1)


if __name__ == '__main__':
    main()
