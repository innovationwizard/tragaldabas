#!/usr/bin/env python3
"""
Generate a secure JWT secret key for Tragaldabas

Usage:
    python generate_jwt_secret.py
    python generate_jwt_secret.py --add-to-env
"""

import secrets
import argparse
from pathlib import Path


def generate_secret_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure random secret key
    
    Args:
        length: Length of the key in bytes (will be URL-safe encoded)
        
    Returns:
        URL-safe base64 encoded secret key
    """
    return secrets.token_urlsafe(length)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a secure JWT secret key"
    )
    parser.add_argument(
        '--add-to-env',
        action='store_true',
        help='Add the key to .env file (creates if not exists)'
    )
    parser.add_argument(
        '--length',
        type=int,
        default=64,
        help='Key length in bytes (default: 64)'
    )
    
    args = parser.parse_args()
    
    # Generate key
    secret_key = generate_secret_key(args.length)
    
    print(f"Generated JWT Secret Key:")
    print(f"JWT_SECRET_KEY={secret_key}")
    print()
    print("Add this to your .env file:")
    print(f"  JWT_SECRET_KEY={secret_key}")
    print()
    print("⚠️  IMPORTANT:")
    print("  - Keep this key secret and never commit it to version control")
    print("  - Use different keys for development and production")
    print("  - Rotate keys periodically for enhanced security")
    
    # Add to .env if requested
    if args.add_to_env:
        env_file = Path('.env')
        
        # Read existing .env if it exists
        existing_content = ""
        if env_file.exists():
            existing_content = env_file.read_text()
            # Check if JWT_SECRET_KEY already exists
            if 'JWT_SECRET_KEY=' in existing_content:
                print()
                print("⚠️  JWT_SECRET_KEY already exists in .env file")
                response = input("Overwrite? (y/N): ").strip().lower()
                if response != 'y':
                    print("Aborted.")
                    return
                # Remove old key
                lines = existing_content.split('\n')
                existing_content = '\n'.join(
                    line for line in lines
                    if not line.startswith('JWT_SECRET_KEY=')
                )
        
        # Add new key
        new_line = f"JWT_SECRET_KEY={secret_key}\n"
        env_file.write_text(existing_content + new_line)
        print()
        print(f"✓ Added to {env_file}")


if __name__ == '__main__':
    main()

